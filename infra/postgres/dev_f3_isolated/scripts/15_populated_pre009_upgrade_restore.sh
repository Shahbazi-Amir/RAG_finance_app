#!/usr/bin/env bash
# Scratch-only representative legacy data + pre-009 backup/restore + 009-010 upgrade.
# Never run against the employer Mac accepted demo or production DB.
set -euo pipefail
source "$(dirname "$0")/_lib.sh"
require_lab_ready; secure_log
[[ "$LAB_PROJECT" == ragfinance_f3_db_lab_* && "$LAB_DB" == rag_finance_f3_lab ]] || { echo STOP_NOT_LAB >&2; exit 70; }
[[ "$(dbpsql -Atc "SELECT count(*) FROM db55_audit.migration_runs WHERE status='APPLIED'")" == 10 ]] || exit 70
[[ -f "$LAB_WORK/restore-tested.marker" ]] || exit 70
admin(){ local svc="$1"; shift; compose exec -T "$svc" psql -X -Atq -v ON_ERROR_STOP=1 -U postgres -d postgres "$@"; }
src=rag_finance_f3_populated_pre009_source
dst=rag_finance_f3_populated_pre009_restored
[[ "$(admin lab-db -c "SELECT count(*) FROM pg_database WHERE datname='$src'")" == 0 ]] || exit 70
[[ "$(admin restore-db -c "SELECT count(*) FROM pg_database WHERE datname='$dst'")" == 0 ]] || exit 70
admin lab-db -c "CREATE DATABASE $src TEMPLATE rag_finance_f3_lab OWNER postgres" >/dev/null
export DB_NAME="$src" DB_SERVICE=lab-db
[[ "$(dbpsql -Atc "SELECT count(*) FROM auth_l1.initial_login_attempts")" == 0 ]] || exit 70
dbpsql -q <<'SQL'
INSERT INTO auth_l1.owners(owner_id) VALUES ('fixture-owner-alpha'),('fixture-owner-beta');
INSERT INTO auth_l1.identity_links(issuer,subject,owner_id)
VALUES ('https://fixture.invalid','fixture-sub-alpha','fixture-owner-alpha'),
       ('https://fixture.invalid','fixture-sub-beta','fixture-owner-beta');
INSERT INTO auth_l1.sessions(
 digest_sha256,owner_id,session_epoch,generation,status,created_at,
 last_activity_at,idle_expires_at,absolute_expires_at,idle_seconds)
VALUES (repeat('a',64),'fixture-owner-alpha',0,0,'active',clock_timestamp(),
 clock_timestamp(),clock_timestamp()+interval '30 minutes',
 clock_timestamp()+interval '2 hours',1800),
 (repeat('b',64),'fixture-owner-beta',0,0,'revoked',clock_timestamp(),
 clock_timestamp(),clock_timestamp()+interval '30 minutes',
 clock_timestamp()+interval '2 hours',1800);
INSERT INTO history_l1.conversations(owner_id,id,title,state)
VALUES ('fixture-owner-alpha','fixture-conv-alpha','fixture title','active'),
       ('fixture-owner-beta','fixture-conv-beta','fixture title','deletion_requested');
INSERT INTO history_l1.messages(owner_id,id,conversation_id,role,body)
VALUES ('fixture-owner-alpha','fixture-msg-alpha','fixture-conv-alpha','user','fixture question'),
       ('fixture-owner-beta','fixture-msg-beta','fixture-conv-beta','user','fixture question');
SQL
ses="SELECT string_agg(owner_id||':'||status,';' ORDER BY owner_id) FROM auth_l1.sessions"
his="SELECT string_agg(owner_id||':'||state,';' ORDER BY owner_id) FROM history_l1.conversations"
s0="$(dbpsql -Atc "$ses")"; h0="$(dbpsql -Atc "$his")"
[[ "$s0" == 'fixture-owner-alpha:active;fixture-owner-beta:revoked' ]] || exit 70
[[ "$h0" == 'fixture-owner-alpha:active;fixture-owner-beta:deletion_requested' ]] || exit 70
for f in 010_initial_login_claim_material.down.sql 009_initial_login_attempt_binding.down.sql; do
 dbpsql -c 'SET ROLE auth_migrator' -f "/run/source/$f" > "$LAB_WORK/populated_$f.log" 2>&1 || {
 echo "STOP_DOWN_$f" >&2; exit 70; }
done
[[ "$(dbpsql -Atc "SELECT to_regclass('auth_l1.initial_login_attempts') IS NULL")" == t ]] || exit 70
[[ "$(dbpsql -Atc "$ses")" == "$s0" && "$(dbpsql -Atc "$his")" == "$h0" ]] || exit 70
# PG17 custom dump with nonsecret synthetic rows, created BEFORE re-upgrading.
dump="$LAB_WORK/pre009_populated_fixture.dump"
[[ ! -e "$dump" ]] || exit 70
compose exec -T lab-db pg_dump -U postgres -d "$src" -Fc > "$dump"
[[ -s "$dump" ]] || exit 70
shasum -a 256 "$dump" > "$LAB_WORK/pre009_populated_fixture.sha256"
shasum -a 256 -c "$LAB_WORK/pre009_populated_fixture.sha256" >/dev/null
chmod 0600 "$dump" "$LAB_WORK/pre009_populated_fixture.sha256"
admin restore-db -c "CREATE DATABASE $dst OWNER postgres" >/dev/null
compose exec -T restore-db pg_restore -U postgres -d "$dst" < "$dump" \
 > "$LAB_WORK/pre009_populated_restore.log" 2>&1 || {
 echo STOP_INDEPENDENT_PRE009_RESTORE >&2; exit 70; }
# Apply the actual immutable SQL as auth_migrator, to two pre-009 populated DBs.
for pair in "lab-db:$src" "restore-db:$dst"; do
 IFS=: read -r DB_SERVICE DB_NAME <<< "$pair"
 export DB_SERVICE DB_NAME
 [[ "$(dbpsql -Atc "SELECT to_regclass('auth_l1.initial_login_attempts') IS NULL")" == t ]] || exit 70
 for f in 009_initial_login_attempt_binding.up.sql 010_initial_login_claim_material.up.sql; do
  dbpsql -c 'SET ROLE auth_migrator' -f "/run/source/$f" > "$LAB_WORK/populated_upgrade_$DB_SERVICE-$f.log" 2>&1 || {
  echo "STOP_POPULATED_UPGRADE_$f" >&2; exit 70; }
 done
 [[ "$(dbpsql -Atc "$ses")" == "$s0" && "$(dbpsql -Atc "$his")" == "$h0" ]] || {
 echo STOP_LEGACY_DATA_CHANGED >&2;exit 70; }
 [[ "$(dbpsql -Atc "SELECT count(*) FROM history_l1.messages")" == 2 ]] || exit 70
 [[ "$(dbpsql -Atc "SELECT auth_l1.validate_session(repeat('a',64)) IS NOT NULL")" == t ]] || exit 70
 [[ "$(dbpsql -Atc "SELECT auth_l1.validate_session(repeat('b',64)) IS NULL")" == t ]] || exit 70
 view="$(dbpsql -Atq <<'SQL'
BEGIN READ ONLY;
SET LOCAL ROLE history_app;
SET LOCAL app.owner_id='fixture-owner-alpha';
SELECT count(*) FROM history_l1.conversations;
COMMIT;
SQL
)"
 [[ "$view" == 1 ]] || { echo STOP_OWNER_SCOPE_CROSS_LEAK >&2;exit 70; }
 dbpsql -c 'SET ROLE db55_lab_auditor' -v db55_phase=private_no_dispatch \
 -f /run/source/db55_verify_staging.sql > "$LAB_WORK/populated_db55_$DB_SERVICE.log" 2>&1 || exit 70
 grep -Fq DB55_private_no_dispatch_DB_ROLE_SCHEMA_AND_FUNCTION_GATE_PASS \
 "$LAB_WORK/populated_db55_$DB_SERVICE.log" || exit 70
done
# The cloned ledger is deliberately NOT a valid pre-009 migration execution
# history; never use it for admission. It is discarded with these DBs.
admin lab-db -c "DROP DATABASE $src WITH (FORCE)" >/dev/null
admin restore-db -c "DROP DATABASE $dst WITH (FORCE)" >/dev/null
echo 'POPULATED_PRE009_BACKUP_AND_INDEPENDENT_RESTORE=PASS'
echo 'POPULATED_LEGACY_HISTORY_AUTH_SESSIONS_PRESERVED=PASS'
echo 'POPULATED_009_010_UPGRADE_ON_BOTH_CLUSTERS=PASS'
echo 'POPULATED_VALID_SESSION_AND_REVOKED_SESSION=PASS'
echo 'POPULATED_OWNER_A_B_RLS=PASS'
echo 'POPULATED_DB55_BOTH_CLUSTERS=PASS'
echo 'POPULATED_PROBES_DROPPED=PASS'
echo 'POPULATED_COPY_LEDGER=EXPERIMENT_ONLY_NOT_ADMISSIBLE'
