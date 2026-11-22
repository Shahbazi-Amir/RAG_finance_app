-- DB55 no-dispatch AUTH bridge — NOT EXECUTED / DBA APPROVAL REQUIRED.
-- Apply only after 001..010 staging inventory+backup+named Foundation sign-off.
-- This file does not create logins, touch product rows or install 011.
\set ON_ERROR_STOP on
BEGIN;
SET LOCAL lock_timeout = '3s';
SET LOCAL statement_timeout = '20s';
DO $db55$
DECLARE r text;
BEGIN
 IF current_database() IN ('postgres','history_ci','template0','template1')
    OR current_database() LIKE '%_ci' THEN
  RAISE EXCEPTION 'DB55_UNATTESTED_STAGING_DATABASE';
 END IF;
 IF current_setting('server_version_num')::int NOT BETWEEN 170000 AND 179999 THEN
  RAISE EXCEPTION 'DB55_REQUIRES_POSTGRESQL17';
 END IF;
 IF current_user IN ('history_app','auth_revoker') THEN
  RAISE EXCEPTION 'DB55_DBA_ROLE_REQUIRED';
 END IF;
 FOREACH r IN ARRAY ARRAY['history_app','auth_revoker'] LOOP
  IF NOT EXISTS(SELECT 1 FROM pg_roles WHERE rolname=r
    AND NOT rolsuper AND NOT rolbypassrls AND NOT rolinherit
    AND NOT rolcreatedb AND NOT rolcreaterole) THEN
   RAISE EXCEPTION 'DB55_SERVICE_ROLE_UNSAFE_OR_MISSING %',r;
  END IF;
 END LOOP;
 IF to_regprocedure('auth_l1.consume_service_assertion(text,bigint)') IS NULL
    OR to_regprocedure('auth_l1.admit_session_fenced(text,text,bigint,integer)') IS NULL
    OR to_regprocedure('auth_l1.revoke_one(text,bigint)') IS NULL THEN
   RAISE EXCEPTION 'DB55_MISSING_003_004_005_FUNCTIONS';
 END IF;
 IF has_table_privilege('history_app','auth_l1.sessions','SELECT')
    OR has_table_privilege('auth_revoker','auth_l1.sessions','SELECT') THEN
   RAISE EXCEPTION 'DB55_UNSAFE_PREEXISTING_AUTH_TABLE_GRANT';
 END IF;
END $db55$;

-- Precisely the CI bridge from #50 and DB review #37, NOT all Auth grants.
GRANT USAGE ON SCHEMA auth_l1 TO history_app;
GRANT EXECUTE ON FUNCTION auth_l1.consume_service_assertion(text,bigint)
 TO history_app,auth_revoker;
GRANT EXECUTE ON FUNCTION auth_l1.admit_session_fenced(text,text,bigint,integer)
 TO history_app,auth_revoker;
GRANT EXECUTE ON FUNCTION auth_l1.revoke_one(text,bigint)
 TO auth_revoker;
COMMIT;

-- Operator must run db55_verify_staging.sql with db55_phase=private_no_dispatch
-- using a DIFFERENT READ-ONLY audit DSN after this COMMIT.
