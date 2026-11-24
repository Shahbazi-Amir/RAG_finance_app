"""CI-only signed POST persistence lab. NOT an app-only product entrypoint.

Uses original route, signature verification and real PG T1/T2. The only
substitute is the post-commit callback, which records UNKNOWN in a private
test ledger without starting a Runner, generating an Answer or calling a
provider. No 011, no staging profile, no product route or image changes.
"""
import hashlib
import os
from pathlib import Path
import re
import ssl
import sys

if (__name__ != "__main__" or os.getenv("CI") != "true"
        or os.getenv("GITHUB_ACTIONS") != "true"
        or os.getenv("F3_REPLAY_PERSISTENCE_CI_ONLY") != "true"
        or os.getenv("API_RUNNER_EXECUTION_MODE") != "NO_DISPATCH_ONLY"
        or os.getenv("PHASE3_APP_MODE") is not None):
    raise SystemExit("REPLAY_CI_ONLY")
root = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(root))
import psycopg
from psycopg.conninfo import conninfo_to_dict
import uvicorn
from starlette.responses import JSONResponse
from apps.api import product_session_api as api
from apps.api.private_staging_asgi import _harden_tls_context
from src.phase3.auth.staging_transport_mtls import (
    TrustedBFFTLSBoundary, make_verified_h11_protocol,
)
from src.phase3.rag_runtime.no_dispatch_handler import NoDispatchHandler, NoDispatchLedger

for name, role in (("DB_APP_DSN","history_app"),("AUTH_REVOKER_DSN","auth_revoker")):
    d = conninfo_to_dict(os.environ[name])
    assert (d.get("host"),d.get("port"),d.get("dbname"),d.get("user")) == (
        "127.0.0.1","5432","history_ci",role)
    assert not set(d)-{"host","port","dbname","user","password","connect_timeout"}
for key in os.environ:
    assert key not in {"OPENAI_API_KEY","API_PROVIDER_KEY","C018_RUNNER_PATH",
                       "QDRANT_URL","MODEL_GATEWAY_URL","API_ENGINE_ENABLED"}
assert api._PRIVATE_STAGING_PROFILE is None and api._SERVER_NO_DISPATCH_TASK is None
assert uvicorn.__version__ == "0.48.0"
directory=Path(os.environ["F3_REPLAY_LAB_DIR"])
assert directory.is_absolute() and str(directory).startswith("/tmp/") and directory.is_dir()
assert directory.stat().st_uid==os.geteuid() and directory.stat().st_mode & 0o077 == 0
ledger=NoDispatchLedger(directory/"outcomes.sqlite")
audit=directory/"callback-counts"
def note(event):
    assert event in ("reserve","callback")
    fd=os.open(audit,os.O_WRONLY|os.O_APPEND|os.O_CREAT|os.O_NOFOLLOW,0o600)
    with os.fdopen(fd,"a") as f:
        f.write(event+"\n")
        f.flush()
        os.fsync(f.fileno())

class CIUnknownOnly(NoDispatchHandler):
    def __init__(self, ledger):
        # No RunnerLayout or approved engine object is constructed.
        self.ledger=ledger
    def reserve(self, owner, binding):
        note("reserve")
        return self.ledger.reserve(owner,binding)
    def __call__(self, owner, binding, question):
        note("callback")
        assert self.ledger.start(owner,binding)
        assert self.ledger.fail(owner,binding,unknown=True)

api.install_server_no_dispatch_handler(CIUnknownOnly(ledger))
cert=Path(os.environ["APP_ONLY_CI_CLIENT_CERT"])
fingerprint=hashlib.sha256(ssl.PEM_cert_to_DER_cert(cert.read_text(encoding="ascii"))).hexdigest()
boundary=TrustedBFFTLSBoundary(fingerprint)

async def guarded(scope,receive,send):
    if scope["type"]!="http" or not boundary.scope_is_verified(scope):
        return await JSONResponse({"error":"AUTH_REQUIRED"},status_code=401,
            headers={"Cache-Control":"no-store"})(scope,receive,send)
    method,path=scope.get("method"),scope.get("raw_path")
    if (method,path) not in {("POST",b"/v1/messages"),("GET",b"/v1/conversations"),
        ("GET",b"/v1/message-requests/status"),("POST",b"/internal/auth/session/v1/revoke-one")}:
        return await JSONResponse({"error":"NOT_FOUND"},status_code=404,
            headers={"Cache-Control":"no-store"})(scope,receive,send)
    return await api.app(scope,receive,send)

# The callback never dispatches. Additionally prevent OS child execution
# or Python outbound socket connections in this entire private test server.
# The real PostgreSQL connection is libpq, constrained by the above DSNs.
def deny_external(event,args):
    if event in {"subprocess.Popen","os.system","os.exec","os.posix_spawn",
                 "socket.connect","socket.getaddrinfo"}:
        raise RuntimeError("REPLAY_LAB_EXTERNAL_EFFECT_DENIED")
sys.addaudithook(deny_external)

uvicorn.Server(uvicorn.Config(
    app=guarded,host="127.0.0.1",port=int(os.environ["APP_ONLY_CI_API_PORT"]),
    loop="asyncio",http=make_verified_h11_protocol(boundary),ws="none",
    lifespan="off",workers=1,reload=False,proxy_headers=False,access_log=False,
    server_header=False,date_header=False,limit_concurrency=32,timeout_keep_alive=5,
    ssl_certfile=os.environ["APP_ONLY_CI_SERVER_CERT"],
    ssl_keyfile=os.environ["APP_ONLY_CI_SERVER_KEY"],
    ssl_ca_certs=os.environ["APP_ONLY_CI_CLIENT_CA"],ssl_cert_reqs=ssl.CERT_REQUIRED,
    ssl_version=ssl.PROTOCOL_TLS_SERVER,ssl_context_factory=_harden_tls_context,
    log_level="error",
)).run()
