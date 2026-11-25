"""Pure, fail-closed routing policy for the private app-only listener."""
from __future__ import annotations

import re

_THREAD = re.compile(rb"/v1/conversations/[A-Za-z0-9][A-Za-z0-9_-]{0,63}/messages")
_HEALTH = frozenset({b"/health/live", b"/health/ready", b"/v1/capabilities"})
_READS = frozenset({b"/v1/conversations", b"/v1/message-requests/status"})


def classify_route(scope) -> str:
    """Only exact canonical paths may reach a product handler.

    This function does not authenticate. The listener checks the TLS peer
    and runtime mode before using it; product handlers verify signed proofs.
    """
    raw = scope.get("raw_path")
    path = scope.get("path")
    method = scope.get("method")
    query = scope.get("query_string", b"")
    if not isinstance(raw, bytes) or not isinstance(path, str) or not isinstance(query, bytes):
        return "deny"
    try:
        if path.encode("ascii") != raw:
            return "deny"
    except UnicodeError:
        return "deny"
    if method == "POST" and raw == b"/v1/messages":
        return "send_disabled"
    if method == "GET" and raw == b"/internal/ready" and not query:
        return "pg_ready"
    if method == "GET" and raw in _HEALTH and not query:
        return "health"
    if method == "GET" and (raw in _READS or _THREAD.fullmatch(raw)):
        return "history"
    if method == "POST" and raw == b"/internal/auth/session/v1/revoke-one" and not query:
        return "revoke"
    return "deny"
