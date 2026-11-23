#!/usr/bin/env bash
# P3M22-A09 bounded actual PG17 SIGKILL/WAL-recovery drill on disposable restore cluster.
# NO accepted Mac, original DB cluster, production, Qdrant, engine or paid endpoint.
set -euo pipefail
source "$(dirname "$0")/_lib.sh"
require_lab_ready; secure_log
[[ "$LAB_PROJECT" == ragfinance_f3_db_lab_* && "$LAB_DB" == rag_finance_f3_lab ]] || {
 echo STOP_NOT_DISPOSABLE_PG_PROJECT >&2;exit 70; }
[[ -f "$LAB_WORK/restore-tested.marker" && -s "$LAB_WORK/backup_integrity_fault_receipt.json" ]] || {
 echo STOP_FULL_RESTORE_AND_PARTIAL_CORRUPTION_PRECONDITIONS >&2;exit 70; }
shasum -a 256 -c "$LAB_WORK/backup.dump.sha256" >/dev/null || exit 70
source_id="$(DB_SERVICE=lab-db DB_NAME=rag_finance_f3_lab dbpsql -Atc "SELECT system_identifier FROM pg_control_system()")"
restore_id="$(DB_SERVICE=restore-db DB_NAME=rag_finance_f3_lab_restore dbpsql -Atc "SELECT system_identifier FROM pg_control_system()")"
[[ -n "$source_id" && -n "$restore_id" && "$source_id" != "$restore_id" ]] || exit 70
probe=rag_finance_f3_pg_crash_probe
admin(){ DB_SERVICE=restore-db DB_NAME=postgres dbpsql -Atq "$@"; }
[[ "$(admin -c "SELECT count(*) FROM pg_database WHERE datname='$probe'")" == 0 ]] || {
 echo STOP_FULL_PG_PROBE_COLLISION >&2;exit 70; }
admin -c "CREATE DATABASE $probe TEMPLATE rag_finance_f3_lab_restore OWNER postgres" >/dev/null
admin -c "REVOKE CONNECT,TEMP ON DATABASE $probe FROM PUBLIC" >/dev/null
admin -c "GRANT CONNECT ON DATABASE $probe TO history_app" >/dev/null
export DB_SERVICE=restore-db DB_NAME="$probe"
dbpsql -q <<'SQL'
INSERT INTO history_l1.conversations(owner_id,id,title)
 VALUES ('crash-owner-a','crash-conv-a','committed a'),
        ('crash-owner-b','crash-conv-b','committed b');
INSERT INTO history_l1.messages(owner_id,id,conversation_id,role,body)
 VALUES ('crash-owner-a','crash-msg-a','crash-conv-a','user','fake a'),
        ('crash-owner-b','crash-msg-b','crash-conv-b','user','fake b');
SQL
[[ "$(dbpsql -Atc "SELECT count(*) FROM history_l1.conversations")" == 2 ]] || exit 70
[[ "$(dbpsql -Atc "SELECT count(*) FROM history_l1.messages")" == 2 ]] || exit 70
# Hold a deliberately uncommitted insert while PostgreSQL sleeps.
# The temporary DB is the ONLY database that receives fake user test rows.
dbpsql -q <<'SQL' > "$LAB_WORK/pg_crash_pending_tx_private.log" 2>&1 &
BEGIN;
INSERT INTO history_l1.conversations(owner_id,id,title)
 VALUES ('crash-owner-a','crash-uncommitted','must disappear after crash');
SELECT pg_sleep(45);
COMMIT;
SQL
pending_pid=$!
sleeping=0
for _ in {1..40}; do
 count="$(dbpsql -Atc "SELECT count(*) FROM pg_stat_activity
  WHERE datname='$probe' AND wait_event='PgSleep'")"
 if [[ "$count" -ge 1 ]]; then sleeping=1;break;fi
 sleep 0.25
done
[[ "$sleeping" == 1 ]] || { echo STOP_FULL_PG_UNCOMMITTED_TX_NOT_OBSERVED >&2;exit 70; }
cid="$(compose --profile restore ps -q restore-db)"
[[ -n "$cid" ]] || { echo STOP_RESTORE_CONTAINER_NOT_RUNNING >&2;exit 70; }
project_label="$(docker inspect -f '{{ index .Config.Labels "com.docker.compose.project" }}' "$cid")"
service_label="$(docker inspect -f '{{ index .Config.Labels "com.docker.compose.service" }}' "$cid")"
[[ "$project_label" == "$LAB_PROJECT" && "$service_label" == restore-db ]] || {
 echo STOP_UNTRUSTED_PG_CRASH_TARGET >&2;exit 70; }
# Real abrupt PostgreSQL server process death. NOT a full machine/volume disaster.
docker kill --signal KILL "$cid" >/dev/null
wait_rc=0
wait "$pending_pid" || wait_rc=$?
[[ "$wait_rc" != 0 ]] || { echo STOP_UNCOMMITTED_PENDING_TX_RETURNED_SUCCESS >&2;exit 70; }
if dbpsql -Atc "SELECT 1" > "$LAB_WORK/pg_crash_offline_private.log" 2>&1; then
 echo STOP_KILLED_RESTORE_CLUSTER_ACCEPTED_DB_CONNECTION >&2;exit 70
fi
compose --profile restore start restore-db > "$LAB_WORK/pg_crash_restart_private.log" 2>&1 || {
 echo STOP_PG_CRASH_RESTART_FAILED >&2;exit 70; }
ready=0
for _ in {1..50}; do
 if [[ "$(dbpsql -Atc 'SELECT current_database()' 2>/dev/null || :)" == "$probe" ]]; then ready=1;break;fi
 sleep 2
done
[[ "$ready" == 1 ]] || { echo STOP_PG_CRASH_WAL_RECOVERY_NOT_READY >&2;exit 70; }
[[ "$(dbpsql -Atc "SELECT system_identifier FROM pg_control_system()")" == "$restore_id" ]] || exit 70
[[ "$(DB_SERVICE=lab-db DB_NAME=rag_finance_f3_lab dbpsql -Atc 'SELECT system_identifier FROM pg_control_system()')" == "$source_id" ]] || exit 70
[[ "$(dbpsql -Atc "SELECT count(*) FROM history_l1.conversations")" == 2 ]] || {
 echo STOP_COMMITTED_HISTORY_LOST_AFTER_WAL_RECOVERY >&2;exit 70; }
[[ "$(dbpsql -Atc "SELECT count(*) FROM history_l1.messages")" == 2 ]] || exit 70
[[ "$(dbpsql -Atc "SELECT count(*) FROM history_l1.conversations
 WHERE id='crash-uncommitted'")" == 0 ]] || {
 echo STOP_UNCOMMITTED_INSERT_REAPPEARED >&2;exit 70; }
scoped(){
 local owner="$1"
 dbpsql -Atq <<SQL
BEGIN READ ONLY;
SET LOCAL ROLE history_app;
SET LOCAL app.owner_id='$owner';
SELECT count(*) FROM history_l1.conversations;
COMMIT;
SQL
}
[[ "$(scoped crash-owner-a)" == 1 && "$(scoped crash-owner-b)" == 1 ]] || exit 70
[[ "$(scoped '')" == 0 ]] || exit 70
[[ "$(dbpsql -Atc "SELECT count(*) FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
 WHERE n.nspname IN ('history_l1','auth_l1') AND c.relkind='r'
 AND c.relrowsecurity AND c.relforcerowsecurity")" == 14 ]] || exit 70
dbpsql -c 'SET ROLE db55_lab_auditor' -v db55_phase=private_no_dispatch \
 -f /run/source/db55_verify_staging.sql > "$LAB_WORK/pg_crash_restored_db55_private.log" 2>&1 || {
 echo STOP_POST_CRASH_DB55_DENIED >&2;exit 70; }
grep -Fq DB55_private_no_dispatch_DB_ROLE_SCHEMA_AND_FUNCTION_GATE_PASS \
 "$LAB_WORK/pg_crash_restored_db55_private.log" || exit 70
admin -c "DROP DATABASE $probe WITH (FORCE)" >/dev/null
[[ "$(admin -c "SELECT count(*) FROM pg_database WHERE datname='$probe'")" == 0 ]] || exit 70
shasum -a 256 -c "$LAB_WORK/backup.dump.sha256" >/dev/null || exit 70
python3 - "$LAB_WORK/pg_crash_recovery_receipt.json" <<'PY'
import json,sys
from pathlib import Path
p=Path(sys.argv[1])
assert not p.exists()
p.write_text(json.dumps({
 "contract_version":"f3.db.synthetic_pg17_crash_and_wal_recovery.v1",
 "scope":"kill_only_disposable_restore_postgres_container_not_host",
 "fault":"SIGKILL_POSTGRES_CONTAINER",
 "database_offline_connection_denied":True,
 "postgres_wal_recovery":"PASS",
 "source_and_restore_cluster_ids_stable":True,
 "committed_conversations_after":2,
 "committed_messages_after":2,
 "uncommitted_insert_after":0,
 "owner_a_visible":1,"owner_b_visible":1,"no_owner_visible":0,
 "force_rls_tables_after_restart":14,
 "db55_after_restart":"PASS",
 "prior_corrupt_backup_pre_restore_negatives":"2_OF_2_FAILED_CLOSED",
 "original_backup_sha256_intact":True,
 "test_probe_removed":True,
 "mac_runtime":"NOT_RUN","full_machine_failure":"NOT_RUN",
 "offsite_encrypted_key_custody":"NOT_DEFINED",
 "pitr":"NOT_RUN","approved_rpo_rto":"NOT_DEFINED",
 "module_gate":"NOT_ACCEPTED"
},indent=2,sort_keys=True)+"\n")
PY
chmod 0600 "$LAB_WORK/pg_crash_recovery_receipt.json"
echo 'M22_A09_ACTUAL_RESTORE_PG_SIGKILL_AND_WAL_RESTART=PASS'
echo 'M22_A09_COMMITTED_ROWS_PRESERVED_UNCOMMITTED_ROW_ABSENT=PASS'
echo 'M22_A09_RLS_14_AND_DB55_AFTER_RESTART=PASS'
echo 'M22_A09_INDEPENDENT_SOURCE_AND_BACKUP_UNCHANGED=PASS'
echo 'M22_A09_FULL_MACHINE_MAC_RPO_RTO=NOT_TESTED'
