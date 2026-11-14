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
    """This profile MUST originate from a reviewed server-only manifest.

    Untrusted HTTP clients must never choose schema bytes, digest or binding
    paths. Direct result fields are unknown until actual Runner code review.
    """
    canonical_schema_sha256: str
    contract_version_field: str
    engine_request_id_field: str
    trace_id_field: str | None = None


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


def validate_schema_pinned_result(
    raw_result: bytes,
    *,
    schema: Mapping,
    profile: ApprovedResultProfile,
    binding: AttemptBinding,
) -> dict:
    """Validate REAL result against separately approved schema and Attempt.

    The API must keep validated but unaccepted operational evidence OUT of
    History until Foundation's LIVE_VERIFIED gate. Never auto-finalize_t3.
    """
    if (not isinstance(raw_result, bytes)
            or not 0 < len(raw_result) <= MAX_ENGINE_RESULT_BYTES
            or not isinstance(schema, Mapping)
            or not isinstance(profile, ApprovedResultProfile)
            or not isinstance(binding, AttemptBinding)
            or len(profile.canonical_schema_sha256) != 64
            or any(c not in "0123456789abcdef"
                   for c in profile.canonical_schema_sha256)):
        raise PreflightDenied()
    field_names = [profile.contract_version_field,
                   profile.engine_request_id_field]
    if profile.trace_id_field is not None:
        field_names.append(profile.trace_id_field)
    if (any(not isinstance(k, str) or not k.isidentifier()
            or len(k) > 80 for k in field_names)
            or len(set(field_names)) != len(field_names)):
        raise PreflightDenied()
    if canonical_schema_digest(schema) != profile.canonical_schema_sha256:
        raise PreflightDenied()
    if schema.get("$schema") != SCHEMA_ID:
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
    if (result.get(profile.contract_version_field) != CONTRACT_EXPECTED
            or result.get(profile.engine_request_id_field)
                != binding.engine_request_id
            or (profile.trace_id_field is not None
                and result.get(profile.trace_id_field) != binding.trace_id)):
        raise PreflightDenied()
    return result
