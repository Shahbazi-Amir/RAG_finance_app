#!/usr/bin/env bash
# Creates a second independent PostgreSQL volume + cluster; never restores into the source.
set -euo pipefail
source "$(dirname "$0")/_lib.sh"
require_lab_ready
secure_log
[[ "$(dbpsql -Atc "SELECT count(*) FROM db55_audit.migration_runs WHERE status='APPLIED'")" == 10 ]] || { echo 'STOP_SOURCE_NOT_COMPLETELY_MIGRATED' >&2; exit 70; }
[[ ! -e "$LAB_WORK/restore-tested.marker" ]] || { echo 'STOP_RESTORE_ALREADY_TESTED' >&2; exit 70; }
[[ ! -e "$LAB_WORK/backup.dump" ]] || { echo 'STOP_BACKUP_PATH_ALREADY_EXISTS' >&2; exit 70; }
# Private pg_dump -Fc; redirection creates a mode 0600 file via umask.
compose exec -T lab-db pg_dump -U postgres -d rag_finance_f3_lab -Fc > "$LAB_WORK/backup.dump"
[[ -s "$LAB_WORK/backup.dump" ]] || { echo 'STOP_EMPTY_BACKUP' >&2; exit 70; }
shasum -a 256 "$LAB_WORK/backup.dump" > "$LAB_WORK/backup.dump.sha256"
chmod 0600 "$LAB_WORK/backup.dump" "$LAB_WORK/backup.dump.sha256"
# A separately named volume; if Compose pre-created it, require ownership by this project.
if docker volume inspect "$LAB_RESTORE_VOLUME" >/dev/null 2>&1; then
  owner="$(docker volume inspect -f '{{ index .Labels "com.docker.compose.project" }}' "$LAB_RESTORE_VOLUME")"
  [[ "$owner" == "$LAB_PROJECT" ]] || { echo 'STOP_RESTORE_VOLUME_NOT_OWNED_BY_LAB' >&2; exit 70; }
fi
compose --profile restore up -d --pull missing restore-db
export DB_SERVICE=restore-db DB_NAME=rag_finance_f3_lab_restore
for i in {1..45}; do
  if dbpsql -Atc 'SELECT current_database()' 2>/dev/null | grep -Fxq "$DB_NAME"; then break; fi
  sleep 2
done
[[ "$(dbpsql -Atc 'SHOW server_version')" == 17.11* ]] || { echo 'STOP_RESTORE_PG_VERSION' >&2; exit 70; }
source_id="$(DB_SERVICE=lab-db DB_NAME=rag_finance_f3_lab dbpsql -Atc 'SELECT system_identifier FROM pg_control_system()')"
restore_id="$(dbpsql -Atc 'SELECT system_identifier FROM pg_control_system()')"
[[ -n "$source_id" && -n "$restore_id" && "$source_id" != "$restore_id" ]] || { echo 'STOP_NOT_INDEPENDENT_PG_CLUSTER' >&2; exit 70; }
# Create needed SQL role identities, then restore original ownership, GRANT and FORCE RLS.
LAB_ROOT="$LAB_ROOT" "$BUNDLE_ROOT/scripts/02_provision_roles.sh" restore-db > "$LAB_WORK/restore_roles.log"
shasum -a 256 -c "$LAB_WORK/backup.dump.sha256" >/dev/null
compose exec -T restore-db pg_restore -U postgres -d rag_finance_f3_lab_restore < "$LAB_WORK/backup.dump" > "$LAB_WORK/restore.log" 2>&1 || { echo 'STOP_PG_RESTORE_FAILED' >&2; exit 70; }
[[ "$(dbpsql -Atc "SELECT count(*) FROM db55_audit.migration_runs WHERE status='APPLIED'")" == 10 ]] || { echo 'STOP_RESTORED_LEDGER_INCOMPLETE' >&2; exit 70; }
dbpsql -c 'SET ROLE db55_lab_auditor' -v db55_phase=private_no_dispatch \
  -f /run/source/db55_verify_staging.sql > "$LAB_WORK/restore_db55.log" 2>&1 || { echo 'STOP_RESTORED_DB55_FAILED' >&2; exit 70; }
grep -Fq 'DB55_private_no_dispatch_DB_ROLE_SCHEMA_AND_FUNCTION_GATE_PASS' "$LAB_WORK/restore_db55.log" || { echo 'STOP_RESTORE_PASS_MARKER_MISSING' >&2; exit 70; }
source_counts="$(DB_SERVICE=lab-db DB_NAME=rag_finance_f3_lab dbpsql -Atc "SELECT (SELECT count(*) FROM pg_tables WHERE schemaname IN ('history_l1','auth_l1')) || '|' || (SELECT count(*) FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace WHERE n.nspname IN ('history_l1','auth_l1'))")"
restore_counts="$(dbpsql -Atc "SELECT (SELECT count(*) FROM pg_tables WHERE schemaname IN ('history_l1','auth_l1')) || '|' || (SELECT count(*) FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace WHERE n.nspname IN ('history_l1','auth_l1'))")"
[[ "$source_counts" == "$restore_counts" ]] || { echo "STOP_RESTORE_OBJECT_COUNT_MISMATCH:$source_counts/$restore_counts" >&2; exit 70; }
[[ "$(dbpsql -Atc "SELECT count(*) FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE (n.nspname,c.relname) IN (('history_l1','messages'),('history_l1','execution_attempts'),('auth_l1','sessions'),('auth_l1','initial_login_attempts')) AND c.relrowsecurity AND c.relforcerowsecurity")" == 4 ]] || { echo 'STOP_RESTORED_FORCE_RLS_MISSING' >&2; exit 70; }
printf 'SOURCE_CLUSTER_ID=%s\nRESTORE_CLUSTER_ID=%s\nOBJECT_COUNTS=%s\n' "$source_id" "$restore_id" "$source_counts" > "$LAB_WORK/restore_receipt.txt"
touch "$LAB_WORK/restore-tested.marker"; chmod 0600 "$LAB_WORK/restore-tested.marker"
echo 'BACKUP_SHA256_VERIFIED=PASS'
echo 'RESTORE_INDEPENDENT_CLUSTER=PASS'
echo 'RESTORED_DB55=PASS'
echo 'RESTORED_FORCE_RLS=PASS'
