"""Private staging product API ASGI entrypoint. ONE NO_DISPATCH_ONLY worker.

An Ops-owned 0600 JSON config is loaded BEFORE any socket is bound.
TLS is terminated in this process: OpenSSL CERT_REQUIRED validates the BFF
chain, and src.phase3.auth.staging_transport_mtls verifies its pinned leaf
fingerprint and injects an in-process object capability. We NEVER interpret
forwarded client certificate / identity / issuer headers as trust evidence.

This is an importable executable, NOT an authorized deployment, SQL grant,
live Gateway client, product.v1 Answer, or confirmation of a host service.
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

from src.phase3.auth.staging_service_profile import (
    PrivateStagingProfile, StagingConfigDenied, RUNNER_C018_SHA256,
)
from src.phase3.auth.staging_transport_mtls import (
    TrustedBFFTLSBoundary, make_verified_h11_protocol, VerifiedPeerUnavailable,
)
from src.phase3.rag_runtime.staging_preflight import (
    RunnerLayout, PreflightDenied, inspect_no_dispatch,
)
from src.phase3.rag_runtime.staging_service_bootstrap import PrivateStagingEngineConfig
from src.phase3.rag_runtime.staging_no_dispatch import _matches_exact_file_sha

CONFIG_VERSION = "api.private_no_dispatch_asgi.v1"
REQUIRED_CONFIG_FIELDS = frozenset({
    "contract_version", "listen_host", "listen_port",
    "server_tls_cert_file", "server_tls_key_file", "trusted_bff_ca_file",
    "bff_leaf_cert_sha256", "bff_issuer", "bff_audience",
    "bff_kid", "bff_rs256_public_key_file",
    "history_dsn", "revoke_dsn", "engine_version", "ledger_file",
})
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


def _protected_file(path: Path, *, secret=False) -> None:
    if not isinstance(path, Path) or not path.is_absolute():
        raise StagingConfigDenied()
    try:
        mode = path.lstat()
        if (not stat.S_ISREG(mode.st_mode)
                or mode.st_uid not in (0, os.geteuid())
                or mode.st_size < 1
                or mode.st_size > 65536
                or stat.S_IMODE(mode.st_mode) & (0o077 if secret else 0o022)):
            raise StagingConfigDenied()
        if not os.access(path, os.R_OK):
            raise StagingConfigDenied()
    except OSError:
        raise StagingConfigDenied() from None


@dataclass(frozen=True, repr=False)
class PrivateASGIConfig:
    listen_port: int
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
    engine_version: str
    ledger_file: Path

    def __repr__(self):
        return "PrivateASGIConfig(<redacted>)"


def load_private_config(config_path: Path) -> PrivateASGIConfig:
    """Config is server-only 0600 owned by root or runtime UID, NOT .env."""
    _protected_file(config_path, secret=True)
    try:
        doc = json.loads(config_path.read_text(encoding="utf-8"))
    except (ValueError, UnicodeError, OSError):
        raise StagingConfigDenied() from None
    if (not isinstance(doc, dict) or set(doc) != REQUIRED_CONFIG_FIELDS
            or doc.get("contract_version") != CONFIG_VERSION
            or doc.get("listen_host") != "127.0.0.1"
            or type(doc.get("listen_port")) is not int
            or not 1 <= doc["listen_port"] <= 65535
            or not isinstance(doc.get("bff_leaf_cert_sha256"), str)
            or _SHA256.fullmatch(doc["bff_leaf_cert_sha256"]) is None):
        raise StagingConfigDenied()
    names = {
        "cert_file": "server_tls_cert_file",
        "key_file": "server_tls_key_file",
        "client_ca": "trusted_bff_ca_file",
        "public_key_file": "bff_rs256_public_key_file",
        "ledger_file": "ledger_file",
    }
    try:
        paths = {k: Path(doc[v]) for k, v in names.items()}
    except (TypeError, ValueError):
        raise StagingConfigDenied() from None
    for p in paths.values():
        if not p.is_absolute() or ".." in p.parts:
            raise StagingConfigDenied()
    for field in ("bff_issuer", "bff_audience", "bff_kid",
                  "history_dsn", "revoke_dsn", "engine_version"):
        if not isinstance(doc[field], str) or not doc[field]:
            raise StagingConfigDenied()
    for p in ("cert_file", "client_ca", "public_key_file"):
        _protected_file(paths[p])
    _protected_file(paths["key_file"], secret=True)
    return PrivateASGIConfig(
        listen_port=doc["listen_port"],
        cert_file=paths["cert_file"], key_file=paths["key_file"],
        client_ca=paths["client_ca"],
        bff_leaf_cert_sha256=doc["bff_leaf_cert_sha256"],
        issuer=doc["bff_issuer"], audience=doc["bff_audience"],
        kid=doc["bff_kid"], public_key_file=paths["public_key_file"],
        history_dsn=doc["history_dsn"], revoke_dsn=doc["revoke_dsn"],
        engine_version=doc["engine_version"], ledger_file=paths["ledger_file"],
    )


def _assert_no_dispatch_environment(environ) -> None:
    if (environ.get("API_RUNNER_EXECUTION_MODE") != "NO_DISPATCH_ONLY"
            or environ.get("CI") == "true"
            or environ.get("GITHUB_ACTIONS") == "true"):
        raise StagingConfigDenied()
    report = inspect_no_dispatch(RunnerLayout.pinned(), environ)
    if (not all(report["filesystem"].values())
            or not all(report["offline_environment"].values())
            or not _matches_exact_file_sha(
                RunnerLayout.pinned().runner(), RUNNER_C018_SHA256)):
        raise StagingConfigDenied()


def _test_tls_material(cfg: PrivateASGIConfig):
    """OpenSSL reads key/chain/CA and verifies presence before any listen."""
    try:
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ctx.minimum_version = ssl.TLSVersion.TLSv1_2
        ctx.load_cert_chain(certfile=str(cfg.cert_file), keyfile=str(cfg.key_file))
        ctx.load_verify_locations(cafile=str(cfg.client_ca))
        ctx.verify_mode = ssl.CERT_REQUIRED
        if ctx.verify_mode != ssl.CERT_REQUIRED:
            raise StagingConfigDenied()
    except (OSError, ValueError, ssl.SSLError):
        raise StagingConfigDenied() from None


def _harden_tls_context(config, default_factory):
    """Invoked by pinned Uvicorn 0.48.0 after loading CA and cert."""
    ctx = default_factory()
    if ctx.verify_mode != ssl.CERT_REQUIRED:
        raise StagingConfigDenied()
    ctx.minimum_version = ssl.TLSVersion.TLSv1_2
    return ctx


def verify_staging_database_authority(profile: PrivateStagingProfile) -> None:
    """Read-only real DB role/004/005/revoke privilege pre-start admission.

    No migrations, grants, writes or SQL exposed to an HTTP caller. It verifies
    the actual server credentials, role identity and scoped EXECUTE permissions.
    No user secrets or DSN are returned or printed.
    """
    import psycopg
    from psycopg.rows import dict_row
    from src.phase3.auth.staging_service_profile import db_attributes_approved

    procedures = {
        "history": (
            "auth_l1.consume_service_assertion(text,bigint)",
            "auth_l1.admit_session_fenced(text,text,bigint,integer)",
        ),
        "revoke": (
            "auth_l1.consume_service_assertion(text,bigint)",
            "auth_l1.admit_session_fenced(text,text,bigint,integer)",
            "auth_l1.revoke_one(text,bigint)",
        ),
    }
    role_names = {"history": "history_app", "revoke": "auth_revoker"}
    for operation, names in procedures.items():
        dsn = profile.dsn(operation)
        if not db_attributes_approved(
                psycopg.conninfo.conninfo_to_dict(dsn), operation):
            raise StagingConfigDenied()
        try:
            with psycopg.connect(dsn, autocommit=True,
                                 row_factory=dict_row, connect_timeout=5) as conn:
                row = conn.execute(
                    "SELECT rolname,rolsuper,rolbypassrls "
                    "FROM pg_roles WHERE rolname=current_user").fetchone()
                if (row is None or row["rolname"] != role_names[operation]
                        or row["rolsuper"] or row["rolbypassrls"]):
                    raise StagingConfigDenied()
                for signature in names:
                    has = conn.execute(
                        "SELECT has_function_privilege(current_user,%s,'EXECUTE') AS ok",
                        (signature,)).fetchone()
                    if has is None or has["ok"] is not True:
                        raise StagingConfigDenied()
        except psycopg.Error:
            raise StagingConfigDenied() from None


def prepare_private_app(cfg: PrivateASGIConfig, environ=None):
    """Validate file/env/TLS and install actual pinned handler BEFORE traffic.

    Must not be called twice. No SQL writes/grants or actual Runner invocation.
    Real History role/004/005 access is checked on the signed smoke request.
    """
    environ = os.environ if environ is None else environ
    _assert_no_dispatch_environment(environ)
    _test_tls_material(cfg)
    boundary = TrustedBFFTLSBoundary(cfg.bff_leaf_cert_sha256)
    profile = PrivateStagingProfile(
        issuer=cfg.issuer, audience=cfg.audience, kid=cfg.kid,
        public_key_path=cfg.public_key_file,
        history_dsn=cfg.history_dsn, revoke_dsn=cfg.revoke_dsn,
        peer_verifier=boundary.scope_is_verified,
        runner_sha256=RUNNER_C018_SHA256,
    )
    # Hard DB gate: refuse to listen before actual restricted roles and 004/005.
    verify_staging_database_authority(profile)
    # Avoid a magic PYTHONPATH dependency for the original repository module.
    project_root = Path(__file__).resolve().parents[2]
    module_dir = project_root / "src/phase3/storage/postgres"
    if str(module_dir) not in sys.path:
        sys.path.insert(0, str(module_dir))
    from apps.api import product_session_api
    engine = PrivateStagingEngineConfig(
        layout=RunnerLayout.pinned(),
        engine_version=cfg.engine_version,
        ledger_file=cfg.ledger_file,
        max_seconds=180,
    )
    product_session_api.install_private_staging_no_dispatch(profile, engine)
    return product_session_api.app, boundary


def run_private_staging(config_file: Path) -> None:
    cfg = load_private_config(config_file)
    app, boundary = prepare_private_app(cfg)
    import uvicorn
    if uvicorn.__version__ != "0.48.0":
        raise StagingConfigDenied()
    protocol = make_verified_h11_protocol(boundary)
    # Only loopback, TLS1.2+, mutual-cert chain verification, pinned BFF leaf,
    # workers=1 / no reload or forwarded-header trust / no websocket.
    server_cfg = uvicorn.Config(
        app=app, host="127.0.0.1", port=cfg.listen_port,
        loop="asyncio", http=protocol, ws="none", lifespan="on",
        workers=1, reload=False, proxy_headers=False,
        access_log=False, server_header=False, date_header=False,
        limit_concurrency=32, timeout_keep_alive=5,
        ssl_certfile=str(cfg.cert_file), ssl_keyfile=str(cfg.key_file),
        ssl_ca_certs=str(cfg.client_ca), ssl_cert_reqs=ssl.CERT_REQUIRED,
        ssl_version=ssl.PROTOCOL_TLS_SERVER,
        ssl_context_factory=_harden_tls_context,
    )
    uvicorn.Server(server_cfg).run()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Pinned private no-dispatch Product API; Ops approval needed.")
    parser.add_argument("--config", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        run_private_staging(args.config)
    except (PreflightDenied, StagingConfigDenied, VerifiedPeerUnavailable,
            ImportError, ModuleNotFoundError, OSError, ValueError, RuntimeError):
        # Do not leak private config/DSNs, Keycloak metadata or TLS paths.
        print("PRIVATE_STAGING_STARTUP_DENIED", file=sys.stderr)
        return 78
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
