-- DB55 bridge rollback — NOT EXECUTED; DBA + Foundation manual approval.
-- ONLY if the exact five grants below were absent in the captured pre-state
-- and added solely by db55_no_dispatch_bridge.sql. Otherwise DO NOT RUN:
-- REVOKE would remove legitimate pre-existing privileges used by other services.
-- Stop/drain the matching API/BFF code before removing its permissions.
\set ON_ERROR_STOP on
BEGIN;
SET LOCAL lock_timeout = '3s';
SET LOCAL statement_timeout = '20s';
DO $db55$
BEGIN
 IF current_database() IN ('postgres','history_ci','template0','template1')
    OR current_database() LIKE '%_ci' THEN
  RAISE EXCEPTION 'DB55_ROLLBACK_UNATTESTED_DATABASE';
 END IF;
 IF current_user IN ('history_app','auth_revoker') THEN
  RAISE EXCEPTION 'DB55_ROLLBACK_DBA_ONLY';
 END IF;
END $db55$;
REVOKE EXECUTE ON FUNCTION auth_l1.revoke_one(text,bigint)
 FROM auth_revoker;
REVOKE EXECUTE ON FUNCTION auth_l1.admit_session_fenced(text,text,bigint,integer)
 FROM auth_revoker,history_app;
REVOKE EXECUTE ON FUNCTION auth_l1.consume_service_assertion(text,bigint)
 FROM auth_revoker,history_app;
REVOKE USAGE ON SCHEMA auth_l1 FROM history_app;
COMMIT;
