"""Isolated app-only API entrypoint. NO engine/Runner/Qdrant/Gateway import.

This is a deliberately narrow internal process listener, NOT a replacement
for the private signed OIDC/BFF/PG History integration. Its liveness endpoint
never claims application readiness; authenticated History remains unavailable
until an approved mTLS+PG product adapter is independently integrated.

No request body is read for Send. No persistence, attempt allocation, task
spawn, model call, or synthetic Answer/Citation may occur in this module.
"""
from __future__ import annotations

import os

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

VERSION = "api.app_only_runtime.v1"
NO_STORE = {"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"}
app = FastAPI(
    title="RAG Finance Internal App-only API",
    docs_url=None, redoc_url=None, openapi_url=None,
    # No startup event, background worker, engine lock or database pool.
)


def _enabled() -> bool:
    return os.environ.get("PHASE3_APP_MODE") == "APP_ONLY"


def _json(body: dict, status: int) -> JSONResponse:
    return JSONResponse(body, status_code=status, headers=NO_STORE)


@app.get("/health/live")
async def live() -> JSONResponse:
    if not _enabled():
        return _json({"error": "APP_ONLY_PROFILE_DENIED"}, 503)
    return _json({
        "kind": "api_app_only_liveness",
        "contract_version": VERSION,
        "process_alive": True,
        "application_ready": False,
        "retrieval_available": False,
        "generation_available": False,
    }, 200)


@app.get("/health/ready")
async def ready() -> JSONResponse:
    # No honest 200 before the *real* signed BFF, IdP, Bootstrap and PG
    # dependency gates are wired. Docker health checks process liveness only.
    if not _enabled():
        return _json({"error": "APP_ONLY_PROFILE_DENIED"}, 503)
    return _json({
        "kind": "api_app_only_readiness",
        "contract_version": VERSION,
        "application_ready": False,
        "reason": "SIGNED_HISTORY_PG_BOOTSTRAP_UNVERIFIED",
        "retrieval_available": False,
        "generation_available": False,
    }, 503)


@app.get("/v1/capabilities")
async def capabilities() -> JSONResponse:
    if not _enabled():
        return _json({"error": "APP_ONLY_PROFILE_DENIED"}, 503)
    return _json({
        "kind": "api_app_only_capabilities",
        "contract_version": VERSION,
        "send_mode": "DISABLED",
        "retrieval_available": False,
        "generation_available": False,
        "background_dispatch_available": False,
    }, 200)


@app.post("/v1/messages")
async def send(_request: Request) -> JSONResponse:
    # Deliberately DO NOT await _request.body(), .json(), .stream() or
    # call any persistence API. A malformed, hostile, or huge Send is
    # denied before reservation of T1/T2, without an engine subprocess.
    if not _enabled():
        return _json({"error": "APP_ONLY_PROFILE_DENIED"}, 503)
    return _json({"error": "ENGINE_NOT_AVAILABLE"}, 503)


@app.get("/v1/conversations")
async def private_history(_request: Request) -> JSONResponse:
    # Never accept client-forwarded owner, cert, subject, role, session
    # or issuer headers. No signed owner/PG binding currently exists here.
    if not _enabled():
        return _json({"error": "APP_ONLY_PROFILE_DENIED"}, 503)
    return _json({"error": "SIGNED_HISTORY_NOT_CONFIGURED"}, 503)


@app.get("/v1/conversations/{conversation_id}/messages")
async def private_thread(_request: Request, conversation_id: str) -> JSONResponse:
    # Return the same closed status for any guessed cross-user ID.
    if not _enabled():
        return _json({"error": "APP_ONLY_PROFILE_DENIED"}, 503)
    return _json({"error": "SIGNED_HISTORY_NOT_CONFIGURED"}, 503)


@app.get("/v1/message-requests/{suffix}")
async def private_attempt(_request: Request, suffix: str) -> JSONResponse:
    # GET-only, no historical replay or dispatch; no actor trust.
    if not _enabled():
        return _json({"error": "APP_ONLY_PROFILE_DENIED"}, 503)
    return _json({"error": "SIGNED_HISTORY_NOT_CONFIGURED"}, 503)
