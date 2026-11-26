"""App-only route fence: deny engine-only operations before DB admission."""
from __future__ import annotations

import re

_ENGINE_READS = frozenset({
    "/v1/message-requests/engine-status",
    "/v1/message-requests/retrieved-sources",
})
_FIXTURE_READS = frozenset({
    "/v1/message-requests/claim-test-status",
    "/v1/message-requests/invited-live-result",
})


async def deny_disabled_route(scope, receive, send, error_response) -> bool:
    """Called only after verified TLS peer and app-only runtime checks.

    Use the decoded ASGI path (same as the router). Never consume the body,
    verify a signed session, connect to PG, or invoke an engine here.
    The caller supplies the existing product.v1 error factory.
    """
    method, path = scope.get("method"), scope.get("path")
    # A disabled alias must not return a framework redirect that invites
    # resubmission of the original body or signed assertion to another path.
    if isinstance(path, str):
        path = path.rstrip("/")
    if method == "POST" and path == "/v1/messages":
        code = "ENGINE_NOT_CONFIGURED"
        message = "Message sending is unavailable until the engine is enabled."
    elif method == "GET" and path in _ENGINE_READS:
        code = "ENGINE_STATUS_UNAVAILABLE"
        message = "History unavailable."
    elif method == "GET" and path in _FIXTURE_READS:
        code = "TEMPORARILY_UNAVAILABLE"
        message = "History unavailable."
    else:
        return False
    await error_response(503, code, "technical", message)(scope, receive, send)
    return True


def app_only_route_allowed(scope) -> bool:
    """Explicit method/decoded path allowlist for the current Product v1 slice.

    The existing signed handler independently checks canonical raw path and
    the signed query/body. Unknown future mutations cannot silently inherit
    APP_ONLY authority, and aliases cannot trigger framework redirects.
    """
    method, path = scope.get("method"), scope.get("path")
    if not isinstance(path, str):
        return False
    if path == "/health/ready":
        # Existing readiness handler returns 503 for a malformed probe.
        return True
    if method == "GET":
        return (path in {"/internal/ready", "/v1/conversations",
                         "/v1/message-requests/status"}
                or re.fullmatch(r"/v1/conversations/[A-Za-z0-9][A-Za-z0-9_-]{0,63}/messages", path) is not None)
    return method == "POST" and path == "/internal/auth/session/v1/revoke-one"
