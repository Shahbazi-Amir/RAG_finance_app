#!/usr/bin/env bash
# Disposal-only: *populated* synthetic 2-owner History backup and independent restore.
# Proves owner RLS and soft deletion state survive logical backup; it does NOT
# establish a policy-approved physical hard delete or anti-resurrection tombstone.
set -euo pipefail
source "$(dirname "$0")/_lib.sh"
require_lab_ready
secure_log
[[ "$LAB_PROJECT" == ragfinance_f3_db_lab_* && "$LAB_DB" == rag_finance_f3_lab ]] || {
  echo STOP_NOT_ISOLATED_CANDIDATE >&2; exit 70;
}
[[ -s "$LAB_WORK/restore_receipt.txt" && -f "$LAB_WORK/restore-tested.marker" ]] || {
  echo STOP_NO_RESTORE_CLUSTER >&2;exit 70;
}
source_db=rag_finance_f3_synth_source
target_db=rag_finance_f3_synth_restored
admin() {
  local svc="$1"
  shift
  compose exec -T "$svc" psql -X -Atq -v ON_ERROR_STOP=1 -U postgres -d postgres "$@"
}
[[ "$(admin lab-db -c "SELECT count(*) FROM pg_database WHERE datname='$source_db'")" == 0 ]] || {
  echo STOP_SYNTH_SOURCE_ALREADY_EXISTS >&2;exit 70;
}
[[ "$(admin restore-db -c "SELECT count(*) FROM pg_database WHERE datname='$target_db'")" == 0 ]] || {
  echo STOP_SYNTH_RESTORE_ALREADY_EXISTS >&2;exit 70;
}
admin lab-db -c "CREATE DATABASE $source_db TEMPLATE rag_finance_f3_lab OWNER postgres" >/dev/null
export DB_NAME="$source_db" DB_SERVICE=lab-db
[[ "$(dbpsql -Atc "SELECT current_database()")" == "$source_db" ]] || exit 70
# These exact values are artificial with no user content.
dbpsql -q <<'SQL'
INSERT INTO history_l1.conversations(owner_id,id,title,state)
VALUES ('synthetic-user-one','synthetic-conv-one','fixture-one','active'),
       ('synthetic-user-two','synthetic-conv-two','fixture-two','deletion_requested');
INSERT INTO history_l1.messages(owner_id,id,conversation_id,role,body)
VALUES ('synthetic-user-one','synthetic-msg-one','synthetic-conv-one','user','fixture message'),
       ('synthetic-user-two','synthetic-msg-two','synthetic-conv-two','user','fixture message');
SQL
snapshot_query="SELECT string_agg(owner_id || '|' || id || '|' || state,';' ORDER BY owner_id)
  FROM history_l1.conversations;"
expected="$(dbpsql -Atc "$snapshot_query")"
[[ "$expected" == 'synthetic-user-one|synthetic-conv-one|active;synthetic-user-two|synthetic-conv-two|deletion_requested' ]] || {
  echo STOP_BAD_SYNTH_SOURCE_DATA >&2;exit 70;
}
data_backup="$LAB_WORK/synthetic_user_lifecycle.dump"
[[ ! -e "$data_backup" ]] || { echo STOP_SYNTH_BACKUP_EXISTS >&2;exit 70; }
compose exec -T lab-db pg_dump -U postgres -d "$source_db" -Fc > "$data_backup"
[[ -s "$data_backup" ]] || exit 70
shasum -a 256 "$data_backup" > "$LAB_WORK/synthetic_user_lifecycle.dump.sha256"
shasum -a 256 -c "$LAB_WORK/synthetic_user_lifecycle.dump.sha256" >/dev/null
chmod 0600 "$data_backup" "$LAB_WORK/synthetic_user_lifecycle.dump.sha256"
admin restore-db -c "CREATE DATABASE $target_db OWNER postgres" >/dev/null
compose exec -T restore-db pg_restore -U postgres -d "$target_db" < "$data_backup" \
 > "$LAB_WORK/synthetic_user_lifecycle_restore.log" 2>&1 || {
 echo STOP_SYNTH_USER_RESTORE_FAILED >&2;exit 70;
}
export DB_SERVICE=restore-db DB_NAME="$target_db"
[[ "$(dbpsql -Atc "$snapshot_query")" == "$expected" ]] || {
 echo STOP_RESTORED_CONVERSATION_LIFECYCLE_DRIFT >&2;exit 70;
}
[[ "$(dbpsql -Atc "SELECT count(*) FROM history_l1.messages")" == 2 ]] || {
 echo STOP_RESTORED_MESSAGES_MISSING >&2;exit 70;
}
[[ "$(dbpsql -Atc "SELECT count(*) FROM db55_audit.migration_runs WHERE status='APPLIED'")" == 10 ]] || {
 echo STOP_RESTORED_SYNTH_LEDGER >&2;exit 70;
}
# RLS: actor one sees one row and not owner two; actor two sees own requested
# deletion row, but ordinary active list MUST contain zero for that user.
actor_one="$(dbpsql -Atq <<'SQL'
BEGIN READ ONLY;
SET LOCAL ROLE history_app;
SET LOCAL app.owner_id = 'synthetic-user-one';
SELECT count(*) FROM history_l1.conversations;
COMMIT;
SQL
)"
[[ "$actor_one" == 1 ]] || { echo STOP_RESTORE_OWNER_ONE_LEAK >&2;exit 70; }
actor_two_active="$(dbpsql -Atq <<'SQL'
BEGIN READ ONLY;
SET LOCAL ROLE history_app;
SET LOCAL app.owner_id = 'synthetic-user-two';
SELECT count(*) FROM history_l1.conversations WHERE state='active';
COMMIT;
SQL
)"
[[ "$actor_two_active" == 0 ]] || { echo STOP_RESTORE_SOFT_DELETE_REACTIVATED >&2;exit 70; }
dbpsql -c 'SET ROLE db55_lab_auditor' -v db55_phase=private_no_dispatch \
  -f /run/source/db55_verify_staging.sql > "$LAB_WORK/synthetic_user_restored_db55.log" 2>&1 || {
  echo STOP_RESTORED_SYNTH_DB55 >&2;exit 70;
}
grep -Fq DB55_private_no_dispatch_DB_ROLE_SCHEMA_AND_FUNCTION_GATE_PASS \
 "$LAB_WORK/synthetic_user_restored_db55.log" || { echo STOP_RESTORED_SYNTH_DB55_MARKER >&2;exit 70; }
# Separate PG system IDs from original restoration were already attested.
[[ "$(admin lab-db -c "SELECT count(*) FROM pg_database WHERE datname='$source_db'")" == 1 ]] || exit 70
[[ "$(admin restore-db -c "SELECT count(*) FROM pg_database WHERE datname='$target_db'")" == 1 ]] || exit 70
admin lab-db -c "DROP DATABASE $source_db WITH (FORCE)" >/dev/null
admin restore-db -c "DROP DATABASE $target_db WITH (FORCE)" >/dev/null
echo 'SYNTHETIC_TWO_OWNER_RESTORE_IN_DISTINCT_CLUSTER=PASS'
echo 'SYNTHETIC_OWNER_RLS_AFTER_RESTORE=PASS'
echo 'SOFT_DELETION_REQUESTED_PRESERVED_AFTER_RESTORE=PASS'
echo 'NO_ACTIVE_REAPPEARANCE_AFTER_RESTORE=PASS'
echo 'SYNTHETIC_RESTORED_DB55_AND_LEDGER=PASS'
echo 'SYNTHETIC_SOURCE_AND_RESTORE_PROBES_DROPPED=PASS'
echo 'HARD_DELETE_ANTI_RESURRECTION=NOT_IMPLEMENTED_PENDING_POLICY'
