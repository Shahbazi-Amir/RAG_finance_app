"""CR-API-03C — accepted 007 → 006 C1 → durable 008 attempt → one IdP call.

Synthetic proof only. 008 can record a committed, bounded *local observation*
of HTTP outcomes; it is NEVER IdP password-change assurance or C2 permission.
No public endpoint, real recovery, reconciliation, retry, worker, C2, Product
Auth, or Gate-open. Short-lived caller memory only for passwords and proofs.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Protocol
from uuid import UUID, uuid4

import psycopg
from psycopg.pq import TransactionStatus
from requests.exceptions import (RequestException, Timeout as HTTPTimeout,
                                 ConnectionError as HTTPConnectionError)

from src.phase3.storage.postgres import reset_c1, reset_identity_lookup, reset_idp_attempt


@dataclass(frozen=True, repr=False)
class BoundSyntheticReset:
    """Issued by an independent trusted CI fixture, never a public DTO."""
    authorization: reset_c1.SyntheticAuthorization
    target_idp_user: str

    def __repr__(self) -> str:
        return "BoundSyntheticReset(<redacted>)"


@dataclass(frozen=True, repr=False)
class DispatchObservation:
    """Local adapter receipt: persisted flag means 008 local CAS confirmed,
    never durable verification of actual IdP credential state.
    """
    operation_id: UUID
    revoked_epoch: int
    observed_result: str
    remote_http_status: int | None
    persisted_remote_outcome: bool = False
    attempt_id: UUID | None = None
    committed_attempt: bool = False
    outcome_code: str | None = None

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
    lookup_connection: Callable[[], psycopg.Connection],
    recorder_connection: Callable[[], psycopg.Connection],
    trusted_issuer: str,
    after_lookup_hook: Callable[[], None] | None = None,
    operation_id: UUID | None = None,
    before_commit_hook: Callable[[], None] | None = None,
    after_commit_hook: Callable[[], None] | None = None,
    before_attempt_commit_hook: Callable[[], None] | None = None,
    after_attempt_commit_hook: Callable[[], None] | None = None,
    before_outcome_commit_hook: Callable[[], None] | None = None,
    after_outcome_commit_hook: Callable[[], None] | None = None,
) -> DispatchObservation:
    """007 Lookup → committed 006 C1 → committed 008 Attempt → one IdP PUT
    → separately committed 008 Outcome. No automatic retries.

    No DB transaction survives into send_reset(). SQL receipts, swallowed
    psycopg.Rollback and unknown COMMIT outcome NEVER license dispatch.
    All injected hooks are private, CI-only fault controls.
    """
    if not isinstance(bound, BoundSyntheticReset) or not isinstance(
        bound.authorization, reset_c1.SyntheticAuthorization
    ) or not isinstance(new_password, str) or not new_password or not callable(
        getattr(transport, "send_reset", None)
    ):
        raise C1Rejected("RESET_C1_INVALID_TRUSTED_INPUT")
    if not isinstance(bound.target_idp_user, str) or not bound.target_idp_user:
        raise C1Rejected("RESET_C1_MISSING_TARGET_BINDING")
    if not callable(lookup_connection) or not callable(recorder_connection) or not isinstance(
        trusted_issuer, str
    ) or not trusted_issuer:
        raise C1Rejected("RESET_C1_SCOPED_LOOKUP_REQUIRED")

    # Accepted 007 interface, NOT the former privileged Fixture identity
    # query. SAME raw synthetic proof, Owner, kind, epoch, server issuer as C1.
    # Reject accidental superuser/admin role. No fallback to another role.
    authority = bound.authorization
    try:
        with lookup_connection() as lookup_conn:
            if not lookup_conn.autocommit or (
                lookup_conn.info.transaction_status != TransactionStatus.IDLE
            ):
                raise C1Rejected("RESET_C1_LOOKUP_CONNECTION_NOT_IDLE")
            role = lookup_conn.execute("SELECT current_user AS role").fetchone()["role"]
            if role != "auth_reset_lookup":
                raise C1Rejected("RESET_C1_SCOPED_LOOKUP_ROLE_REQUIRED")
            identity = reset_identity_lookup.resolve(
                lookup_conn, authority.opaque,
                trusted_owner_id=authority.owner_id,
                kind=authority.kind,
                expected_epoch=authority.expected_epoch,
                expected_issuer=trusted_issuer,
            )
    except Exception:
        raise C1Rejected("RESET_C1_SCOPED_LOOKUP_DENIED") from None
    if (not isinstance(identity, dict)
        or set(identity) != {"issuer", "subject"}
        or identity["issuer"] != trusted_issuer
        or not isinstance(identity["subject"], str)
        or not identity["subject"]
        or identity["subject"] != bound.target_idp_user):
        raise C1Rejected("RESET_C1_IDP_OWNER_MISMATCH")
    verified_target_idp_user = identity["subject"]

    # Trusted CI-only interleaving injection: the successful read-only 007
    # observation is not a reservation; 006 MUST independently recheck C1.
    if after_lookup_hook is not None:
        after_lookup_hook()

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
            # A user hook may close the connection while SQL is pending.
            # psycopg may exit its Transaction context without a successful
            # COMMIT acknowledgement on an already-closed connection.
            if conn.closed or conn.info.transaction_status != TransactionStatus.IDLE:
                raise C1Rejected("RESET_C1_CONNECTION_COMMIT_UNVERIFIED")
            # A receipt alone, without a confirmed transaction exit, is not
            # permission to advance to Recorder or IdP.
    except (psycopg.Error, ValueError, RuntimeError) as exc:
        if isinstance(exc, C1Rejected):
            raise
        raise C1Rejected("RESET_C1_NOT_COMMITTED_NO_DISPATCH") from None

    # CI stop/crash hook. Its error deliberately propagates, leaving the
    # committed operation active with the product reset gate CLOSED.
    if after_commit_hook is not None:
        after_commit_hook()

    # CR-API-03C: Record a durable, one-time intent AFTER C1 is committed,
    # but BEFORE any external HTTP. Receipt inside a transaction is NOT an ACK.
    # A different auth_reset_idp_recorder connection is mandatory.
    attempt_id = uuid4()
    try:
        with recorder_connection() as recorder:
            if not recorder.autocommit or (
                recorder.info.transaction_status != TransactionStatus.IDLE
            ):
                raise C1Rejected("RESET_IDP_RECORDER_CONNECTION_NOT_IDLE")
            role = recorder.execute("SELECT current_user AS role").fetchone()["role"]
            if role != "auth_reset_idp_recorder":
                raise C1Rejected("RESET_IDP_RECORDER_ROLE_REQUIRED")
            with recorder.transaction():
                try:
                    attempt_receipt = reset_idp_attempt.record_attempt(
                        recorder, authority.opaque,
                        owner_id=authority.owner_id, kind=authority.kind,
                        revoked_epoch=receipt["revoked_epoch"],
                        operation_id=op, attempt_id=attempt_id,
                    )
                    if before_attempt_commit_hook is not None:
                        before_attempt_commit_hook()
                except psycopg.Rollback:
                    # Psycopg silently swallows Rollback at transaction exit.
                    # Convert to a normal raised exception *inside* the TX.
                    raise C1Rejected("RESET_IDP_ATTEMPT_ROLLBACK_NO_DISPATCH") from None
            if recorder.closed or (
                recorder.info.transaction_status != TransactionStatus.IDLE
            ):
                raise C1Rejected("RESET_IDP_ATTEMPT_CONNECTION_COMMIT_UNVERIFIED")
        # The recorder connection and transaction are now CLOSED; failure or
        # ambiguous COMMIT above cannot be interpreted as a successful attempt.
        if (attempt_receipt["attempt_id"] != str(attempt_id)
            or attempt_receipt["operation_id"] != str(op)
            or attempt_receipt["status"] != reset_idp_attempt.NO_OUTCOME_RECORDED):
            raise C1Rejected("RESET_IDP_ATTEMPT_UNVERIFIED_NO_DISPATCH")
        if after_attempt_commit_hook is not None:
            # Inject a lost/ambiguous COMMIT acknowledgement or process stop:
            # even if the row DID commit, do NOT send a remote request.
            after_attempt_commit_hook()
    except (psycopg.Error, RuntimeError, ValueError, TimeoutError, OSError):
        raise C1Rejected("RESET_IDP_ATTEMPT_COMMIT_NOT_CONFIRMED_NO_DISPATCH") from None

    # The sole IdP call is strictly *after* known C1 and Attempt commits and
    # connection close. No recorder/executor/lookup locks survive this call.
    status: int | None = None
    observed: str = "REMOTE_UNKNOWN"
    code = "UNVERIFIABLE"
    durable_outcome = reset_idp_attempt.UNKNOWN
    try:
        status = transport.send_reset(verified_target_idp_user, new_password)
    except HTTPTimeout:
        code = "TIMEOUT"
    except TimeoutError:
        code = "TIMEOUT"
    except HTTPConnectionError:
        code = "DISCONNECT"
    except OSError:
        code = "DISCONNECT"
    except RequestException:
        code = "UNVERIFIABLE"
    else:
        if type(status) is not int:
            status = None
            code = "UNVERIFIABLE"
        elif status == 204:
            observed = "OBSERVED_REMOTE_SUCCESS"
            durable_outcome = reset_idp_attempt.OBSERVED_REMOTE_SUCCESS
            code = "REMOTE_2XX_OBSERVED"
        elif status == 403:
            observed = "REMOTE_REJECTED"
            durable_outcome = reset_idp_attempt.DEFINITIVE_REJECTION
            code = "POLICY_REJECTED"
        elif status == 404:
            observed = "REMOTE_REJECTED"
            durable_outcome = reset_idp_attempt.DEFINITIVE_REJECTION
            code = "ACCOUNT_REJECTED"
        elif 500 <= status <= 599:
            code = "REMOTE_5XX"
        else:
            # 400/401/other and unexpected 2xx are not independently
            # documented as *definitive no-change* responses.
            code = "OTHER_UNKNOWN"

    # Record the bounded local observation in a NEW, short, explicit TX.
    # A failed/ambiguous outcome COMMIT never becomes a durable claim.
    persisted = False
    try:
        with recorder_connection() as recorder:
            if not recorder.autocommit or (
                recorder.info.transaction_status != TransactionStatus.IDLE
            ):
                raise C1Rejected("RESET_IDP_OUTCOME_CONNECTION_NOT_IDLE")
            role = recorder.execute("SELECT current_user AS role").fetchone()["role"]
            if role != "auth_reset_idp_recorder":
                raise C1Rejected("RESET_IDP_OUTCOME_RECORDER_ROLE_REQUIRED")
            with recorder.transaction():
                try:
                    result = reset_idp_attempt.record_outcome(
                        recorder, authority.opaque,
                        owner_id=authority.owner_id, kind=authority.kind,
                        revoked_epoch=receipt["revoked_epoch"],
                        operation_id=op, attempt_id=attempt_id,
                        outcome=durable_outcome, code=code,
                    )
                    if before_outcome_commit_hook is not None:
                        before_outcome_commit_hook()
                except psycopg.Rollback:
                    raise C1Rejected("RESET_IDP_OUTCOME_ROLLBACK") from None
            if recorder.closed or (
                recorder.info.transaction_status != TransactionStatus.IDLE
            ):
                raise C1Rejected("RESET_IDP_OUTCOME_CONNECTION_COMMIT_UNVERIFIED")
        if (result["attempt_id"] != str(attempt_id)
            or result["outcome"] != durable_outcome
            or result["code"] != code):
            raise C1Rejected("RESET_IDP_OUTCOME_UNVERIFIED")
        if after_outcome_commit_hook is not None:
            after_outcome_commit_hook()
        persisted = True
    except (psycopg.Error, RuntimeError, ValueError, TimeoutError, OSError):
        # We cannot distinguish failed from acknowledged-but-lost COMMIT.
        # Never resend to IdP, and never claim persisted IDP_CONFIRMED.
        persisted = False

    return DispatchObservation(
        operation_id=op, revoked_epoch=receipt["revoked_epoch"],
        observed_result=observed, remote_http_status=status,
        persisted_remote_outcome=persisted, attempt_id=attempt_id,
        committed_attempt=True, outcome_code=code if persisted else None,
    )
