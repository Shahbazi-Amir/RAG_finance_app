"""Private HTTPS/mTLS + RS256 Initial OIDC Bootstrap for staging.

The public OAuth callback is handled ONLY by the Next BFF:
https://ragfinance.ir/api/auth/callback. This private server exposes exactly
five POST RPC endpoints under /internal/auth/oidc/v1; never a browser
redirect. No staging DB creation/grants, no CI fallback, no product Answer,
Runner, Gateway or HTTP header-based client-certificate identity.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import ssl
import stat
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.concurrency import run_in_threadpool

from apps.api.private_staging_asgi import _protected_file, _test_tls_material, _harden_tls_context
from src.phase3.auth.bootstrap_oidc import BootstrapOIDC, BootstrapDenied, OPS, PATH_ROOT
from src.phase3.auth.staging_service_profile import StagingConfigDenied
from src.phase3.auth.staging_transport_mtls import (
    TrustedBFFTLSBoundary, VerifiedPeerUnavailable, make_verified_h11_protocol,
)

CONFIG_VERSION = "api.private_oidc_bootstrap_asgi.v1"
REDIRECT_URI = "https://ragfinance.ir/api/auth/callback"
HEX64 = re.compile(r"^[0-9a-f]{64}$")
KID = re.compile(r"^[A-Za-z0-9_.-]{1,80}$")
FKEY = re.compile(rb"^[A-Za-z0-9_-]{43}=$")
ROLES = {
    "replay": "auth_trust_api",
    "bootstrap": "auth_login_bootstrap",
    "claim_reader": "auth_login_claim_reader",
    "issuer": "auth_login_issuer",
    "mapper": "auth_mapper",
    "binder": "auth_login_binder",
    "reader": "auth_login_reader",
}
FUNCTIONS = {
    "replay": ("auth_l1.consume_service_assertion(text,bigint)",),
    "bootstrap": (
        "auth_l1.start_initial_login_attempt(uuid,text,uuid,text,text,text,text,text,bytea,bytea,integer)",
        "auth_l1.mark_initial_login_unknown(uuid,text,text)",
    ),
    "claim_reader": (
        "auth_l1.claim_initial_login_exchange_material(uuid,text,uuid,text,text)",
    ),
    "issuer": (
        "auth_l1.issue_initial_login_pending(uuid,text,text,text,text,text,bigint,text,integer,integer)",
    ),
    "mapper": ("auth_l1.map_identity(text,text)",),
    "binder": (
        "auth_l1.ack_initial_login_binding(uuid,uuid,text,text,text,bigint,text)",
        "auth_l1.abort_initial_login_binding(uuid,uuid,text,text,text,bigint)",
    ),
    "reader": ("auth_l1.status_initial_login_attempt(uuid,text,text)",),
}
CONFIG_FIELDS = frozenset({
    "contract_version", "listen_host", "listen_port",
    "server_tls_cert_file", "server_tls_key_file", "trusted_bff_ca_file",
    "bff_leaf_cert_sha256", "bff_issuer", "bff_audience", "bff_kid",
    "bff_rs256_public_key_file", "seal_key_file", "seal_key_kid",
    "idp_ca_file", "oidc_issuer", "oidc_authorization_endpoint",
    "oidc_token_endpoint", "oidc_jwks_uri", "oidc_client_id",
    "oidc_redirect_uri", "dsn_replay", "dsn_bootstrap",
    "dsn_claim_reader", "dsn_issuer", "dsn_mapper", "dsn_binder",
    "dsn_reader",
})
PROTECTED_RESPONSE_HEADERS = {"Cache-Control": "no-store",
    "X-Content-Type-Options": "nosniff"}


@dataclass(frozen=True, repr=False)
class StagingBootstrapConfig:
    port: int
    cert_file: Path
    key_file: Path
    client_ca: Path
    leaf_sha256: str
    issuer: str
    audience: str
    kid: str
    public_key: Path
    seal_key: Path
    seal_kid: str
    idp_ca: Path
    oidc: dict
    client_id: str
    redirect_uri: str
    dsns: dict

    def __repr__(self):
        return "StagingBootstrapConfig(<redacted>)"


def load_staging_bootstrap_config(path: Path) -> StagingBootstrapConfig:
    """Exactly one Ops-owned 0600 config; no .env, browser or CI defaults."""
    _protected_file(path, secret=True)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, UnicodeError):
        raise StagingConfigDenied() from None
    if (not isinstance(data, dict) or set(data) != CONFIG_FIELDS
            or data.get("contract_version") != CONFIG_VERSION
            or data.get("listen_host") != "127.0.0.1"
            or type(data.get("listen_port")) is not int
            or not 1 <= data["listen_port"] <= 65535
            or data.get("oidc_redirect_uri") != REDIRECT_URI
            or not isinstance(data.get("bff_leaf_cert_sha256"), str)
            or not HEX64.fullmatch(data["bff_leaf_cert_sha256"])
            or not isinstance(data.get("bff_kid"), str)
            or not KID.fullmatch(data["bff_kid"])
            or not isinstance(data.get("seal_key_kid"), str)
            or not re.fullmatch(r"[A-Za-z0-9_-]{1,32}", data["seal_key_kid"])):
        raise StagingConfigDenied()
    paths = {}
    for key in ("server_tls_cert_file", "server_tls_key_file",
                "trusted_bff_ca_file", "bff_rs256_public_key_file",
                "seal_key_file", "idp_ca_file"):
        value = data[key]
        if (not isinstance(value, str) or not value.startswith("/")
                or ".." in Path(value).parts):
            raise StagingConfigDenied()
        paths[key] = Path(value)
        _protected_file(paths[key], secret=key in {
            "server_tls_key_file", "seal_key_file"})
    for key in ("bff_issuer", "bff_audience", "oidc_issuer",
                "oidc_authorization_endpoint", "oidc_token_endpoint",
                "oidc_jwks_uri", "oidc_client_id"):
        if not isinstance(data[key], str) or not data[key]:
            raise StagingConfigDenied()
    dsns = {}
    for role in ROLES:
        value = data["dsn_" + role]
        if not isinstance(value, str) or not value:
            raise StagingConfigDenied()
        dsns[role] = value
    return StagingBootstrapConfig(
        port=data["listen_port"],
        cert_file=paths["server_tls_cert_file"],
        key_file=paths["server_tls_key_file"],
        client_ca=paths["trusted_bff_ca_file"],
        leaf_sha256=data["bff_leaf_cert_sha256"],
        issuer=data["bff_issuer"], audience=data["bff_audience"],
        kid=data["bff_kid"], public_key=paths["bff_rs256_public_key_file"],
        seal_key=paths["seal_key_file"], seal_kid=data["seal_key_kid"],
        idp_ca=paths["idp_ca_file"],
        oidc={
            "issuer": data["oidc_issuer"],
            "authorization_endpoint": data["oidc_authorization_endpoint"],
            "token_endpoint": data["oidc_token_endpoint"],
            "jwks_uri": data["oidc_jwks_uri"],
        },
        client_id=data["oidc_client_id"],
        redirect_uri=data["oidc_redirect_uri"], dsns=dsns,
    )


def verify_bootstrap_roles(dsns: Mapping[str, str]) -> None:
    """Read-only PG role identity, function EXECUTE and table SELECT denial.

    Does NOT apply migrations or grants. Actual DB staging must be provisioned
    separately after the successfully audited disposable clone.
    """
    import psycopg
    from psycopg.rows import dict_row
    if not isinstance(dsns, Mapping) or set(dsns) != set(ROLES):
        raise StagingConfigDenied()
    for role, user in ROLES.items():
        try:
            info = psycopg.conninfo.conninfo_to_dict(dsns[role])
            host = info.get("host")
            if (info.get("user") != user
                    or not isinstance(info.get("dbname"), str)
                    or info["dbname"] in {"history_ci", "postgres", "template0", "template1"}
                    or not isinstance(host, str) or not host
                    or info.get("sslmode") in {"disable", "allow", "prefer", "require"}
                    or (not (host.startswith("/") or host in {
                        "localhost", "127.0.0.1", "::1"})
                        and (info.get("sslmode") != "verify-full"
                             or not Path(info.get("sslrootcert", "")).is_absolute()))):
                raise StagingConfigDenied()
            with psycopg.connect(dsns[role], autocommit=True,
                                 row_factory=dict_row, connect_timeout=5) as conn:
                row = conn.execute(
                    "SELECT rolname,rolsuper,rolbypassrls FROM pg_roles "
                    "WHERE rolname=current_user").fetchone()
                if (row is None or row["rolname"] != user
                        or row["rolsuper"] or row["rolbypassrls"]):
                    raise StagingConfigDenied()
                if not conn.execute(
                    "SELECT has_schema_privilege(current_user,'auth_l1','USAGE') AS ok"
                ).fetchone()["ok"]:
                    raise StagingConfigDenied()
                for signature in FUNCTIONS[role]:
                    if conn.execute(
                        "SELECT has_function_privilege(current_user,%s,'EXECUTE') AS ok",
                        (signature,),
                    ).fetchone()["ok"] is not True:
                        raise StagingConfigDenied()
                # Bootstrap BFF is function-only. No direct table reads.
                for table in ("auth_l1.initial_login_attempts",
                              "auth_l1.sessions",
                              "auth_l1.service_assertion_replays"):
                    if conn.execute(
                        "SELECT has_table_privilege(current_user,%s,'SELECT') AS ok",
                        (table,),
                    ).fetchone()["ok"]:
                        raise StagingConfigDenied()
        except (psycopg.Error, OSError, ValueError, TypeError):
            raise StagingConfigDenied() from None


def build_bootstrap_service(cfg: StagingBootstrapConfig, *, check_db=True):
    """Validate OIDC HTTPS and exact callback; create service before listen."""
    # check_db=False is ONLY an off-server unit-test constructor, never an
    # executable staging server. The runner always calls check_db=True.
    if check_db and (os.getenv("CI") == "true"
                     or os.getenv("GITHUB_ACTIONS") == "true"):
        raise StagingConfigDenied()
    from src.phase3.auth.service_proof import BFFServiceVerifier
    from cryptography.fernet import Fernet
    _test_tls_material(cfg)
    boundary = TrustedBFFTLSBoundary(cfg.leaf_sha256)
    public = cfg.public_key.read_bytes()
    BFFServiceVerifier(
        issuer=cfg.issuer, audience=cfg.audience,
        public_keys={cfg.kid: public})
    seal = cfg.seal_key.read_bytes().strip()
    if not FKEY.fullmatch(seal):
        raise StagingConfigDenied()
    Fernet(seal)  # never log key or sealed login material
    service = BootstrapOIDC(
        service_issuer=cfg.issuer, audience=cfg.audience,
        service_keys={cfg.kid: public},
        cert_fingerprints={cfg.issuer: cfg.leaf_sha256},
        seal_keys={cfg.seal_kid: seal},
        active_seal_kid=cfg.seal_kid,
        db_dsn=cfg.dsns, oidc=cfg.oidc, client_id=cfg.client_id,
        redirect_uri=cfg.redirect_uri,
        runtime_profile="private_staging", idp_ca_file=str(cfg.idp_ca),
    )
    if check_db:
        verify_bootstrap_roles(cfg.dsns)
    return service, boundary


async def _bounded_json_body(request: Request) -> bytes:
    """Prevent unbounded allocations on a client-supplied Content-Length."""
    if request.scope.get("query_string") not in (b"", None):
        raise BootstrapDenied(401)
    if request.scope.get("raw_path") != request.url.path.encode("ascii"):
        raise BootstrapDenied(401)
    headers = request.scope.get("headers", [])
    authorization = [v for k, v in headers if k.lower() == b"authorization"]
    content_types = [v for k, v in headers if k.lower() == b"content-type"]
    lengths = [v for k, v in headers if k.lower() == b"content-length"]
    if (len(authorization) != 1 or len(content_types) != 1
            or content_types[0].lower() != b"application/json"
            or len(lengths) > 1):
        raise BootstrapDenied(401)
    if lengths:
        try:
            n = int(lengths[0])
            if n < 0 or n > 8192:
                raise BootstrapDenied(413)
        except ValueError:
            raise BootstrapDenied(401) from None
    chunks, size = [], 0
    async for fragment in request.stream():
        size += len(fragment)
        if size > 8192:
            raise BootstrapDenied(413)
        chunks.append(fragment)
    return b"".join(chunks)


def create_bootstrap_app(service: BootstrapOIDC, boundary: TrustedBFFTLSBoundary):
    if not isinstance(service, BootstrapOIDC) or not isinstance(
            boundary, TrustedBFFTLSBoundary):
        raise StagingConfigDenied()
    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None,
                  title="Private Initial OIDC Bootstrap")

    async def operation(request: Request):
        try:
            der = boundary.peer_der_from_scope(request.scope)
            if der is None:
                raise BootstrapDenied()
            raw = await _bounded_json_body(request)
            header = [v for k, v in request.scope["headers"]
                      if k.lower() == b"authorization"][0].decode("ascii")
            if len(header) > 4150:
                raise BootstrapDenied()
            status, data = await run_in_threadpool(
                service.handle, peer_der=der,
                authorization=header, method="POST",
                path=request.url.path, raw_body=raw)
            return JSONResponse(status_code=status, content=data,
                                headers=PROTECTED_RESPONSE_HEADERS)
        except BootstrapDenied as exc:
            return JSONResponse(
                status_code=exc.status,
                content={"kind": "bootstrap_error", "status": "DENIED"},
                headers=PROTECTED_RESPONSE_HEADERS)
        except (UnicodeError, ValueError, KeyError, OSError, RuntimeError):
            return JSONResponse(
                status_code=503,
                content={"kind": "bootstrap_error", "status": "UNAVAILABLE"},
                headers=PROTECTED_RESPONSE_HEADERS)

    for name in sorted(OPS):
        app.add_api_route(PATH_ROOT + name, operation, methods=["POST"],
                          include_in_schema=False)
    return app


def run_staging_bootstrap(config_path: Path, *, preflight_only=False) -> None:
    if os.getenv("CI") == "true" or os.getenv("GITHUB_ACTIONS") == "true":
        raise StagingConfigDenied()
    cfg = load_staging_bootstrap_config(config_path)
    service, boundary = build_bootstrap_service(cfg)
    if preflight_only:
        print("PRIVATE_BOOTSTRAP_PREFLIGHT_PASS")
        return
    import uvicorn
    if uvicorn.__version__ != "0.48.0":
        raise StagingConfigDenied()
    app = create_bootstrap_app(service, boundary)
    uvicorn.Server(uvicorn.Config(
        app=app, host="127.0.0.1", port=cfg.port,
        loop="asyncio", http=make_verified_h11_protocol(boundary), ws="none",
        lifespan="on", workers=1, reload=False, proxy_headers=False,
        access_log=False, server_header=False, date_header=False,
        limit_concurrency=32, timeout_keep_alive=5,
        ssl_certfile=str(cfg.cert_file), ssl_keyfile=str(cfg.key_file),
        ssl_ca_certs=str(cfg.client_ca), ssl_cert_reqs=ssl.CERT_REQUIRED,
        ssl_version=ssl.PROTOCOL_TLS_SERVER,
        ssl_context_factory=_harden_tls_context,
    )).run()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Staging-only HTTPS mTLS OIDC bootstrap")
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--preflight-only", action="store_true")
    args = parser.parse_args(argv)
    try:
        run_staging_bootstrap(args.config, preflight_only=args.preflight_only)
    except (BootstrapDenied, StagingConfigDenied, VerifiedPeerUnavailable,
            OSError, RuntimeError, ValueError, TypeError, ssl.SSLError):
        print("PRIVATE_BOOTSTRAP_STARTUP_DENIED", file=sys.stderr)
        return 78
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
