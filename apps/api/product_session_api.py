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
from src.phase3.rag_runtime.staging_preflight import PreflightDenied
from src.phase3.auth.service_proof import (
    BFFServiceVerifier, TrustRejected, assertion_from_asgi_headers, wire_request,
)
from src.phase3.auth.transactional_admission import (
    AdmissionSerializationUnavailable, protected_transaction,
)
from src.phase3.storage.postgres import auth_session
# Use the same repository module as History, including its exception classes.
from repository import finalize_t3, mark_attempt, start_t2
from src.phase3.storage.postgres.service_replay import PostgresDurableReplayStore

app = FastAPI(title="Product Session API H1 isolated", docs_url=None,
              redoc_url=None, openapi_url=None)
_REPLAY = PostgresDurableReplayStore()
# Server-injected only after Ops verifies runner CLI/digest and DB authority.
# An environment toggle alone NEVER installs or authorizes this handler.
_SERVER_NO_DISPATCH_TASK = None
_REVOKE_PATH = b"/internal/auth/session/v1/revoke-one"
_HISTORY_PATH = b"/v1/conversations"
_SEND_PATH = b"/v1/messages"
_STATUS_PATH = b"/v1/message-requests/status"
_CONVERSATION_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}")
_UUID = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$")
_SESSION_ROLES = {"history": "history_app", "revoke": "auth_revoker"}


def _config():
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
    dsn = os.getenv(key, "")
    opts = psycopg.conninfo.conninfo_to_dict(dsn)
    if (opts.get("host") != "127.0.0.1" or opts.get("port") != "5432"
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
                   "trace_id": history.uid(), "session_transaction": True}
            result = action(ctx)
    return proof, result


def _history_error(exc):
    if isinstance(exc, AdmissionSerializationUnavailable):
        return history._safe_error(503, "TEMPORARILY_UNAVAILABLE", "technical",
                                   "History unavailable.")
    if isinstance(exc, TrustRejected):
        return history._safe_error(401, "AUTH_REQUIRED", "authorization",
                                   "Authentication required.")
    status, code, category = history._exception_code(exc)
    return history._safe_error(status, code, category, "History unavailable.")


_HISTORY_ERRORS = (AdmissionSerializationUnavailable, TrustRejected,
                   history.ApiFailure, history.NotFound,
                   history.Conflict, history.IntegrityAnomaly, ValidationError,
                   psycopg.Error, RuntimeError, OSError, TypeError)


def _signed_read(request, path, action, *, coherent_read=False):
    try:
        _, response = _signed_history(request, b"", path, action,
                                      coherent_read=coherent_read)
    except _HISTORY_ERRORS as exc:
        response = _history_error(exc)
    response.headers["Cache-Control"] = "no-store"
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
        if answer["provenance"]["origin"] != "SYNTHETIC":
            raise ValueError("FIXTURE_PROVENANCE_REQUIRED")
    except TimeoutError:
        failure = (504, "PROVIDER_TIMEOUT")
    except (OSError, ValueError, ValidationError, StopIteration):
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
        _, value = _signed_history(request, raw_body, _SEND_PATH, reserve)
        return value

    def enqueue(binding, question):
        # Register task AFTER outer PG COMMIT. Never wait ~82 seconds in HTTP.
        # A browser Poll only invokes the existing signed Status GET.
        background_tasks.add_task(_SERVER_NO_DISPATCH_TASK, binding, question)

    receipt, stage = prepare_post_commit_no_dispatch(
        committed_operation, enqueue, payload["question"])
    return history._send_success(receipt, 200 if stage.is_replay else 202)


@app.post("/v1/messages")
async def session_send_message(request: Request, background_tasks: BackgroundTasks):
    try:
        if request.scope.get("query_string") or len(request.headers.getlist("content-length")) > 1:
            raise history.ApiFailure(422, "INVALID_REQUEST", "validation")
        payload, raw_body = await history._read_body(
            request, "send_message_request", include_raw=True)
        if os.getenv("API_RUNNER_EXECUTION_MODE") == "NO_DISPATCH_ONLY":
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
