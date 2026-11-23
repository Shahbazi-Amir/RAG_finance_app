"""APP_ONLY: real authenticated History after mTLS/PG preflight; no engine or Runner.
The CI-only loopback probe is a deliberately untrusted limited HTTP surface.
"""
import argparse
import json
import os
from pathlib import Path
import re
import ssl
import sys

from src.phase3.auth.staging_service_profile import PrivateStagingProfile, StagingConfigDenied
from src.phase3.auth.staging_transport_mtls import (
    TrustedBFFTLSBoundary, VerifiedPeerUnavailable, make_verified_h11_protocol)
from src.phase3.auth.service_proof import BFFServiceVerifier
from apps.api.private_staging_asgi import (
    PrivateASGIConfig, _protected_file, _test_tls_material, _harden_tls_context,
    verify_staging_database_authority)

VERSION = "api.private_app_only_asgi.v1"
FIELDS = frozenset(("contract_version listen_host listen_port server_tls_cert_file "
    "server_tls_key_file trusted_bff_ca_file bff_leaf_cert_sha256 bff_issuer "
    "bff_audience bff_kid bff_rs256_public_key_file history_dsn revoke_dsn").split())
PATH_FIELDS = ("server_tls_cert_file","server_tls_key_file",
    "trusted_bff_ca_file","bff_rs256_public_key_file")

class AppOnly:
    def __init__(self, inner=None, *, ready=False, readiness_probe=None):
        self.inner = inner
        self.ready = ready
        self.readiness_probe = readiness_probe

    @staticmethod
    async def respond(send, status, doc):
        data = json.dumps(doc,sort_keys=True,separators=(",",":")).encode()
        await send({"type":"http.response.start","status":status,"headers":[
            (b"content-type",b"application/json"),(b"cache-control",b"no-store"),
            (b"x-content-type-options",b"nosniff"),
            (b"content-length",str(len(data)).encode())]})
        await send({"type":"http.response.body","body":data})

    async def __call__(self,scope,receive,send):
        if scope["type"] == "lifespan":
            if self.inner is not None:
                return await self.inner(scope,receive,send)
            while True:
                msg = await receive()
                if msg["type"] == "lifespan.startup":
                    await send({"type":"lifespan.startup.complete"})
                elif msg["type"] == "lifespan.shutdown":
                    await send({"type":"lifespan.shutdown.complete"})
                    return
        if scope["type"] != "http":
            return await self.respond(send,404,{"error":"NOT_FOUND"})
        path=scope.get("raw_path")
        if path != scope.get("path","").encode():
            return await self.respond(send,404,{"error":"NOT_FOUND"})
        method=scope.get("method")
        if method == "GET" and path == b"/health/live":
            return await self.respond(send,200,{"contract_version":"api.app_only_health.v1",
                "service":"api","process":"live","dependencies_verified":self.ready})
        if method == "GET" and path == b"/health/ready":
            # Startup passed is not lasting DB readiness: verify restricted
            # Postgres roles and grants again, with a bounded timeout.
            verified = bool(self.ready and self.inner is not None
                            and self.readiness_probe is not None)
            if verified:
                import asyncio
                try:
                    await asyncio.wait_for(
                        asyncio.to_thread(self.readiness_probe), timeout=7.0)
                except (OSError, RuntimeError, ValueError, Exception):
                    verified = False
            return await self.respond(send,200 if verified else 503,{
                "contract_version":"api.app_only_health.v1",
                "ready":verified,"retrieval":"unavailable","generation":"unavailable"})
        if method == "GET" and path == b"/v1/capabilities":
            return await self.respond(send,200,{
                "contract_version":"api.app_only_capabilities.v1",
                "profile":"app-only","retrieval":"unavailable",
                "generation":"unavailable","send_enabled":False})
        # Gate BEFORE request.stream(), PKI verification, SQL, reservations or spawn.
        if path == b"/v1/messages" and method == "POST":
            return await self.respond(send,503,{"contract_version":"api.app_only_error.v1",
                                                "error":"ENGINE_UNAVAILABLE"})
        if path in (b"/v1/message-requests/engine-status",
                    b"/v1/message-requests/retrieved-sources",
                    b"/v1/message-requests/invited-live-result",
                    b"/v1/message-requests/claim-test-status"):
            return await self.respond(send,503,{"contract_version":"api.app_only_error.v1",
                                                "error":"ENGINE_UNAVAILABLE"})
        if not self.ready or self.inner is None:
            return await self.respond(send,503,{"contract_version":"api.app_only_error.v1",
                                                "error":"APP_DEPENDENCIES_NOT_READY"})
        return await self.inner(scope,receive,send)

# Importing this object cannot start or authorize History, a Runner, or a Gateway.
app=AppOnly()

def load_config(file:Path):
    _protected_file(file,secret=True)
    try:
        cfg=json.loads(file.read_text(encoding="utf-8"))
    except (OSError,ValueError,UnicodeError):
        raise StagingConfigDenied() from None
    if (not isinstance(cfg,dict) or set(cfg)!=FIELDS
            or cfg["contract_version"]!=VERSION or cfg["listen_host"]!="127.0.0.1"
            or type(cfg["listen_port"]) is not int
            or not 1<=cfg["listen_port"]<=65535
            or not isinstance(cfg["bff_leaf_cert_sha256"],str)
            or re.fullmatch("[0-9a-f]{64}",cfg["bff_leaf_cert_sha256"]) is None):
        raise StagingConfigDenied()
    paths={}
    for f in PATH_FIELDS:
        val=cfg[f]
        if not isinstance(val,str) or not val.startswith("/") or ".." in Path(val).parts:
            raise StagingConfigDenied()
        paths[f]=Path(val)
        _protected_file(paths[f],secret=f=="server_tls_key_file")
    for f in ("bff_issuer","bff_audience","bff_kid","history_dsn","revoke_dsn"):
        if not isinstance(cfg[f],str) or not cfg[f]:
            raise StagingConfigDenied()
    return PrivateASGIConfig(
        listen_port=cfg["listen_port"],cert_file=paths["server_tls_cert_file"],
        key_file=paths["server_tls_key_file"],client_ca=paths["trusted_bff_ca_file"],
        bff_leaf_cert_sha256=cfg["bff_leaf_cert_sha256"],
        issuer=cfg["bff_issuer"],audience=cfg["bff_audience"],kid=cfg["bff_kid"],
        public_key_file=paths["bff_rs256_public_key_file"],
        history_dsn=cfg["history_dsn"],revoke_dsn=cfg["revoke_dsn"],
        engine_version="UNAVAILABLE",ledger_file=Path("/dev/null"))

def prepare_private_app(cfg):
    if (os.getenv("API_RUNTIME_PROFILE")!="APP_ONLY"
            or os.getenv("API_RUNNER_EXECUTION_MODE") is not None
            or os.getenv("CI")=="true" or os.getenv("GITHUB_ACTIONS")=="true"):
        raise StagingConfigDenied()
    _test_tls_material(cfg)
    boundary=TrustedBFFTLSBoundary(cfg.bff_leaf_cert_sha256)
    profile=PrivateStagingProfile(
        issuer=cfg.issuer,audience=cfg.audience,kid=cfg.kid,
        public_key_path=cfg.public_key_file,history_dsn=cfg.history_dsn,
        revoke_dsn=cfg.revoke_dsn,peer_verifier=boundary.scope_is_verified)
    BFFServiceVerifier(issuer=profile.issuer,audience=profile.audience,
                       public_keys={profile.kid:profile.load_public_key()})
    verify_staging_database_authority(profile)
    sys.path.insert(0,str(Path(__file__).resolve().parents[2]/
                          "src/phase3/storage/postgres"))
    from apps.api import product_session_api
    product_session_api.install_private_staging_auth(profile)
    return AppOnly(product_session_api.app,ready=True,
                   readiness_probe=lambda: verify_staging_database_authority(profile)),boundary

def main(argv=None):
    parser=argparse.ArgumentParser()
    parser.add_argument("--config",type=Path)
    parser.add_argument("--preflight-only",action="store_true")
    parser.add_argument("--ci-loopback-only",action="store_true")
    opt=parser.parse_args(argv)
    try:
        import uvicorn
        if uvicorn.__version__!="0.48.0":
            raise StagingConfigDenied()
        if opt.ci_loopback_only:
            if (opt.config or opt.preflight_only
                    or os.getenv("CI")!="true"
                    or os.getenv("GITHUB_ACTIONS")!="true"
                    or os.getenv("API_RUNTIME_PROFILE")!="APP_ONLY"):
                raise StagingConfigDenied()
            uvicorn.run(app,host="127.0.0.1",port=8080,
                        proxy_headers=False,access_log=False,
                        server_header=False,ws="none",workers=1)
            return 0
        if opt.config is None:
            raise StagingConfigDenied()
        cfg=load_config(opt.config)
        private,boundary=prepare_private_app(cfg)
        if opt.preflight_only:
            print("APP_ONLY_PKI_PG_ROLE_PREFLIGHT_PASS")
            return 0
        uvicorn.Server(uvicorn.Config(
            app=private,host="127.0.0.1",port=cfg.listen_port,
            http=make_verified_h11_protocol(boundary),ws="none",workers=1,
            loop="asyncio",lifespan="on",proxy_headers=False,
            access_log=False,server_header=False,date_header=False,
            ssl_certfile=str(cfg.cert_file),ssl_keyfile=str(cfg.key_file),
            ssl_ca_certs=str(cfg.client_ca),ssl_cert_reqs=ssl.CERT_REQUIRED,
            ssl_version=ssl.PROTOCOL_TLS_SERVER,
            ssl_context_factory=_harden_tls_context)).run()
        return 0
    except (StagingConfigDenied,VerifiedPeerUnavailable,RuntimeError,OSError,
            ValueError,ssl.SSLError,ImportError,ModuleNotFoundError):
        print("APP_ONLY_STARTUP_DENIED",file=sys.stderr)
        return 78

if __name__=="__main__":
    raise SystemExit(main())
