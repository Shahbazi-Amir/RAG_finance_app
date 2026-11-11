"""CR-DB-01A — internal PostgreSQL-only, synthetic controlled reset C1.

No browser, public endpoint, IdP proof validation, C2 or credential change here.
The trusted issuer and reset executor MUST use DIFFERENT restricted PG roles.
The issuer must already have independently verified a one-time server proof;
fixture issuance is NOT real recovery, email ownership or fresh step-up.
Never log/store raw authorization; only SHA256 travels to PostgreSQL.
"""
from __future__ import annotations
from dataclasses import dataclass
from uuid import UUID, uuid4
import hashlib
import secrets
from psycopg.pq import TransactionStatus

KIND_RECOVERY = "RECOVERY"
KIND_AUTHENTICATED = "AUTHENTICATED_PASSWORD_CHANGE"
PURPOSE = "CONTROLLED_RESET_C1"

@dataclass(frozen=True, repr=False)
class SyntheticAuthorization:
    """Raw capability is ephemeral server memory only; representation redacted."""
    opaque: str
    owner_id: str
    kind: str
    expected_epoch: int
    expires_epoch: int
    def __repr__(self) -> str:
        return "SyntheticAuthorization(<redacted>)"

def digest_authorization(opaque: str) -> str:
    if not isinstance(opaque, str) or len(opaque) < 32 or not opaque.isascii():
        raise ValueError("valid opaque authorization required in trusted RAM")
    return hashlib.sha256(opaque.encode("ascii")).hexdigest()

def issue_synthetic_verified_authorization(
    conn, owner_id: str, kind: str, expected_epoch: int, expires_epoch: int,
    *, trusted_session_digest: str | None = None,
    trusted_session_generation: int | None = None,
) -> SyntheticAuthorization:
    """TEST/FIXTURE ONLY. Separate auth_reset_issuer connection is mandatory.

    Existing verified external recovery/step-up evidence is ASSUMED here,
    not proven or emulated by the DB. Expiry is a caller-selected test value,
    not a Production policy or product TTL decision.
    """
    opaque = secrets.token_urlsafe(32)
    digest = digest_authorization(opaque)
    with conn.transaction():
        good = conn.execute(
            "SELECT auth_l1.issue_reset_c1_authorization("
            "%s,%s,%s,%s,%s,%s,%s,%s) AS allowed",
            (digest, owner_id, kind, PURPOSE, expected_epoch, expires_epoch,
             trusted_session_digest, trusted_session_generation),
        ).fetchone()["allowed"]
        if good is not True:
            raise RuntimeError("RESET_C1_ISSUANCE_NOT_TRUE")
    return SyntheticAuthorization(opaque,owner_id,kind,expected_epoch,expires_epoch)

def commit_c1(conn, authorization_opaque: str, *, owner_id: str, kind: str,
              expected_epoch: int, operation_id: UUID | None = None) -> dict:
    """Execute C1 once; caller MUST own explicit outer SAME-CONNECTION PG TX.

    This routine does not commit itself: caller must commit the outer transaction
    only after successful exact-state result; any exception must cause rollback.
    It never authorizes IdP calls, C2, new sessions or retry of consumed proof.
    An operation_id is an audit identifier, not authority or a bearer token.
    """
    if conn.info.transaction_status != TransactionStatus.INTRANS:
        raise RuntimeError("RESET_C1_REQUIRES_OUTER_TRANSACTION")
    op = operation_id if operation_id is not None else uuid4()
    if not isinstance(op, UUID):
        raise ValueError("operation_id must be UUID, not a capability")
    result = conn.execute(
        "SELECT auth_l1.execute_reset_c1(%s,%s,%s,%s,%s,%s) AS result",
        (digest_authorization(authorization_opaque), owner_id, kind, PURPOSE,
         expected_epoch, op),
    ).fetchone()["result"]
    if result["status"] != "REVOKED_PENDING_IDP" or result["revoked_epoch"] != expected_epoch+1:
        raise RuntimeError("RESET_C1_UNEXPECTED_RESULT")
    return result
