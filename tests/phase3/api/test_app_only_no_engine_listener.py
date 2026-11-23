"""Real FastAPI handler/negative unit checks; NOT an approved Mac/IdP test."""
from __future__ import annotations

import os
import subprocess
import sys
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from apps.api.app_only_asgi import app, approved_ci_profile


class AppOnlyNoEngineBoundary(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_liveness_is_not_readiness(self):
        live = self.client.get("/health/live")
        ready = self.client.get("/health/ready")
        self.assertEqual(live.status_code, 200)
        self.assertEqual(live.json()["state"], "alive")
        self.assertEqual(ready.status_code, 503)
        self.assertEqual(ready.json()["code"], "DEPENDENCIES_NOT_ATTESTED")
        self.assertEqual(ready.headers["Cache-Control"], "no-store")

    def test_engine_capabilities_absent_and_no_fake_answer(self):
        response = self.client.get("/v1/capabilities")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["retrieval"], "unavailable")
        self.assertEqual(response.json()["generation"], "unavailable")
        self.assertFalse(response.json()["answer_creation"])
        self.assertFalse(response.json()["external_dispatch"])

    def test_send_fails_closed_even_with_malformed_payload(self):
        for payload in (b"{}", b'{"message":"demo"}', b"{not-json", b""):
            with self.subTest(payload=payload):
                response = self.client.post(
                    "/v1/messages",
                    content=payload,
                    headers={"content-type": "application/json"},
                )
                self.assertEqual(response.status_code, 503)
                self.assertEqual(response.json(), {"error": "ENGINE_UNAVAILABLE"})
                self.assertEqual(response.headers["Cache-Control"], "no-store")
                self.assertNotIn("answer", response.text.lower())

    def test_history_requires_trusted_identity(self):
        response = self.client.get("/v1/conversations")
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json(), {"error": "IDENTITY_NOT_ATTESTED"})

    def test_host_guard_and_no_public_docs(self):
        response = self.client.get(
            "/health/live", headers={"host": "untrusted.example"}
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.client.get("/docs").status_code, 404)
        self.assertEqual(self.client.get("/openapi.json").status_code, 404)

    def test_no_environment_only_start_without_exact_ci_tuple(self):
        correct = {"CI": "true", "GITHUB_ACTIONS": "true",
                   "APP_ONLY_PROFILE": "ISOLATED_CI_NO_ENGINE",
                   "APP_ONLY_PORT": "18880"}
        self.assertTrue(approved_ci_profile(correct))
        for field in correct:
            case = dict(correct)
            case.pop(field)
            self.assertFalse(approved_ci_profile(case), field)
        self.assertFalse(approved_ci_profile({}))

    def test_clean_app_only_module_imports_no_engine_or_db(self):
        code = (
            "import sys; import apps.api.app_only_asgi; "
            "assert not any(k.startswith('src.phase3.rag_runtime') "
            "or k.startswith('src.phase3.storage.postgres') "
            "for k in sys.modules)"
        )
        proc = subprocess.run(
            [sys.executable, "-c", code],
            capture_output=True,
            text=True,
            cwd=os.getcwd(),
            timeout=15,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, (proc.stdout, proc.stderr))


if __name__ == "__main__":
    unittest.main()
