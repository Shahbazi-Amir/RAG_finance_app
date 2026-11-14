"""Fail-closed, schema-pinned raw engine-result validation before any product T3.

There is NO approved real rag_finance.mvp_engine_result.v1 Schema bundled here.
This validator requires a separately vetted server-side SHA256 schema and
field binding profile. Passing it does NOT authorize LIVE_VERIFIED or persist.
No raw output/secret/answer is logged, stored, or included in exceptions.
"""
from __future__ import annotations

import hashlib
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


@dataclass(frozen=True)
class ApprovedReadinessProfile:
    """Separately approved shape of the offline CONTEXT_READY response.

    This shape need not have LIVE result 'schema' or 'request_id'. The
    caller must pin every field/path to the inspected C018/C019 implementation.
    """
    canonical_schema_sha256: str
    context_state_field: str
    engine_request_id_field: str | None = None


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
    raw_result: bytes, *, schema: Mapping, profile: ApprovedReadinessProfile,
    binding: AttemptBinding,
) -> dict:
    """Distinct offline shape; NEVER interpret it as a generated answer.

    The actual key carrying CONTEXT_READY must be sourced from NB23 C018/C019
    and configured in the trusted profile. No default or shape guessing.
    """
    if (not isinstance(profile, ApprovedReadinessProfile)
            or not isinstance(binding, AttemptBinding)
            or not _safe_field(profile.context_state_field)
            or not _safe_field(profile.engine_request_id_field, optional=True)
            or profile.context_state_field == profile.engine_request_id_field):
        raise PreflightDenied()
    result = _decode_and_validate(
        raw_result, schema, profile.canonical_schema_sha256)
    if result.get(profile.context_state_field) != "CONTEXT_READY":
        raise PreflightDenied()
    if (profile.engine_request_id_field is not None
            and result.get(profile.engine_request_id_field)
                != binding.engine_request_id):
        raise PreflightDenied()
    # Return only operational readiness, not answer text or Citations.
    return {"state": "CONTEXT_READY",
            "engine_request_id": binding.engine_request_id,
            "trace_id": binding.trace_id,
            "dispatch_performed": False,
            "live_verified": False}
