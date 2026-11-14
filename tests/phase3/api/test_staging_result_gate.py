"""Synthetic-only test of approved-schema gate; NOT evidence of actual Runner result."""
from __future__ import annotations

import json
import unittest
from dataclasses import replace

from src.phase3.rag_runtime.result_contract_gate import (
    ApprovedResultProfile, canonical_schema_digest,
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
            "required": ["contract_version", "request_id", "trace_id", "status"],
            "properties": {
                "contract_version": {
                    "type": "string", "const": "rag_finance.mvp_engine_result.v1",
                },
                "request_id": {"type": "string", "pattern": "^[0-9a-f]{32}$"},
                "trace_id": {"type": "string", "pattern": "^[0-9a-f]{32}$"},
                "status": {"type": "string", "enum": ["synthetic_only"]},
            },
        }
        self.profile = ApprovedResultProfile(
            canonical_schema_sha256=canonical_schema_digest(self.schema),
            contract_version_field="contract_version",
            engine_request_id_field="request_id",
            trace_id_field="trace_id",
        )
        self.value = {
            "contract_version": "rag_finance.mvp_engine_result.v1",
            "request_id": self.binding.engine_request_id,
            "trace_id": self.binding.trace_id,
            "status": "synthetic_only",
        }

    def check(self, value, *, schema=None, profile=None, binding=None):
        return validate_schema_pinned_result(
            json.dumps(value, separators=(",", ":")).encode(),
            schema=self.schema if schema is None else schema,
            profile=self.profile if profile is None else profile,
            binding=self.binding if binding is None else binding,
        )

    def test_pinned_synthetic_schema_and_trace_binding(self):
        self.assertEqual(self.check(self.value), self.value)

    def test_wrong_version_request_id_trace_and_extra_field_denied(self):
        invalid = [
            {**self.value, "contract_version": "unknown"},
            {**self.value, "request_id": "f"*32},
            {**self.value, "trace_id": "e"*32},
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
            b'{"contract_version":NaN}',
            b"{}"+b" "*1_048_576,
        ):
            with self.subTest(bytes=len(raw)):
                with self.assertRaises(PreflightDenied):
                    validate_schema_pinned_result(
                        raw, schema=self.schema, profile=self.profile,
                        binding=self.binding)


if __name__ == "__main__":
    unittest.main(verbosity=2)
