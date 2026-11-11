"""CR-DB-01C — durable product-PG IdP attempt/outcome (synthetic only).

Only the separate auth_reset_idp_recorder role may invoke these two named
SECURITY DEFINER functions. This is NOT an IdP caller, retry service, C2,
reconciliation policy, password-change proof or product session publisher.
Operation ID is NOT authority; SQL receives only a digest of the already-
consumed C1 capability plus exact trusted Owner, kind and revoked epoch.
"""
from __future__ import annotations

from uuid import UUID,uuid4
from psycopg.pq import TransactionStatus

from .reset_c1 import digest_authorization, PURPOSE, KIND_RECOVERY, KIND_AUTHENTICATED

NO_OUTCOME_RECORDED = "NO_OUTCOME_RECORDED"
OBSERVED_REMOTE_SUCCESS = "OBSERVED_REMOTE_SUCCESS"
DEFINITIVE_REJECTION = "DEFINITIVE_REJECTION"
UNKNOWN = "UNKNOWN"

ALLOWED_CODES = {
    OBSERVED_REMOTE_SUCCESS: frozenset(("REMOTE_2XX_OBSERVED",)),
    DEFINITIVE_REJECTION: frozenset(("POLICY_REJECTED","ACCOUNT_REJECTED")),
    UNKNOWN: frozenset(("TIMEOUT","DISCONNECT","REMOTE_5XX","UNVERIFIABLE","OTHER_UNKNOWN")),
}


def _validate_scope(conn, authorization_opaque, owner_id, kind, revoked_epoch, operation_id, attempt_id):
    if conn.info.transaction_status != TransactionStatus.INTRANS:
        raise RuntimeError("RESET_IDP_REQUIRES_EXPLICIT_OUTER_TRANSACTION")
    if not isinstance(owner_id,str) or not owner_id.strip():
        raise ValueError("trusted Owner required")
    if kind not in (KIND_RECOVERY,KIND_AUTHENTICATED):
        raise ValueError("trusted C1 kind required")
    if type(revoked_epoch) is not int or revoked_epoch <= 0:
        raise ValueError("current post-C1 epoch required")
    if not isinstance(operation_id,UUID) or not isinstance(attempt_id,UUID):
        raise ValueError("operation_id and attempt_id must be UUID")
    return digest_authorization(authorization_opaque)


def record_attempt(conn,authorization_opaque: str,*,owner_id: str,kind: str,
                   revoked_epoch: int,operation_id: UUID,
                   attempt_id: UUID | None = None) -> dict:
    """Record durable attempt BEFORE any future IdP call; caller MUST COMMIT.

    A returned receipt from an open caller transaction is NOT durable yet.
    The caller must commit then close/release the DB transaction before any
    separate remote dispatch. No HTTP/IdP call is performed here.
    """
    identifier=uuid4() if attempt_id is None else attempt_id
    digest=_validate_scope(conn,authorization_opaque,owner_id,kind,revoked_epoch,
                           operation_id,identifier)
    data=conn.execute(
        "SELECT auth_l1.record_reset_idp_attempt(%s,%s,%s,%s,%s,%s,%s) AS receipt",
        (digest,owner_id,kind,PURPOSE,revoked_epoch,operation_id,identifier),
    ).fetchone()["receipt"]
    if data["status"] != NO_OUTCOME_RECORDED or data["attempt_id"] != str(identifier):
        raise RuntimeError("RESET_IDP_UNEXPECTED_ATTEMPT_RECEIPT")
    return data


def record_outcome(conn,authorization_opaque: str,*,owner_id: str,kind: str,
                   revoked_epoch: int,operation_id: UUID,attempt_id: UUID,
                   outcome: str,code: str) -> dict:
    """CAS an already committed attempt to one immutable local observation.

    UNKNOWN is terminal for this package; NO_OUTCOME_RECORDED is semantically
    unknown as well and never licenses a second attempt or Gate opening.
    OBSERVED_REMOTE_SUCCESS is not proof a password was changed.
    """
    digest=_validate_scope(conn,authorization_opaque,owner_id,kind,revoked_epoch,
                           operation_id,attempt_id)
    if not isinstance(outcome,str) or not isinstance(code,str) or code not in ALLOWED_CODES.get(outcome,()):
        raise ValueError("only allowlisted outcome/code pairs may be stored")
    data=conn.execute(
        "SELECT auth_l1.record_reset_idp_outcome(%s,%s,%s,%s,%s,%s,%s,%s,%s) AS receipt",
        (digest,owner_id,kind,PURPOSE,revoked_epoch,operation_id,attempt_id,outcome,code),
    ).fetchone()["receipt"]
    if data["attempt_id"] != str(attempt_id) or data["outcome"] != outcome or data["code"] != code:
        raise RuntimeError("RESET_IDP_UNEXPECTED_OUTCOME_RECEIPT")
    return data
