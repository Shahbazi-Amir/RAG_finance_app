#!/usr/bin/env bash
# Dynamic SQL tests read-only on isolated test DB. No changes to accepted Mac demo.
set -euo pipefail
source "$(dirname "$0")/_lib.sh"
require_lab_ready
secure_log
[[ "$(dbpsql -Atc "SELECT count(*) FROM db55_audit.migration_runs WHERE status='APPLIED'")" == 10 ]] || { echo 'STOP_MIGRATIONS_NOT_APPLIED' >&2; exit 70; }
roles=(history_app auth_revoker auth_trust_api auth_login_bootstrap auth_login_claim_reader auth_login_issuer auth_mapper auth_login_binder auth_login_reader)
for role in "${roles[@]}"; do
  result="$(compose exec -T -u root lab-db psql -X -Atq -v ON_ERROR_STOP=1 \
    "host=demo-db port=5432 dbname=rag_finance_f3_lab user=$role sslmode=verify-full sslrootcert=/run/lab_secrets/ca.crt passfile=/run/lab_secrets/pgpass" \
    -c "SELECT current_user || '|' || ssl::text FROM pg_stat_ssl WHERE pid=pg_backend_pid()" 2>/dev/null)" || { echo "STOP_TLS_LOGIN_FAILED_ROLE=$role" >&2; exit 70; }
  [[ "$result" == "$role|true" ]] || { echo "STOP_TLS_ROLE_ID_OR_SSL_NOT_VALID:$role" >&2; exit 70; }
  unsafe="$(dbpsql -Atc "SELECT count(*) FROM pg_roles WHERE rolname='$role' AND (rolsuper OR rolbypassrls OR rolinherit OR rolcreatedb OR rolcreaterole)")"
  [[ "$unsafe" == 0 ]] || { echo "STOP_UNSAFE_SERVICE_ROLE:$role" >&2; exit 70; }
  echo "TLS_VERIFY_FULL_ROLE=$role PASS"
done
# Require clear-text TCP to be explicitly rejected by pg_hba, not merely by failed password.
if compose exec -T -u root lab-db psql -X -Atq -v ON_ERROR_STOP=1 \
  "host=demo-db port=5432 dbname=rag_finance_f3_lab user=history_app sslmode=disable passfile=/run/lab_secrets/pgpass" \
   -c 'SELECT 1' > "$LAB_WORK/non_tls_denied.log" 2>&1; then
  echo 'STOP_NON_TLS_CONNECTION_ACCEPTED' >&2; exit 70
fi
grep -Eiq 'pg_hba|no encryption|reject' "$LAB_WORK/non_tls_denied.log" || { echo 'STOP_NON_TLS_FAILED_FOR_OTHER_REASON' >&2; exit 70; }
# 9 roles x 8 real auth tables = 72 DIRECT SELECT negatives.
read -r -d '' sql <<'SQL' || true
WITH r(rolname) AS (VALUES
 ('history_app'),('auth_revoker'),('auth_trust_api'),
 ('auth_login_bootstrap'),('auth_login_claim_reader'),
 ('auth_login_issuer'),('auth_mapper'),('auth_login_binder'),('auth_login_reader')
), t(obj) AS (VALUES
 ('auth_l1.sessions'),('auth_l1.initial_login_attempts'),
 ('auth_l1.service_assertion_replays'),('auth_l1.reset_c1_authorizations'),
 ('auth_l1.reset_c1_operations'),('auth_l1.reset_idp_attempts'),
 ('auth_l1.owners'),('auth_l1.identity_links')
) SELECT count(*) || '|' || count(*) FILTER (WHERE to_regclass(obj) IS NOT NULL AND NOT has_table_privilege(rolname,obj,'SELECT'))
FROM r CROSS JOIN t;
SQL
result="$(dbpsql -Atc "$sql")"
[[ "$result" == '72|72' ]] || { echo "STOP_72_SELECT_NEGATIVE_MATRIX:$result" >&2; exit 70; }
# Exact required seven Bootstrap API function privileges, from pinned API source.
read -r -d '' fn_sql <<'SQL' || true
WITH e(role_name,signature) AS (VALUES
 ('auth_trust_api','auth_l1.consume_service_assertion(text,bigint)'),
 ('auth_login_bootstrap','auth_l1.start_initial_login_attempt(uuid,text,uuid,text,text,text,text,text,bytea,bytea,integer)'),
 ('auth_login_bootstrap','auth_l1.mark_initial_login_unknown(uuid,text,text)'),
 ('auth_login_claim_reader','auth_l1.claim_initial_login_exchange_material(uuid,text,uuid,text,text)'),
 ('auth_login_issuer','auth_l1.issue_initial_login_pending(uuid,text,text,text,text,text,bigint,text,integer,integer)'),
 ('auth_mapper','auth_l1.map_identity(text,text)'),
 ('auth_login_binder','auth_l1.ack_initial_login_binding(uuid,uuid,text,text,text,bigint,text)'),
 ('auth_login_binder','auth_l1.abort_initial_login_binding(uuid,uuid,text,text,text,bigint)'),
 ('auth_login_reader','auth_l1.status_initial_login_attempt(uuid,text,text)')
) SELECT count(*) || '|' || count(*) FILTER (WHERE to_regprocedure(signature) IS NOT NULL AND has_function_privilege(role_name,signature,'EXECUTE'))
FROM e;
SQL
fn_result="$(dbpsql -Atc "$fn_sql")"
[[ "$fn_result" == '9|9' ]] || { echo "STOP_BOOTSTRAP_FUNCTIONS:$fn_result" >&2; exit 70; }
# Additional read-only historical + current RLS checks; DB55 itself covers main tables.
result_rls="$(dbpsql -Atc "SELECT count(*) FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE (n.nspname,c.relname) IN (('history_l1','messages'),('history_l1','execution_attempts'),('auth_l1','sessions'),('auth_l1','initial_login_attempts')) AND c.relrowsecurity AND c.relforcerowsecurity")"
[[ "$result_rls" == 4 ]] || { echo 'STOP_RLS_MISSING' >&2; exit 70; }
echo 'TLS_VERIFY_FULL_NINE_ROLES=9/9_PASS'
echo 'NON_TLS_REJECTED=PASS'
echo 'NEGATIVE_TABLE_SELECT=72/72_PASS'
echo 'BOOTSTRAP_FUNCTION_GRANTS=9/9_PASS'
echo 'FOUR_CRITICAL_TABLES_FORCE_RLS=PASS'
