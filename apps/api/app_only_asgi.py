"""Conservative app-only ASGI surface, NOT the signed Product API.

This component proves a real API process/listener without any Engine import,
Runner, index, paid Gateway, personal-data read or durable message admission.
It intentionally CANNOT declare product readiness until signed IdP/PG wiring is
installed by Ops in a distinct profile. Do not expose it as a public product.
"""
from __future__ import annotations

import os

from fastapi import FastAPI
from fastapi.responses import JSONResponse

MODE = "APP_ONLY"
NO_STORE = {"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"}
app = FastAPI(title="Foundation F3 app-only restricted listener",
              docs_url=None, redoc_url=None, openapi_url=None)


def require_app_only() -> None:
    """Never turn an environment string into engine authorization."""
    if os.environ.get("PHASE3_APP_MODE", MODE) != MODE:
        raise RuntimeError("APP_ONLY_PROFILE_REQUIRED")


require_app_only()


def _response(status: int, payload: dict) -> JSONResponse:
    return JSONResponse(status_code=status, content=payload, headers=NO_STORE)


@app.get("/health/live")
async def live() -> JSONResponse:
    # Process liveness only: no assertion about bootstrap, PG or signed BFF.
    return _response(200, {"component": "api", "process": "alive",
                           "app_ready": False})


@app.get("/health/ready")
async def ready() -> JSONResponse:
    # Never silently promote this fence-only component to product readiness.
    return _response(503, {"error": "APP_DEPENDENCIES_UNWIRED",
                           "app_ready": False})


@app.get("/v1/capabilities")
async def capabilities() -> JSONResponse:
    return _response(200, {
        "kind": "ui_runtime_capabilities",
        "contract_version": "ui.runtime_capabilities.v1",
        "send_mode": "DISABLED",
        "engine_available": False,
        "generation_available": False,
    })


@app.post("/v1/messages")
async def send_disabled() -> JSONResponse:
    # No Request argument, body parser, admission handler, or storage import:
    # deny BEFORE consuming body and before any network or process dispatch.
    return _response(503, {"error": "ENGINE_NOT_AVAILABLE"})


@app.get("/v1/conversations")
@app.get("/v1/conversations/{conversation_id}/messages")
@app.get("/v1/message-requests/status")
@app.get("/v1/message-requests/engine-status")
@app.get("/v1/message-requests/retrieved-sources")
async def private_reads_unwired(conversation_id: str = "") -> JSONResponse:
    # No fixture history or fake ownership result. Real signed API is distinct.
    return _response(503, {"error": "SIGNED_PRODUCT_API_NOT_WIRED"})
