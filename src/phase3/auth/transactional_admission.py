"""Transaction-scoped API admission with the accepted DB-owned durable replay.

The only replay backend accepted here is Migration 005's DB adapter, not
the former auth_trust_ci.replay_jti fixture. No fallback on bad config.
This is still isolated synthetic SQL, never product Auth/History wiring.
"""
from __future__ import annotations

from contextlib import contextmanager

from typing import Callable, Protocol, TypeVar

import psycopg
from psycopg.pq import TransactionStatus

from src.phase3.storage.postgres import auth_session
from src.phase3.storage.postgres.service_replay import PostgresDurableReplayStore
from .service_proof import BFFServiceVerifier, TrustRejected, VerifiedServiceProof

T = TypeVar("T")


class AdmissionSerializationUnavailable(Exception):
    """Sanitized, non-auth PostgreSQL retryable-transaction failure (no retry)."""


class ReplayStore(Protocol):
    """Must atomically consume a JTI on THE SAME transaction/connection."""

    def consume(self, conn: psycopg.Connection, assertion: VerifiedServiceProof) -> bool:
        ...


@contextmanager
def protected_transaction(
    conn: psycopg.Connection,
    *,
    verifier: BFFServiceVerifier,
    replay_store: ReplayStore | None,
    compact_assertion: str,
    method: str,
    raw_path: bytes,
    raw_query: bytes,
    body: bytes,
):
    """Verify BFF, consume 005 JTI and enforce 004, then hold one outer TX.

    An explicit outer transaction is REQUIRED on a writable PostgreSQL primary.
    Failure, False, unavailable replay table or action error => rollback all
    writes; only EXACT `True` from the accepted DB wrapper is authorization.
    No other DB session validation is reimplemented in Python.

    Final time admission: after the JTI INSERT and Migration 004 Owner/Session
    row locks, take a FRESH PostgreSQL primary clock_timestamp() sample and
    require iat<=sample, nbf<=sample<exp (and age<=30s) before action. The
    pre-lock verifier time is NOT authority after a PostgreSQL lock wait.
    Once action begins before expiration, expiry does NOT cancel it mid-flight.

    JTI policy: consumed only on COMMIT. An attempted use rolled back due to
    action error/expired-after-wait leaves JTI unused; a still-unexpired assertion may
    retry. On successful commit, replay is rejected, even after process restart
    with durable DB. Operation idempotency is DISTINCT; a newly signed JTI
    never changes the product operation's idempotency key or Receipt semantics.
    """
    # No old CI replay table, memory backend, duck-typed replacement or
    # absent configured durable DB adapter is allowed to grant an actor.
    if (not isinstance(replay_store, PostgresDurableReplayStore)
            or verifier is None or conn is None):
        raise TrustRejected() from None
    # On validation error the connection is never even asked to write.
    assertion = verifier.verify(compact_assertion, method=method,
                                raw_path=raw_path, raw_query=raw_query,
                                raw_body=body)
    # Hold one outer transaction for the History read, including Repository savepoints.
    # Even inspecting a *closed or failed* PG connection may itself raise a
    # psycopg error; that too must fail closed, before any protected callback.
    try:
        if not conn.autocommit or conn.info.transaction_status != TransactionStatus.IDLE:
            raise TrustRejected() from None
        with conn.transaction():
            if replay_store.consume(conn, assertion) is not True:
                raise TrustRejected() from None
            permitted = auth_session.admit_session_fenced(
                conn, assertion.session_ref, assertion.owner_id,
                assertion.epoch, assertion.generation,
            )
            if permitted is not True:
                raise TrustRejected() from None
            # Critical TOCTOU boundary: replay insert OR the SQL admission
            # may have waited behind PostgreSQL row/unique locks. Do not
            # authorize a NEW protected action with the verifier's earlier time.
            # A MATERIALIZED CTE samples the primary DB wall clock ONCE,
            # strictly after Migration 004 admission locks are held.
            temporal = conn.execute(
                """WITH decision_clock AS MATERIALIZED
                         (SELECT clock_timestamp() AS checked_at)
                   SELECT (checked_at >= to_timestamp(%s)
                       AND checked_at >= to_timestamp(%s)
                       AND checked_at < to_timestamp(%s)
                       AND checked_at - to_timestamp(%s)
                           <= interval '30 seconds') AS time_valid
                   FROM decision_clock""",
                (assertion.issued_at, assertion.not_before,
                 assertion.expires_at, assertion.issued_at),
            ).fetchone()
            valid = (temporal.get("time_valid") if isinstance(temporal, dict)
                     else temporal[0] if temporal is not None else None)
            if valid is not True:
                # One outer rollback removes the pending JTI INSERT as well.
                raise TrustRejected() from None
            yield assertion.owner_id
    except psycopg.Error as exc:
        # 40001 (serialization) and 40P01 (deadlock) are transaction failures,
        # NOT evidence of an invalid/revoked BFF proof or Product Session.
        # psycopg's outer transaction context has already rolled back 005 JTI
        # and any nested T1/T2 writes before this exception handler runs.
        # No retry and no PostgreSQL details propagate to an HTTP caller.
        if exc.sqlstate in {"40001", "40P01"}:
            raise AdmissionSerializationUnavailable() from None
        # Preserve the existing 005 replay-UNIQUE and absent-grant fail-closed
        # 401 behavior; these do not authorize a protected action.
        raise TrustRejected() from None
    except (ValueError, RuntimeError, TypeError):
        # Existing invalid adapter/proof and unavailable-connection behavior.
        raise TrustRejected() from None


def protected_operation(
    conn: psycopg.Connection,
    *,
    verifier: BFFServiceVerifier,
    replay_store: ReplayStore | None,
    compact_assertion: str,
    method: str,
    raw_path: bytes,
    raw_query: bytes,
    body: bytes,
    action: Callable[[psycopg.Connection, str], T],
) -> T:
    """Execute existing protected action within the same admission transaction."""
    if action is None:
        raise TrustRejected() from None
    with protected_transaction(
        conn, verifier=verifier, replay_store=replay_store,
        compact_assertion=compact_assertion, method=method,
        raw_path=raw_path, raw_query=raw_query, body=body,
    ) as owner:
        return action(conn, owner)
