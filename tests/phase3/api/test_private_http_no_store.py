"""Private HTTP cache safety: full FastAPI routes and pure ASGI transport."""
from __future__ import annotations

import asyncio
import unittest

from fastapi.testclient import TestClient

from apps.api.product_session_api import app
from src.phase3.auth.private_http_no_store import PrivateHttpNoStore


class ProductAPICacheSafetyTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_framework_404_is_never_cacheable(self):
        response = self.client.get("/v1/no-such-private-route")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.headers["cache-control"], "no-store")

    def test_framework_405_is_never_cacheable(self):
        response = self.client.post("/v1/conversations")
        self.assertEqual(response.status_code, 405)
        self.assertEqual(response.headers["cache-control"], "no-store")

    def test_unsupported_public_openapi_route_also_no_store(self):
        response = self.client.get("/openapi.json")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.headers["cache-control"], "no-store")

    def test_rejected_signed_history_cannot_be_cached(self):
        response = self.client.get("/v1/conversations")
        self.assertGreaterEqual(response.status_code, 400)
        self.assertEqual(response.headers["cache-control"], "no-store")

    def test_rejected_message_query_cannot_be_cached(self):
        response = self.client.post("/v1/messages?client_override=1",
                                    json={"question": "synthetic"})
        self.assertGreaterEqual(response.status_code, 400)
        self.assertEqual(response.headers["cache-control"], "no-store")


class PureASGICachePolicyTests(unittest.TestCase):
    def test_replaces_public_cache_headers_without_buffering_chunks(self):
        events = []

        async def upstream(scope, receive, send):
            await send({"type": "http.response.start", "status": 200,
                        "headers": [(b"content-type", b"text/event-stream"),
                                    (b"Cache-Control", b"public, max-age=3600"),
                                    (b"cache-control", b"private"),
                                    (b"x-trace-status", b"sanitized")]})
            await send({"type": "http.response.body", "body": b"frame1",
                        "more_body": True})
            await send({"type": "http.response.body", "body": b"frame2",
                        "more_body": False})

        async def sink(message):
            events.append(message)

        asyncio.run(PrivateHttpNoStore(upstream)(
            {"type": "http", "path": "/v1/events"}, None, sink))
        self.assertEqual([e["type"] for e in events],
                         ["http.response.start", "http.response.body",
                          "http.response.body"])
        headers = events[0]["headers"]
        self.assertEqual(
            [(k, v) for k, v in headers if k.lower() == b"cache-control"],
            [(b"cache-control", b"no-store")])
        self.assertIn((b"x-trace-status", b"sanitized"), headers)
        self.assertEqual(events[1]["body"], b"frame1")
        self.assertTrue(events[1]["more_body"])
        self.assertEqual(events[2]["body"], b"frame2")

    def test_no_store_does_not_modify_websocket_scope(self):
        events = []
        async def upstream(scope, receive, send):
            await send({"type": "websocket.accept",
                        "headers": [(b"x-a", b"1")]})

        async def sink(message):
            events.append(message)

        asyncio.run(PrivateHttpNoStore(upstream)(
            {"type": "websocket"}, None, sink))
        self.assertEqual(events, [
            {"type": "websocket.accept", "headers": [(b"x-a", b"1")]}
        ])


if __name__ == "__main__":
    unittest.main()
