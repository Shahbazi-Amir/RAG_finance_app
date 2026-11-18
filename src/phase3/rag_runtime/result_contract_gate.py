"""Fail-closed, schema-pinned raw engine-result validation before any product T3.

There is NO approved real rag_finance.mvp_engine_result.v1 Schema bundled here.
This validator requires a separately vetted server-side SHA256 schema and
field binding profile. Passing it does NOT authorize LIVE_VERIFIED or persist.
No raw output/secret/answer is logged, stored, or included in exceptions.
"""
from __future__ import annotations

import hashlib
import hmac
import json
from dataclasses import dataclass
from typing import Mapping

from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError, ValidationError

from src.phase3.rag_runtime.staging_preflight import (
    CONTRACT_EXPECTED, AttemptBinding, PreflightDenied,
)

MAX_ENGINE_RESULT_BYTES = 1_048_576
SCHEMA_ID = "https://json-schema.org/draft/2020-12/schema"


@dataclass(frozen=True)
class ApprovedResultProfile:
    """Reviewed, server-only LIVE result schema; NEVER selected by a browser.

    C018/C019 notebook version (2) is not mounted in this workspace.
    Until its complete schema is supplied, no profile is approved.
    Runner emits 'schema' and 'request_id', NEVER a trace_id.
    """
    canonical_schema_sha256: str
    contract_version_field: str = "schema"
    engine_request_id_field: str = "request_id"


def correlate_api_trace(validated_runner_result: Mapping,
                        binding: AttemptBinding) -> dict:
    """API-side trace metadata only, never asserted to be Runner output.

    Operational metadata is NOT a product.v1 Answer or a LIVE_VERIFIED claim.
    """
    if (not isinstance(validated_runner_result, Mapping)
            or not isinstance(binding, AttemptBinding)
            or not isinstance(validated_runner_result.get("request_id"), str)
            or validated_runner_result["request_id"] != binding.engine_request_id):
        raise PreflightDenied()
    return {"engine_request_id": binding.engine_request_id,
            "product_request_id": binding.product_request_id,
            "trace_id": binding.trace_id,
            "provenance": "API_ATTEMPT_ONLY",
            "live_verified": False}


def canonical_schema_digest(schema: Mapping) -> str:
    try:
        encoded = json.dumps(schema, sort_keys=True, separators=(",", ":"),
                             ensure_ascii=True, allow_nan=False).encode("ascii")
    except (ValueError, TypeError, UnicodeError):
        raise PreflightDenied() from None
    return hashlib.sha256(encoded).hexdigest()


def _unique_object(pairs):
    obj = {}
    for key, value in pairs:
        if key in obj:
            raise PreflightDenied()
        obj[key] = value
    return obj


def _reject_constant(_):
    raise PreflightDenied()


def _decode_and_validate(raw_result: bytes, schema: Mapping, digest: str) -> dict:
    """Strict JSON + independently SHA-pinned schema, no leaked errors."""
    if (not isinstance(raw_result, bytes)
            or not 0 < len(raw_result) <= MAX_ENGINE_RESULT_BYTES
            or not isinstance(schema, Mapping)
            or not isinstance(digest, str)
            or len(digest) != 64
            or any(c not in "0123456789abcdef" for c in digest)
            or canonical_schema_digest(schema) != digest
            or schema.get("$schema") != SCHEMA_ID):
        raise PreflightDenied()
    try:
        Draft202012Validator.check_schema(schema)
        result = json.loads(
            raw_result.decode("utf-8"),
            object_pairs_hook=_unique_object,
            parse_constant=_reject_constant,
        )
        if not isinstance(result, dict):
            raise PreflightDenied()
        Draft202012Validator(schema).validate(result)
    except (SchemaError, ValidationError, ValueError, UnicodeError, TypeError):
        raise PreflightDenied() from None
    return result


def _safe_field(name: str | None, *, optional: bool = False) -> bool:
    return (name is None and optional) or (
        isinstance(name, str) and name.isidentifier() and 1 <= len(name) <= 80)


def validate_schema_pinned_result(
    raw_result: bytes,
    *,
    schema: Mapping,
    profile: ApprovedResultProfile,
    binding: AttemptBinding,
) -> dict:
    """LIVE result shape: 'schema' + Runner 'request_id'; NO Runner trace ID.

    Do not call finalize_t3: this validates structure/identity only and does
    not prove authentic source attribution, a Locator or LIVE_VERIFIED.
    """
    if (not isinstance(profile, ApprovedResultProfile)
            or not isinstance(binding, AttemptBinding)
            or profile.contract_version_field != "schema"
            or profile.engine_request_id_field != "request_id"):
        raise PreflightDenied()
    result = _decode_and_validate(
        raw_result, schema, profile.canonical_schema_sha256)
    if (result.get("schema") != CONTRACT_EXPECTED
            or result.get("request_id") != binding.engine_request_id):
        raise PreflightDenied()
    return result


def validate_no_dispatch_context_ready(
    raw_result: bytes, *, question: str, binding: AttemptBinding,
) -> dict:
    """NB23.C018 no-dispatch shape: exactly five fields, no IDs.

    No generated Answer. The stored API Attempt owns request_id and trace_id.
    Validate the private question only as a hash; never reflect question,
    content or raw retrieved top10 in the response/History.
    """
    if (not isinstance(raw_result, bytes)
            or not 0 < len(raw_result) <= MAX_ENGINE_RESULT_BYTES
            or not isinstance(question, str) or not question.strip()
            or not isinstance(binding, AttemptBinding)):
        raise PreflightDenied()
    try:
        value = json.loads(
            raw_result.decode("utf-8"),
            object_pairs_hook=_unique_object, parse_constant=_reject_constant)
    except (ValueError, UnicodeError, TypeError):
        raise PreflightDenied() from None
    if (not isinstance(value, dict)
            or set(value) != {
                "status", "question_sha256", "context_sha256",
                "top10", "generation_calls"
            }
            or value["status"] != "CONTEXT_READY"
            or type(value["generation_calls"]) is not int
            or value["generation_calls"] != 0):
        raise PreflightDenied()
    def hex_digest(v):
        return isinstance(v, str) and len(v) == 64 and all(
            c in "0123456789abcdef" for c in v)
    if (not hex_digest(value["question_sha256"])
            or not hex_digest(value["context_sha256"])):
        raise PreflightDenied()
    actual = hashlib.sha256(question.encode("utf-8")).hexdigest()
    if not hmac.compare_digest(actual, value["question_sha256"]):
        raise PreflightDenied()
    top10 = value["top10"]
    # The user-supplied C018 contract gives the field name, not element type.
    # Permit only a bounded count or a bounded list; never echo list content.
    if type(top10) is int and 0 <= top10 <= 10:
        top10_count = top10
    elif isinstance(top10, list) and 0 <= len(top10) <= 10:
        top10_count = len(top10)
    else:
        raise PreflightDenied()
    return {
        "state": "CONTEXT_READY",
        "engine_request_id": binding.engine_request_id,
        "trace_id": binding.trace_id,
        "question_sha256_matches": True,
        "top10_count": top10_count,
        "generation_calls": 0,
        "dispatch_performed": False,
        "live_verified": False,
    }
