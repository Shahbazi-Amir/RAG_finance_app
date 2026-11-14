"""Synthetic-only test of approved-schema gate; NOT evidence of actual Runner result."""
from __future__ import annotations

import json
import unittest
from dataclasses import replace

from src.phase3.rag_runtime.result_contract_gate import (
    ApprovedResultProfile, ApprovedReadinessProfile, canonical_schema_digest,
    correlate_api_trace, validate_no_dispatch_context_ready,
    validate_schema_pinned_result,
)
from src.phase3.rag_runtime.staging_preflight import (
    AttemptBinding, PreflightDenied,
)


class ResultSchemaGate(unittest.TestCase):
    def setUp(self):
        self.binding = AttemptBinding("a"*32, "b"*32, "c"*32)
        self.schema = {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "type": "object",
            "additionalProperties": False,
            "required": ["schema", "request_id", "status"],
            "properties": {
                "schema": {
                    "type": "string", "const": "rag_finance.mvp_engine_result.v1",
                },
                "request_id": {"type": "string", "pattern": "^[0-9a-f]{32}$"},
                "status": {"type": "string", "enum": ["synthetic_only"]},
            },
        }
        self.profile = ApprovedResultProfile(
            canonical_schema_sha256=canonical_schema_digest(self.schema),
            contract_version_field="schema",
            engine_request_id_field="request_id",
        )
        self.value = {
            "schema": "rag_finance.mvp_engine_result.v1",
            "request_id": self.binding.engine_request_id,
            "status": "synthetic_only",
        }

    def check(self, value, *, schema=None, profile=None, binding=None):
        return validate_schema_pinned_result(
            json.dumps(value, separators=(",", ":")).encode(),
            schema=self.schema if schema is None else schema,
            profile=self.profile if profile is None else profile,
            binding=self.binding if binding is None else binding,
        )

    def test_pinned_synthetic_live_schema_and_api_only_trace(self):
        self.assertEqual(self.check(self.value), self.value)
        self.assertNotIn('trace_id', self.check(self.value))
        tagged = correlate_api_trace(self.check(self.value), self.binding)
        self.assertEqual(tagged['trace_id'], self.binding.trace_id)
        self.assertFalse(tagged['live_verified'])

    def test_wrong_version_request_id_and_extra_field_denied(self):
        invalid = [
            {**self.value, "schema": "unknown"},
            {**self.value, "request_id": "f"*32},
            {**self.value, "secret_response": "NEVER_LOG_RAW_ANSWER"},
        ]
        for row in invalid:
            with self.subTest(reason=list(set(row.items()) - set(self.value.items()))):
                with self.assertRaises(PreflightDenied) as failure:
                    self.check(row)
                self.assertEqual(str(failure.exception), "STAGING_PREFLIGHT_DENIED")

    def test_schema_digest_wrong_or_missing_blocks_without_fallback(self):
        wrong = replace(self.profile, canonical_schema_sha256="0"*64)
        with self.assertRaises(PreflightDenied):
            self.check(self.value, profile=wrong)
        unsupported = dict(self.schema)
        unsupported["$schema"] = "http://json-schema.org/draft-07/schema#"
        mismatched_profile = replace(
            self.profile, canonical_schema_sha256=canonical_schema_digest(unsupported))
        with self.assertRaises(PreflightDenied):
            self.check(self.value, schema=unsupported, profile=mismatched_profile)

    def test_duplicate_raw_keys_oversized_raw_and_nonfinite_denied(self):
        valid = json.dumps(self.value).encode()
        duplicated = valid[:-1] + b',"request_id":"'+b"a"*32+b'"}'
        for raw in (
            duplicated,
            b'{"schema":NaN}',
            b"{}"+b" "*1_048_576,
        ):
            with self.subTest(bytes=len(raw)):
                with self.assertRaises(PreflightDenied):
                    validate_schema_pinned_result(
                        raw, schema=self.schema, profile=self.profile,
                        binding=self.binding)


    def test_distinct_no_dispatch_context_ready_schema(self):
        # Synthetic *alternative* wire shape only. The real notebook (2) C018
        # / C019 schema and state field must still be supplied and pinned.
        ready_schema = {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "type": "object", "additionalProperties": False,
            "required": ["phase", "top_k", "generation"],
            "properties": {
                "phase": {"const": "CONTEXT_READY"},
                "top_k": {"type": "integer", "minimum": 0},
                "generation": {"type": "integer", "const": 0},
            },
        }
        profile = ApprovedReadinessProfile(
            canonical_schema_sha256=canonical_schema_digest(ready_schema),
            context_state_field="phase")
        raw = b'{"phase":"CONTEXT_READY","top_k":10,"generation":0}'
        result = validate_no_dispatch_context_ready(
            raw, schema=ready_schema, profile=profile, binding=self.binding)
        self.assertEqual(result["engine_request_id"], self.binding.engine_request_id)
        self.assertEqual(result["trace_id"], self.binding.trace_id)
        self.assertFalse(result["dispatch_performed"])
        self.assertFalse(result["live_verified"])
        with self.assertRaises(PreflightDenied):
            validate_no_dispatch_context_ready(
                b'{"phase":"COMPLETE","top_k":10,"generation":0}',
                schema=ready_schema, profile=profile, binding=self.binding)
        with self.assertRaises(PreflightDenied):
            validate_schema_pinned_result(
                raw, schema=ready_schema, profile=self.profile, binding=self.binding)

    def test_no_dispatch_does_not_require_unverified_runner_trace(self):
        ready_schema = {
            "$schema":"https://json-schema.org/draft/2020-12/schema",
            "type":"object", "additionalProperties":False,
            "required":["phase","request_id"],
            "properties":{
                "phase":{"const":"CONTEXT_READY"},
                "request_id":{"type":"string"}
            }
        }
        profile = ApprovedReadinessProfile(
            canonical_schema_digest(ready_schema), "phase", "request_id")
        raw = json.dumps(
            {"phase":"CONTEXT_READY", "request_id":self.binding.engine_request_id}
        ).encode()
        result = validate_no_dispatch_context_ready(
            raw, schema=ready_schema, profile=profile, binding=self.binding)
        self.assertNotIn("raw_output", result)
        with self.assertRaises(PreflightDenied):
            validate_no_dispatch_context_ready(
                json.dumps({"phase":"CONTEXT_READY","request_id":"foreign"}).encode(),
                schema=ready_schema, profile=profile, binding=self.binding)


if __name__ == "__main__":
    unittest.main(verbosity=2)
