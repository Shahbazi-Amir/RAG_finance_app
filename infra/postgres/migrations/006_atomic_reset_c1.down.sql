-- 006_atomic_reset_c1.down.sql — fail closed; use psql -1 -v ON_ERROR_STOP=1.
-- Empty-check and DDL MUST share the same READ COMMITTED outer transaction.
-- A one-transaction script WITHOUT these locks permits a TOCTOU insert/consume.
-- Migration-only ACCESS EXCLUSIVE on owners deliberately fences every new
-- issuer/executor BEFORE locking reset tables. This matches their Owner-first
-- lock ordering; it also serializes DROP TRIGGER on owners and avoids an
-- issuer holding an Owner lock while waiting for our reset-table lock.
-- No PostgreSQL/IdP/Production data or previous 001..005 migrations altered.
SET TRANSACTION ISOLATION LEVEL READ COMMITTED;
LOCK TABLE auth_l1.owners IN ACCESS EXCLUSIVE MODE;
LOCK TABLE auth_l1.reset_c1_authorizations IN ACCESS EXCLUSIVE MODE;
LOCK TABLE auth_l1.reset_c1_operations IN ACCESS EXCLUSIVE MODE;
-- The table locks persist until outer COMMIT/ROLLBACK; the following check
-- sees commits of previous waiters because isolation is READ COMMITTED.
-- A committed issuance or C1 causes a raised error, aborting all this DDL.
DO $$
BEGIN
 IF EXISTS(SELECT 1 FROM auth_l1.reset_c1_operations)
    OR EXISTS(SELECT 1 FROM auth_l1.reset_c1_authorizations)
 THEN RAISE EXCEPTION 'RESET_C1_ROLLBACK_REFUSED_EVIDENCE_EXISTS'
      USING ERRCODE='P0001'; END IF;
END $$;
DROP TRIGGER block_c1_gate_open_trg ON auth_l1.owners;
DROP FUNCTION auth_l1.block_c1_gate_open();
DROP FUNCTION auth_l1.execute_reset_c1(text,text,text,text,bigint,uuid);
DROP FUNCTION auth_l1.issue_reset_c1_authorization(text,text,text,text,bigint,bigint,text,integer);
DROP TABLE auth_l1.reset_c1_operations;
DROP TABLE auth_l1.reset_c1_authorizations;
REVOKE USAGE ON SCHEMA auth_l1 FROM auth_reset_issuer,auth_reset_executor;
