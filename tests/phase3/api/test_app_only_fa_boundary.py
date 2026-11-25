"""Offline fixture/contract checks: never import or invoke a runner/provider."""
import copy
import json
import unittest
from pathlib import Path
from jsonschema import Draft202012Validator, ValidationError, FormatChecker
from src.phase3.rag_runtime.claim_citation_graph import (
    CitationGraphDenied, inspect_answer_citation_graph,
)

ROOT = Path(__file__).resolve().parents[3]
CONTRACTS = ROOT / "packages/contracts"
PRODUCT = json.loads((CONTRACTS / "product.v1.schema.json").read_text())
CORPUS = json.loads((CONTRACTS / "fixtures/app-only.fa.redteam.v1.json").read_text())
CASES = json.loads((CONTRACTS / "fixtures/product.v1.cases.json").read_text())["cases"]

def example(name):
    return copy.deepcopy(next(c["document"] for c in CASES if c["case_id"] == name))

def validator(name):
    return Draft202012Validator({"$defs": PRODUCT["$defs"], "$ref": "#/$defs/" + name},
                                format_checker=FormatChecker())

class AppOnlyPersianBoundary(unittest.TestCase):
    def test_fa_redteam_corpus_version_categories_and_no_approval(self):
        self.assertEqual(CORPUS["origin"], "SYNTHETIC")
        self.assertEqual(CORPUS["policy_status"], "PROPOSED_NOT_APPROVED")
        self.assertEqual(CORPUS["contract_version"], "app_only.fa.redteam.v1")
        cases = CORPUS["cases"]
        self.assertEqual(len(cases), 12)
        self.assertEqual(len({x["id"] for x in cases}), 12)
        self.assertEqual(len({x["category"] for x in cases}), 12)
        for case in cases:
            self.assertTrue(any("\u0600" <= c <= "\u06ff" for c in case["question"]))
            self.assertEqual((case["expected_http_status"], case["expected_http_code"]),
                             (503, "ENGINE_NOT_CONFIGURED"))

    def test_proposed_education_personal_and_ambiguous_shapes_are_not_live(self):
        # Explicit fixture outcomes, not a classifier or approved policy.
        for case in CORPUS["cases"]:
            doc = example("valid_answer_no_answer")
            doc.update(outcome=case["expected_shape"], state="completed",
                       claims=[], citations=[], error=None)
            self.assertEqual(doc["provenance"]["origin"], "SYNTHETIC")
            result = inspect_answer_citation_graph(doc)
            self.assertFalse(result.authorizes_product_t3)
            self.assertFalse(result.live_verified)

    def test_refusal_no_answer_and_clarification_cannot_carry_claims(self):
        for outcome in ("refusal", "no_answer", "clarification"):
            doc = example("valid_answer_unresolved_source")
            doc["outcome"] = outcome
            with self.assertRaises(CitationGraphDenied):
                inspect_answer_citation_graph(doc)

    def test_confidence_requires_meaning_and_calibration_scope(self):
        v = validator("confidence")
        v.validate(None)
        valid = {"value": 0, "meaning": "synthetic", "calibration_scope": "fixture"}
        v.validate(valid)
        for key in ("meaning", "calibration_scope"):
            bad = dict(valid)
            del bad[key]
            with self.assertRaises(ValidationError):
                v.validate(bad)
        for value in (-0.01, 1.01):
            with self.assertRaises(ValidationError):
                v.validate(dict(valid, value=value))

    def test_release_binding_cannot_promote_missing_release(self):
        v = validator("rag_binding")
        v.validate({"status":"provisional","blocked_by":"NB23",
                    "release_id":None,"adapter_verified":False})
        for bad in (
            {"status":"verified","blocked_by":None,"release_id":None,"adapter_verified":True},
            {"status":"verified","blocked_by":None,"release_id":"","adapter_verified":True},
        ):
            with self.assertRaises(ValidationError):
                v.validate(bad)

    def test_five_locator_variants_and_mismatched_source_types(self):
        variants = [
            ("website", {"kind":"url","url":"https://example.invalid/source","page":None,"timestamp_ms":None}),
            ("book", {"kind":"book_page","url":None,"page":1,"timestamp_ms":None}),
            ("book", {"kind":"book_anchor","url":None,"page":None,"timestamp_ms":None,
                      "work_id":"synthetic-work","edition_id":"synthetic-edition","anchor":"synthetic-anchor"}),
            ("transcript", {"kind":"transcript_timestamp","url":None,"page":None,"timestamp_ms":0}),
            ("transcript", {"kind":"transcript_segment","url":None,"page":None,"timestamp_ms":None,
                            "episode_id":"synthetic-episode","segment_anchor":"synthetic-segment"}),
        ]
        for source_type, locator in variants:
            doc = example("valid_answer_unresolved_source")
            source = doc["citations"][0]["source"]
            source.update(source_type=source_type, locator=locator,
                          resolution_status="verified", source_id="synthetic-source",
                          attribution_status="unknown")
            # Only syntactic validation; fixture's claimed resolution is not true authority.
            before = copy.deepcopy(doc)
            result = inspect_answer_citation_graph(doc)
            self.assertFalse(result.source_verified)
            self.assertFalse(result.authorizes_product_t3)
            self.assertEqual(doc, before)
            source["source_type"] = "website" if source_type != "website" else "book"
            with self.assertRaises(CitationGraphDenied):
                inspect_answer_citation_graph(doc)

    def test_source_text_cannot_add_privileged_instruction_field(self):
        doc = example("valid_answer_unresolved_source")
        source = doc["citations"][0]["source"]
        source["system_instruction"] = CORPUS["cases"][7]["question"]
        with self.assertRaises(CitationGraphDenied) as err:
            inspect_answer_citation_graph(doc)
        self.assertEqual(str(err.exception), "CITATION_GRAPH_DENIED")

    def test_offline_structured_answer_and_unknown_fields(self):
        doc = example("valid_answer_unresolved_source")
        v = validator("answer")
        v.validate(doc)
        for key in ("claims","citations","provenance","confidence"):
            bad = copy.deepcopy(doc)
            del bad[key]
            with self.assertRaises(ValidationError):
                v.validate(bad)

if __name__ == "__main__":
    unittest.main()
