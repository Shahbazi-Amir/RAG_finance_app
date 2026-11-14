"""Offline tests for C018's five-field output; no Runner or Gateway."""
import hashlib
import json
import unittest

from src.phase3.rag_runtime.result_contract_gate import (
    ApprovedResultProfile, canonical_schema_digest,
    correlate_api_trace, validate_no_dispatch_context_ready,
    validate_schema_pinned_result,
)
from src.phase3.rag_runtime.staging_preflight import AttemptBinding, PreflightDenied


class ResultSchemaGate(unittest.TestCase):
    def setUp(self):
        self.binding = AttemptBinding("a"*32, "b"*32, "c"*32)
        self.question = "سؤال مصنوعی تستی"
        self.context = "d"*64
        self.ready = {
            "status": "CONTEXT_READY",
            "question_sha256": hashlib.sha256(self.question.encode("utf-8")).hexdigest(),
            "context_sha256": self.context,
            "top10": 10, "generation_calls": 0,
        }

    def parse(self, obj, *, question=None):
        return validate_no_dispatch_context_ready(
            json.dumps(obj, ensure_ascii=False).encode(),
            question=self.question if question is None else question,
            binding=self.binding)

    def test_exact_c018_five_field_context_ready_and_api_trace(self):
        result = self.parse(self.ready)
        self.assertEqual(result["state"], "CONTEXT_READY")
        self.assertEqual(result["top10_count"], 10)
        self.assertEqual(result["generation_calls"], 0)
        self.assertTrue(result["question_sha256_matches"])
        self.assertEqual(result["engine_request_id"], self.binding.engine_request_id)
        self.assertEqual(result["trace_id"], self.binding.trace_id)
        self.assertFalse(result["live_verified"])
        self.assertNotIn("answer", result)

    def test_c018_runner_has_no_request_id_or_trace_id(self):
        for key in ("request_id", "trace_id"):
            with self.subTest(key=key), self.assertRaises(PreflightDenied):
                self.parse({**self.ready, key: "f"*32})

    def test_wrong_question_hash_fails_closed(self):
        with self.assertRaises(PreflightDenied):
            self.parse(self.ready, question="سؤال دیگری")
        with self.assertRaises(PreflightDenied):
            self.parse({**self.ready, "question_sha256": "x"*64})

    def test_nonzero_or_noninteger_generation_denied(self):
        for value in (1, -1, True, "0"):
            with self.subTest(value=value), self.assertRaises(PreflightDenied):
                self.parse({**self.ready, "generation_calls": value})

    def test_top10_list_or_count_redacted(self):
        self.assertEqual(self.parse({**self.ready,"top10":[{"private":"DO_NOT_ECHO"}]})["top10_count"],1)
        for bad in (11,-1,True,"10",list(range(11))):
            with self.subTest(str(bad)),self.assertRaises(PreflightDenied):
                self.parse({**self.ready,"top10":bad})

    def test_missing_wrong_state_context_hash_denied(self):
        for obj in (
            {**self.ready, "status":"ANSWER_COMMITTED"},
            {k:v for k,v in self.ready.items() if k!="context_sha256"},
            {**self.ready,"context_sha256":"x"*64},
        ):
            with self.assertRaises(PreflightDenied):
                self.parse(obj)

    def test_duplicate_raw_keys_nan_and_size_denied(self):
        duplicate = json.dumps(self.ready).encode()[:-1]+b',"status":"CONTEXT_READY"}'
        for raw in (duplicate, b'{"status":NaN}', b"{}"+b" "*1_048_576):
            with self.assertRaises(PreflightDenied):
                validate_no_dispatch_context_ready(
                    raw,question=self.question,binding=self.binding)

    def test_live_result_still_pins_schema_request_id_not_trace(self):
        schema={
            "$schema":"https://json-schema.org/draft/2020-12/schema",
            "type":"object","additionalProperties":False,
            "required":["schema","request_id"],
            "properties":{
                "schema":{"const":"rag_finance.mvp_engine_result.v1"},
                "request_id":{"type":"string"},
            },
        }
        profile=ApprovedResultProfile(canonical_schema_digest(schema))
        raw=json.dumps({
            "schema":"rag_finance.mvp_engine_result.v1",
            "request_id":self.binding.engine_request_id,
        }).encode()
        validated=validate_schema_pinned_result(
            raw,schema=schema,profile=profile,binding=self.binding)
        tagged=correlate_api_trace(validated,self.binding)
        self.assertEqual(tagged["trace_id"],self.binding.trace_id)
        self.assertFalse(tagged["live_verified"])
        self.assertNotIn("trace_id",validated)

    def test_failed_live_schema_never_becomes_ready(self):
        with self.assertRaises(PreflightDenied):
            self.parse({"schema":"rag_finance.mvp_engine_result.v1",
                        "request_id":self.binding.engine_request_id})


if __name__ == "__main__":
    unittest.main(verbosity=2)
