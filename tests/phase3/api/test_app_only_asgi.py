"""Offline ASGI-boundary tests for Foundation's restricted API listener."""
from __future__ import annotations

import asyncio
import json
import os
import subprocess
import unittest
from unittest.mock import patch

from apps.api.app_only_asgi import app, require_app_only


def probe(path, method="GET"):
    frames = []
    reads = 0

    async def receive():
        nonlocal reads
        reads += 1
        return {"type": "http.request",
                "body": b'{"question":"SENSITIVE_MUST_NOT_BE_READ"}',
                "more_body": False}

    async def send(frame):
        frames.append(frame)

    scope = {
        "type": "http", "asgi": {"version": "3.0"},
        "http_version": "1.1", "scheme": "http", "method": method,
        "path": path, "raw_path": path.encode("utf-8"),
        "root_path": "", "query_string": b"",
        "headers": [(b"host", b"localhost"),
                    (b"content-type", b"application/json")],
        "client": ("127.0.0.1", 1),
        "server": ("127.0.0.1", 8080),
    }
    asyncio.run(app(scope, receive, send))
    status = next(f["status"] for f in frames if f["type"] == "http.response.start")
    header_frame = next(f for f in frames if f["type"] == "http.response.start")
    headers = dict(header_frame["headers"])
    body = b"".join(f.get("body", b"") for f in frames
                    if f["type"] == "http.response.body")
    return status, json.loads(body), reads, headers


class AppOnlyListenerTests(unittest.TestCase):
    def test_health_is_not_product_readiness(self):
        live = probe("/health/live")
        ready = probe("/health/ready")
        self.assertEqual(live[0], 200)
        self.assertFalse(live[1]["app_ready"])
        self.assertEqual(ready[0], 503)
        self.assertFalse(ready[1]["app_ready"])

    def test_no_engine_no_generation_and_no_dispatch_surface(self):
        status, body, reads, headers = probe("/v1/capabilities")
        self.assertEqual(status, 200)
        self.assertEqual(reads, 0)
        self.assertEqual(body, {
            "kind": "ui_runtime_capabilities",
            "contract_version": "ui.runtime_capabilities.v1",
            "send_mode": "DISABLED",
            "engine_available": False,
            "generation_available": False,
        })
        self.assertEqual(headers[b"cache-control"], b"no-store")

    def test_send_denied_before_body_or_process_spawn(self):
        with patch.object(subprocess, "Popen", side_effect=AssertionError("spawn")):
            status, body, reads, headers = probe("/v1/messages", "POST")
        self.assertEqual((status, body, reads),
                         (503, {"error": "ENGINE_NOT_AVAILABLE"}, 0))
        self.assertEqual(headers[b"cache-control"], b"no-store")

    def test_no_fixture_history_or_untrusted_session(self):
        for path in ("/v1/conversations",
                     "/v1/conversations/demo/messages",
                     "/v1/message-requests/status",
                     "/v1/message-requests/engine-status",
                     "/v1/message-requests/retrieved-sources"):
            status, body, reads, _ = probe(path)
            self.assertEqual((status, reads), (503, 0), path)
            self.assertEqual(body["error"], "SIGNED_PRODUCT_API_NOT_WIRED")

    def test_unapproved_profile_fails_closed(self):
        with patch.dict(os.environ, {"PHASE3_APP_MODE": "ENGINE_ENABLED"}):
            with self.assertRaisesRegex(RuntimeError, "APP_ONLY_PROFILE_REQUIRED"):
                require_app_only()

    def test_unknown_route_does_not_expose_data(self):
        status, _, _, _ = probe("/v1/admin")
        self.assertEqual(status, 404)


if __name__ == "__main__":
    unittest.main()
