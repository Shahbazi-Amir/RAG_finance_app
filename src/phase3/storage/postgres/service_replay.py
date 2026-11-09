"""BND-DB-03 durable PostgreSQL replay; implements API ReplayStore Protocol.
Input must be a VERIFIED BFF proof; this adapter does not validate RSA/IdP.
Raw JWT, JTI, cookie or Session NEVER enter SQL or logs.
"""
from __future__ import annotations
from hashlib import sha256
import re
import psycopg
from psycopg.pq import TransactionStatus

ISSUER=re.compile(r"^[\x21-\x7e]{1,1024}$")
JTI=re.compile(r"^[A-Za-z0-9_-]{20,128}$")

def _digest_and_exp(proof):
    try:
        issuer,jti,expires=proof.issuer,proof.jti,proof.expires_at
    except (AttributeError,TypeError):
        raise ValueError("REPLAY_INVALID_VERIFIED_PROOF") from None
    if (not isinstance(issuer,str) or not ISSUER.fullmatch(issuer)
        or "\x00" in issuer or not isinstance(jti,str) or not JTI.fullmatch(jti)
        or type(expires) is not int or expires<=0 or expires>253402300799):
        raise ValueError("REPLAY_INVALID_VERIFIED_PROOF") from None
    return sha256((issuer+"\x00"+jti).encode("utf8")).hexdigest(),expires

def _outer(conn):
    if (conn is None or not conn.autocommit
            or conn.info.transaction_status!=TransactionStatus.INTRANS):
        raise RuntimeError("REPLAY_REQUIRES_OUTER_TRANSACTION")

class PostgresDurableReplayStore:
    """consume(conn, verified_proof) -> True or exception.

    Role auth_trust_api. UniqueViolation aborts outer transaction until
    coordinator rolls back. No False that could be mistaken as authorization.
    A rollback frees JTI only while unexpired; COMMIT consumes permanently
    until optional expired-key cleanup. Not message idempotency.
    """
    def consume(self,conn:psycopg.Connection,assertion)->bool:
        _outer(conn)
        key,expires=_digest_and_exp(assertion)
        row=conn.execute(
            "SELECT auth_l1.consume_service_assertion(%s,%s) AS accepted",
            (key,expires)).fetchone()
        valid=row.get("accepted") if isinstance(row,dict) else row[0] if row else None
        if valid is not True:
            raise RuntimeError("REPLAY_STORE_DENIED")
        return True

def cleanup_expired(conn:psycopg.Connection,limit:int)->int:
    """Manual only, auth_replay_cleaner role; no scheduled retention policy."""
    _outer(conn)
    row=conn.execute(
        "SELECT auth_l1.purge_expired_service_assertions(%s) AS deleted",(limit,)
    ).fetchone()
    if row is None: raise RuntimeError("REPLAY_CLEANUP_NO_RESPONSE")
    return row.get("deleted") if isinstance(row,dict) else row[0]
