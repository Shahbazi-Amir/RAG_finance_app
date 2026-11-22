-- 009_initial_login_attempt_binding.down.sql — guarded, fail-closed.
-- Refuses to erase committed login start, claim, issued Session or ACK evidence.
-- Same Owner table first ordering as all 009 SECURITY DEFINER routines.
BEGIN;
DO $$
BEGIN
 LOCK TABLE auth_l1.owners IN ACCESS EXCLUSIVE MODE;
 LOCK TABLE auth_l1.initial_login_attempts IN ACCESS EXCLUSIVE MODE;
 LOCK TABLE auth_l1.sessions IN ACCESS EXCLUSIVE MODE;
 IF EXISTS(SELECT 1 FROM auth_l1.initial_login_attempts) THEN
  RAISE EXCEPTION 'LOGIN_009_DOWN_REFUSED_EVIDENCE_EXISTS' USING ERRCODE='P0001';
 END IF;
 IF EXISTS(SELECT 1 FROM auth_l1.sessions WHERE status='PENDING_BINDING') THEN
  RAISE EXCEPTION 'LOGIN_009_DOWN_REFUSED_PENDING_SESSION' USING ERRCODE='P0001';
 END IF;
END $$;
DROP FUNCTION auth_l1.cleanup_initial_login_attempt(uuid);
DROP FUNCTION auth_l1.status_initial_login_attempt(uuid,text,text);
DROP FUNCTION auth_l1.abort_initial_login_binding(uuid,uuid,text,text,text,bigint);
DROP FUNCTION auth_l1.ack_initial_login_binding(uuid,uuid,text,text,text,bigint,text);
DROP FUNCTION auth_l1.issue_initial_login_pending(
 uuid,text,text,text,text,text,bigint,text,integer,integer);
DROP FUNCTION auth_l1.mark_initial_login_unknown(uuid,text,text);
DROP FUNCTION auth_l1.claim_initial_login_exchange(uuid,text,text,text);
DROP FUNCTION auth_l1.start_initial_login_attempt(
 uuid,text,uuid,text,text,text,text,text,bytea,bytea,integer);
DROP TABLE auth_l1.initial_login_attempts;
ALTER TABLE auth_l1.sessions DROP CONSTRAINT sessions_status_check;
ALTER TABLE auth_l1.sessions ADD CONSTRAINT sessions_status_check
 CHECK(status IN ('active','rotated','revoked'));
COMMIT;
