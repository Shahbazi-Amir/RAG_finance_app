"""Ops-injected private-staging trust boundary; never enabled by CI flags alone.

This is a source-level candidate, NOT a deployed mTLS identity or DB grant.
Only a trusted server startup may construct and install it. It does not
authorize paid Dispatch, model answers, or a synthetic History fixture.
"""
from __future__ import annotations

import os
import re
import stat
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Mapping

RUNNER_C018_SHA256 = "93233bfdf25e40684fd9120b82ec19c217695fdb632ed4a1f7d2bb2a3abcb17d"
_HEX = re.compile(r"^[0-9a-f]{64}$")
_KID = re.compile(r"^[A-Za-z0-9_.-]{1,80}$")
_SAFE_ROLE = {"history": "history_app", "revoke": "auth_revoker"}


class StagingConfigDenied(Exception):
    def __str__(self) -> str:
        return "PRIVATE_STAGING_CONFIG_DENIED"


@dataclass(frozen=True, repr=False)
class PrivateStagingProfile:
    """Injected from the trusted service bootstrap, never from an HTTP request.

    peer_verifier MUST derive its decision from a verified TLS client cert
    supplied by the trusted ASGI transport (or a rigorously authenticated
    local sidecar), not from any caller-controlled X-Forwarded-* header.
    Absence of this verifier means fail-closed, not 'trust loopback'.
    """

    issuer: str
    audience: str
    kid: str
    public_key_path: Path
    history_dsn: str
    revoke_dsn: str
    peer_verifier: Callable[[Mapping], bool]
    runner_sha256: str = RUNNER_C018_SHA256

    def __post_init__(self) -> None:
        if (not isinstance(self.issuer, str) or not self.issuer.startswith("urn:")
                or not isinstance(self.audience, str) or not self.audience.startswith("urn:")
                or not isinstance(self.kid, str) or not _KID.fullmatch(self.kid)
                or not isinstance(self.public_key_path, Path)
                or not self.public_key_path.is_absolute()
                or not isinstance(self.history_dsn, str) or not self.history_dsn
                or not isinstance(self.revoke_dsn, str) or not self.revoke_dsn
                or not callable(self.peer_verifier)
                or not isinstance(self.runner_sha256, str)
                or not _HEX.fullmatch(self.runner_sha256)
                or self.runner_sha256 != RUNNER_C018_SHA256):
            raise StagingConfigDenied()

    def load_public_key(self) -> bytes:
        """Read only a pinned local public key, never a Gateway secret or .env."""
        p = self.public_key_path
        try:
            s = p.lstat()
            if (not stat.S_ISREG(s.st_mode) or p.is_symlink()
                    or s.st_uid not in (0, os.geteuid())
                    or stat.S_IMODE(s.st_mode) & 0o022
                    or not 1 <= s.st_size <= 65536):
                raise StagingConfigDenied()
            data = p.read_bytes()
            if len(data) != s.st_size:
                raise StagingConfigDenied()
            return data
        except OSError:
            raise StagingConfigDenied() from None

    def dsn(self, operation: str) -> str:
        if operation == "history":
            return self.history_dsn
        if operation == "revoke":
            return self.revoke_dsn
        raise StagingConfigDenied()

    def allowed_peer(self, scope: Mapping) -> bool:
        """Trusted transport evidence is required for EVERY signed API call."""
        try:
            return (isinstance(scope, Mapping)
                    and scope.get("type") == "http"
                    and scope.get("scheme") == "https"
                    and self.peer_verifier(scope) is True)
        except Exception:
            return False


def db_attributes_approved(options: Mapping, operation: str) -> bool:
    """Narrow staged DB allowlist; never grant privileges or print a DSN.

    Remote PostgreSQL must verify server certificate against a named host;
    Unix sockets and host-loopback connections still require a separate
    Ops attestation and a runtime non-superuser/non-BYPASS role check.
    """
    if not isinstance(options, Mapping) or operation not in _SAFE_ROLE:
        return False
    user = options.get("user")
    host = options.get("host")
    database = options.get("dbname")
    if (user != _SAFE_ROLE[operation]
            or not isinstance(host, str) or not host or "," in host
            # libpq hostaddr/service may silently change the destination
            # behind the hostname that this trust policy actually approved.
            or any(k in options for k in ("hostaddr", "service", "servicefile"))
            or options.get("gssencmode") not in (None, "disable")
            or (isinstance(options.get("port"), str) and "," in options["port"])
            or not isinstance(database, str) or not database
            or database in {"history_ci", "postgres", "template0", "template1"}
            or options.get("sslmode") in {"disable", "allow", "prefer", "require"}):
        return False
    is_local = host in ("127.0.0.1", "::1", "localhost") or host.startswith("/")
    if is_local:
        return True
    rootcert = options.get("sslrootcert")
    return (options.get("sslmode") == "verify-full"
            and isinstance(rootcert, str) and Path(rootcert).is_absolute())


def private_db_connection_options(dsn: str, operation: str) -> dict:
    """Validate the actual libpq connection configuration before connecting.

    A local DSN must not become remote via PGHOSTADDR or PGSERVICE. A
    verify-full DSN must not negotiate GSS instead of validating the pinned
    TLS server certificate. Never leak malformed DSNs through parser errors.
    """
    import psycopg
    try:
        options = psycopg.conninfo.conninfo_to_dict(dsn)
    except (psycopg.Error, TypeError, ValueError):
        raise StagingConfigDenied() from None
    if (not db_attributes_approved(options, operation)
            or any(os.environ.get(k) for k in ("PGHOSTADDR", "PGSERVICE", "PGSERVICEFILE"))):
        raise StagingConfigDenied()
    # Pass explicitly to libpq, overriding the ambient GSS encryption default.
    return {"gssencmode": "disable"}
