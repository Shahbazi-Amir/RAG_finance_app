"""Schema-level v1 CI-only fixture wire, negative provenance/locator checks."""
import copy
import json
import unittest
from pathlib import Path

from src.phase3.rag_runtime.staging_invited_result_contract import (
    validate_ci_invited_result,
)
from src.phase3.rag_runtime.staging_preflight import PreflightDenied


class InvitedResultSchemaTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        sample = Path(__file__).parent / "fixtures/staging_invited_live_result_ready.example.json"
        cls.example = json.loads(sample.read_text(encoding="utf-8"))

    def test_01_exact_UI_sample_is_valid_READY(self):
        validate_ci_invited_result(self.example)
        self.assertEqual(self.example["contract_version"],
                         "staging.invited_live_result.v1")
        self.assertEqual(self.example["answer"]["citations"][0]["locator"], None)

    def test_02_pending_and_unknown_never_expose_answer(self):
        for status in ("PENDING", "FAILED", "UNKNOWN"):
            doc = copy.deepcopy(self.example)
            doc["result_status"] = status
            doc["answer"] = None
            validate_ci_invited_result(doc)
            doc["answer"] = self.example["answer"]
            with self.assertRaises(PreflightDenied):
                validate_ci_invited_result(doc)

    def test_03_attempt_and_session_fields_required(self):
        for name in ("owner_user_id", "resolved_conversation_id", "attempt_id",
                     "attempt_request_id", "attempt_trace_id", "idempotency_key",
                     "client_message_id", "provenance"):
            doc = copy.deepcopy(self.example)
            doc.pop(name)
            with self.subTest(name=name), self.assertRaises(PreflightDenied):
                validate_ci_invited_result(doc)

    def test_04_spoofed_LIVE_VERIFIED_and_unsafe_locator_denied(self):
        for field, replacement in (
            ("state", "LIVE_VERIFIED"),
            ("origin", "ACTUAL_PROVIDER"),
            ("product_live_verified", True),
        ):
            doc = copy.deepcopy(self.example)
            doc["provenance"][field] = replacement
            with self.subTest(field=field), self.assertRaises(PreflightDenied):
                validate_ci_invited_result(doc)
        doc = copy.deepcopy(self.example)
        doc["answer"]["citations"][0]["locator"] = "https://unknown.invalid"
        with self.assertRaises(PreflightDenied):
            validate_ci_invited_result(doc)
        doc = copy.deepcopy(self.example)
        doc["answer"]["citations"][0]["excerpt"] = "invented quote"
        with self.assertRaises(PreflightDenied):
            validate_ci_invited_result(doc)

    def test_05_reject_wrong_schema_or_extra_fields(self):
        for change in (
            {"contract_version": "product.v1"},
            {"consent_scope": "INVITED_STAGING_OPT_IN"},
            {"result_status": "LIVE_VERIFIED"},
            {"untrusted": "payload"},
        ):
            doc = copy.deepcopy(self.example)
            doc.update(change)
            with self.assertRaises(PreflightDenied):
                validate_ci_invited_result(doc)

    def test_06_negative_ready_must_have_answer_and_T2(self):
        for field, value in (
            ("answer", None), ("attempt_id", None),
            ("attempt_request_id", None),
            ("attempt_trace_id", None),
            ("retention_expires_at_unix", None),
        ):
            doc = copy.deepcopy(self.example)
            doc[field] = value
            with self.assertRaises(PreflightDenied):
                validate_ci_invited_result(doc)


if __name__ == "__main__":
    unittest.main()
