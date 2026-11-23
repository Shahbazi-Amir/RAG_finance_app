"""Provisional Product v1 client lifecycle DTOs: no consent/DB side effects."""
from __future__ import annotations

import copy
import json
import unittest

from src.phase3.auth.lifecycle_intent_shape import (
    LifecycleIntentDenied, inspect_lifecycle_intent,
)


class LifecycleIntentShapeTests(unittest.TestCase):
    def setUp(self):
        self.feedback = {
            "kind": "feedback_submit_request", "contract_version": "product.v1",
            "client_feedback_id": "fb01", "conversation_id": "c01",
            "answer_id": "a01", "rating": "positive",
            "reason": None, "idempotency_key": "fixture_key_12345",
        }
        self.delete = {
            "kind": "delete_command", "contract_version": "product.v1",
            "deletion_scope": "conversation", "conversation_id": "c01",
            "confirmed_by_user": True, "client_action_id": "delete01",
        }

    def parse(self, payload, kind=None):
        k = kind or payload.get("kind")
        return inspect_lifecycle_intent(
            json.dumps(payload, ensure_ascii=False, allow_nan=False).encode(),
            kind=k)

    def denied(self, payload, kind=None):
        with self.assertRaises(LifecycleIntentDenied) as ctx:
            self.parse(payload, kind)
        self.assertEqual(str(ctx.exception), "LIFECYCLE_INTENT_DENIED")

    def test_valid_feedback_is_only_a_structural_intent(self):
        result = self.parse(self.feedback)
        self.assertTrue(result.shape_valid)
        self.assertFalse(result.transaction_authorized)
        self.assertFalse(result.side_effect_performed)
        self.assertEqual(result.kind, "feedback_submit_request")
        self.assertNotIn("fixture_key_12345", repr(result))

    def test_valid_conversation_deletion_is_not_delete_receipt(self):
        result = self.parse(self.delete)
        self.assertEqual(result.kind, "delete_command")
        self.assertFalse(result.transaction_authorized)
        self.assertFalse(result.side_effect_performed)

    def test_valid_account_delete_must_have_null_conversation(self):
        self.denied({**self.delete, "deletion_scope": "account"})
        result = self.parse({**self.delete,
                             "deletion_scope": "account",
                             "conversation_id": None})
        self.assertFalse(result.transaction_authorized)

    def test_confirmed_by_user_is_exact_boolean_true(self):
        for confirmation in (False, 1, "true", None):
            with self.subTest(confirmation=confirmation):
                self.denied({**self.delete, "confirmed_by_user": confirmation})

    def test_feedback_requires_existing_answer_reference_shape(self):
        for value in (None, "", "bad/answer", " "):
            with self.subTest(value=value):
                self.denied({**self.feedback, "answer_id": value})
        self.denied({k: v for k, v in self.feedback.items()
                     if k != "answer_id"})

    def test_feedback_wrong_rating_rejected(self):
        for value in ("good", 1, None, "NEUTRAL"):
            with self.subTest(value=value):
                self.denied({**self.feedback, "rating": value})

    def test_foreign_owner_and_server_trace_fields_not_client_authorized(self):
        for kind, fixture in (("feedback", self.feedback),
                              ("deletion", self.delete)):
            for server_field in ("owner_user_id", "request_id", "trace_id",
                                 "session_ref", "session_epoch"):
                with self.subTest(kind=kind, field=server_field):
                    self.denied({**fixture, server_field: "owner_B"})

    def test_semantic_digest_independent_of_json_property_order(self):
        first = self.parse(self.feedback)
        second = inspect_lifecycle_intent(
            json.dumps(dict(reversed(list(self.feedback.items()))),
                       ensure_ascii=False).encode(),
            kind="feedback_submit_request")
        self.assertEqual(first.canonical_payload_sha256,
                         second.canonical_payload_sha256)

    def test_same_client_key_modified_payload_has_distinct_digest(self):
        one = self.parse(self.feedback)
        two = self.parse({**self.feedback, "reason": "synthetic changed"})
        self.assertEqual(one.client_idempotency_ref,
                         two.client_idempotency_ref)
        self.assertNotEqual(one.canonical_payload_sha256,
                            two.canonical_payload_sha256)
        # An actual 409 conflict requires a DB idempotency transaction.

    def test_null_optional_feedback_reason_allowed_but_size_bounded(self):
        self.parse({**self.feedback, "reason": "short synthetic reason"})
        self.denied({**self.feedback, "reason": "x" * 501})

    def test_unapproved_consent_and_export_intents_fail_closed(self):
        for name in ("consent_request", "export_request", "withdraw_consent"):
            with self.subTest(kind=name):
                with self.assertRaises(LifecycleIntentDenied):
                    inspect_lifecycle_intent(b'{"kind":"any"}', kind=name)

    def test_duplicate_keys_rejected_not_last_key_wins(self):
        raw = (b'{"kind":"delete_command","kind":"delete_command",'
               b'"contract_version":"product.v1"}')
        with self.assertRaises(LifecycleIntentDenied):
            inspect_lifecycle_intent(raw, kind="delete_command")

    def test_non_json_constants_rejected(self):
        raw = json.dumps(self.feedback).replace('"positive"', "NaN")
        with self.assertRaises(LifecycleIntentDenied):
            inspect_lifecycle_intent(
                raw.encode(), kind="feedback_submit_request")

    def test_non_utf8_or_oversized_request_rejected(self):
        for raw in (b"\xff", b"", b"x" * 8193, "not bytes", None):
            with self.subTest(raw_type=str(type(raw))):
                with self.assertRaises(LifecycleIntentDenied):
                    inspect_lifecycle_intent(
                        raw, kind="feedback_submit_request")

    def test_version_mismatch_and_unknown_fields_rejected(self):
        self.denied({**self.feedback, "contract_version": "product.v2"})
        self.denied({**self.delete, "kind": "some_random_command"},
                    kind="delete_command")
        self.denied({**self.feedback, "verified": True})

    def test_no_explicit_owner_in_client_action_dto(self):
        result = self.parse(self.delete)
        self.assertEqual(result.client_idempotency_ref, "delete01")
        self.assertNotIn("owner", repr(result))


if __name__ == "__main__":
    unittest.main()
