"""Closed versioned synthetic result contract for Foundation review.

JSON Schema is API-owned and isolated from immutable product.v1. This
CI-only validator cannot be used to promote a provisional fixture to T3.
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Mapping

from jsonschema import Draft202012Validator, ValidationError, SchemaError

from src.phase3.rag_runtime.staging_invited_result_fixture import (
    FIXTURE_ANSWER, VERSION,
)
from src.phase3.rag_runtime.staging_preflight import PreflightDenied

_SCHEMA = Path(__file__).with_name("staging_invited_live_result.v1.schema.json")


@lru_cache(maxsize=1)
def _validator() -> Draft202012Validator:
    try:
        schema = json.loads(_SCHEMA.read_text(encoding="utf-8"))
        Draft202012Validator.check_schema(schema)
        return Draft202012Validator(schema)
    except (OSError, ValueError, SchemaError):
        raise PreflightDenied() from None


def validate_ci_invited_result(doc: Mapping) -> None:
    """Exact PENDING/READY/UNKNOWN/FAILED wire; never creates a Product Answer."""
    if not isinstance(doc, Mapping) or doc.get("contract_version") != VERSION:
        raise PreflightDenied()
    try:
        _validator().validate(doc)
    except (ValidationError, TypeError, ValueError):
        raise PreflightDenied() from None
    if doc["result_status"] == "READY" and doc["answer"] != FIXTURE_ANSWER:
        raise PreflightDenied()
