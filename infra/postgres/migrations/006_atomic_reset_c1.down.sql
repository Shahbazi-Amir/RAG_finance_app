-- 006_atomic_reset_c1.down.sql — fail closed; use psql --single-transaction.
-- Never silently delete recovery authority/active reset operations or reopen Gate.
-- This rollback is ONLY permitted for an empty, unused 006 installation in CI.
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
