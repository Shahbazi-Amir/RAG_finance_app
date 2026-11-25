"""Isolated ASGI routes for Product-session History, Fixture send and revoke.

Uses original History product.v1 implementation and DB 005/004 in ONE
transaction on the actual history_app connection, not a FastAPI dependency
override or browser-selected actor. CI-only configuration and runner mTLS.
The answer producer is offline. These routes are not deployable as staging Auth.
"""
from __future__ import annotations

import json
import os
import re
import sqlite3
import time
import threading
from pathlib import Path

import psycopg
from fastapi import BackgroundTasks, FastAPI, Request
from fastapi.responses import JSONResponse
from jsonschema import ValidationError
from starlette.concurrency import run_in_threadpool
from psycopg import IsolationLevel
from psycopg.rows import dict_row

from apps.api import history_api as history
from apps.api.product_message_fixture import answer_from_fixture
from src.phase3.rag_runtime.staging_no_dispatch import prepare_post_commit_no_dispatch
from src.phase3.rag_runtime.claim_citation_graph import (
    CitationGraphDenied, inspect_answer_citation_graph,
)
from src.phase3.rag_runtime.dispatch_claim_bridge import (
    DispatchClaimDenied, claim_within_signed_t2,
    after_definitive_commit, owner_scoped_claim_status, flag_reporter_unknown,
)
from src.phase3.rag_runtime.dispatch_claim_test_stub import CountOnlyGatewayStub
from src.phase3.rag_runtime.staging_invited_result_fixture import (
    InvitedBinding, FixedInvitedGatewayStub, PrivateFixtureResultLedger,
    VERSION as INVITED_RESULT_VERSION, WARNING as INVITED_WARNING,
    session_ref_digest,
)
from src.phase3.rag_runtime.staging_invited_result_contract import (
    validate_ci_invited_result,
)
from src.phase3.rag_runtime.no_dispatch_handler import NoDispatchHandler
from src.phase3.rag_runtime.staging_preflight import PreflightDenied
from src.phase3.rag_runtime.retrieved_sources import (
    CONTRACT as SOURCES_CONTRACT, CHUNKS_SHA256, ENGINE_SHA256,
)
from src.phase3.rag_runtime.staging_service_bootstrap import (
    PrivateStagingEngineConfig, build_private_no_dispatch_handler,
)
from src.phase3.auth.staging_service_profile import (
    PrivateStagingProfile, StagingConfigDenied, db_attributes_approved,
)
from src.phase3.auth.service_proof import (
    BFFServiceVerifier, TrustRejected, assertion_from_asgi_headers, wire_request,
)
from src.phase3.auth.private_http_no_store import PrivateHttpNoStore
from src.phase3.auth.transactional_admission import (
    AdmissionSerializationUnavailable, protected_transaction,
)
from src.phase3.storage.postgres import auth_session
# Use the same repository module as History, including its exception classes.
from repository import finalize_t3, mark_attempt, start_t2
from src.phase3.storage.postgres.service_replay import PostgresDurableReplayStore

app = FastAPI(title="Product Session API H1 isolated", docs_url=None,
              redoc_url=None, openapi_url=None)
# Defense-in-depth: private responses stay uncached even for framework 4xx.
app.add_middleware(PrivateHttpNoStore)
_REPLAY = PostgresDurableReplayStore()
# Server-injected only after Ops verifies runner CLI/digest and DB authority.
# An environment toggle alone NEVER installs or authorizes this handler.
_SERVER_NO_DISPATCH_TASK = None
# Optional network-free CI-only Gateway counter. No production dispatch client.
_CI_CLAIM_STUB = None
_CI_DISPATCH_REPORTER_DSN = None
# CI-only fixed synthetic response receipt, never Product History or private staging.
_CI_INVITED_RESULT_STORE = None
# Only explicitly injected from a trusted Ops startup; never from an HTTP/env toggle.
_PRIVATE_STAGING_PROFILE = None
_PRIVATE_STAGING_VERIFIER = None
_REVOKE_PATH = b"/internal/auth/session/v1/revoke-one"
_HISTORY_PATH = b"/v1/conversations"
_SEND_PATH = b"/v1/messages"
_STATUS_PATH = b"/v1/message-requests/status"
_ENGINE_STATUS_PATH = b"/v1/message-requests/engine-status"
_RETRIEVED_SOURCES_PATH = b"/v1/message-requests/retrieved-sources"
_CLAIM_TEST_STATUS_PATH = b"/v1/message-requests/claim-test-status"
_INVITED_RESULT_PATH = b"/v1/message-requests/invited-live-result"
_CONVERSATION_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}")
_UUID = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$")
_SESSION_ROLES = {"history": "history_app", "revoke": "auth_revoker"}


def _config():
    if _PRIVATE_STAGING_PROFILE is not None:
        return _PRIVATE_STAGING_VERIFIER
    if os.getenv("CI") != "true" or os.getenv("GITHUB_ACTIONS") != "true":
        raise RuntimeError("ISOLATED_CI_ONLY")
    path = os.environ.get("API_PRODUCT_PROOF_PUBLIC_KEY_PATH", "")
    if not path.startswith("/tmp/") or ".." in path:
        raise RuntimeError("PRODUCT_PROOF_CONFIG")
    issuer = os.getenv("API_PRODUCT_PROOF_ISSUER", "")
    audience = os.getenv("API_PRODUCT_PROOF_AUDIENCE", "")
    kid = os.getenv("API_PRODUCT_PROOF_KID", "")
    if not kid or not re.fullmatch(r"[A-Za-z0-9_.-]{1,80}", kid):
        raise RuntimeError("PRODUCT_PROOF_CONFIG")
    return BFFServiceVerifier(issuer=issuer, audience=audience,
                              public_keys={kid: Path(path).read_bytes()})


def _conn(operation: str):
    if operation not in _SESSION_ROLES:
        raise RuntimeError("AUTH_INVALID_ROLE")
    key = "DB_APP_DSN" if operation == "history" else "AUTH_REVOKER_DSN"
    dsn = (_PRIVATE_STAGING_PROFILE.dsn(operation)
           if _PRIVATE_STAGING_PROFILE is not None else os.getenv(key, ""))
    opts = psycopg.conninfo.conninfo_to_dict(dsn)
    if _PRIVATE_STAGING_PROFILE is not None:
        if not db_attributes_approved(opts, operation):
            raise RuntimeError("PRIVATE_STAGING_DB_DENIED")
    elif (opts.get("host") != "127.0.0.1" or opts.get("port") != "5432"
            or opts.get("dbname") != "history_ci"
            or opts.get("user") != _SESSION_ROLES[operation]):
        raise RuntimeError("CI_DSN_NOT_ALLOWED")
    conn = psycopg.connect(dsn, autocommit=True, row_factory=dict_row,
                           connect_timeout=5)
    try:
        role = conn.execute(
            "SELECT rolname,rolsuper,rolbypassrls FROM pg_roles "
            "WHERE rolname=current_user").fetchone()
        if (role is None or role["rolname"] != _SESSION_ROLES[operation]
                or role["rolsuper"] or role["rolbypassrls"]):
            raise RuntimeError("CI_ROLE_DENIED")
        return conn
    except BaseException:
        conn.close()
        raise


def _err(status: int, code: str):
    return JSONResponse(status_code=status,
                        content={"error": code},
                        headers={"Cache-Control": "no-store"})


def _signed_history(request, raw_body, expected_path, action, *, coherent_read=False):
    # Service assertions cannot substitute for real private transport identity.
    if (_PRIVATE_STAGING_PROFILE is not None
            and not _PRIVATE_STAGING_PROFILE.allowed_peer(request.scope)):
        raise TrustRejected()
    if request.scope.get("raw_path") != expected_path:
        raise TrustRejected()
    token = assertion_from_asgi_headers(request.scope)
    method, path, query, body = wire_request(request.scope, raw_body)
    verifier = _config()
    proof = verifier.verify(token, method=method, raw_path=path,
                            raw_query=query, raw_body=body)
    with _conn("history") as conn:
        if coherent_read:
            # 005 writes replay state, so use a writable snapshot. Repository
            # reads must inherit it rather than SET TRANSACTION in a savepoint.
            conn.isolation_level = IsolationLevel.REPEATABLE_READ
        with protected_transaction(
            conn, verifier=verifier, replay_store=_REPLAY,
            compact_assertion=token, method=method,
            raw_path=path, raw_query=query, body=body,
        ) as owner:
            ctx = {"owner": owner, "conn": conn, "request_id": history.uid(),
                   "trace_id": history.uid(), "session_transaction": True,
                   "session_ref_sha256": session_ref_digest(proof.session_ref),
                   "session_epoch": proof.epoch,
                   "session_generation": proof.generation}
            result = action(ctx)
    return proof, result


def _history_error(exc):
    if isinstance(exc, (PreflightDenied, sqlite3.Error)):
        return history._safe_error(
            503, "ENGINE_STATUS_UNAVAILABLE", "technical",
            "History unavailable.")
    if isinstance(exc, AdmissionSerializationUnavailable):
        return history._safe_error(503, "TEMPORARILY_UNAVAILABLE", "technical",
                                   "History unavailable.")
    if isinstance(exc, TrustRejected):
        return history._safe_error(401, "AUTH_REQUIRED", "authorization",
                                   "Authentication required.")
    status, code, category = history._exception_code(exc)
    return history._safe_error(status, code, category, "History unavailable.")


_HISTORY_ERRORS = (PreflightDenied, sqlite3.Error,
                   AdmissionSerializationUnavailable, TrustRejected,
                   history.ApiFailure, history.NotFound,
                   history.Conflict, history.IntegrityAnomaly, ValidationError,
                   psycopg.Error, RuntimeError, OSError, TypeError)


_HISTORY_EVENT_LOCK = threading.Lock()


def _signed_read(request, path, action, *, coherent_read=False):
    # Bounded correlation for ordinary signed History/status reads only.
    # No actor, header, URL, body or exception details enter this event.
    route = ("list" if path == _HISTORY_PATH else
             "status" if path == _STATUS_PATH else
             "detail" if path.startswith(_HISTORY_PATH + b"/") and path.endswith(b"/messages") else None)
    started = time.monotonic_ns()
    correlation = {}
    def observe(ctx):
        if route is not None:
            correlation.update(request_id=ctx["request_id"], trace_id=ctx["trace_id"])
        return action(ctx)
    try:
        _, response = _signed_history(request, b"", path, observe,
                                      coherent_read=coherent_read)
    except _HISTORY_ERRORS as exc:
        response = _history_error(exc)
        if route is not None:
            doc = json.loads(response.body)
            correlation = {k: doc[k] for k in ("request_id", "trace_id")}
    response.headers["Cache-Control"] = "no-store"
    if route is not None:
        assert all(isinstance(correlation.get(k), str) and
                   re.fullmatch(r"[0-9a-f]{32}", correlation[k])
                   for k in ("request_id", "trace_id"))
        response.headers["X-Request-ID"] = correlation["request_id"]
        response.headers["X-Trace-ID"] = correlation["trace_id"]
        event = dict(event="signed_history_read", route=route,
                     status=response.status_code,
                     elapsed_ms=(time.monotonic_ns()-started)//1_000_000,
                     **correlation)
        # A complete structured line is one write, serialized among all
        # signed History reader threads. Never expose actor or raw request.
        with _HISTORY_EVENT_LOCK:
            print("F3_HISTORY_EVENT " + json.dumps(event, sort_keys=True), flush=True)
    return response


@app.get("/v1/conversations")
def session_conversations(request: Request):
    return _signed_read(request, _HISTORY_PATH,
                        lambda ctx: history.conversations(request, ctx))


@app.get("/v1/conversations/{conversation_id}/messages")
def session_messages(conversation_id: str, request: Request):
    if not _CONVERSATION_ID.fullmatch(conversation_id):
        return _history_error(history.NotFound())
    path = _HISTORY_PATH + b"/" + conversation_id.encode("ascii") + b"/messages"
    return _signed_read(request, path,
                        lambda ctx: history.messages(conversation_id, request, ctx),
                        coherent_read=True)


@app.get("/v1/message-requests/status")
def session_message_status(request: Request):
    return _signed_read(request, _STATUS_PATH,
                        lambda ctx: history.status(request, ctx), coherent_read=True)


def install_private_staging_auth(profile: PrivateStagingProfile) -> None:
    """Ops-only explicit injection; real BFF public key and DB roles required.

    No CI flags, injected headers, local fixture, or browser requests authorize
    a production trust profile. Peer verification MUST use trusted TLS state.
    Does not apply DB grants or enable paid Dispatch.
    """
    global _PRIVATE_STAGING_PROFILE, _PRIVATE_STAGING_VERIFIER
    if (not isinstance(profile, PrivateStagingProfile)
            or _PRIVATE_STAGING_PROFILE is not None
            or os.getenv("CI") == "true"
            or os.getenv("GITHUB_ACTIONS") == "true"):
        raise StagingConfigDenied()
    for operation in ("history", "revoke"):
        if not db_attributes_approved(
                psycopg.conninfo.conninfo_to_dict(profile.dsn(operation)),
                operation):
            raise StagingConfigDenied()
    verifier = BFFServiceVerifier(
        issuer=profile.issuer, audience=profile.audience,
        public_keys={profile.kid: profile.load_public_key()})
    if (_SERVER_NO_DISPATCH_TASK is not None
            and _SERVER_NO_DISPATCH_TASK.profile.runner_file_sha256
                != profile.runner_sha256):
        raise StagingConfigDenied()
    _PRIVATE_STAGING_PROFILE = profile
    _PRIVATE_STAGING_VERIFIER = verifier


def install_server_no_dispatch_handler(handler: NoDispatchHandler) -> None:
    """Ops-controlled startup injection, not a client or env-controlled grant.

    The CI-only Auth/DSN guards are intentionally unchanged. A real staging
    ASGI deployment requires separately reviewed session trust/role profile.
    """
    if (not isinstance(handler, NoDispatchHandler)
            or (_PRIVATE_STAGING_PROFILE is not None
                and handler.profile.runner_file_sha256
                    != _PRIVATE_STAGING_PROFILE.runner_sha256)):
        raise PreflightDenied()
    global _SERVER_NO_DISPATCH_TASK
    _SERVER_NO_DISPATCH_TASK = handler


def install_ci_count_only_dispatch(stub: CountOnlyGatewayStub, reporter_dsn: str) -> None:
    """Test harness only; never installs a live network Gateway client.

    CI-only DB must independently provision Migration 011 and reporter role;
    it is never applied to staging here. No browser-controlled injection.
    """
    global _CI_CLAIM_STUB, _CI_DISPATCH_REPORTER_DSN
    if (os.getenv("CI") != "true" or os.getenv("GITHUB_ACTIONS") != "true"
            or os.getenv("API_RUNNER_EXECUTION_MODE") not in {
                "CLAIM_STUB_CI_ONLY", "INVITED_RESULT_STUB_CI_ONLY"}
            or _PRIVATE_STAGING_PROFILE is not None
            or _CI_CLAIM_STUB is not None
            or not isinstance(stub, CountOnlyGatewayStub)
            or not isinstance(reporter_dsn, str)):
        raise DispatchClaimDenied()
    attrs = psycopg.conninfo.conninfo_to_dict(reporter_dsn)
    if ((attrs.get("host"), attrs.get("port"), attrs.get("dbname"),
         attrs.get("user")) !=
            ("127.0.0.1", "5432", "history_ci", "history_dispatch_reporter")
            or set(attrs) - {"host", "port", "dbname", "user",
                             "password", "connect_timeout"}):
        raise DispatchClaimDenied()
    _CI_DISPATCH_REPORTER_DSN = reporter_dsn
    _CI_CLAIM_STUB = stub


def install_ci_invited_result_fixture(
    store: PrivateFixtureResultLedger, gateway: FixedInvitedGatewayStub,
    reporter_dsn: str,
) -> None:
    """CI fixture ONLY; never exposes or stores a real generated Answer."""
    global _CI_INVITED_RESULT_STORE
    if (os.getenv("CI") != "true" or os.getenv("GITHUB_ACTIONS") != "true"
            or os.getenv("API_RUNNER_EXECUTION_MODE") != "INVITED_RESULT_STUB_CI_ONLY"
            or _CI_INVITED_RESULT_STORE is not None
            or not isinstance(store, PrivateFixtureResultLedger)
            or not isinstance(gateway, FixedInvitedGatewayStub)):
        raise DispatchClaimDenied()
    install_ci_count_only_dispatch(gateway, reporter_dsn)
    _CI_INVITED_RESULT_STORE = store


def install_private_staging_no_dispatch(
    profile: PrivateStagingProfile, engine: PrivateStagingEngineConfig,
) -> None:
    """Only trusted Ops startup may call; service stays no-dispatch ONLY.

    First validate pinned C018 runner file/hash and shared private ledger.
    Then install the separately verified BFF/mTLS/DB profile atomically in
    process memory. Does not perform HTTP, SQL grants or engine execution.
    """
    if (os.getenv("API_RUNNER_EXECUTION_MODE") != "NO_DISPATCH_ONLY"
            or _PRIVATE_STAGING_PROFILE is not None
            or _SERVER_NO_DISPATCH_TASK is not None):
        raise StagingConfigDenied()
    handler = build_private_no_dispatch_handler(
        profile=profile, config=engine, environ=os.environ)
    install_private_staging_auth(profile)
    install_server_no_dispatch_handler(handler)


@app.get("/v1/message-requests/engine-status")
def session_engine_status(request: Request):
    """Separate authenticated technical status; NEVER a Product Answer.

    BFF must sign exact new path/query/body, same verified session+Owner,
    and use the same original status query keys as product.v1 Status.
    """
    def read(ctx):
        if _SERVER_NO_DISPATCH_TASK is None:
            raise PreflightDenied()
        query = history._query(request, "message_request_status_query")
        doc = history.read_status(
            ctx["conn"], ctx["owner"], query, ctx["request_id"], ctx["trace_id"],
            session_transaction=True)
        if doc["owner_user_id"] != ctx["owner"]:
            raise TrustRejected()
        attempt_id = doc["attempt_id"]
        data = (_SERVER_NO_DISPATCH_TASK.read(ctx["owner"], attempt_id)
                if attempt_id else {
                    "state": "NOT_STARTED", "top10_count": None,
                    "generation_calls": None, "question_hash_match": None})
        return JSONResponse(status_code=200, content={
            "kind": "no_dispatch_execution_status",
            "contract_version": "api.no_dispatch_status.v1",
            "request_id": doc["request_id"],
            "trace_id": doc["trace_id"],
            "attempt_id": attempt_id,
            "attempt_trace_id": doc["attempt_trace_id"],
            "product_status": doc["status"],
            "preflight_state": data["state"],
            "question_sha256_matches": data["question_hash_match"],
            "top10_count": data["top10_count"],
            "generation_calls": data["generation_calls"],
            "dispatch_performed": False,
            "answer": None,
        }, headers={"Cache-Control": "no-store"})
    return _signed_read(request, _ENGINE_STATUS_PATH, read, coherent_read=True)


@app.get("/v1/message-requests/retrieved-sources")
def session_retrieved_sources(request: Request):
    """Same signed status correlators, OWNER-scoped immutable C018 evidence.

    Does no Runner execution, no reservations, no Gateway, no History T3.
    Source ID is an observation and no locator is VERIFIED until ENGINE's
    independently reviewed member_locators schema/authorization is supplied.
    """
    def read(ctx):
        if _SERVER_NO_DISPATCH_TASK is None:
            raise PreflightDenied()
        query = history._query(request, "message_request_status_query")
        doc = history.read_status(
            ctx["conn"], ctx["owner"], query, ctx["request_id"], ctx["trace_id"],
            session_transaction=True)
        if doc["owner_user_id"] != ctx["owner"]:
            raise TrustRejected()
        attempt_id = doc["attempt_id"]
        attempt_trace = doc["attempt_trace_id"]
        receipt = (_SERVER_NO_DISPATCH_TASK.read_sources(
            ctx["owner"], attempt_id, attempt_trace)
            if attempt_id is not None and attempt_trace is not None else None)
        if receipt is None:
            # Never fill an absent/failed/unknown source receipt with an
            # archived Q2 row or a browser-supplied source.
            receipt = {
                "kind": "retrieved_sources",
                "contract_version": SOURCES_CONTRACT,
                "attempt_id": attempt_id,
                "attempt_trace_id": attempt_trace,
                "retrieval_state": "NOT_AVAILABLE",
                "engine_sha256": ENGINE_SHA256,
                "chunks_sha256": CHUNKS_SHA256,
                "generation_calls": None,
                "rows": [],
            }
        if (receipt.get("chunks_sha256") != CHUNKS_SHA256
                or receipt.get("engine_sha256") != ENGINE_SHA256):
            raise PreflightDenied()
        return JSONResponse(status_code=200, content=receipt,
                            headers={"Cache-Control": "no-store"})
    return _signed_read(
        request, _RETRIEVED_SOURCES_PATH, read, coherent_read=True)


@app.get("/v1/message-requests/claim-test-status")
def session_claim_test_status(request: Request):
    """Disposable signed HTTP diagnostic only; NOT a Foundation staging DTO."""
    def read(ctx):
        if (_CI_CLAIM_STUB is None or
                os.getenv("API_RUNNER_EXECUTION_MODE") != "CLAIM_STUB_CI_ONLY"):
            raise DispatchClaimDenied()
        query = history._query(request, "message_request_status_query")
        doc = history.read_status(
            ctx["conn"], ctx["owner"], query, ctx["request_id"], ctx["trace_id"],
            session_transaction=True)
        data = owner_scoped_claim_status(ctx["conn"], ctx["owner"], doc)
        if data is None:
            raise history.NotFound()
        return JSONResponse(status_code=200, content={
            "kind": "claim_test_status",
            "contract_version": "api.claim_stub_diagnostic.v0",
            "product_status": doc["status"],
            "dispatch_state": data["dispatch_state"],
            "attempt_id": doc["attempt_id"],
            "attempt_trace_id": doc["attempt_trace_id"],
            "answer": None,
        }, headers={"Cache-Control": "no-store"})
    return _signed_read(request, _CLAIM_TEST_STATUS_PATH, read, coherent_read=True)


def _invited_binding_from_status(ctx, doc):
    return InvitedBinding(
        owner_user_id=ctx["owner"],
        session_ref_sha256=ctx["session_ref_sha256"],
        session_epoch=ctx["session_epoch"],
        session_generation=ctx["session_generation"],
        requested_conversation_id=doc["requested_conversation_id"],
        resolved_conversation_id=doc["resolved_conversation_id"],
        client_message_id=doc["client_message_id"],
        idempotency_key=doc["idempotency_key"],
        attempt_id=doc["attempt_id"],
        attempt_request_id=doc["attempt_request_id"],
        attempt_trace_id=doc["attempt_trace_id"],
    )


@app.get("/v1/message-requests/invited-live-result")
def session_invited_live_result(request: Request):
    """CI-fixture-only staging DTO; 005/004 signed and 100% read-only.

    Every GET independently rechecks the actual authenticated Product session
    and reads the original persisted owner/Conversation/T2 Attempt.
    No Gateway, Runner, Claim, second T1/T2, T3 or answer-history write.
    """
    def read(ctx):
        if (_CI_INVITED_RESULT_STORE is None
                or os.getenv("CI") != "true"
                or os.getenv("GITHUB_ACTIONS") != "true"
                or os.getenv("API_RUNNER_EXECUTION_MODE")
                    != "INVITED_RESULT_STUB_CI_ONLY"
                or _PRIVATE_STAGING_PROFILE is not None):
            raise DispatchClaimDenied()
        query = history._query(request, "message_request_status_query")
        doc = history.read_status(
            ctx["conn"], ctx["owner"], query, ctx["request_id"], ctx["trace_id"],
            session_transaction=True)
        if doc["owner_user_id"] != ctx["owner"]:
            raise TrustRejected()
        if doc["status"] == "answer_committed":
            # This route MUST NOT represent a Product Answer as provisional.
            raise DispatchClaimDenied()
        item = None
        if doc["attempt_id"] is not None:
            binding = _invited_binding_from_status(ctx, doc)
            item = _CI_INVITED_RESULT_STORE.read(binding)
        if item is None:
            if doc["attempt_id"] is not None:
                claim = owner_scoped_claim_status(ctx["conn"], ctx["owner"], doc)
                if claim is None:
                    raise history.NotFound()
                # An existing claimed T2 with NO result receipt after Commit
                # is AMBIGUOUS, never a prompt to execute the producer again.
                state = "UNKNOWN"
            else:
                state = "PENDING"
            item = {"result_status": state, "answer": None,
                    "retention_expires_at": None}
        if doc["status"] in ("attempt_unknown", "failed", "cancelled"):
            item["result_status"] = (
                "UNKNOWN" if doc["status"] == "attempt_unknown" else "FAILED")
            item["answer"] = None
        # No real Gateway/Answer provenance or product.v1 History row.
        result_document = {
            "kind": "invited_live_result",
            "contract_version": INVITED_RESULT_VERSION,
            "result_status": item["result_status"],
            "owner_user_id": ctx["owner"],
            "requested_conversation_id": doc["requested_conversation_id"],
            "resolved_conversation_id": doc["resolved_conversation_id"],
            "client_message_id": doc["client_message_id"],
            "idempotency_key": doc["idempotency_key"],
            "attempt_id": doc["attempt_id"],
            "attempt_request_id": doc["attempt_request_id"],
            "attempt_trace_id": doc["attempt_trace_id"],
            "request_id": doc["request_id"],
            "trace_id": doc["trace_id"],
            "retention_expires_at_unix": item["retention_expires_at"],
            "consent_scope": "CI_FIXTURE_ONLY",
            "provenance": {
                "state": "UNVERIFIED_STAGING",
                "origin": "FIXED_GATEWAY_STUB",
                "product_live_verified": False,
                "warning": INVITED_WARNING,
            },
            "answer": item["answer"] if item["result_status"] == "READY" else None,
        }
        validate_ci_invited_result(result_document)
        return JSONResponse(status_code=200, content=result_document,
                            headers={"Cache-Control": "no-store"})
    return _signed_read(request, _INVITED_RESULT_PATH, read, coherent_read=True)


def _run_fixture_send(request, raw_body, payload):
    def reserve(ctx):
        conn, owner = ctx["conn"], ctx["owner"]
        receipt = history.send_t1(conn, owner, payload, ctx["request_id"], ctx["trace_id"])
        if receipt["disposition"] == "replayed":
            return receipt, None
        attempt = start_t2(conn, owner, payload["requested_conversation_id"],
                           payload["client_message_id"], payload["idempotency_key"],
                           history.uid(), ctx["trace_id"])
        return receipt, attempt

    proof, (receipt, attempt) = _signed_history(request, raw_body, _SEND_PATH, reserve)
    if attempt is None:
        return history._send_success(receipt, 200)

    # T1 and T2 committed together under admission. No PostgreSQL connection
    # or session lock is held during this call. Only the question crosses it.
    failure = None
    try:
        answer = answer_from_fixture(payload["question"])
        answer.update(answer_id=attempt["reserved_answer_id"],
                      conversation_id=receipt["resolved_conversation_id"],
                      message_id=history.uid(),
                      request_id=attempt["attempt_request_id"],
                      trace_id=attempt["attempt_trace_id"])
        history.check_wire(answer, "answer")
        # JSON Schema cannot express Claim↔Citation reciprocal ID references.
        # This adds structural integrity to CI fixture T3, never LIVE evidence.
        inspect_answer_citation_graph(answer)
        if answer["provenance"]["origin"] != "SYNTHETIC":
            raise ValueError("FIXTURE_PROVENANCE_REQUIRED")
    except TimeoutError:
        failure = (504, "PROVIDER_TIMEOUT")
    except (OSError, ValueError, ValidationError, StopIteration,
            CitationGraphDenied):
        failure = (502, "PROVIDER_REQUEST_FAILED")

    with _conn("history") as conn, conn.transaction():
        # This is a continuation of an already admitted request. Consume its
        # JTI only once, but fence the exact same session again before T3.
        if auth_session.admit_session_fenced(
            conn, proof.session_ref, proof.owner_id, proof.epoch, proof.generation,
        ) is not True:
            raise TrustRejected()
        if failure:
            status, code = failure
            mark_attempt(conn, proof.owner_id, attempt["id"], "failed", code)
        else:
            finalize_t3(conn, proof.owner_id, attempt["id"], answer, answer["answer_text"])

    if failure:
        return history._safe_error(
            status, code, "technical", "Fixture execution failed.",
            request_id=attempt["attempt_request_id"],
            trace_id=attempt["attempt_trace_id"],
        )
    return history._send_success(receipt, 202)


def _run_server_no_dispatch_send(request, raw_body, payload, background_tasks):
    """Signed #52 T1 -> T2 COMMIT, promptly 202, read-only async Runner.

    No T3, no user-selected Runner/Owner. Exact Runner handler is missing
    until reviewed CLI/schema and DB dispatch authority are supplied.
    """
    if _SERVER_NO_DISPATCH_TASK is None:
        return history._safe_error(
            503, "ENGINE_NOT_CONFIGURED", "technical",
            "History unavailable.")

    accepted_owner = {"id": None}
    handler = _SERVER_NO_DISPATCH_TASK

    def committed_operation():
        def reserve(ctx):
            conn, owner = ctx["conn"], ctx["owner"]
            receipt = history.send_t1(
                conn, owner, payload, ctx["request_id"], ctx["trace_id"])
            if receipt["disposition"] == "replayed":
                return receipt, None
            attempt = start_t2(
                conn, owner, payload["requested_conversation_id"],
                payload["client_message_id"], payload["idempotency_key"],
                history.uid(), ctx["trace_id"])
            return receipt, attempt

        # _signed_history's outer transaction must EXIT and COMMIT before
        # this function returns to prepare_post_commit_no_dispatch.
        proof, value = _signed_history(request, raw_body, _SEND_PATH, reserve)
        accepted_owner["id"] = proof.owner_id
        return value

    def enqueue(binding, question):
        # A durable, per-Owner single-host operational reservation is written
        # only AFTER PG COMMIT. Even if process crashes, retries cannot
        # automatically re-run the engine (they replay #52 send receipt).
        owner = accepted_owner["id"]
        if handler.reserve(owner, binding):
            background_tasks.add_task(handler, owner, binding, question)

    receipt, stage = prepare_post_commit_no_dispatch(
        committed_operation, enqueue, payload["question"])
    return history._send_success(receipt, 200 if stage.is_replay else 202)


def _report_ci_dispatch_unknown(permit, reason):
    """Only CI reporter role; failure never authorizes a second send."""
    if _CI_DISPATCH_REPORTER_DSN is None:
        return False
    try:
        with psycopg.connect(
            _CI_DISPATCH_REPORTER_DSN, autocommit=True, row_factory=dict_row,
            connect_timeout=5,
        ) as conn:
            role = conn.execute(
                "SELECT rolname,rolsuper,rolbypassrls FROM pg_roles "
                "WHERE rolname=current_user").fetchone()
            if (role is None or role["rolname"] != "history_dispatch_reporter"
                    or role["rolsuper"] or role["rolbypassrls"]):
                return False
            return flag_reporter_unknown(conn, permit, reason)
    except (psycopg.Error, RuntimeError, OSError, DispatchClaimDenied):
        return False


def _invoke_ci_count_only_gateway(permit, question, invited_binding=None):
    """Post-commit stub call, max ONE; optional immutable synthetic result."""
    try:
        result = _CI_CLAIM_STUB(permit, question)
        if invited_binding is not None:
            if (_CI_INVITED_RESULT_STORE is None
                    or not _CI_INVITED_RESULT_STORE.ready(invited_binding, result)):
                raise DispatchClaimDenied()
    except TimeoutError:
        if invited_binding is not None and _CI_INVITED_RESULT_STORE is not None:
            _CI_INVITED_RESULT_STORE.unknown(invited_binding)
        _report_ci_dispatch_unknown(permit, "TIMEOUT")
    except ConnectionError:
        if invited_binding is not None and _CI_INVITED_RESULT_STORE is not None:
            _CI_INVITED_RESULT_STORE.unknown(invited_binding)
        _report_ci_dispatch_unknown(permit, "LOST_RESPONSE")
    except (DispatchClaimDenied, sqlite3.Error, ValueError):
        if invited_binding is not None and _CI_INVITED_RESULT_STORE is not None:
            _CI_INVITED_RESULT_STORE.unknown(invited_binding)
    # A process crash cannot reuse the consumed Claim, even if report is lost.


def _run_ci_claim_send(request, raw_body, payload, background_tasks):
    """Signed 005/004 T1→T2→011 Claim outer COMMIT before counted stub."""
    mode = os.getenv("API_RUNNER_EXECUTION_MODE")
    if (_CI_CLAIM_STUB is None
            or os.getenv("CI") != "true"
            or os.getenv("GITHUB_ACTIONS") != "true"
            or mode not in {"CLAIM_STUB_CI_ONLY", "INVITED_RESULT_STUB_CI_ONLY"}
            or _PRIVATE_STAGING_PROFILE is not None
            or (mode == "INVITED_RESULT_STUB_CI_ONLY"
                and (_CI_INVITED_RESULT_STORE is None
                     or not isinstance(_CI_CLAIM_STUB, FixedInvitedGatewayStub)))):
        return history._safe_error(
            503, "ENGINE_NOT_CONFIGURED", "technical", "History unavailable.")

    accepted = {"binding": None}

    def committed_operation():
        def reserve(ctx):
            conn, owner = ctx["conn"], ctx["owner"]
            receipt = history.send_t1(
                conn, owner, payload, ctx["request_id"], ctx["trace_id"])
            if receipt["disposition"] == "replayed":
                return receipt, None
            attempt = start_t2(
                conn, owner, payload["requested_conversation_id"],
                payload["client_message_id"], payload["idempotency_key"],
                history.uid(), ctx["trace_id"])
            # DB #56 Migration 011, same 005/004 outer transaction.
            permit = claim_within_signed_t2(conn, owner, attempt)
            if mode == "INVITED_RESULT_STUB_CI_ONLY":
                accepted["binding"] = _invited_binding_from_status(ctx, {
                    **receipt,
                    "attempt_id": attempt["id"],
                    "attempt_request_id": attempt["attempt_request_id"],
                    "attempt_trace_id": attempt["attempt_trace_id"],
                })
            return receipt, permit
        # The original protected_transaction EXIT/COMMIT must succeed first.
        _, value = _signed_history(request, raw_body, _SEND_PATH, reserve)
        return value

    def enqueue(permit, question):
        binding = accepted["binding"]
        if mode == "INVITED_RESULT_STUB_CI_ONLY":
            if binding is None or not _CI_INVITED_RESULT_STORE.reserve(binding):
                raise DispatchClaimDenied()
        background_tasks.add_task(
            _invoke_ci_count_only_gateway, permit, question, binding)

    receipt, created = after_definitive_commit(
        committed_operation, enqueue, payload["question"])
    return history._send_success(receipt, 202 if created else 200)


@app.post("/v1/messages")
async def session_send_message(request: Request, background_tasks: BackgroundTasks):
    try:
        # Check trusted transport before consuming/decoding any user question.
        # BFF assertion headers alone are not mTLS peer evidence.
        if (_PRIVATE_STAGING_PROFILE is not None
                and not _PRIVATE_STAGING_PROFILE.allowed_peer(request.scope)):
            raise TrustRejected()
        if request.scope.get("query_string") or len(request.headers.getlist("content-length")) > 1:
            raise history.ApiFailure(422, "INVALID_REQUEST", "validation")
        payload, raw_body = await history._read_body(
            request, "send_message_request", include_raw=True)
        if (_PRIVATE_STAGING_PROFILE is not None
                and os.getenv("API_RUNNER_EXECUTION_MODE") != "NO_DISPATCH_ONLY"):
            # Never execute synthetic fixture inside private staging.
            response = history._safe_error(
                503, "ENGINE_NOT_CONFIGURED", "technical", "History unavailable.")
        elif os.getenv("API_RUNNER_EXECUTION_MODE") in {
                "CLAIM_STUB_CI_ONLY", "INVITED_RESULT_STUB_CI_ONLY"}:
            response = await run_in_threadpool(
                _run_ci_claim_send,
                request, raw_body, payload, background_tasks)
        elif os.getenv("API_RUNNER_EXECUTION_MODE") == "NO_DISPATCH_ONLY":
            # Server-only feature gate, not browser-supplied. Without an
            # approved handler this returns 503 BEFORE any DB write.
            response = await run_in_threadpool(
                _run_server_no_dispatch_send,
                request, raw_body, payload, background_tasks)
        else:
            response = await run_in_threadpool(
                _run_fixture_send, request, raw_body, payload)
    except PreflightDenied:
        response = history._safe_error(
            503, "ENGINE_NOT_CONFIGURED", "technical", "History unavailable.")
    except _HISTORY_ERRORS as exc:
        response = _history_error(exc)
    response.headers["Cache-Control"] = "no-store"
    return response


@app.post("/internal/auth/session/v1/revoke-one")
async def session_revoke_one(request: Request):
    """Same-session signed, replay fenced, real restricted-role 003 revoke.

    There is NO anonymous owner selector or bootstrap-before-session authority.
    A successful response is produced strictly AFTER PostgreSQL COMMIT. An
    ambiguous connection/COMMIT response never becomes success.
    """
    try:
        # Revoke is as sensitive as History. Require trusted TLS peer identity
        # at the route too, before reading a token or opening an Auth DB role.
        # Forwarded headers are never transport evidence.
        if (_PRIVATE_STAGING_PROFILE is not None
                and not _PRIVATE_STAGING_PROFILE.allowed_peer(request.scope)):
            raise TrustRejected()
        if (request.scope.get("raw_path") != _REVOKE_PATH
                or request.scope.get("query_string") != b""
                or request.headers.get("content-type", "").split(";")[0] != "application/json"
                or len(request.headers.getlist("content-length")) > 1):
            return _err(422, "INVALID_REQUEST")
        chunks = []
        total = 0
        async for part in request.stream():
            total += len(part)
            if total > 512:
                return _err(413, "REQUEST_TOO_LARGE")
            chunks.append(part)
        raw = b"".join(chunks)
        if request.headers.get("content-length") is not None:
            value = request.headers["content-length"]
            if not value.isdecimal() or int(value) != len(raw):
                return _err(422, "INVALID_REQUEST")
        def no_duplicates(pairs):
            x = {}
            for key, value in pairs:
                if key in x:
                    raise ValueError()
                x[key] = value
            return x
        payload = json.loads(raw.decode("utf-8"), object_pairs_hook=no_duplicates)
        if (not isinstance(payload, dict) or set(payload) != {"operation_id"}
                or not isinstance(payload["operation_id"], str)
                or not _UUID.fullmatch(payload["operation_id"])):
            return _err(422, "INVALID_REQUEST")
        token = assertion_from_asgi_headers(request.scope)
        method, path, query, body = wire_request(request.scope, raw)
        verifier = _config()
        verified = verifier.verify(token, method=method, raw_path=path,
                                   raw_query=query, raw_body=body)
        with _conn("revoke") as conn:
            with protected_transaction(
                conn, verifier=verifier, replay_store=_REPLAY,
                compact_assertion=token, method=method, raw_path=path,
                raw_query=query, body=body,
            ) as owner:
                if owner != verified.owner_id:
                    raise TrustRejected()
                # 003 runs Owner->Session locks, with the outer transaction
                # remaining live until COMMIT acknowledgment; no separate
                # pre-check detached from this exact signed session.
                if auth_session.revoke_one(
                    conn, verified.session_ref, verified.epoch) is not True:
                    raise TrustRejected()
            return JSONResponse(status_code=200,
                content={"state": "REVOKED_COMMITTED",
                         "operation_id": payload["operation_id"]},
                headers={"Cache-Control": "no-store"})
    except TrustRejected:
        return _err(401, "AUTH_DENIED")
    except AdmissionSerializationUnavailable:
        # No committed revoke is proven by a failed/unknown DB transaction.
        return _err(503, "REVOKE_OUTCOME_UNKNOWN")
    except (json.JSONDecodeError, UnicodeError, ValueError, KeyError):
        return _err(422, "INVALID_REQUEST")
    except (psycopg.Error, RuntimeError, OSError, TypeError):
        return _err(503, "REVOKE_OUTCOME_UNKNOWN")
