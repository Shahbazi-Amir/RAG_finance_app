"""CR-API-03A — internal C1-commit-before-IdP dispatch; synthetic authority only.

No public endpoint, real recovery, worker, retry, durable IdP outcome, C2 or
Product Auth integration. This module never issues reset authorization. A
separate CI-only fixture owns the issuer role. Sensitive capabilities and the
new password must remain in short-lived trusted caller memory.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Protocol
from uuid import UUID, uuid4

import psycopg
from psycopg.pq import TransactionStatus
from requests.exceptions import RequestException

from src.phase3.storage.postgres import reset_c1


@dataclass(frozen=True, repr=False)
class BoundSyntheticReset:
    """Issued by an independent trusted CI fixture, never a public DTO."""
    authorization: reset_c1.SyntheticAuthorization
    target_idp_user: str

    def __repr__(self) -> str:
        return "BoundSyntheticReset(<redacted>)"


@dataclass(frozen=True, repr=False)
class DispatchObservation:
    """Ephemeral, in-process only. NEVER a persisted Keycloak outcome."""
    operation_id: UUID
    revoked_epoch: int
    observed_result: str
    remote_http_status: int | None
    persisted_remote_outcome: bool = False

    def __repr__(self) -> str:
        return "DispatchObservation(<redacted>)"


class ScopedResetTransport(Protocol):
    def send_reset(self, target_idp_user: str, new_password: str) -> int:
        """Perform at most one actual Keycloak PUT; return only HTTP status."""


class C1Rejected(RuntimeError):
    """Generic fail-closed C1 denial; no PG SQL or raw capability in message."""


def dispatch_after_committed_c1(
    executor_connection: Callable[[], psycopg.Connection],
    bound: BoundSyntheticReset,
    new_password: str,
    transport: ScopedResetTransport,
    *,
    resolve_identity: Callable[[str], tuple[str, str] | None],
    trusted_issuer: str,
    operation_id: UUID | None = None,
    before_commit_hook: Callable[[], None] | None = None,
    after_commit_hook: Callable[[], None] | None = None,
) -> DispatchObservation:
    """One C1 transaction, then at most one IdP request; NEVER retry.

    Only a real successful outer PostgreSQL COMMIT grants dispatch. The CI
    hooks inject rollback, a pending commit or a post-commit process stop.
    Hooks are trusted test-only injection points, not authorization paths.
    Existing C1 consumed proof / active operation denies another dispatch.
    """
    if not isinstance(bound, BoundSyntheticReset) or not isinstance(
        bound.authorization, reset_c1.SyntheticAuthorization
    ) or not isinstance(new_password, str) or not new_password or not callable(
        getattr(transport, "send_reset", None)
    ):
        raise C1Rejected("RESET_C1_INVALID_TRUSTED_INPUT")
    if not isinstance(bound.target_idp_user, str) or not bound.target_idp_user:
        raise C1Rejected("RESET_C1_MISSING_TARGET_BINDING")
    if not callable(resolve_identity) or not isinstance(
        trusted_issuer, str
    ) or not trusted_issuer:
        raise C1Rejected("RESET_C1_TRUSTED_IDENTITY_RESOLVER_MISSING")

    # The caller's target hint is NOT authority. Derive the real IdP subject
    # from the independent, trusted Product owner→(issuer,subject) mapping.
    # The resolver is a different trusted server component, NEVER the
    # auth_reset_executor role (which cannot SELECT the Owner mapping).
    # Production use requires a separately reviewed narrow DB read interface;
    # current implementation has only a CI-private privileged read fixture.
    authority = bound.authorization
    try:
        identity = resolve_identity(authority.owner_id)
    except Exception:
        raise C1Rejected("RESET_C1_IDENTITY_LOOKUP_DENIED") from None
    if (not isinstance(identity, tuple) or len(identity) != 2
        or not all(isinstance(v, str) and v for v in identity)
        or identity[0] != trusted_issuer
        or identity[1] != bound.target_idp_user):
        raise C1Rejected("RESET_C1_IDP_OWNER_MISMATCH")
    verified_target_idp_user = identity[1]
    op = operation_id if operation_id is not None else uuid4()
    if not isinstance(op, UUID):
        raise C1Rejected("RESET_C1_INVALID_OPERATION_REFERENCE")

    try:
        with executor_connection() as conn:
            # Accepted wrapper needs a real explicit outer transaction on
            # this exact primary connection; no autocommit SQL shortcut.
            if not conn.autocommit or (
                conn.info.transaction_status != TransactionStatus.IDLE
            ):
                raise C1Rejected("RESET_C1_WRONG_CONNECTION")
            with conn.transaction():
                try:
                    receipt = reset_c1.commit_c1(
                        conn, authority.opaque, owner_id=authority.owner_id,
                        kind=authority.kind, expected_epoch=authority.expected_epoch,
                        operation_id=op,
                    )
                    if before_commit_hook is not None:
                        before_commit_hook()
                except psycopg.Rollback:
                    # psycopg.transaction.Transaction.__exit__ SWALLOWS
                    # psycopg.Rollback after rolling back. If this exception
                    # escaped only to the context manager, execution would
                    # incorrectly continue to the IdP call after a rollback.
                    # Convert it *inside* the context into a denial so no
                    # successful exit/receipt is mistaken for a COMMIT.
                    raise C1Rejected("RESET_C1_ROLLBACK_NO_DISPATCH") from None
            # The block above must COMMIT, not merely return a SQL receipt,
            # before execution ever reaches the network call.
    except (psycopg.Error, ValueError, RuntimeError) as exc:
        if isinstance(exc, C1Rejected):
            raise
        raise C1Rejected("RESET_C1_NOT_COMMITTED_NO_DISPATCH") from None

    # CI stop/crash hook. Its error deliberately propagates, leaving the
    # committed operation active with the product reset gate CLOSED.
    if after_commit_hook is not None:
        after_commit_hook()

    # This is ONE call, with no automatic retry on any response or error.
    try:
        status = transport.send_reset(verified_target_idp_user, new_password)
    except (RequestException, TimeoutError, OSError):
        return DispatchObservation(op, receipt["revoked_epoch"],
                                   "REMOTE_UNKNOWN", None)
    if type(status) is not int:
        return DispatchObservation(op, receipt["revoked_epoch"],
                                   "REMOTE_UNKNOWN", None)
    if status == 204:
        return DispatchObservation(op, receipt["revoked_epoch"],
                                   "OBSERVED_REMOTE_SUCCESS", status)
    if status in (400, 401, 403, 404):
        # Definitive HTTP rejection observed; does not reverse Product C1.
        return DispatchObservation(op, receipt["revoked_epoch"],
                                   "REMOTE_REJECTED", status)
    return DispatchObservation(op, receipt["revoked_epoch"],
                               "REMOTE_UNKNOWN", status)
