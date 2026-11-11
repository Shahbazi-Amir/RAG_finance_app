-- 008_durable_idp_attempt_outcome.down.sql — fail closed with evidence.
-- Required: psql -X -1 -v ON_ERROR_STOP=1 -f <THIS EXACT FILE>.
-- Locks ordered Owner-table FIRST, then 008 attempts to serialize concurrent
-- record/outcome calls and ensure no committed attempt can be silently dropped.
-- Both locks persist through check + DDL until the same outer transaction ends.
SET TRANSACTION ISOLATION LEVEL READ COMMITTED;
LOCK TABLE auth_l1.owners IN ACCESS EXCLUSIVE MODE;
LOCK TABLE auth_l1.reset_idp_attempts IN ACCESS EXCLUSIVE MODE;
DO $$
BEGIN
 IF EXISTS(SELECT 1 FROM auth_l1.reset_idp_attempts)
 THEN RAISE EXCEPTION 'RESET_IDP_ATTEMPT_ROLLBACK_REFUSED_EVIDENCE_EXISTS'
      USING ERRCODE='P0001'; END IF;
END $$;
DROP FUNCTION auth_l1.record_reset_idp_outcome(
 text,text,text,text,bigint,uuid,uuid,text,text);
DROP FUNCTION auth_l1.record_reset_idp_attempt(
 text,text,text,text,bigint,uuid,uuid);
DROP TABLE auth_l1.reset_idp_attempts;
REVOKE USAGE ON SCHEMA auth_l1 FROM auth_reset_idp_recorder;
