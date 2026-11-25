"""App-only route fence: deny engine-only operations before DB admission."""
from __future__ import annotations

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
