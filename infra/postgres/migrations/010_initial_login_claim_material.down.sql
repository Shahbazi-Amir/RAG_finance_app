-- 010_initial_login_claim_material.down.sql
-- Conservative evidence-preserving rollback: no attempt may be destroyed or stranded.
BEGIN;
DO $$
BEGIN
 LOCK TABLE auth_l1.owners IN ACCESS EXCLUSIVE MODE;
 LOCK TABLE auth_l1.initial_login_attempts IN ACCESS EXCLUSIVE MODE;
 IF EXISTS (SELECT 1 FROM auth_l1.initial_login_attempts) THEN
  RAISE EXCEPTION 'LOGIN_010_DOWN_REFUSED_EVIDENCE_EXISTS' USING ERRCODE='P0001';
 END IF;
END $$;
REVOKE EXECUTE ON FUNCTION auth_l1.claim_initial_login_exchange_material(
 uuid,text,uuid,text,text) FROM auth_login_claim_reader;
DROP FUNCTION auth_l1.claim_initial_login_exchange_material(
 uuid,text,uuid,text,text);
REVOKE USAGE ON SCHEMA auth_l1 FROM auth_login_claim_reader;
COMMIT;
