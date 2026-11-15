"""API-owned adapter for DB #56 Migration 011's immutable external Claim.

This is strictly an authorization boundary, NOT a real Gateway client.
The signed #52 005 + 004 fenced transaction owns the connection and commits
T1 + T2 + Claim together. A winning claim's result is NOT a send receipt;
the only permitted external call is *after definitively confirmed COMMIT*.
No automatic retry after unknown Commit, Gateway timeout or process restart.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Callable, Mapping
from uuid import UUID

from src.phase3.rag_runtime.staging_preflight import (
    AttemptBinding, PreflightDenied, bind_persisted_attempt,
)


class DispatchClaimDenied(PreflightDenied):
    def __str__(self) -> str:
        return "EXTERNAL_CLAIM_NOT_AUTHORIZED"


@dataclass(frozen=True, repr=False)
class CommittedDispatchPermit:
    """Trusted internal T2 binding and DB-issued opaque UUID, never browser data."""

    owner_id: str
    binding: AttemptBinding
    claim_id: UUID

    def __repr__(self) -> str:
        return "CommittedDispatchPermit(<redacted>)"


def claim_within_signed_t2(conn, owner_id: str, attempt: Mapping) -> CommittedDispatchPermit:
    """Execute exact DB-owned 011 SQL using the SAME signed and fenced connection.

    Caller MUST run this after send_t1 + start_t2 and before the SAME outer
    protected_transaction exits. Return value is NOT a committed permit until
    the caller's outer transaction exits without ambiguity. A denial raises,
    rolling back T1/T2/JTI/Claim rather than leaving unclaimed new messages.
    """
    if not isinstance(owner_id, str) or not owner_id or not isinstance(attempt, Mapping):
        raise DispatchClaimDenied()
    binding = bind_persisted_attempt(attempt)
    if attempt.get("owner_id") != owner_id:
        raise DispatchClaimDenied()
    # No client-supplied owner, attempt ID, trace or claim id is consulted.
    row = conn.execute(
        "SELECT claim_won,claim_id,claimed_at FROM "
        "history_l1.claim_external_dispatch(%s,%s,%s)",
        (owner_id, binding.engine_request_id, binding.trace_id),
    ).fetchone()
    if (not isinstance(row, Mapping)
            or row.get("claim_won") is not True
            or not isinstance(row.get("claim_id"), UUID)
            or not isinstance(row.get("claimed_at"), datetime)
            or row["claimed_at"].tzinfo is None):
        raise DispatchClaimDenied()
    return CommittedDispatchPermit(owner_id, binding, row["claim_id"])


def after_definitive_commit(
    committed_operation: Callable[[], tuple[Mapping, CommittedDispatchPermit | None]],
    enqueue_one: Callable[[CommittedDispatchPermit, str], None],
    question: str,
) -> tuple[Mapping, bool]:
    """Only a definitive COMMIT-returned winner may schedule one send boundary.

    Never schedule on an exception, replay, unclaimed receipt or unknown
    Commit outcome. A queue/process crash does NOT re-acquire the DB Claim.
    """
    if not isinstance(question, str) or not question.strip():
        raise DispatchClaimDenied()
    receipt, permit = committed_operation()
    if not isinstance(receipt, Mapping):
        raise DispatchClaimDenied()
    if receipt.get("disposition") == "replayed":
        if permit is not None:
            raise DispatchClaimDenied()
        return receipt, False
    if receipt.get("disposition") != "created" or not isinstance(permit, CommittedDispatchPermit):
        raise DispatchClaimDenied()
    # No server-side DB transaction survives committed_operation return.
    enqueue_one(permit, question)
    return receipt, True


def owner_scoped_claim_status(conn, owner_id: str, attempt: Mapping) -> dict | None:
    """Read-only 011 lookup. Caller MUST be an independently signed 005/004 GET.

    No sending, claim re-acquisition, raw Answer, or sensitive claim_id.
    """
    if not isinstance(owner_id, str) or not isinstance(attempt, Mapping):
        raise DispatchClaimDenied()
    if attempt.get("owner_user_id") != owner_id:
        raise DispatchClaimDenied()
    attempt_id, trace = attempt.get("attempt_id"), attempt.get("attempt_trace_id")
    if attempt_id is None:
        return {"dispatch_state": "NOT_STARTED"}
    if (not isinstance(attempt_id, str) or len(attempt_id) != 32
            or not isinstance(trace, str) or len(trace) != 32):
        raise DispatchClaimDenied()
    row = conn.execute(
        "SELECT dispatch_state,claimed_at,unknown_at,reconciled_at FROM "
        "history_l1.status_external_dispatch(%s,%s,%s)",
        (owner_id, attempt_id, trace),
    ).fetchone()
    if row is None:
        # Owner/Conversation/Attempt mismatch is hidden by the caller.
        return None
    if (not isinstance(row, Mapping)
            or row.get("dispatch_state") not in {
                "NOT_CLAIMED", "CLAIMED", "UNKNOWN",
                "RECONCILED_DELIVERED", "RECONCILED_NOT_DELIVERED"
            }):
        raise DispatchClaimDenied()
    return {"dispatch_state": row["dispatch_state"]}


def flag_reporter_unknown(conn, permit: CommittedDispatchPermit, reason: str) -> bool:
    """Restricted, externally provisioned 011 reporter role; never History app.

    Can only mark ambiguity after the boundary was actually attempted.
    Failed reporting preserves a local UNKNOWN obligation; NEVER retry send.
    """
    if (not isinstance(permit, CommittedDispatchPermit)
            or reason not in {"TIMEOUT", "LOST_RESPONSE", "CRASH", "COMMIT_UNCERTAIN"}):
        raise DispatchClaimDenied()
    row = conn.execute(
        "SELECT history_l1.flag_external_dispatch_unknown(%s,%s,%s,%s,%s) AS ok",
        (permit.owner_id, permit.binding.engine_request_id,
         permit.binding.trace_id, permit.claim_id, reason),
    ).fetchone()
    return isinstance(row, Mapping) and row.get("ok") is True
