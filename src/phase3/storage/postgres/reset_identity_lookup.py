"""CR-DB-01B — synthetic-only scoped, read-only Owner→(issuer,subject) lookup.

Internal storage boundary only. No API or IdP connection. The independently
trusted fixture must already have verified the authorization and must use a
distinct auth_reset_lookup PostgreSQL role. A raw opaque capability remains
only in transient caller memory; SQL gets its fixed SHA-256 digest, never a
Recovery link, password, browser Cookie, Session token or email.

The result is a NON-LOCKING, time-of-query observation. C1 MUST independently
validate and consume the same proof/Owner/epoch at its own transactional commit.
"""
from __future__ import annotations

from .reset_c1 import digest_authorization, PURPOSE, KIND_RECOVERY, KIND_AUTHENTICATED


def resolve(
    conn, authorization_opaque: str, *,
    trusted_owner_id: str, kind: str,
    expected_epoch: int, expected_issuer: str,
) -> dict[str, str]:
    """Return ONLY {'issuer': ..., 'subject': ...} for an unconsumed C1 proof.

    Requires dedicated auth_reset_lookup role. This function deliberately does
    not hold any row lock beyond a SQL statement, consume the authority, or
    promise identity remains valid until a future C1/IdP call. The issuer
    expectation is trusted service context, not a user-supplied email.
    """
    if not isinstance(trusted_owner_id, str) or not trusted_owner_id.strip():
        raise ValueError("trusted owner required")
    if kind not in (KIND_RECOVERY, KIND_AUTHENTICATED):
        raise ValueError("reset kind required")
    if type(expected_epoch) is not int or expected_epoch < 0:
        raise ValueError("expected nonnegative epoch required")
    if not isinstance(expected_issuer, str) or not expected_issuer.strip():
        raise ValueError("expected issuer required")
    digest=digest_authorization(authorization_opaque)
    with conn.transaction():
        result=conn.execute(
            "SELECT auth_l1.resolve_reset_identity(%s,%s,%s,%s,%s,%s) AS pair",
            (digest,trusted_owner_id,kind,PURPOSE,expected_epoch,expected_issuer),
        ).fetchone()["pair"]
        if not isinstance(result,dict) or set(result)!={"issuer","subject"}:
            raise RuntimeError("RESET_IDENTITY_INVALID_RESULT")
    return result
