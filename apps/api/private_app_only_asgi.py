"""Private app-only API listener: signed History/Auth without a RAG engine.

This is an Ops-configured candidate.  It DOES NOT authorize an external
deployment, synthetic model, C018 runner, Gateway, Qdrant or T3.  Config is
only an owner-controlled 0600 file and signed mTLS is required on EVERY route.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import ssl
import sys
from dataclasses import dataclass
from pathlib import Path

from starlette.responses import JSONResponse
from starlette.concurrency import run_in_threadpool

from apps.api.private_staging_asgi import (
    _harden_tls_context, _protected_file, _test_tls_material,
    verify_staging_database_authority,
)
from src.phase3.auth.staging_service_profile import (
    PrivateStagingProfile, StagingConfigDenied,
)
from src.phase3.auth.staging_transport_mtls import (
    TrustedBFFTLSBoundary, VerifiedPeerUnavailable, make_verified_h11_protocol,
)

APP_ONLY_VERSION = "api.private_app_only_asgi.v2"
APP_ONLY_FIELDS = frozenset({
    "contract_version", "listen_host", "listen_port",
    "server_tls_cert_file", "server_tls_key_file", "trusted_bff_ca_file",
    "bff_leaf_cert_sha256", "bff_issuer", "bff_audience",
    "bff_kid", "bff_rs256_public_key_file", "history_dsn", "revoke_dsn",
    "cursor_key_file", "cursor_ttl_seconds",
})
_HEX64 = re.compile(r"^[0-9a-f]{64}$")
_NO_ENGINE_FLAGS = (
    "C018_RUNNER_PATH", "QDRANT_URL", "MODEL_GATEWAY_URL",
    "OPENAI_API_KEY", "API_ENGINE_ENABLED", "API_PROVIDER_KEY",
)


@dataclass(frozen=True, repr=False)
class AppOnlyConfig:
    host: str
    port: int
    cert_file: Path
    key_file: Path
    client_ca: Path
    bff_leaf_cert_sha256: str
    issuer: str
    audience: str
    kid: str
    public_key_file: Path
    history_dsn: str
    revoke_dsn: str
    cursor_key_file: Path
    cursor_ttl_seconds: int

    def __repr__(self):
        return "AppOnlyConfig(<private>)"


def _unique_config_keys(pairs):
    fields = {}
    for name, value in pairs:
        if name in fields:
            raise StagingConfigDenied()
        fields[name] = value
    return fields


def _deny_non_json_constant(_):
    raise StagingConfigDenied()


def read_cursor_key(path: Path) -> str:
    """An owner-only, high-entropy ASCII token; never print or return over HTTP."""
    _protected_file(path, secret=True)
    try:
        key = path.read_text(encoding="ascii").strip()
        if not re.fullmatch(r"[A-Za-z0-9_-]{43,128}", key):
            raise StagingConfigDenied()
        return key
    except (OSError, UnicodeError):
        raise StagingConfigDenied() from None


def load_app_only_config(path: Path) -> AppOnlyConfig:
    """Strict 0600 server file; reject duplicate keys, non-JSON and engine."""
    _protected_file(path, secret=True)
    try:
        data = json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=_unique_config_keys,
            parse_constant=_deny_non_json_constant,
        )
        if (not isinstance(data, dict) or set(data) != APP_ONLY_FIELDS
                or data.get("contract_version") != APP_ONLY_VERSION
                or data.get("listen_host") not in {"127.0.0.1", "0.0.0.0"}
                or type(data.get("listen_port")) is not int
                or not 1 <= data["listen_port"] <= 65535
                or type(data.get("cursor_ttl_seconds")) is not int
                or not 1 <= data["cursor_ttl_seconds"] <= 3600
                or not isinstance(data.get("bff_leaf_cert_sha256"), str)
                or not _HEX64.fullmatch(data["bff_leaf_cert_sha256"])):
            raise StagingConfigDenied()
        for field in ("bff_issuer", "bff_audience", "bff_kid",
                      "history_dsn", "revoke_dsn"):
            if not isinstance(data[field], str) or not data[field]:
                raise StagingConfigDenied()
        mapping = {
            "cert_file": "server_tls_cert_file",
            "key_file": "server_tls_key_file",
            "client_ca": "trusted_bff_ca_file",
            "public_key_file": "bff_rs256_public_key_file",
            "cursor_key_file": "cursor_key_file",
        }
        paths = {key: Path(data[name]) for key, name in mapping.items()}
        for key, p in paths.items():
            if not p.is_absolute() or ".." in p.parts:
                raise StagingConfigDenied()
            _protected_file(p, secret=key in {"key_file", "cursor_key_file"})
        read_cursor_key(paths["cursor_key_file"])
        return AppOnlyConfig(
            host=data["listen_host"], port=data["listen_port"],
            cert_file=paths["cert_file"],
            key_file=paths["key_file"], client_ca=paths["client_ca"],
            bff_leaf_cert_sha256=data["bff_leaf_cert_sha256"],
            issuer=data["bff_issuer"], audience=data["bff_audience"],
            kid=data["bff_kid"], public_key_file=paths["public_key_file"],
            history_dsn=data["history_dsn"], revoke_dsn=data["revoke_dsn"],
            cursor_key_file=paths["cursor_key_file"],
            cursor_ttl_seconds=data["cursor_ttl_seconds"],
        )
    except (TypeError, ValueError, KeyError, OSError, UnicodeError):
        raise StagingConfigDenied() from None


def assert_app_only_environment(environ) -> None:
    """CI switches, dispatch toggles and model handles cannot enable app-only."""
    if (environ.get("API_RUNNER_EXECUTION_MODE") != "APP_ONLY"
            or environ.get("CI") == "true"
            or environ.get("GITHUB_ACTIONS") == "true"
            or any(environ.get(key) for key in _NO_ENGINE_FLAGS)):
        raise StagingConfigDenied()


class AppOnlyASGI:
    """mTLS-scope fence plus deny-before-body POST and live PG readiness.

    Only the authorized Product-session app handles History/Revoke.  We never
    dispatch an engine or create a Send receipt.  All error paths are no-store.
    """
    def __init__(self, app, profile: PrivateStagingProfile, *, signing_key_sha256=None):
        self._app = app
        self._profile = profile
        self._signing_key_sha256 = signing_key_sha256

    async def __call__(self, scope, receive, send):
        async def private_send(event):
            if event["type"] == "http.response.start":
                headers = [(k, v) for k, v in event.get("headers", ())
                           if k.lower() not in {b"cache-control",
                                               b"x-content-type-options"}]
                event = dict(event, headers=headers + [
                    (b"cache-control", b"no-store"),
                    (b"x-content-type-options", b"nosniff")])
            await send(event)

        if scope["type"] == "lifespan":
            return await self._app(scope, receive, send)
        if scope["type"] != "http":
            return await JSONResponse(
                {"error": "AUTH_REQUIRED"}, status_code=401,
                headers={"Cache-Control": "no-store"})(scope, receive, private_send)
        if not self._profile.allowed_peer(scope):
            return await JSONResponse(
                {"error": "AUTH_REQUIRED"}, status_code=401,
                headers={"Cache-Control": "no-store"})(scope, receive, private_send)
        if os.environ.get("API_RUNNER_EXECUTION_MODE") != "APP_ONLY":
            return await JSONResponse(
                {"error": "SERVICE_UNAVAILABLE"}, status_code=503,
                headers={"Cache-Control": "no-store"})(scope, receive, private_send)
        if (scope.get("raw_path") == b"/v1/messages"
                and scope.get("method") == "POST"):
            # No body parsing, trusted-user mutation, PG T1/T2, runner queue,
            # synthetic Answer, citation, or Gateway network call.
            return await JSONResponse({"error": "ENGINE_NOT_AVAILABLE"}, status_code=503)(scope, receive, private_send)
        if (scope.get("raw_path") == b"/internal/ready"
                and scope.get("method") == "GET"
                and not scope.get("query_string")):
            try:
                if self._signing_key_sha256 is not None:
                    current = hashlib.sha256(self._profile.load_public_key()).hexdigest()
                    if current != self._signing_key_sha256:
                        raise StagingConfigDenied()
                    from apps.api import history_api
                    try:
                        history_api._cursor_config()
                    except history_api.ApiFailure:
                        raise StagingConfigDenied() from None
                await run_in_threadpool(verify_staging_database_authority, self._profile)
            except (StagingConfigDenied, OSError, RuntimeError, ValueError, TypeError):
                return await JSONResponse(
                    {"kind": "app_only_readiness", "state": "unavailable",
                     "retrieval": "unavailable", "generation": "unavailable"},
                    status_code=503,
                    headers={"Cache-Control": "no-store"})(scope, receive, private_send)
            return await JSONResponse(
                {"kind": "app_only_readiness", "state": "ready",
                 "history_db": "verified", "bootstrap_idp": "not_probed",
                 "retrieval": "unavailable", "generation": "unavailable"},
                headers={"Cache-Control": "no-store"})(scope, receive, private_send)
        # Exact raw paths only: never delegate an alternate encoding, slash
        # redirect, future mutation, engine route, or fixture to the inner app.
        raw = scope.get("raw_path", b"")
        method = scope.get("method")
        if method == "GET" and raw in (b"/health/live", b"/health/ready", b"/v1/capabilities") and not scope.get("query_string"):
            # Full product readiness remains false until Bootstrap and IdP
            # are probed by the integrated candidate. PG-only /internal/ready
            # is a separate, explicitly scoped API signal.
            from apps.api.app_only_asgi import live, ready, capabilities
            handlers = {b"/health/live": live, b"/health/ready": ready,
                        b"/v1/capabilities": capabilities}
            response = await handlers[raw]()
            return await response(scope, receive, private_send)
        read_path = (raw in (b"/v1/conversations", b"/v1/message-requests/status")
                     or re.fullmatch(rb"/v1/conversations/[A-Za-z0-9][A-Za-z0-9_-]{0,63}/messages", raw))
        if ((method == "GET" and read_path)
                or (method == "POST" and raw == b"/internal/auth/session/v1/revoke-one")):
            return await self._app(scope, receive, private_send)
        return await JSONResponse({"error": "PRODUCT_ROUTE_NOT_AVAILABLE"}, status_code=404)(scope, receive, private_send)


def prepare_app_only(cfg: AppOnlyConfig, environ=None):
    """Preflight real DB+TLS without a C018 lock, spawn, ledger or model."""
    environ = os.environ if environ is None else environ
    assert_app_only_environment(environ)
    _test_tls_material(cfg)
    boundary = TrustedBFFTLSBoundary(cfg.bff_leaf_cert_sha256)
    profile = PrivateStagingProfile(
        issuer=cfg.issuer, audience=cfg.audience, kid=cfg.kid,
        public_key_path=cfg.public_key_file,
        history_dsn=cfg.history_dsn, revoke_dsn=cfg.revoke_dsn,
        peer_verifier=boundary.scope_is_verified,
    )
    from src.phase3.auth.service_proof import BFFServiceVerifier
    public_key = profile.load_public_key()
    BFFServiceVerifier(
        issuer=cfg.issuer, audience=cfg.audience,
        public_keys={cfg.kid: public_key})
    verify_staging_database_authority(profile)
    # Original History API imports repository as a top-level module. Do not
    # mutate product.v1, reimplement SQL, or import a fixture.
    module_dir = Path(__file__).resolve().parents[2] / "src/phase3/storage/postgres"
    if str(module_dir) not in sys.path:
        sys.path.insert(0, str(module_dir))
    from apps.api import product_session_api
    product_session_api.install_private_staging_auth(profile)
    if profile.load_public_key() != public_key:
        raise StagingConfigDenied()
    return AppOnlyASGI(product_session_api.app, profile,
                       signing_key_sha256=hashlib.sha256(public_key).hexdigest()), boundary


def run_app_only(config_file: Path) -> None:
    cfg = load_app_only_config(config_file)
    # The existing canonical History cursor implementation reads these from
    # this process only. The trusted file wins over inherited env settings.
    os.environ["API_CURSOR_KEY"] = read_cursor_key(cfg.cursor_key_file)
    os.environ["API_CURSOR_TTL_SECONDS"] = str(cfg.cursor_ttl_seconds)
    app, boundary = prepare_app_only(cfg)
    import uvicorn
    if uvicorn.__version__ != "0.48.0":
        raise StagingConfigDenied()
    server_cfg = uvicorn.Config(
        app=app, host=cfg.host, port=cfg.port,
        loop="asyncio", http=make_verified_h11_protocol(boundary),
        ws="none", lifespan="on", workers=1, reload=False,
        proxy_headers=False, access_log=False,
        server_header=False, date_header=False,
        limit_concurrency=32, timeout_keep_alive=5,
        ssl_certfile=str(cfg.cert_file), ssl_keyfile=str(cfg.key_file),
        ssl_ca_certs=str(cfg.client_ca), ssl_cert_reqs=ssl.CERT_REQUIRED,
        ssl_version=ssl.PROTOCOL_TLS_SERVER,
        ssl_context_factory=_harden_tls_context,
    )
    uvicorn.Server(server_cfg).run()


def main(argv=None):
    parser = argparse.ArgumentParser(description="Private app-only API, no engine")
    parser.add_argument("--config", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        run_app_only(args.config)
    except (StagingConfigDenied, VerifiedPeerUnavailable,
            ImportError, ModuleNotFoundError, ValueError, RuntimeError, OSError):
        print("APP_ONLY_STARTUP_DENIED", file=sys.stderr)
        return 78
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
