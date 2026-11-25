"""App-only PostgreSQL transport policy, independent of DB credentials."""
from pathlib import Path


def pg_tls_options_allowed(options) -> bool:
    """Require one explicit TCP endpoint and hostname-verifying TLS.

    The caller separately checks the role and the CA file, and sets
    gssencmode=disable before opening a libpq connection.
    """
    if not isinstance(options, dict):
        return False
    host = options.get("host")
    port = options.get("port")
    root = options.get("sslrootcert")
    return (
        isinstance(host, str) and bool(host)
        and not any(ch.isspace() or ch in ",/\\" for ch in host)
        and not host.startswith("@")
        and isinstance(port, str) and port.isascii() and port.isdecimal()
        and 1 <= len(port) <= 5 and 1 <= int(port) <= 65535
        and options.get("sslmode") == "verify-full"
        and isinstance(root, str) and Path(root).is_absolute()
        and ".." not in Path(root).parts and Path(root).name != ""
        and not options.get("service") and not options.get("hostaddr")
        and options.get("gssencmode") in (None, "disable")
    )



def same_history_database(history, revoke) -> bool:
    """Require both restricted roles to target the same explicit PG database.

    This is a configuration consistency fence, not a claim that matching
    DNS names identify an immutable physical cluster. Never compare or expose
    passwords. A split restore or stale DSN must not produce successful revoke
    on a different database than the one admitting History.
    """
    if not pg_tls_options_allowed(history) or not pg_tls_options_allowed(revoke):
        return False
    def endpoint(options):
        database = options.get("dbname")
        if not isinstance(database, str) or not database or not database.strip():
            return None
        return (options["host"], int(options["port"]), database)
    left, right = endpoint(history), endpoint(revoke)
    return left is not None and left == right
