"""Revoke-one private-staging mTLS peer guard: isolated ASGI tests.

No live client certificates, PostgreSQL, IdP, Qdrant, Runner, or paid Gateway
are used. A successful mock peer is NOT a Mac signed-HTTP acceptance.
"""
from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, Mock, patch

from fastapi.testclient import TestClient

from apps.api import product_session_api as api


REVOKE_URL = "/internal/auth/session/v1/revoke-one"
OP_ID = "12345678-1234-4123-8123-123456789abc"


class RevokePeerBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(api.app)
        self.body = {"operation_id": OP_ID}
        self.spoofed = {"X-Forwarded-Client-Cert": "FAKE",
                        "X-SSL-Client-Verify": "SUCCESS"}

    def test_no_trusted_transport_rejected_before_jwt_or_database(self):
        profile = SimpleNamespace(allowed_peer=Mock(return_value=False))
        with (patch.object(api, "_PRIVATE_STAGING_PROFILE", profile),
              patch.object(api, "assertion_from_asgi_headers") as parse,
              patch.object(api, "_config") as config,
              patch.object(api, "_conn") as connect,
              patch.object(api.auth_session, "revoke_one") as revoke):
            response = self.client.post(
                REVOKE_URL, json=self.body, headers=self.spoofed)
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json(), {"error": "AUTH_DENIED"})
        self.assertEqual(response.headers["cache-control"], "no-store")
        profile.allowed_peer.assert_called_once()
        parse.assert_not_called()
        config.assert_not_called()
        connect.assert_not_called()
        revoke.assert_not_called()

    def test_trusted_transport_preserves_signed_revoke_commit(self):
        # Every auth, transport and PG interaction here is a stub, L1 only.
        profile = SimpleNamespace(allowed_peer=Mock(return_value=True))
        verifier = Mock()
        verifier.verify.return_value = SimpleNamespace(
            owner_id="owner_A", session_ref="S" * 43, epoch=5)
        conn_context = MagicMock()
        connection = object()
        conn_context.__enter__.return_value = connection
        owner_transaction = MagicMock()
        owner_transaction.__enter__.return_value = "owner_A"
        with (patch.object(api, "_PRIVATE_STAGING_PROFILE", profile),
              patch.object(api, "assertion_from_asgi_headers",
                           return_value="fixture-signed") as parse,
              patch.object(api, "wire_request",
                           return_value=("POST", api._REVOKE_PATH, b"", b"{}")),
              patch.object(api, "_config", return_value=verifier),
              patch.object(api, "_conn", return_value=conn_context) as connect,
              patch.object(api, "protected_transaction",
                           return_value=owner_transaction) as admission,
              patch.object(api.auth_session, "revoke_one",
                           return_value=True) as revoke):
            response = self.client.post(REVOKE_URL, json=self.body)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {
            "state": "REVOKED_COMMITTED", "operation_id": OP_ID})
        self.assertEqual(response.headers["cache-control"], "no-store")
        profile.allowed_peer.assert_called_once()
        parse.assert_called_once()
        connect.assert_called_once_with("revoke")
        admission.assert_called_once()
        revoke.assert_called_once_with(connection, "S" * 43, 5)

    def test_trusted_transport_cannot_override_rejected_db_revoke(self):
        profile = SimpleNamespace(allowed_peer=Mock(return_value=True))
        verifier = Mock()
        verifier.verify.return_value = SimpleNamespace(
            owner_id="owner_A", session_ref="S" * 43, epoch=5)
        conn_context = MagicMock()
        conn_context.__enter__.return_value = object()
        owner_transaction = MagicMock()
        owner_transaction.__enter__.return_value = "owner_A"
        with (patch.object(api, "_PRIVATE_STAGING_PROFILE", profile),
              patch.object(api, "assertion_from_asgi_headers",
                           return_value="fixture-signed"),
              patch.object(api, "wire_request",
                           return_value=("POST", api._REVOKE_PATH, b"", b"{}")),
              patch.object(api, "_config", return_value=verifier),
              patch.object(api, "_conn", return_value=conn_context),
              patch.object(api, "protected_transaction",
                           return_value=owner_transaction),
              patch.object(api.auth_session, "revoke_one",
                           return_value=False) as revoke):
            response = self.client.post(REVOKE_URL, json=self.body)
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json(), {"error": "AUTH_DENIED"})
        revoke.assert_called_once()


if __name__ == "__main__":
    unittest.main()
