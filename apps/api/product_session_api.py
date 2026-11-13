"""Isolated, real ASGI routes for Product-session History LIST and private revoke.

Uses original History product.v1 implementation and DB 005/004 in ONE
transaction on the actual history_app connection, not a FastAPI dependency
override or browser-selected actor. CI-only configuration and runner mTLS.
Nothing here enables production Auth or additional History endpoints.
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path

import psycopg
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from psycopg.rows import dict_row

from apps.api import history_api as history
from src.phase3.auth.service_proof import (
    BFFServiceVerifier, TrustRejected, assertion_from_asgi_headers, wire_request,
)
from src.phase3.auth.transactional_admission import protected_transaction
from src.phase3.storage.postgres import auth_session
from src.phase3.storage.postgres.service_replay import PostgresDurableReplayStore

app = FastAPI(title="Product Session API H1 isolated", docs_url=None,
              redoc_url=None, openapi_url=None)
_REPLAY = PostgresDurableReplayStore()
_REVOKE_PATH = b"/internal/auth/session/v1/revoke-one"
_HISTORY_PATH = b"/v1/conversations"
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


@app.get("/v1/conversations")
def session_conversations(request: Request):
    """True API handler; signed session JTI + 004 and owner SQL share one TX."""
    try:
        if request.scope.get("raw_path") != _HISTORY_PATH:
            return _err(401, "AUTH_REQUIRED")
        token = assertion_from_asgi_headers(request.scope)
        method, path, query, body = wire_request(request.scope, b"")
        verifier = _config()
        with _conn("history") as conn:
            with protected_transaction(
                conn, verifier=verifier, replay_store=_REPLAY,
                compact_assertion=token, method=method,
                raw_path=path, raw_query=query, body=body,
            ) as owner:
                # The original product.v1 parser, cursor and History repository
                # are reused. Nested psycopg transactions become savepoints.
                ctx = {"owner": owner, "conn": conn,
                       "request_id": history.uid(), "trace_id": history.uid()}
                parsed = history._query(request, "conversation_list_request")
                limit = parsed["limit"]
                anchor, last = (
                    history._cursor_decode(parsed["cursor"], ctx,
                                           "conversations", None, limit)
                    if parsed["cursor"] else (None, None)
                )
                if not parsed["cursor"]:
                    anchor = history._initial_anchor(conn, owner, "conversations", None)
                rows = history.list_conversations(
                    conn, owner, limit=limit, anchor=anchor, last=last)
                response = history._page("conversation_page", ctx, rows, limit,
                                         anchor, "conversations")
            # Leaving the outer transaction has COMMITTED 005+004+History read.
            response.headers["Cache-Control"] = "no-store"
            return response
    except TrustRejected:
        return history._safe_error(401, "AUTH_REQUIRED", "authorization",
                                   "Authentication required.")
    except (history.ApiFailure, history.NotFound, history.Conflict,
            history.IntegrityAnomaly, ValueError) as exc:
        status, code, category = history._exception_code(exc)
        return history._safe_error(status, code, category, "History unavailable.")
    except (psycopg.Error, RuntimeError, OSError, TypeError):
        return history._safe_error(503, "TEMPORARILY_UNAVAILABLE",
                                   "technical", "History temporarily unavailable.")


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
    except (json.JSONDecodeError, UnicodeError, ValueError, KeyError):
        return _err(422, "INVALID_REQUEST")
    except (psycopg.Error, RuntimeError, OSError, TypeError):
        return _err(503, "REVOKE_OUTCOME_UNKNOWN")
