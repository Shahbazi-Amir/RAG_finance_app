"""BND-DB-01: PostgreSQL product Owner Mapping / opaque Session Store.

INTERNAL TRUST BOUNDARY: Only a server-side authenticated OIDC/BFF worker may call
map_identity(), issue(), finish_simulated_reauth(), etc. This module does NOT
verify issuer/signature/subject, perform Keycloak reset, issue cookies, or
authorize HTTP. Each SQL connection must use its dedicated service-role DSN.
Do NOT expose raw opaque session IDs in logs, SQL, artifacts or persistence.
"""
from __future__ import annotations
from dataclasses import dataclass
import hashlib
import secrets

# CSPRNG: token_urlsafe(32) contains 256 bits of entropy. It exists only in
# trusted caller RAM; PostgreSQL receives fixed-length SHA-256 hexadecimal.
def _new_opaque():
    return secrets.token_urlsafe(32)

def _digest(opaque):
    if not isinstance(opaque, str) or not opaque:
        raise ValueError("opaque token required in trusted server memory")
    return hashlib.sha256(opaque.encode("ascii")).hexdigest()

@dataclass(frozen=True, repr=False)
class Issued:
    """Opaque secret MUST stay in server memory / secure HTTP-only cookie only."""
    opaque: str
    owner_id: str
    epoch: int
    generation: int
    idle_expires_at: str
    absolute_expires_at: str

    def __repr__(self):
        return "Issued(<redacted opaque token>)"

def _exec(conn,statement,args=()):
    with conn.transaction():
        return conn.execute(statement,args).fetchone()["data"]

def map_identity(conn,issuer,subject):
    """TRUSTED OIDC claims only: map issuer+subject to immutable internal owner.

    Use auth_mapper role. No contact attribute is accepted or stored.
    """
    return _exec(conn,"SELECT auth_l1.map_identity(%s,%s) AS data",(issuer,subject))

def issue(conn,owner_id,expected_epoch,*,idle_seconds,absolute_seconds):
    """TRUSTED BFF callback only, auth_sessions role; test TTL explicit.

    Race against revoke_all uses owner-row lock + expected epoch/gate CAS.
    """
    raw=_new_opaque()
    metadata=_exec(conn,"SELECT auth_l1.issue_session(%s,%s,%s,%s,%s) AS data",
                   (owner_id,expected_epoch,_digest(raw),idle_seconds,absolute_seconds))
    return Issued(raw,metadata["owner_id"],metadata["epoch"],metadata["generation"],
                  metadata["idle_expires_at"],metadata["absolute_expires_at"])

def inspect(conn,opaque):
    """Read-only admission on primary; no activity/idle refresh side effect."""
    return _exec(conn,"SELECT auth_l1.validate_session(%s) AS data",(_digest(opaque),))

def touch(conn,opaque,expected_epoch):
    """Extend idle from trusted activity, never absolute deadline."""
    return _exec(conn,"SELECT auth_l1.touch_session(%s,%s) AS data",
                 (_digest(opaque),expected_epoch))

def rotate(conn,opaque,expected_epoch,expected_generation):
    """Atomic old→new CAS, never persist/print either raw opaque identifier."""
    new=_new_opaque()
    meta=_exec(conn,"SELECT auth_l1.rotate_session(%s,%s,%s,%s) AS data",
               (_digest(opaque),_digest(new),expected_epoch,expected_generation))
    return Issued(new,meta["owner_id"],meta["epoch"],meta["generation"],
                  meta["idle_expires_at"],meta["absolute_expires_at"])

def revoke_one(conn,opaque,expected_epoch):
    return _exec(conn,"SELECT auth_l1.revoke_one(%s,%s) AS data",
                 (_digest(opaque),expected_epoch))

def revoke_all(conn,owner_id,expected_epoch):
    """TRUSTED auth_revoker role only; increments epoch and opens deny gate."""
    return _exec(conn,"SELECT auth_l1.revoke_all(%s,%s) AS data",
                 (owner_id,expected_epoch))

def suspend_owner(conn,owner_id,expected_epoch):
    """TRUSTED policy/admin role only; no automatic reactivation."""
    return _exec(conn,"SELECT auth_l1.suspend_owner(%s,%s) AS data",
                 (owner_id,expected_epoch))

def finish_simulated_reauth(conn,owner_id,expected_epoch):
    """ONLY separate auth_reauth role. No IdP fresh-auth evidence is verified.

    In real product the caller MUST prove fresh credential/assurance separately,
    bind it to this owner+epoch, and prevent stale SSO reuse before invocation.
    """
    return _exec(conn,"SELECT auth_l1.finish_simulated_reauth(%s,%s) AS data",
                 (owner_id,expected_epoch))

def fence_owner(conn,owner_id,expected_epoch):
    """One product DB transaction fencing check.

    For linearizable protected SQL work caller MUST wrap this call and the work
    inside the SAME conn.transaction(), retaining the DB owner row lock until
    the outer transaction commits. This does NOT fence cross-DB/HTTP work.
    """
    return _exec(conn,"SELECT auth_l1.fence_owner(%s,%s) AS data",
                 (owner_id,expected_epoch))
