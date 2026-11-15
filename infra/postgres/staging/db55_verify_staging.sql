-- DB55 verify-staging.sql — READ ONLY / never calls application functions.
-- Usage: psql -X -v ON_ERROR_STOP=1 -v db55_phase=private_no_dispatch \
--          "$DB55_READONLY_DSN" -f infra/postgres/staging/db55_verify_staging.sql
-- db55_phase: session_core | private_no_dispatch | live_011
-- This is a post-provisioning GATE, not a privilege/DDL installer.
\set ON_ERROR_STOP on
BEGIN TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY;
SELECT set_config('db55.audit_phase', :'db55_phase', true);
DO $db55$
DECLARE
  p text := current_setting('db55.audit_phase');
  sig text;
  r text;
BEGIN
  IF p NOT IN ('session_core','private_no_dispatch','live_011') THEN
    RAISE EXCEPTION 'DB55_INVALID_PHASE';
  END IF;
  IF current_database() IN ('postgres','history_ci','template0','template1')
    OR current_database() LIKE '%_ci' THEN
    RAISE EXCEPTION 'DB55_TARGET_DATABASE_NOT_ATTESTED';
  END IF;
  IF current_setting('server_version_num')::integer NOT BETWEEN 170000 AND 179999 THEN
    RAISE EXCEPTION 'DB55_REQUIRES_POSTGRESQL_17';
  END IF;
  IF to_regclass('history_l1.conversations') IS NULL
    OR to_regclass('history_l1.execution_attempts') IS NULL
    OR to_regclass('history_l1.send_receipts') IS NULL
    OR to_regclass('history_l1.messages') IS NULL
    OR to_regclass('auth_l1.sessions') IS NULL
    OR to_regclass('auth_l1.service_assertion_replays') IS NULL THEN
    RAISE EXCEPTION 'DB55_MISSING_001_TO_005_SCHEMA';
  END IF;
  FOREACH sig IN ARRAY ARRAY[
    'auth_l1.consume_service_assertion(text,bigint)',
    'auth_l1.admit_session_fenced(text,text,bigint,integer)',
    'auth_l1.revoke_one(text,bigint)'
  ] LOOP
    IF to_regprocedure(sig) IS NULL THEN
      RAISE EXCEPTION 'DB55_MISSING_CORE_FUNCTION %',sig;
    END IF;
  END LOOP;
  FOREACH r IN ARRAY ARRAY['history_app','auth_revoker'] LOOP
    IF NOT EXISTS(SELECT 1 FROM pg_roles WHERE rolname=r
      AND NOT rolsuper AND NOT rolbypassrls AND NOT rolinherit
      AND NOT rolcreatedb AND NOT rolcreaterole) THEN
      RAISE EXCEPTION 'DB55_UNSAFE_OR_MISSING_SERVICE_ROLE %',r;
    END IF;
  END LOOP;
  IF NOT (
       has_schema_privilege('history_app','history_l1','USAGE')
   AND has_schema_privilege('history_app','auth_l1','USAGE')
   AND has_schema_privilege('auth_revoker','auth_l1','USAGE')
   AND has_function_privilege('history_app',
         'auth_l1.consume_service_assertion(text,bigint)','EXECUTE')
   AND has_function_privilege('history_app',
         'auth_l1.admit_session_fenced(text,text,bigint,integer)','EXECUTE')
   AND has_function_privilege('auth_revoker',
         'auth_l1.consume_service_assertion(text,bigint)','EXECUTE')
   AND has_function_privilege('auth_revoker',
         'auth_l1.admit_session_fenced(text,text,bigint,integer)','EXECUTE')
   AND has_function_privilege('auth_revoker',
         'auth_l1.revoke_one(text,bigint)','EXECUTE')
  ) THEN
    RAISE EXCEPTION 'DB55_MISSING_APPROVED_004_005_003_BRIDGE_GRANTS';
  END IF;
  IF has_table_privilege('history_app','auth_l1.sessions','SELECT')
    OR has_table_privilege('history_app','auth_l1.service_assertion_replays','SELECT')
    OR has_table_privilege('auth_revoker','auth_l1.sessions','SELECT')
    OR has_table_privilege('auth_revoker','history_l1.messages','SELECT')
    OR has_function_privilege('history_app',
         'auth_l1.revoke_one(text,bigint)','EXECUTE') THEN
    RAISE EXCEPTION 'DB55_DIRECT_AUTH_OR_CROSS_ROLE_PRIVILEGE_DENIED';
  END IF;
  IF p IN ('private_no_dispatch','live_011') THEN
    IF to_regclass('auth_l1.reset_c1_authorizations') IS NULL
      OR to_regclass('auth_l1.reset_c1_operations') IS NULL
      OR to_regclass('auth_l1.reset_idp_attempts') IS NULL
      OR to_regprocedure('auth_l1.resolve_reset_identity(text,text,text,text,bigint,text)') IS NULL THEN
      RAISE EXCEPTION 'DB55_MISSING_ORDERED_006_007_008_CHAIN';
    END IF;
    FOREACH r IN ARRAY ARRAY['auth_mapper','auth_sessions','auth_reauth',
      'auth_trust_api','auth_replay_cleaner','auth_reset_issuer',
      'auth_reset_executor','auth_reset_lookup','auth_reset_idp_recorder'] LOOP
      IF NOT EXISTS(SELECT 1 FROM pg_roles WHERE rolname=r
        AND NOT rolsuper AND NOT rolbypassrls AND NOT rolinherit) THEN
        RAISE EXCEPTION 'DB55_UNSAFE_OR_MISSING_ORDERED_AUTH_ROLE %',r;
      END IF;
    END LOOP;
    IF to_regclass('auth_l1.initial_login_attempts') IS NULL
      OR to_regprocedure('auth_l1.start_initial_login_attempt(uuid,text,uuid,text,text,text,text,text,bytea,bytea,integer)') IS NULL
      OR to_regprocedure('auth_l1.issue_initial_login_pending(uuid,text,text,text,text,text,bigint,text,integer,integer)') IS NULL
      OR to_regprocedure('auth_l1.ack_initial_login_binding(uuid,uuid,text,text,text,bigint,text)') IS NULL
      OR to_regprocedure('auth_l1.claim_initial_login_exchange_material(uuid,text,uuid,text,text)') IS NULL THEN
      RAISE EXCEPTION 'DB55_MISSING_APPROVED_009_010_AUTH_CHAIN';
    END IF;
    FOREACH r IN ARRAY ARRAY['auth_login_bootstrap','auth_login_issuer',
      'auth_login_binder','auth_login_reader','auth_login_cleaner',
      'auth_login_claim_reader'] LOOP
      IF NOT EXISTS(SELECT 1 FROM pg_roles WHERE rolname=r
        AND NOT rolsuper AND NOT rolbypassrls AND NOT rolinherit) THEN
        RAISE EXCEPTION 'DB55_UNSAFE_OR_MISSING_LOGIN_ROLE %',r;
      END IF;
    END LOOP;
    IF NOT has_function_privilege('auth_login_claim_reader',
         'auth_l1.claim_initial_login_exchange_material(uuid,text,uuid,text,text)','EXECUTE')
       OR has_table_privilege('auth_login_claim_reader',
         'auth_l1.initial_login_attempts','SELECT')
       OR NOT has_function_privilege('auth_login_bootstrap',
         'auth_l1.start_initial_login_attempt(uuid,text,uuid,text,text,text,text,text,bytea,bytea,integer)','EXECUTE')
       OR NOT has_function_privilege('auth_login_issuer',
         'auth_l1.issue_initial_login_pending(uuid,text,text,text,text,text,bigint,text,integer,integer)','EXECUTE')
       OR NOT has_function_privilege('auth_login_binder',
         'auth_l1.ack_initial_login_binding(uuid,uuid,text,text,text,bigint,text)','EXECUTE') THEN
      RAISE EXCEPTION 'DB55_LOGIN_FUNCTION_GRANT_MATRIX_FAILED';
    END IF;
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_class WHERE oid=
       'history_l1.messages'::regclass AND relrowsecurity AND relforcerowsecurity)
    OR NOT EXISTS (SELECT 1 FROM pg_class WHERE oid=
       'history_l1.execution_attempts'::regclass AND relrowsecurity AND relforcerowsecurity) THEN
    RAISE EXCEPTION 'DB55_HISTORY_FORCE_RLS_MISSING';
  END IF;
  IF p = 'live_011' THEN
    IF to_regclass('history_l1.external_dispatch_claims') IS NULL THEN
      RAISE EXCEPTION 'DB55_011_NOT_INSTALLED';
    END IF;
    FOREACH sig IN ARRAY ARRAY[
      'history_l1.claim_external_dispatch(text,text,text)',
      'history_l1.status_external_dispatch(text,text,text)',
      'history_l1.flag_external_dispatch_unknown(text,text,text,uuid,text)',
      'history_l1.reconcile_external_dispatch(text,text,text,text,text)'
    ] LOOP
      IF to_regprocedure(sig) IS NULL THEN
        RAISE EXCEPTION 'DB55_011_MISSING_FUNCTION %',sig;
      END IF;
      IF EXISTS(SELECT 1 FROM pg_proc q,
           LATERAL aclexplode(COALESCE(q.proacl,acldefault('f',q.proowner))) a
        WHERE q.oid=to_regprocedure(sig) AND a.grantee=0
          AND a.privilege_type='EXECUTE') THEN
        RAISE EXCEPTION 'DB55_011_PUBLIC_EXECUTE %',sig;
      END IF;
    END LOOP;
    FOREACH r IN ARRAY ARRAY['history_dispatch_reporter',
      'history_dispatch_reconciler'] LOOP
      IF NOT EXISTS(SELECT 1 FROM pg_roles WHERE rolname=r
        AND NOT rolsuper AND NOT rolbypassrls AND NOT rolinherit
        AND NOT rolcreatedb AND NOT rolcreaterole) THEN
        RAISE EXCEPTION 'DB55_011_UNSAFE_ROLE %',r;
      END IF;
    END LOOP;
    IF NOT (
      has_function_privilege('history_app',
        'history_l1.claim_external_dispatch(text,text,text)','EXECUTE')
      AND has_function_privilege('history_app',
        'history_l1.status_external_dispatch(text,text,text)','EXECUTE')
      AND has_function_privilege('history_dispatch_reporter',
        'history_l1.flag_external_dispatch_unknown(text,text,text,uuid,text)','EXECUTE')
      AND has_function_privilege('history_dispatch_reconciler',
        'history_l1.reconcile_external_dispatch(text,text,text,text,text)','EXECUTE')
    ) OR has_table_privilege('history_app',
        'history_l1.external_dispatch_claims','SELECT')
      OR has_table_privilege('history_dispatch_reporter',
        'history_l1.external_dispatch_claims','SELECT')
      OR has_table_privilege('history_dispatch_reconciler',
        'history_l1.external_dispatch_claims','SELECT')
      OR has_function_privilege('history_dispatch_reporter',
        'history_l1.claim_external_dispatch(text,text,text)','EXECUTE')
      OR has_function_privilege('history_app',
        'history_l1.flag_external_dispatch_unknown(text,text,text,uuid,text)','EXECUTE')
      OR has_function_privilege('history_dispatch_reporter',
        'history_l1.reconcile_external_dispatch(text,text,text,text,text)','EXECUTE')
      OR has_function_privilege('history_dispatch_reconciler',
        'history_l1.claim_external_dispatch(text,text,text)','EXECUTE')
      OR has_function_privilege('history_dispatch_reconciler',
        'history_l1.status_external_dispatch(text,text,text)','EXECUTE')
      OR has_function_privilege('history_app',
        'history_l1.reconcile_external_dispatch(text,text,text,text,text)','EXECUTE')
      THEN
      RAISE EXCEPTION 'DB55_011_LEAST_PRIVILEGE_CHECK_FAILED';
    END IF;
    IF NOT EXISTS(SELECT 1 FROM pg_class WHERE oid =
       'history_l1.external_dispatch_claims'::regclass
       AND relrowsecurity AND relforcerowsecurity) THEN
      RAISE EXCEPTION 'DB55_011_RLS_FORCE_MISSING';
    END IF;
  END IF;
  RAISE NOTICE 'DB55_%_DB_ROLE_SCHEMA_AND_FUNCTION_GATE_PASS',p;
END $db55$;
SELECT current_database() AS stage_database, current_user AS auditor_role,
 current_setting('server_version') AS postgres_version,
 current_setting('db55.audit_phase') AS checked_phase;
COMMIT;
