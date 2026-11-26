"""CI-only real mTLS H11 wrapping ORIGINAL signed Product API and PG roles.

Never used for Ops/production. CI's original 009/010 Keycloak and isolated
history_ci DB allowlist continue to enforce actual session/owner checks.
The wrapper MUST be the same AppOnlyASGI class as the live app-only service.
"""
from __future__ import annotations

import hashlib
import os
import ssl
import sys
from pathlib import Path

if __name__ != "__main__" or os.getenv("CI") != "true" or os.getenv("GITHUB_ACTIONS") != "true":
    raise SystemExit("HARD_STOP_CI_ONLY")
if (os.getenv("API_RUNNER_EXECUTION_MODE") != "APP_ONLY"
        or os.getenv("PHASE3_APP_MODE") != "APP_ONLY"
        or "dbname=history_ci" not in os.getenv("DB_APP_DSN", "")):
    raise SystemExit("HARD_STOP_WRONG_LAB_OR_MODE")

root = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(root))
import uvicorn
from apps.api import product_session_api
from apps.api.private_app_only_asgi import AppOnlyASGI
from apps.api.private_staging_asgi import _harden_tls_context
from src.phase3.auth.staging_transport_mtls import (
    TrustedBFFTLSBoundary, make_verified_h11_protocol,
)

if product_session_api._SERVER_NO_DISPATCH_TASK is not None:
    raise SystemExit("HARD_STOP_ENGINE_HANDLER_PRESENT")
if uvicorn.__version__ != "0.48.0":
    raise SystemExit("HARD_STOP_UVICORN_VERSION")

cert = Path(os.environ["APP_ONLY_CI_CLIENT_CERT"])
server_cert = Path(os.environ["APP_ONLY_CI_SERVER_CERT"])
server_key = Path(os.environ["APP_ONLY_CI_SERVER_KEY"])
ca = Path(os.environ["APP_ONLY_CI_CLIENT_CA"])
if not all(p.is_file() and p.is_absolute() for p in (cert, server_cert, server_key, ca)):
    raise SystemExit("HARD_STOP_CERT_MISSING")
fingerprint = hashlib.sha256(
    ssl.PEM_cert_to_DER_cert(cert.read_text(encoding="ascii"))
).hexdigest()
boundary = TrustedBFFTLSBoundary(fingerprint)

class TestOnlyTLSProfile:
    def allowed_peer(self, scope):
        return boundary.scope_is_verified(scope)

app = AppOnlyASGI(product_session_api.app, TestOnlyTLSProfile())
server = uvicorn.Server(uvicorn.Config(
    app=app,
    host="127.0.0.1", port=int(os.environ["APP_ONLY_CI_API_PORT"]),
    loop="asyncio", http=make_verified_h11_protocol(boundary),
    ws="none", lifespan="off", workers=1, reload=False,
    proxy_headers=False, access_log=False, server_header=False,
    date_header=False, limit_concurrency=32, timeout_keep_alive=5,
    ssl_certfile=str(server_cert), ssl_keyfile=str(server_key),
    ssl_ca_certs=str(ca), ssl_cert_reqs=ssl.CERT_REQUIRED,
    ssl_version=ssl.PROTOCOL_TLS_SERVER,
    ssl_context_factory=_harden_tls_context,
    log_level="error",
))
server.run()
