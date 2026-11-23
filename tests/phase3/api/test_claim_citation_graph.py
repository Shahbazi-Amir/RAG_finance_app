"""Cross-link and source trust negative suite for existing Product.v1 Answer."""
from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from apps.api import product_session_api as api
from src.phase3.rag_runtime.claim_citation_graph import (
    CitationGraphDenied, inspect_answer_citation_graph,
)

_FIXTURE = (Path(__file__).resolve().parents[3] /
            "packages/contracts/fixtures/product.v1.cases.json")


class ClaimCitationGraphTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cases = json.loads(_FIXTURE.read_text(encoding="utf-8"))["cases"]
        cls.valid = next(c["document"] for c in cases
                         if c["case_id"] == "valid_answer_unresolved_source")

    def setUp(self):
        self.answer = copy.deepcopy(self.valid)

    def deny(self, answer):
        with self.assertRaises(CitationGraphDenied) as err:
            inspect_answer_citation_graph(answer)
        self.assertEqual(str(err.exception), "CITATION_GRAPH_DENIED")

    def test_existing_synthetic_fixture_graph_passes_but_is_unverified(self):
        result = inspect_answer_citation_graph(self.answer)
        self.assertEqual((result.claim_count, result.citation_count,
                          result.reciprocal_links), (1, 1, 1))
        self.assertTrue(result.graph_consistent)
        self.assertFalse(result.source_verified)
        self.assertFalse(result.live_verified)
        self.assertFalse(result.authorizes_product_t3)
        self.assertNotIn("پاسخ", repr(result))

    def test_unknown_citation_from_claim_fails(self):
        self.answer["claims"][0]["citation_ids"] = ["cite_missing"]
        self.deny(self.answer)

    def test_dangling_claim_from_citation_fails(self):
        self.answer["citations"][0]["claim_ids"] = ["claim_missing"]
        self.deny(self.answer)

    def test_asymmetric_links_with_two_claims_fail(self):
        extra = copy.deepcopy(self.answer["claims"][0])
        extra["claim_id"] = "claim_two"
        self.answer["claims"].append(extra)
        # cite_1 only enumerates claim_1; claim_two's link has no reciprocal.
        self.deny(self.answer)

    def test_duplicate_claim_id_rejected(self):
        self.answer["claims"].append(copy.deepcopy(self.answer["claims"][0]))
        self.deny(self.answer)

    def test_duplicate_citation_id_rejected(self):
        self.answer["citations"].append(copy.deepcopy(self.answer["citations"][0]))
        self.deny(self.answer)

    def test_extra_citation_without_valid_claim_reverse_link_rejected(self):
        extra = copy.deepcopy(self.answer["citations"][0])
        extra["citation_id"] = "cite_two"
        self.answer["citations"].append(extra)
        self.deny(self.answer)

    def test_synthetic_source_editor_name_does_not_become_authority(self):
        source = self.answer["citations"][0]["source"]
        source["editorial_supervisor_name"] = "یک سردبیر ساختگی"
        source["credited_author_name"] = None
        original = copy.deepcopy(self.answer)
        result = inspect_answer_citation_graph(self.answer)
        self.assertFalse(result.source_verified)
        self.assertEqual(self.answer, original)
        self.assertIsNone(source["credited_author_name"])

    def test_self_claimed_live_verified_on_unresolved_source_fails(self):
        p = self.answer["provenance"]
        p["origin"] = "LIVE_VERIFIED"
        p["producer_reference"] = "fixture_fake_producer"
        p["source_fingerprint"] = "a" * 64
        p["rag_binding"]["status"] = "verified"
        p["rag_binding"]["blocked_by"] = None
        p["rag_binding"]["release_id"] = "fake_release"
        p["rag_binding"]["adapter_verified"] = True
        self.deny(self.answer)

    def test_no_answer_zero_graph_still_not_authorized_as_live(self):
        self.answer.update(outcome="no_answer", state="completed",
                           answer_text=None, claims=[], citations=[])
        result = inspect_answer_citation_graph(self.answer)
        self.assertEqual((result.claim_count, result.citation_count), (0, 0))
        self.assertFalse(result.authorizes_product_t3)

    def test_missing_required_fields_and_invalid_source_types_fail(self):
        for key in ("claims", "citations", "provenance"):
            with self.subTest(key=key):
                bad = copy.deepcopy(self.answer)
                del bad[key]
                self.deny(bad)
        self.answer["citations"][0]["source"]["source_type"] = "unknown"
        self.deny(self.answer)

    def test_bad_payload_and_oversized_refused_without_leaking(self):
        for value in (None, [], "answer", {"kind": "answer"}):
            with self.subTest(value_type=str(type(value))):
                self.deny(value)
        self.answer["answer_text"] = "z" * 1_100_000
        self.deny(self.answer)

    def test_unsupported_extra_fields_denied(self):
        self.answer["citations"][0]["source"]["secret_owner"] = "owner_B"
        self.deny(self.answer)

    def test_route_fixture_rejects_broken_graph_before_product_t3(self):
        broken = copy.deepcopy(self.valid)
        broken["claims"][0]["citation_ids"] = ["nonexistent_citation"]
        proof = SimpleNamespace(owner_id="owner_A", session_ref="session",
                                epoch=1, generation=1)
        receipt = {"disposition": "created", "resolved_conversation_id": "conv_1"}
        attempt = {"id": "attempt_1", "reserved_answer_id": "ans_1",
                   "attempt_request_id": "req_1", "attempt_trace_id": "trace_1"}
        connection = MagicMock()
        connect = MagicMock()
        connect.__enter__.return_value = connection
        with (patch.object(api, "_signed_history", return_value=(
                  proof, (receipt, attempt))),
              patch.object(api, "_conn", return_value=connect) as connect_db,
              patch.object(api, "answer_from_fixture", return_value=broken),
              patch.object(api.auth_session, "admit_session_fenced",
                           return_value=True) as admission,
              patch.object(api, "mark_attempt") as failed,
              patch.object(api, "finalize_t3") as finalize):
            response = api._run_fixture_send(
                None, b"fake_wire", {"question": "synthetic question"})
        self.assertEqual(response.status_code, 502)
        self.assertNotIn("nonexistent_citation",
                         response.body.decode("utf-8"))
        self.assertNotIn("owner_A", response.body.decode("utf-8"))
        connect_db.assert_called_once_with("history")
        admission.assert_called_once()
        failed.assert_called_once_with(
            connection, "owner_A", "attempt_1", "failed",
            "PROVIDER_REQUEST_FAILED")
        finalize.assert_not_called()


if __name__ == "__main__":
    unittest.main()
