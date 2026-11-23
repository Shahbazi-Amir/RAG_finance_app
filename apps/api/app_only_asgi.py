"""Isolated CI-only real API listener for the app-without-engine boundary.

This is NOT a production/Ops private API. No IdP or database has been attested,
so readiness is intentionally HTTP 503 and all user-data routes are denied.
Only an explicit GitHub Actions CI profile can bind the localhost listener.
It never imports C018, Qdrant, an LLM gateway or durable History.
"""
from __future__ import annotations

import os
import sys

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from starlette.middleware.trustedhost import TrustedHostMiddleware

PROFILE = "ISOLATED_CI_NO_ENGINE"
PORT = 18880
app = FastAPI(
    title="App-only isolated CI probe",
    openapi_url=None,
    docs_url=None,
    redoc_url=None,
)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=["127.0.0.1", "localhost"])


@app.middleware("http")
async def never_cache(request, call_next):
    response = await call_next(request)
    response.headers["Cache-Control"] = "no-store"
    response.headers["X-Content-Type-Options"] = "nosniff"
    return response


@app.get("/health/live")
def live():
    return {"state": "alive", "profile": "app_only", "probe_only": True}


@app.get("/health/ready")
def ready():
    return JSONResponse(
        status_code=503,
        content={"state": "not_ready", "code": "DEPENDENCIES_NOT_ATTESTED"},
    )


@app.get("/v1/capabilities")
def capabilities():
    return {
        "profile": "app_only",
        "retrieval": "unavailable",
        "generation": "unavailable",
        "answer_creation": False,
        "external_dispatch": False,
    }


@app.post("/v1/messages")
def engine_unavailable():
    # Deliberately no Request/body parameter: do not parse or store Send.
    # No signed user identity is trusted in this CI-only listener.
    return JSONResponse(
        status_code=503,
        content={"error": "ENGINE_UNAVAILABLE"},
    )


@app.get("/v1/conversations")
def identity_unavailable():
    # No unsigned History access or fake conversations.
    return JSONResponse(
        status_code=503,
        content={"error": "IDENTITY_NOT_ATTESTED"},
    )


def approved_ci_profile(environ=None):
    environ = os.environ if environ is None else environ
    return (
        environ.get("CI") == "true"
        and environ.get("GITHUB_ACTIONS") == "true"
        and environ.get("APP_ONLY_PROFILE") == PROFILE
        and environ.get("APP_ONLY_PORT") == str(PORT)
    )


def main():
    if not approved_ci_profile():
        print("APP_ONLY_CI_LISTENER_NOT_AUTHORIZED", file=sys.stderr)
        return 78
    import uvicorn
    uvicorn.run(
        app,
        host="127.0.0.1",
        port=PORT,
        workers=1,
        proxy_headers=False,
        access_log=False,
        server_header=False,
        timeout_keep_alive=3,
        limit_concurrency=16,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
