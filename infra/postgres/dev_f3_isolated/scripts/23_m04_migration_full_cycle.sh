#!/usr/bin/env bash
# P3M04-A07 exact empty 001-010 reverse/reinstall + already-proven populated 009/010 restore.
# This is an intentionally DESTRUCTIVE full rollback ONLY inside a new disposable clone.
# No accepted Mac database/volume or original lab database is changed.
set -euo pipefail
source "$(dirname "$0")/_lib.sh"
require_lab_ready; secure_log
[[ "$LAB_PROJECT" == ragfinance_f3_db_lab_* && "$LAB_DB" == rag_finance_f3_lab ]] || exit 70
[[ -f "$LAB_WORK/restore-tested.marker" ]] || { echo STOP_RESTORE_PREREQUISITE >&2; exit 70; }
[[ "$(dbpsql -Atc "SELECT count(*) FROM db55_audit.migration_runs WHERE status='APPLIED'")" == 10 ]] || exit 70
[[ "$(dbpsql -Atc "SELECT count(*) FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname IN ('auth_l1','history_l1') AND c.relkind='r'")" == 14 ]] || exit 70
# Require earlier real populated upgrade/restoration on BOTH independent clusters.
[[ -s "$LAB_WORK/pre009_populated_fixture.sha256" ]] || { echo STOP_MISSING_POPULATED_RESTORE >&2;exit 70; }
for svc in lab-db restore-db; do
  grep -Fq DB55_private_no_dispatch_DB_ROLE_SCHEMA_AND_FUNCTION_GATE_PASS "$LAB_WORK/populated_db55_$svc.log" || exit 70
  for name in 009_initial_login_attempt_binding.up.sql 010_initial_login_claim_material.up.sql; do
    [[ -f "$LAB_WORK/populated_upgrade_$svc-$name.log" ]] || exit 70
  done
done
# Verify that actual source SQL bytes have NOT changed after the earlier install.
( cd "$LAB_SOURCE" && shasum -a 256 -c SHA256SUMS >/dev/null ) || exit 70
probe=rag_finance_f3_m04_full_cycle_probe
admin(){ DB_SERVICE=lab-db DB_NAME=postgres dbpsql -Atq "$@"; }
[[ "$(admin -c "SELECT count(*) FROM pg_database WHERE datname='$probe'")" == 0 ]] || {
 echo STOP_M04_PROBE_COLLISION >&2;exit 70; }
admin -c "CREATE DATABASE $probe TEMPLATE rag_finance_f3_lab OWNER postgres" >/dev/null
# Only the disposable probe inherits prior ledger; clear it BEFORE any destructive test.
export DB_SERVICE=lab-db DB_NAME="$probe"
dbpsql -q -c 'DELETE FROM db55_audit.migration_runs' >/dev/null
[[ "$(dbpsql -Atc "SELECT count(*) FROM db55_audit.migration_runs")" == 0 ]] || exit 70
snapshot(){
 local db="$1" out="$2"
 compose exec -T lab-db pg_dump -U postgres -d "$db" --schema-only --no-owner \
   --no-privileges --schema=auth_l1 --schema=history_l1 |
 python3 -c 'import sys; sys.stdout.writelines(x for x in sys.stdin if not (x.startswith(chr(92)+"restrict ") or x.startswith(chr(92)+"unrestrict ")))' > "$out"
 [[ -s "$out" ]] || { echo STOP_EMPTY_M04_SCHEMA_DUMP >&2;exit 70; }
}
before="$LAB_WORK/m04_source_private_schema.sql"
after="$LAB_WORK/m04_roundtrip_private_schema.sql"
[[ ! -e "$before" && ! -e "$after" && ! -e "$LAB_WORK/m04_migration_full_cycle_receipt.json" ]] || exit 70
snapshot rag_finance_f3_lab "$before"
# Reverse dependency order. 001 and 003 are DESTRUCTIVE; the probe is EMPTY.
# 006/008 use one outer transaction as required by their own SQL contracts.
while IFS=$'\t' read -r v direction commit path blob; do
 [[ "$direction" == DOWN ]] || continue
 filename="$(basename "$path")"
 [[ -f "$LAB_SOURCE/$filename" && "$(git hash-object "$LAB_SOURCE/$filename")" == "$blob" ]] || exit 70
 role=auth_migrator
 [[ "$v" == 001 || "$v" == 002 ]] && role=history_migrator
 if [[ "$v" == 006 || "$v" == 008 ]]; then
  dbpsql -1 -c "SET ROLE $role" -f "/run/source/$filename" \
   > "$LAB_WORK/m04_down_$v.log" 2>&1 || { echo "STOP_M04_DOWN_$v" >&2;exit 70; }
 else
  dbpsql -c "SET ROLE $role" -f "/run/source/$filename" \
   > "$LAB_WORK/m04_down_$v.log" 2>&1 || { echo "STOP_M04_DOWN_$v" >&2;exit 70; }
 fi
done < <(tail -n +2 "$LAB_SOURCE/manifest.tsv" | awk -F '\t' '$2=="DOWN"{print}' | sort -r)
[[ "$(dbpsql -Atc "SELECT count(*) FROM pg_namespace WHERE nspname IN ('auth_l1','history_l1')")" == 0 ]] || {
 echo STOP_M04_REVERSE_SCHEMAS_REMAIN >&2;exit 70; }
# Forward reinstall in ORIGINAL PINNED order, with new disposable durable ledger.
while IFS=$'\t' read -r v direction commit path blob; do
 [[ "$direction" == UP ]] || continue
 filename="$(basename "$path")"; sql="$LAB_SOURCE/$filename"
 [[ -s "$sql" && "$(git hash-object "$sql")" == "$blob" ]] || exit 70
 sha="$(shasum -a 256 "$sql" | awk '{print $1}')"
 role=auth_migrator
 [[ "$v" == 001 || "$v" == 002 ]] && role=history_migrator
 dbpsql -q -c "INSERT INTO db55_audit.migration_runs
   (version,source_commit,git_blob_sha1,sql_sha256,status,cluster_system_id)
   VALUES('$v','$commit','$blob','$sha','STARTED',(SELECT system_identifier::text FROM pg_control_system()))" >/dev/null
 dbpsql -c "SET ROLE $role" -f "/run/source/$filename" > "$LAB_WORK/m04_up_$v.log" 2>&1 || {
  echo "STOP_M04_REUP_$v" >&2;exit 70; }
 dbpsql -q -c "UPDATE db55_audit.migration_runs
  SET status='APPLIED',applied_at=clock_timestamp(),applied_txid=txid_current()
  WHERE version='$v' AND status='STARTED'" >/dev/null
done < <(tail -n +2 "$LAB_SOURCE/manifest.tsv")
[[ "$(dbpsql -Atc "SELECT count(*) FROM db55_audit.migration_runs
 WHERE status='APPLIED' AND applied_txid IS NOT NULL AND applied_at>=started_at")" == 10 ]] || {
 echo STOP_M04_NEW_LEDGER_INCOMPLETE >&2;exit 70; }
[[ "$(dbpsql -Atc "SELECT count(*) FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
 WHERE n.nspname IN ('auth_l1','history_l1') AND c.relkind='r'
 AND c.relrowsecurity AND c.relforcerowsecurity")" == 14 ]] || exit 70
dbpsql -c 'SET ROLE db55_lab_auditor' -v db55_phase=private_no_dispatch \
 -f /run/source/db55_verify_staging.sql > "$LAB_WORK/m04_full_cycle_db55.log" 2>&1 || {
 echo STOP_M04_REUP_DB55 >&2;exit 70; }
grep -Fq DB55_private_no_dispatch_DB_ROLE_SCHEMA_AND_FUNCTION_GATE_PASS \
 "$LAB_WORK/m04_full_cycle_db55.log" || exit 70
snapshot "$probe" "$after"
before_sha="$(shasum -a 256 "$before" | awk '{print $1}')"
after_sha="$(shasum -a 256 "$after" | awk '{print $1}')"
[[ "$before_sha" == "$after_sha" ]] || {
 echo "STOP_M04_SCHEMA_CONSISTENCY_DRIFT" >&2;exit 70; }
# Source DB must remain unchanged; probe must be destroyed before emitting evidence.
snapshot rag_finance_f3_lab "$LAB_WORK/m04_source_recheck_private_schema.sql"
[[ "$(shasum -a 256 "$LAB_WORK/m04_source_recheck_private_schema.sql" | awk '{print $1}')" == "$before_sha" ]] || exit 70
admin -c "DROP DATABASE $probe WITH (FORCE)" >/dev/null
[[ "$(admin -c "SELECT count(*) FROM pg_database WHERE datname='$probe'")" == 0 ]] || exit 70
cat > "$LAB_WORK/m04_migration_full_cycle_receipt.json" <<JSON
{
 "contract_version":"f3.db.p3m04_a07_full_cycle.v1",
 "source_db":"disposable_pg17.11_base",
 "full_empty_001_010_down_and_forward":"PASS_10_DOWN_10_UP",
 "schema_only_source_sha256":"$before_sha",
 "schema_only_roundtrip_sha256":"$after_sha",
 "source_equals_roundtrip":true,
 "new_probe_ledger_applied":10,
 "force_rls_tables_after_roundtrip":14,
 "db55_after_roundtrip":"PASS_PRIVATE_NO_DISPATCH",
 "populated_pre009_upgrade":"PASS_TWO_OWNERS_BOTH_CLUSTERS_009_010",
 "populated_restore":"PASS_SEPARATE_PG_CLUSTER",
 "data_bearing_001_003_destructive_reverse":"NOT_PERMITTED",
 "probe_removed":true,
 "original_lab_untouched":true,
 "mac_runtime":"NOT_RUN",
 "module_gate":"NOT_ACCEPTED"
}
JSON
chmod 0600 "$LAB_WORK/m04_migration_full_cycle_receipt.json"
echo 'M04_A07_EMPTY_001_010_FULL_DOWN_AND_REINSTALL=PASS'
echo 'M04_A07_SCHEMA_ROUNDTRIP_SHA256_EQUAL=PASS'
echo 'M04_A07_TWO_OWNER_POPULATED_009_010_RESTORE=PASS'
echo 'M04_A07_NEW_LEDGER_DB55_14_FORCE_RLS=PASS'
echo 'M04_A07_DISPOSABLE_PROBE_REMOVED=PASS'
echo 'M04_A07_PRODUCTION_DATA_BEARING_FULL_ROLLBACK=NOT_AUTHORIZED'
