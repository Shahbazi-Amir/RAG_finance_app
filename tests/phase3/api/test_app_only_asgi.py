"""App-only API source and real ASGI HTTP regression. Synthetic/CI only."""
import ast
import os
import subprocess
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient
from starlette.requests import Request

from apps.api.app_only_asgi import app, VERSION


class AppOnlyASGITests(unittest.TestCase):
    def setUp(self):
        self.patcher = patch.dict(os.environ, {"PHASE3_APP_MODE": "APP_ONLY"})
        self.patcher.start()
        self.addCleanup(self.patcher.stop)
        self.client = TestClient(app)

    def test_liveness_does_not_fake_app_readiness_or_engine(self):
        response = self.client.get("/health/live")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["cache-control"], "no-store")
        self.assertEqual(response.json(), {
            "kind": "api_app_only_liveness", "contract_version": VERSION,
            "process_alive": True, "application_ready": False,
            "retrieval_available": False, "generation_available": False,
        })
        status = self.client.get("/health/ready")
        self.assertEqual(status.status_code, 503)
        self.assertFalse(status.json()["application_ready"])
        self.assertEqual(status.json()["reason"],
                         "SIGNED_HISTORY_PG_BOOTSTRAP_UNVERIFIED")

    def test_capability_contains_no_live_or_actor_credential(self):
        response = self.client.get("/v1/capabilities")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {
            "kind": "api_app_only_capabilities", "contract_version": VERSION,
            "send_mode": "DISABLED", "retrieval_available": False,
            "generation_available": False,
            "background_dispatch_available": False,
        })
        self.assertNotIn("owner", response.text)
        self.assertNotIn("token", response.text.lower())
        self.assertNotIn("secret", response.text.lower())

    def test_send_denied_before_any_body_read(self):
        # FastAPI receives Request itself and has no body validation stage.
        with patch.object(Request, "body", side_effect=AssertionError("BODY_READ")), \
             patch.object(Request, "json", side_effect=AssertionError("JSON_READ")):
            response = self.client.post("/v1/messages",
                                        content=b"not-json" + b"x" * 32768,
                                        headers={"content-type": "application/json"})
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json(), {"error": "ENGINE_NOT_AVAILABLE"})
        self.assertEqual(response.headers["cache-control"], "no-store")

    def test_zero_spawn_gateway_job_or_replay_across_requests(self):
        with patch.object(subprocess, "Popen", side_effect=AssertionError("SPAWN")), \
             patch.object(os, "system", side_effect=AssertionError("SHELL")):
            for _ in range(3):
                self.assertEqual(self.client.post("/v1/messages",
                                 json={"client_message_id": "same"}).status_code, 503)
            self.assertEqual(self.client.get("/v1/message-requests/status").status_code, 503)
            self.assertEqual(self.client.get("/v1/message-requests/engine-status").status_code, 503)
            self.assertEqual(self.client.get("/v1/conversations").status_code, 503)

    def test_owner_headers_are_not_trusted(self):
        identity={"authorization": "Bearer attacker",
                  "x-owner-user-id": "A", "x-forwarded-client-cert": "FORGED"}
        a=self.client.get("/v1/conversations",headers=identity)
        b=self.client.get("/v1/conversations/guess-owner-A/messages",
                          headers={**identity,"x-owner-user-id":"B"})
        self.assertEqual(a.status_code, 503)
        self.assertEqual(b.status_code, 503)
        self.assertEqual(a.json(), b.json())
        self.assertEqual(a.json()["error"], "SIGNED_HISTORY_NOT_CONFIGURED")

    def test_unknown_profile_never_downgrades_engine_enabled(self):
        for mode in ("ENGINE_ENABLED", "APP_ONLY ", "LIVE", ""):
            with self.subTest(mode=mode), patch.dict(
                    os.environ, {"PHASE3_APP_MODE": mode}):
                for route in ("/health/live", "/health/ready", "/v1/capabilities"):
                    self.assertEqual(self.client.get(route).status_code, 503)
                response=self.client.post("/v1/messages",json={"msg": "forged"})
                self.assertEqual(response.status_code, 503)
                self.assertEqual(response.json(), {"error": "APP_ONLY_PROFILE_DENIED"})

    def test_explicit_profile_absence_is_denied(self):
        with patch.dict(os.environ, clear=True):
            self.assertEqual(self.client.get("/health/live").status_code, 503)
            self.assertEqual(self.client.post("/v1/messages").status_code, 503)

    def test_no_unsafe_docs_debug_or_fallback_routes(self):
        for path in ("/docs", "/redoc", "/openapi.json", "/admin",
                     "/v1/runner", "/v1/answer", "/v1/dispatch"):
            self.assertEqual(self.client.get(path).status_code, 404)

    def test_import_graph_contains_no_engine_db_or_credential_layer(self):
        module=Path(__file__).resolve().parents[3]/"apps/api/app_only_asgi.py"
        source=module.read_text(encoding="utf-8")
        tree=ast.parse(source)
        imported=[]
        for node in ast.walk(tree):
            if isinstance(node,ast.Import):
                imported.extend(a.name for a in node.names)
            if isinstance(node,ast.ImportFrom):
                imported.append(node.module or "")
        for name in imported:
            self.assertFalse(name.startswith(("src.phase3", "apps.api.history",
                              "subprocess", "psycopg", "qdrant_client")),name)
        self.assertNotIn("create_task(", source)
        self.assertNotIn("asyncio.run(", source)
        self.assertNotIn("BackgroundTasks", source)


if __name__ == "__main__":
    unittest.main()
