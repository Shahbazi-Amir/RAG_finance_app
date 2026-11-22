#!/usr/bin/env bash
# Separate disposable lab only: 001..010 + 011 compatibility, NO Gateway/Runner.
set -euo pipefail
source "$(dirname "$0")/_lib.sh"
require_lab_ready
secure_log
: "${SOURCE_REPO:?Set SOURCE_REPO to a local Git checkout}"
[[ "$LAB_PROJECT" == ragfinance_f3_db_lab_* ]] || exit 70
[[ "$(dbpsql -Atc "SELECT current_database()")" == rag_finance_f3_lab ]] || { echo STOP_011_WRONG_DATABASE >&2; exit 70; }
[[ "$(dbpsql -Atc "SELECT count(*) FROM db55_audit.migration_runs WHERE status='APPLIED'")" == 10 ]] || { echo STOP_011_BASE_NOT_READY >&2; exit 70; }
[[ "$(dbpsql -Atc "SELECT status FROM db55_audit.bridge_runs WHERE id=1")" == APPLIED ]] || { echo STOP_011_DB55_BRIDGE_ABSENT >&2; exit 70; }
[[ "$(dbpsql -Atc "SELECT to_regclass('history_l1.external_dispatch_claims') IS NULL")" == t ]] || { echo STOP_011_ALREADY_INSTALLED >&2; exit 70; }
pin=b0ba6dbf6100109cb58f8cb49da808839d68c5f0
for direction in up down; do
  name="011_external_dispatch_claim.${direction}.sql"
  git -C "$SOURCE_REPO" cat-file -e "${pin}^{commit}" || { echo STOP_011_COMMIT_MISSING >&2; exit 70; }
  git -C "$SOURCE_REPO" show "$pin:infra/postgres/migrations/$name" > "$LAB_SOURCE/$name"
  if [[ "$direction" == up ]]; then wanted=031d2f438f000154eb4e2b374ce42181b3d812b3; else wanted=ce3e7d8a2394f4a090650623770ad261eee2f4c2; fi
  [[ "$(git hash-object "$LAB_SOURCE/$name")" == "$wanted" ]] || { echo "STOP_011_BLOB_MISMATCH_$direction" >&2; exit 70; }
done
chmod 0644 "$LAB_SOURCE/011_external_dispatch_claim."*.sql
[[ "$(dbpsql -Atc "SELECT count(*) FROM pg_roles WHERE rolname IN ('history_dispatch_reporter','history_dispatch_reconciler')")" == 0 ]] || { echo STOP_011_ROLES_EXIST >&2; exit 70; }
for role in history_dispatch_reporter history_dispatch_reconciler; do
  pw="$(openssl rand -hex 32)"
  printf "CREATE ROLE %s LOGIN NOSUPERUSER NOBYPASSRLS NOINHERIT NOCREATEDB NOCREATEROLE PASSWORD '%s';\n" "$role" "$pw" | dbpsql >/dev/null
done
dbpsql -c 'GRANT CONNECT ON DATABASE rag_finance_f3_lab TO history_dispatch_reporter,history_dispatch_reconciler' >/dev/null
dbpsql -c 'SET ROLE history_migrator' -f /run/source/011_external_dispatch_claim.up.sql > "$LAB_WORK/011_up.log" 2>&1 || { echo STOP_011_UP_FAIL >&2; exit 70; }
dbpsql -c 'SET ROLE db55_lab_auditor' -v db55_phase=live_011 -f /run/source/db55_verify_staging.sql > "$LAB_WORK/db55_live011.log" 2>&1 || { echo STOP_011_DB55_FAIL >&2; exit 70; }
grep -Fq 'DB55_live_011_DB_ROLE_SCHEMA_AND_FUNCTION_GATE_PASS' "$LAB_WORK/db55_live011.log" || { echo STOP_011_DB55_MARKER >&2; exit 70; }
flags="$(dbpsql -Atc "SELECT
 (SELECT relrowsecurity AND relforcerowsecurity FROM pg_class WHERE oid='history_l1.external_dispatch_claims'::regclass)
 AND has_function_privilege('history_app','history_l1.claim_external_dispatch(text,text,text)','EXECUTE')
 AND has_function_privilege('history_app','history_l1.status_external_dispatch(text,text,text)','EXECUTE')
 AND has_function_privilege('history_dispatch_reporter','history_l1.flag_external_dispatch_unknown(text,text,text,uuid,text)','EXECUTE')
 AND has_function_privilege('history_dispatch_reconciler','history_l1.reconcile_external_dispatch(text,text,text,text,text)','EXECUTE')
 AND NOT has_table_privilege('history_app','history_l1.external_dispatch_claims','SELECT')
 AND NOT has_table_privilege('history_dispatch_reporter','history_l1.external_dispatch_claims','SELECT')
 AND NOT has_table_privilege('history_dispatch_reconciler','history_l1.external_dispatch_claims','SELECT')
 AND NOT has_function_privilege('history_dispatch_reporter','history_l1.claim_external_dispatch(text,text,text)','EXECUTE')
 AND NOT has_function_privilege('history_dispatch_reconciler','history_l1.claim_external_dispatch(text,text,text)','EXECUTE');")"
[[ "$flags" == t ]] || { echo STOP_011_RLS_FUNCTION_ACL_MATRIX >&2; exit 70; }
claim="$(dbpsql -c 'SET ROLE history_app' -Atc "SELECT claim_won FROM history_l1.claim_external_dispatch('synthetic_missing_owner','aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa','synthetic_trace')")"
[[ "$claim" == f ]] || { echo STOP_011_UNAUTHORIZED_CLAIM >&2; exit 70; }
[[ "$(dbpsql -Atc 'SELECT count(*) FROM history_l1.external_dispatch_claims')" == 0 ]] || { echo STOP_011_UNEXPECTED_CLAIM >&2; exit 70; }
echo 'POST010_011_PINNED_GIT_BLOBS=2/2_PASS'
echo 'POST010_011_ON_SEPARATE_001_010_LAB=PASS'
echo 'POST010_011_DB55_LIVE_GATE=PASS'
echo 'POST010_011_FUNCTION_RLS_ROLE_MATRIX=PASS'
echo 'POST010_011_UNAUTHORIZED_CLAIM=DENIED'
echo 'POST010_011_GATEWAY_CALLS=0'
