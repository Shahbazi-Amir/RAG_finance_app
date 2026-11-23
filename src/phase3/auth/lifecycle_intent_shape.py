"""Source-only Product.v1 lifecycle intent validation, never an API writer.

Reuses existing *provisional* product.v1 client DTOs. No new Consent,
Feedback, Delete, Retention or Export endpoints/policy are invented.
Only a signed, owner-fenced PostgreSQL transaction may perform the mutation
after separate DB/UI/CENTRAL contract approval.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError, ValidationError

_CONTRACT = Path(__file__).resolve().parents[3] / "packages/contracts/product.v1.schema.json"
_INTENTS = frozenset({"feedback_submit_request", "delete_command"})
_MAX_BODY_BYTES = 8192


class LifecycleIntentDenied(Exception):
    """Never echo user reason, raw body, or session data in an error."""

    def __str__(self) -> str:
        return "LIFECYCLE_INTENT_DENIED"


@dataclass(frozen=True, repr=False)
class StructuralLifecycleIntent:
    """Idempotency identity is untrusted until signed Product admission."""

    kind: str
    client_idempotency_ref: str
    canonical_payload_sha256: str
    shape_valid: bool = True
    transaction_authorized: bool = False
    side_effect_performed: bool = False

    def __repr__(self) -> str:
        return "StructuralLifecycleIntent(<redacted; not authorized>)"


def _no_duplicate_keys(pairs):
    obj = {}
    for name, value in pairs:
        if name in obj:
            raise LifecycleIntentDenied()
        obj[name] = value
    return obj


def _deny_nonjson_constant(_):
    raise LifecycleIntentDenied()


def inspect_lifecycle_intent(raw_body: bytes, *, kind: str) -> StructuralLifecycleIntent:
    """Parse closed, canonical client intent without owner/session elevation.

    This source-level helper validates only original provisional schema shapes;
    it is not an endpoint, an idempotency reservation or a deletion receipt.
    """
    if (kind not in _INTENTS or not isinstance(raw_body, bytes)
            or not 0 < len(raw_body) <= _MAX_BODY_BYTES):
        raise LifecycleIntentDenied()
    try:
        full = json.loads(_CONTRACT.read_text(encoding="utf-8"))
        if (not isinstance(full, dict)
                or full.get("$id") != "urn:ragfinance:product:v1"
                or full.get("$schema") != "https://json-schema.org/draft/2020-12/schema"):
            raise LifecycleIntentDenied()
        defs = full["$defs"]
        schema = {
            "$schema": full["$schema"],
            "$defs": defs,
            **defs[kind],
        }
        Draft202012Validator.check_schema(schema)
        payload = json.loads(
            raw_body.decode("utf-8"),
            object_pairs_hook=_no_duplicate_keys,
            parse_constant=_deny_nonjson_constant,
        )
        if not isinstance(payload, dict) or payload.get("kind") != kind:
            raise LifecycleIntentDenied()
        Draft202012Validator(schema).validate(payload)
        ref = (payload["idempotency_key"]
               if kind == "feedback_submit_request"
               else payload["client_action_id"])
        # Same semantic JSON has one digest regardless of property ordering.
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"),
                               ensure_ascii=False, allow_nan=False).encode("utf-8")
        return StructuralLifecycleIntent(
            kind=kind,
            client_idempotency_ref=ref,
            canonical_payload_sha256=hashlib.sha256(canonical).hexdigest(),
        )
    except (OSError, ValueError, UnicodeError, TypeError, KeyError,
            SchemaError, ValidationError, LifecycleIntentDenied):
        raise LifecycleIntentDenied() from None
