"""Send HTTP private TLS peer boundary; no real IdP, PG, C018 or model.

Deliberate early admission defense in depth: a forged BFF header cannot
authorize reading the question or opening the History DB. Outer ASGI mTLS
still remains mandatory; TestClient never proves real TLS identity.
"""
from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

from fastapi.testclient import TestClient

from apps.api import product_session_api as api

SEND = "/v1/messages"


class SendPeerBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(api.app)
        self.spoofed = {
            "X-Forwarded-Client-Cert": "FAKE_CERT",
            "X-SSL-Client-Verify": "SUCCESS",
            "X-BFF-Signed-Assertion": "fake",
        }

    def test_untrusted_mtls_peer_denied_before_question_parse_and_db(self):
        profile = SimpleNamespace(allowed_peer=Mock(return_value=False))
        with (patch.object(api, "_PRIVATE_STAGING_PROFILE", profile),
              patch.object(api.history, "_read_body", new_callable=AsyncMock) as parser,
              patch.object(api, "_config") as config,
              patch.object(api, "_conn") as db,
              patch.object(api, "assertion_from_asgi_headers") as auth,
              patch.object(api, "_run_server_no_dispatch_send") as handler):
            response = self.client.post(
                SEND, json={"question": "UNTRUSTED_PRIVATE_QUESTION"},
                headers=self.spoofed)
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["error"]["code"], "AUTH_REQUIRED")
        self.assertEqual(response.headers["cache-control"], "no-store")
        profile.allowed_peer.assert_called_once()
        parser.assert_not_awaited()
        config.assert_not_called()
        db.assert_not_called()
        auth.assert_not_called()
        handler.assert_not_called()

    def test_invalid_or_large_body_is_not_parsed_before_transport_identity(self):
        profile = SimpleNamespace(allowed_peer=Mock(return_value=False))
        with (patch.object(api, "_PRIVATE_STAGING_PROFILE", profile),
              patch.object(api.history, "_read_body", new_callable=AsyncMock) as parser,
              patch.object(api, "_conn") as db):
            response = self.client.post(
                SEND, content=b"INVALID" * 10_000,
                headers={**self.spoofed, "Content-Type": "application/json"})
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.headers["cache-control"], "no-store")
        parser.assert_not_awaited()
        db.assert_not_called()

    def test_trusted_peer_enters_existing_validation_without_forged_success(self):
        profile = SimpleNamespace(allowed_peer=Mock(return_value=True))
        # Independently verified transport may proceed to parse, but does not
        # by itself authorize signing, DB access, or model execution.
        failure = api.history.ApiFailure(422, "INVALID_REQUEST", "validation")
        with (patch.object(api, "_PRIVATE_STAGING_PROFILE", profile),
              patch.object(api.history, "_read_body", new_callable=AsyncMock,
                           side_effect=failure) as parser,
              patch.object(api, "_conn") as db):
            response = self.client.post(SEND, content=b"{}",
                                        headers={"Content-Type": "application/json"})
        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.json()["error"]["code"], "INVALID_REQUEST")
        parser.assert_awaited_once()
        db.assert_not_called()

    def test_no_private_profile_keeps_existing_ci_validation_path(self):
        failure = api.history.ApiFailure(422, "INVALID_REQUEST", "validation")
        with (patch.object(api, "_PRIVATE_STAGING_PROFILE", None),
              patch.object(api.history, "_read_body", new_callable=AsyncMock,
                           side_effect=failure) as parser):
            response = self.client.post(SEND, content=b"{}",
                                        headers={"Content-Type": "application/json"})
        self.assertEqual(response.status_code, 422)
        parser.assert_awaited_once()


if __name__ == "__main__":
    unittest.main()
