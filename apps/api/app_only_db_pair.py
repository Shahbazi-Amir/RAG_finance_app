"""App-only History and revoke must share one explicit TLS database endpoint."""
from __future__ import annotations

from collections.abc import Mapping
from pathlib import PurePosixPath


def same_tls_database(history: Mapping, revoke: Mapping) -> bool:
    """Compare parsed connection attributes, never credentials or raw DSNs."""
    if not isinstance(history, Mapping) or not isinstance(revoke, Mapping):
        return False
    for options, role in ((history, "history_app"), (revoke, "auth_revoker")):
        host, port, db, ca = (options.get(k) for k in
                              ("host", "port", "dbname", "sslrootcert"))
        if (options.get("user") != role or not isinstance(host, str)
                or not host or host.startswith("/") or "," in host
                or not isinstance(port, str) or not port.isascii()
                or not port.isdecimal() or len(port) > 5
                or not 1 <= int(port) <= 65535
                or not isinstance(db, str) or not db
                or options.get("sslmode") != "verify-full"
                or not isinstance(ca, str) or not PurePosixPath(ca).is_absolute()
                or ".." in PurePosixPath(ca).parts
                or any(k in options for k in ("hostaddr", "service", "servicefile"))
                or options.get("gssencmode") not in (None, "disable")):
            return False
    return all(history[k] == revoke[k] for k in
               ("host", "port", "dbname", "sslrootcert"))
