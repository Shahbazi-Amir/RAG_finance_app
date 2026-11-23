"""Constant private HTTP cache policy for the signed Product API.

Pure ASGI, intentionally no buffering of body or stream frames. All API HTTP
responses (including framework-generated 404/405/422) are non-cacheable.
Does not replace authorization, owner isolation, release-keyed public caching
or an approved product cache policy. Never inspect or log response bodies.
"""
from __future__ import annotations


class PrivateHttpNoStore:
    """Replace every HTTP Cache-Control response header with no-store."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope.get("type") != "http":
            await self.app(scope, receive, send)
            return

        async def send_private(message):
            if message.get("type") == "http.response.start":
                headers = [
                    (key, value)
                    for key, value in message.get("headers", [])
                    if key.lower() != b"cache-control"
                ]
                headers.append((b"cache-control", b"no-store"))
                # Do not mutate the original event, whose headers may be shared.
                message = {**message, "headers": headers}
            await send(message)

        await self.app(scope, receive, send_private)
