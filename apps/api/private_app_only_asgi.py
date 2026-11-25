"""Private app-only API listener: signed History/Auth without a RAG engine.

This is an Ops-configured candidate.  It DOES NOT authorize an external
deployment, synthetic model, C018 runner, Gateway, Qdrant or T3.  Config is
only an owner-controlled 0600 file and signed mTLS is required on EVERY route.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import ssl
import sys
from dataclasses import dataclass
from pathlib import Path

from starlette.responses import JSONResponse
from starlette.concurrency import run_in_threadpool
from apps.api.app_only_signer_pin import SignerPin

from apps.api.private_staging_asgi import (
    _harden_tls_context, _protected_file, _test_tls_material,
    verify_staging_database_authority,
)
from src.phase3.auth.staging_service_profile import (
    PrivateStagingProfile, StagingConfigDenied,
)
from src.phase3.auth.service_proof import TrustRejected
from src.phase3.auth.staging_transport_mtls import (
    TrustedBFFTLSBoundary, VerifiedPeerUnavailable, make_verified_h11_protocol,
)

APP_ONLY_VERSION = "api.private_app_only_asgi.v1"
APP_ONLY_FIELDS = frozenset({
    "contract_version", "listen_host", "listen_port",
    "server_tls_cert_file", "server_tls_key_file", "trusted_bff_ca_file",
    "bff_leaf_cert_sha256", "bff_issuer", "bff_audience",
    "bff_kid", "bff_rs256_public_key_file", "history_dsn", "revoke_dsn",
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
        }
        paths = {key: Path(data[name]) for key, name in mapping.items()}
        for key, p in paths.items():
            if not p.is_absolute() or ".." in p.parts:
                raise StagingConfigDenied()
            _protected_file(p, secret=key == "key_file")
        return AppOnlyConfig(
            host=data["listen_host"], port=data["listen_port"],
            cert_file=paths["cert_file"],
            key_file=paths["key_file"], client_ca=paths["client_ca"],
            bff_leaf_cert_sha256=data["bff_leaf_cert_sha256"],
            issuer=data["bff_issuer"], audience=data["bff_audience"],
            kid=data["bff_kid"], public_key_file=paths["public_key_file"],
            history_dsn=data["history_dsn"], revoke_dsn=data["revoke_dsn"],
        )
    except (TypeError, ValueError, KeyError, OSError, UnicodeError):
        raise StagingConfigDenied() from None


def assert_app_only_environment(environ) -> None:
    """CI switches, dispatch toggles and model handles cannot enable app-only."""
    if (environ.get("PHASE3_APP_MODE") != "APP_ONLY"
            or environ.get("API_RUNNER_EXECUTION_MODE") != "APP_ONLY"
            or environ.get("CI") == "true"
            or environ.get("GITHUB_ACTIONS") == "true"
            or any(environ.get(key) for key in _NO_ENGINE_FLAGS)):
        raise StagingConfigDenied()


def _bodyless_get(scope) -> bool:
    """Reject GET payload framing before proof verification or PG admission."""
    lengths = [value for name, value in scope.get("headers", ())
               if name.lower() == b"content-length"]
    return (lengths in ([], [b"0"])
            and not any(name.lower() == b"transfer-encoding"
                        for name, _ in scope.get("headers", ())))


class AppOnlyASGI:
    """mTLS-scope fence plus deny-before-body POST and live PG readiness.

    Only the authorized Product-session app handles History/Revoke.  We never
    dispatch an engine or create a Send receipt.  All error paths are no-store.
    """
    def __init__(self, app, profile: PrivateStagingProfile, *, signer_pin: SignerPin | None = None):
        self._app = app
        self._profile = profile
        self._signer_pin = signer_pin

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
        if (scope.get("path") == "/v1/messages"
                and scope.get("method") == "POST"):
            # Routing uses the percent-decoded ASGI path. A raw-path-only
            # comparison could let /v1/%6dessages bypass the pre-body fence.
            # No body parsing, trusted-user mutation, PG T1/T2, runner queue,
            # synthetic Answer, citation, or Gateway network call.
            from apps.api import history_api
            return await history_api._safe_error(
                503, "ENGINE_NOT_CONFIGURED", "technical",
                "Message sending is unavailable until the engine is enabled.",
            )(scope, receive, private_send)
        # The production composition pins the very key installed in the
        # verifier. A broken/replaced Ops file is not a valid configuration.
        # Keep the no-engine Send denial ahead of this check.
        if (self._signer_pin is not None and not await run_in_threadpool(
                self._signer_pin.current, self._profile.load_public_key)):
            if scope.get("path") == "/health/ready":
                response = JSONResponse(
                    {"kind": "api_app_only_readiness", "state": "unavailable"}, status_code=503)
            elif scope.get("path") == "/internal/ready":
                response = JSONResponse(
                    {"kind": "app_only_readiness", "state": "unavailable",
                     "retrieval": "unavailable", "generation": "unavailable"}, status_code=503)
            elif scope.get("path") == "/internal/auth/session/v1/revoke-one":
                response = JSONResponse({"error": "REVOKE_OUTCOME_UNKNOWN"}, status_code=503)
            else:
                from apps.api import history_api
                response = history_api._safe_error(
                    503, "TEMPORARILY_UNAVAILABLE", "technical", "History unavailable.")
            return await response(scope, receive, private_send)
        # Signed History reads bind exactly b"". A body-bearing GET cannot
        # be admitted under an otherwise valid empty-body BFF assertion.
        if scope.get("method") == "GET" and not _bodyless_get(scope):
            if scope.get("path") == "/health/ready":
                return await JSONResponse(
                    {"kind": "api_app_only_readiness", "state": "unavailable"},
                    status_code=503)(scope, receive, private_send)
            if scope.get("path") == "/internal/ready":
                return await JSONResponse(
                    {"kind": "app_only_readiness", "state": "unavailable",
                     "retrieval": "unavailable", "generation": "unavailable"},
                    status_code=503)(scope, receive, private_send)
            from apps.api import history_api
            return await history_api._safe_error(
                401, "AUTH_REQUIRED", "authorization", "Authentication required.",
            )(scope, receive, private_send)
        if scope.get("raw_path") == b"/health/ready":
            # Strict readiness checks the *same* signed 004/005 session
            # admission and owner-bound PostgreSQL transaction as History.
            # PG-role-only /internal/ready is NOT proof the BFF signer works.
            if (scope.get("method") != "GET"
                    or scope.get("query_string")):
                return await JSONResponse(
                    {"kind": "api_app_only_readiness", "state": "unavailable"},
                    status_code=503)(scope, receive, private_send)
            try:
                from starlette.requests import Request
                from apps.api import product_session_api, history_api
                request = Request(scope, receive)

                def probe_history(ctx):
                    # Verify the actual canonical owner-scoped History read,
                    # including cursor config and response validation. Do not
                    # expose the returned conversations in a readiness DTO.
                    history_api._cursor_config()
                    page = history_api.conversations(request, ctx)
                    if page.status_code != 200:
                        raise StagingConfigDenied()

                # No synthetic owner, no Auth override. Cryptographic
                # issuer/audience/method/path/session/PG binding is checked
                # inside the original signed, transaction-fenced function.
                # The real PG session/replay transaction is synchronous.
                # Never block the ASGI event loop for a slow dependency:
                # separate requests (including deny-before-body Send) must
                # remain schedulable while readiness probes PG.
                await run_in_threadpool(
                    product_session_api._signed_history,
                    request, b"", b"/health/ready", probe_history,
                )
            except Exception:
                # Signature, role, session, revoked user, PG outage and
                # uncertain transaction results are all fail-closed.
                return await JSONResponse(
                    {"kind": "api_app_only_readiness", "state": "unavailable"},
                    status_code=503)(scope, receive, private_send)
            return await JSONResponse({
                "kind": "api_app_only_readiness",
                "state": "ready",
                "signed_actor_pg": "verified",
                "bootstrap_idp": "not_probed",
                "retrieval": "unavailable", "generation": "unavailable",
            })(scope, receive, private_send)
        if (scope.get("raw_path") == b"/internal/ready"
                and scope.get("method") == "GET"
                and not scope.get("query_string")):
            try:
                # Real role/004+005 metadata queries are synchronous.
                # Keep /internal/ready from blocking unrelated ASGI traffic.
                await run_in_threadpool(
                    verify_staging_database_authority, self._profile)
            except (StagingConfigDenied, OSError, RuntimeError):
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
        return await self._app(scope, receive, private_send)


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
    signer_pin = SignerPin.capture(public_key)
    BFFServiceVerifier(
        issuer=cfg.issuer, audience=cfg.audience,
        public_keys={cfg.kid: public_key})
    verify_staging_database_authority(profile)
    # Original History API imports repository as a top-level module. Do not
    # mutate product.v1, reimplement SQL, or import a fixture.
    module_dir = Path(__file__).resolve().parents[2] / "src/phase3/storage/postgres"
    if str(module_dir) not in sys.path:
        sys.path.insert(0, str(module_dir))
    from apps.api import product_session_api, history_api
    # App-only must never inherit an already installed execution capability
    # from another composition in this interpreter. Reject rather than clear
    # it silently (which would conceal an invalid server startup).
    if any(getattr(product_session_api, name) is not None for name in (
            "_SERVER_NO_DISPATCH_TASK", "_CI_CLAIM_STUB",
            "_CI_DISPATCH_REPORTER_DSN", "_CI_INVITED_RESULT_STORE")):
        raise StagingConfigDenied()
    # Real History pagination depends on a stable, server-owned HMAC key.
    # Never start a seemingly "ready" API that fails on the second page.
    # This is the original History cursor contract, not a new wire DTO.
    try:
        history_api._cursor_config()
    except history_api.ApiFailure:
        raise StagingConfigDenied() from None
    product_session_api.install_private_staging_auth(profile, expected_public_key=public_key)
    return AppOnlyASGI(product_session_api.app, profile, signer_pin=signer_pin), boundary


def run_app_only(config_file: Path) -> None:
    cfg = load_app_only_config(config_file)
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
    except (StagingConfigDenied, VerifiedPeerUnavailable, TrustRejected,
            ImportError, ModuleNotFoundError, ValueError, RuntimeError, OSError):
        print("APP_ONLY_STARTUP_DENIED", file=sys.stderr)
        return 78
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
