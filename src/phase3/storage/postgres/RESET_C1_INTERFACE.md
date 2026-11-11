# CR-DB-01A — Atomic Controlled Reset C1, PostgreSQL interface

**Scope:** synthetic-only product PostgreSQL C1. Design baseline: merged ADR 0006 / main `447c460a63ef8c2db4de47d52f51f72953ff73e4`. NOT IdP, email ownership, recovery verification, fresh step-up, browser session, endpoint, actual password change, C2, production Auth, or Gate acceptance.

## Authority and separate roles

- `auth_reset_issuer` is an independently trusted **CI fixture** role with EXECUTE **only** on `auth_l1.issue_reset_c1_authorization`. It assumes an externally verified one-time recovery or fresh step-up proof; PostgreSQL **cannot verify** that proof, email, issuer or subject. Synthetic fixture never becomes a production proof issuer by assumption.
- `auth_reset_executor` has EXECUTE **only** on `auth_l1.execute_reset_c1`; it **cannot self-issue** authorization, directly read/write reset tables, map owners, open Gate, issue/rotate sessions, revoke outside C1 or access History.
- Both are non-superuser, non-BYPASSRLS, no table or DDL grants, explicit schema USAGE and function-only grants. DB tables use FORCE RLS/direct-deny and SECURITY DEFINER with fixed `search_path=pg_catalog` under the **CI-only** privileged `auth_migrator`. Production definer, identity/role and secret controls still require review.
- `operation_id` is a UUID trace/reference, **not** authorization. Neither user email nor operation ID alone allows revoke. The raw high-entropy proof lives only briefly in trusted server RAM; SHA256 digest alone enters SQL. No raw JWT, opaque Session, password, Cookie or Recovery link in DB or logging.

## C1 protocol

1. Trusted separate issuer generates random raw authorization in RAM, hashes it, and issues a SQL row with digest, exact owner, one of `RECOVERY` or `AUTHENTICATED_PASSWORD_CHANGE`, purpose `CONTROLLED_RESET_C1`, expected epoch and caller-provided expiration. `AUTHENTICATED_PASSWORD_CHANGE` additionally binds a **session digest and generation**; it is not fresh step-up evidence. Issuer validates current owner state/gate/epoch under Owner `FOR SHARE`; proof/expiry policy is synthetic, no production TTL chosen.
2. Executor requires **explicit outer transaction on the same primary connection**: `with conn.transaction(): reset_c1.commit_c1(...)`. It sends digest, owner, kind, purpose, epoch and a generated UUID. The C1 SQL function validates inputs, takes Owner `FOR UPDATE` **first**, checks active operation and epoch/gate/state, takes authorization `FOR UPDATE` **second**, and checks bindings, consumption and `clock_timestamp()` expiry **after locks**. Authenticated mode calls accepted 004 exact-session fence after this. Existing admission, rotation and revoke also lock Owner before Session; no lock-order inversion.
3. SQL inserts durable `reset_c1_operations` with `REVOKED_PENDING_IDP`, marks authorization consumed, calls accepted 003 `revoke_all(owner,expected_epoch)` within same transaction (epoch CAS + all active sessions revoked + gate pending), checks returned new epoch, then returns a scrubbed receipt.
4. COMMIT means **all** authority consumption, operation record, epoch, sessions and pending gate persist; any exception or injected abort means **all** rollback. No IdP call, network retry or C2 in this package. Two concurrent C1 attempts serialize on Owner; the per-owner partial unique active-operation index forbids a second active operation. Both stale epoch and consumed proof fail. Even a different proof for the same owner cannot bump again.
5. C1 operations remain active without a status-clearing method. The 006 owner trigger prevents `pending_reauth→open` while any C1 operation remains active, including attempts through prior **synthetic** 003 reauth. Future C2 needs a separately authorized migration and proof-based transition; no unlock path here.

## Migration/rollback

Files: `006_atomic_reset_c1.up.sql` and `006_atomic_reset_c1.down.sql`; never change 001–005. Down is guarded: if **any** C1 authorization or operation row exists, SQL raises `RESET_C1_ROLLBACK_REFUSED_EVIDENCE_EXISTS`; owner gate and ledger remain intact. Empty unused installation only may be down-migrated; always execute migration with `psql --single-transaction -v ON_ERROR_STOP=1` on disposable CI DB. This is not backup/restore. No retention/cleanup scheduler is provided.

## Explicit non-claims

No authentic recovery/step-up issuance, no owner selection from real OIDC, no service proof binding over HTTP, no C2, IdP write, password handling, external cross-DB atomicity, production roles/retention, stream cancellation or operational Gate PASS. Assertions apply only to synthetic PostgreSQL primary transactions and CI role fixtures. The existing `003.finish_simulated_reauth` remains a test-only function for owners without an active C1 operation; the 006 trigger specifically blocks it from opening C1 owners. The issuer and executor must never share a principal or credential in production. The external policy for proof expiry must be approved separately.
