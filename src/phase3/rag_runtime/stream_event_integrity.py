"""Product.v1 stream-integrity L1 boundary; NEVER a stream producer.

Reads the repository's provisional product.v1 schema. This helper validates
an in-memory event sequence and server-bound correlation IDs. It does not
authenticate a provider, verify an Answer/Citation, dispatch a Runner, write T3,
or authorize LIVE_VERIFIED. The no-dispatch mode is always the safe default.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError, ValidationError

_CONTRACT_PATH = (Path(__file__).resolve().parents[3] /
                  "packages/contracts/product.v1.schema.json")
_CORRELATORS = ("stream_id", "answer_id", "request_id", "trace_id")
_TERMINALS = frozenset({"completed", "failed", "unknown", "server_cancelled"})
_LIVE_ONLY = frozenset({"generating", "delta", "completed"})
_FOLLOWING = {
    "connected": frozenset({
        "retrieving", "cancel_requested", "display_cancelled", "failed", "unknown"}),
    "retrieving": frozenset({
        "generating", "cancel_requested", "display_cancelled", "failed", "unknown"}),
    "generating": frozenset({
        "delta", "completed", "cancel_requested", "display_cancelled",
        "failed", "unknown"}),
    "delta": frozenset({
        "delta", "completed", "cancel_requested", "display_cancelled",
        "failed", "unknown"}),
    "cancel_requested": frozenset({
        "server_cancelled", "display_cancelled", "completed", "failed", "unknown"}),
}
_MAX_EVENTS = 4096
_MAX_SESSION_BYTES = 1_048_576


class StreamIntegrityDenied(Exception):
    """Public-safe refusal: no event text, bearer token or owner information."""

    def __str__(self) -> str:
        return "STREAM_INTEGRITY_DENIED"


@dataclass(frozen=True, repr=False)
class ServerStreamBinding:
    """Server-generated, signed/transaction-bound identifiers, not client IDs."""

    stream_id: str
    answer_id: str
    request_id: str
    trace_id: str

    def __repr__(self) -> str:
        return "ServerStreamBinding(<redacted>)"


@dataclass(frozen=True)
class StructuralStreamReceipt:
    """Technical L1 inspection result, not a provider or T3 receipt."""

    event_count: int
    final_event: str
    delivery_state: str
    structural_only: bool = True
    live_verified: bool = False
    authorizes_product_t3: bool = False


def _schema_validator() -> Draft202012Validator:
    """Read the actual source-tree product contract; never fetch remote schema."""
    try:
        schema = json.loads(_CONTRACT_PATH.read_text(encoding="utf-8"))
        if (not isinstance(schema, dict)
                or schema.get("$id") != "urn:ragfinance:product:v1"
                or schema.get("$schema") != "https://json-schema.org/draft/2020-12/schema"):
            raise StreamIntegrityDenied()
        definitions = schema["$defs"]
        envelope = {
            "$schema": schema["$schema"],
            "$defs": definitions,
            **definitions["stream_session"],
        }
        Draft202012Validator.check_schema(envelope)
        return Draft202012Validator(envelope)
    except (OSError, ValueError, KeyError, TypeError, SchemaError):
        raise StreamIntegrityDenied() from None


def inspect_stream_session(
    session: Mapping,
    *,
    binding: ServerStreamBinding,
    no_dispatch_only: bool = True,
) -> StructuralStreamReceipt:
    """Check exact product.v1 event DTO and monotonic state transition rules.

    Call only after a trusted, signed Product session supplies `binding`.
    Caller must separately authenticate every upstream producer and verify
    accepted Generation/Answer+Citation provenance before any persist/publish.
    Even a structurally valid completed event is NOT an authorized T3.
    """
    if (not isinstance(binding, ServerStreamBinding)
            or type(no_dispatch_only) is not bool
            or not isinstance(session, Mapping)):
        raise StreamIntegrityDenied()
    try:
        if set(session) != {"kind", "contract_version", *_CORRELATORS,
                            "delivery_state", "events"}:
            raise StreamIntegrityDenied()
        events = session["events"]
        if not isinstance(events, list) or not 1 <= len(events) <= _MAX_EVENTS:
            raise StreamIntegrityDenied()
        raw = json.dumps(session, ensure_ascii=False, allow_nan=False)
        if len(raw.encode("utf-8")) > _MAX_SESSION_BYTES:
            raise StreamIntegrityDenied()
        _schema_validator().validate(session)
        for name in _CORRELATORS:
            expected = getattr(binding, name)
            if (not isinstance(expected, str)
                    or session[name] != expected):
                raise StreamIntegrityDenied()
        previous = None
        for index, event in enumerate(events):
            if (not isinstance(event, dict) or type(event.get("seq")) is not int
                    or event["seq"] != index
                    or any(event[name] != getattr(binding, name)
                           for name in _CORRELATORS)):
                raise StreamIntegrityDenied()
            event_type = event["event_type"]
            if no_dispatch_only and event_type in _LIVE_ONLY:
                raise StreamIntegrityDenied()
            if index == 0:
                if event_type != "connected":
                    raise StreamIntegrityDenied()
            elif event_type not in _FOLLOWING.get(previous, ()):
                raise StreamIntegrityDenied()
            if (event_type == "completed"
                    and event["data"]["final_answer_id"] != binding.answer_id):
                raise StreamIntegrityDenied()
            previous = event_type

        delivery_state = session["delivery_state"]
        if previous in _TERMINALS:
            if delivery_state != "terminal":
                raise StreamIntegrityDenied()
        elif previous == "display_cancelled":
            if delivery_state != "display_cancelled":
                raise StreamIntegrityDenied()
        elif delivery_state not in {"open", "disconnected"}:
            # A transport disconnect is NOT server cancellation.
            raise StreamIntegrityDenied()
        return StructuralStreamReceipt(
            event_count=len(events), final_event=previous,
            delivery_state=delivery_state,
        )
    except (KeyError, AttributeError, TypeError, ValueError, OverflowError,
            ValidationError, StreamIntegrityDenied):
        raise StreamIntegrityDenied() from None
