#!/usr/bin/env bash
# Actual six-table two-owner PostgreSQL negative suite on disposable clone only.
# SQL application GUC is NOT a signed IdP actor; test trust boundary explicitly.
set -euo pipefail
source "$(dirname "$0")/_lib.sh"
require_lab_ready; secure_log
[[ "$LAB_PROJECT" == ragfinance_f3_db_lab_* && "$LAB_DB" == rag_finance_f3_lab ]] || exit 70
[[ "$(dbpsql -Atc "SELECT count(*) FROM db55_audit.migration_runs WHERE status='APPLIED'")" == 10 ]] || exit 70
probe=rag_finance_f3_history_rls_probe
admin(){ compose exec -T lab-db psql -X -Atq -v ON_ERROR_STOP=1 -U postgres -d postgres "$@"; }
[[ "$(admin -c "SELECT count(*) FROM pg_database WHERE datname='$probe'")" == 0 ]] || exit 70
admin -c "CREATE DATABASE $probe TEMPLATE rag_finance_f3_lab OWNER postgres" >/dev/null
export DB_SERVICE=lab-db DB_NAME="$probe"
[[ "$(dbpsql -Atc "SELECT current_database()")" == "$probe" ]] || exit 70
[[ "$(dbpsql -Atc "SELECT count(*) FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='history_l1' AND c.relkind='r' AND c.relrowsecurity AND c.relforcerowsecurity")" == 6 ]] || exit 70
dbpsql -q <<'SQL'
INSERT INTO history_l1.conversations(owner_id,id,title,state)
VALUES ('synthetic-owner-a','conv-a','title A','active'),('synthetic-owner-b','conv-b','title B','active');
INSERT INTO history_l1.messages(owner_id,id,conversation_id,role,body)
VALUES ('synthetic-owner-a','msg-a','conv-a','user','fixture A'),('synthetic-owner-b','msg-b','conv-b','user','fixture B');
INSERT INTO history_l1.create_receipts(owner_id,client_conversation_id,idempotency_key,payload_sha256,conversation_id,created_snapshot)
VALUES ('synthetic-owner-a','client-conv-a','create-a',repeat('a',64),'conv-a','{}'::jsonb),
       ('synthetic-owner-b','client-conv-b','create-b',repeat('b',64),'conv-b','{}'::jsonb);
INSERT INTO history_l1.send_receipts(owner_id,id,requested_conversation_id,resolved_conversation_id,user_message_id,client_message_id,idempotency_key,payload_sha256,initial_request_id,initial_trace_id)
VALUES ('synthetic-owner-a','send-a','conv-a','conv-a','msg-a','client-msg-a','idem-a',repeat('a',64),'req-a','trace-a'),
       ('synthetic-owner-b','send-b','conv-b','conv-b','msg-b','client-msg-b','idem-b',repeat('b',64),'req-b','trace-b');
INSERT INTO history_l1.execution_attempts(owner_id,id,send_receipt_id,attempt_request_id,attempt_trace_id,reserved_answer_id)
VALUES ('synthetic-owner-a','attempt-a','send-a','areq-a','atrace-a','answer-a'),
       ('synthetic-owner-b','attempt-b','send-b','areq-b','atrace-b','answer-b');
INSERT INTO history_l1.answers(owner_id,id,conversation_id,message_id,attempt_id,payload)
VALUES ('synthetic-owner-a','answer-a','conv-a','msg-a','attempt-a','{"fixture":"A"}'::jsonb),
       ('synthetic-owner-b','answer-b','conv-b','msg-b','attempt-b','{"fixture":"B"}'::jsonb);
SQL
actor_counts(){
  local owner="$1"
  dbpsql -Atq <<SQL
BEGIN READ ONLY;
SET LOCAL ROLE history_app;
SET LOCAL app.owner_id='$owner';
SELECT (SELECT count(*) FROM history_l1.conversations)||'|'||
       (SELECT count(*) FROM history_l1.messages)||'|'||
       (SELECT count(*) FROM history_l1.create_receipts)||'|'||
       (SELECT count(*) FROM history_l1.send_receipts)||'|'||
       (SELECT count(*) FROM history_l1.execution_attempts)||'|'||
       (SELECT count(*) FROM history_l1.answers);
COMMIT;
SQL
}
[[ "$(actor_counts synthetic-owner-a)" == '1|1|1|1|1|1' ]] || { echo STOP_OWNER_A_RLS >&2;exit 70; }
[[ "$(actor_counts synthetic-owner-b)" == '1|1|1|1|1|1' ]] || { echo STOP_OWNER_B_RLS >&2;exit 70; }
no_owner="$(dbpsql -Atq <<'SQL'
BEGIN READ ONLY;
SET LOCAL ROLE history_app;
SELECT (SELECT count(*) FROM history_l1.conversations)||'|'||
       (SELECT count(*) FROM history_l1.messages)||'|'||
       (SELECT count(*) FROM history_l1.create_receipts)||'|'||
       (SELECT count(*) FROM history_l1.send_receipts)||'|'||
       (SELECT count(*) FROM history_l1.execution_attempts)||'|'||
       (SELECT count(*) FROM history_l1.answers);
COMMIT;
SQL
)"
[[ "$no_owner" == '0|0|0|0|0|0' ]] || { echo STOP_UNSET_OWNER_RLS >&2;exit 70; }
own_write="$(dbpsql -Atq <<'SQL'
BEGIN;
SET LOCAL ROLE history_app;
SET LOCAL app.owner_id='synthetic-owner-a';
UPDATE history_l1.conversations SET title='changed A',updated_at=clock_timestamp() WHERE id='conv-a' RETURNING id;
COMMIT;
SQL
)"
[[ "$own_write" == conv-a ]] || { echo STOP_OWNER_A_WRITE >&2;exit 70; }
foreign_write="$(dbpsql -Atq <<'SQL'
BEGIN;
SET LOCAL ROLE history_app;
SET LOCAL app.owner_id='synthetic-owner-a';
UPDATE history_l1.conversations SET title='ATTACK' WHERE id='conv-b' RETURNING id;
COMMIT;
SQL
)"
[[ -z "$foreign_write" ]] || { echo STOP_OWNER_B_MUTATION >&2;exit 70; }
expect_denied(){
  local label="$1" why="$2" sql="$3"
  if dbpsql -Atq -c "$sql" > "$LAB_WORK/history_negative_$label.log" 2>&1; then
    echo "STOP_NEGATIVE_SQL_ACCEPTED:$label" >&2;exit 70
  fi
  grep -Fqi "$why" "$LAB_WORK/history_negative_$label.log" || { echo "STOP_WRONG_NEGATIVE_REASON:$label" >&2;exit 70; }
  echo "SQL_NEGATIVE_$label=PASS"
}
expect_denied forged_owner_insert 'row-level security policy' \
"BEGIN; SET LOCAL ROLE history_app; SET LOCAL app.owner_id='synthetic-owner-a';
INSERT INTO history_l1.messages(owner_id,id,conversation_id,role,body)
VALUES('synthetic-owner-b','forged-msg-b','conv-b','user','attack'); COMMIT;"
expect_denied cross_owner_message_fk 'foreign key constraint' \
"BEGIN; SET LOCAL ROLE history_app; SET LOCAL app.owner_id='synthetic-owner-a';
INSERT INTO history_l1.messages(owner_id,id,conversation_id,role,body)
VALUES('synthetic-owner-a','cross-msg','conv-b','user','attack'); COMMIT;"
expect_denied immutable_message_update 'permission denied' \
"BEGIN; SET LOCAL ROLE history_app; SET LOCAL app.owner_id='synthetic-owner-a';
UPDATE history_l1.messages SET body='rewritten' WHERE id='msg-a'; COMMIT;"
expect_denied immutable_answer_update 'permission denied' \
"BEGIN; SET LOCAL ROLE history_app; SET LOCAL app.owner_id='synthetic-owner-a';
UPDATE history_l1.answers SET payload='{}'::jsonb WHERE id='answer-a'; COMMIT;"
expect_denied forbidden_history_delete 'permission denied' \
"BEGIN; SET LOCAL ROLE history_app; SET LOCAL app.owner_id='synthetic-owner-a';
DELETE FROM history_l1.conversations WHERE id='conv-a'; COMMIT;"
expect_denied cross_owner_answer_fk 'foreign key constraint' \
"INSERT INTO history_l1.answers(owner_id,id,conversation_id,message_id,attempt_id,payload)
VALUES('synthetic-owner-a','bad-answer','conv-b','msg-b','attempt-a','{}'::jsonb);"
expect_denied duplicate_send 'duplicate key value violates unique constraint' \
"INSERT INTO history_l1.send_receipts(owner_id,id,requested_conversation_id,resolved_conversation_id,user_message_id,client_message_id,idempotency_key,payload_sha256,initial_request_id,initial_trace_id)
VALUES('synthetic-owner-a','send-clone','conv-a','conv-a','msg-a','client-msg-a','idem-a',repeat('a',64),'req-clone','trace-clone');"
# Expected risk: direct history_app SQL client can set an owner GUC.
# This test does NOT mark same-TX signed IdP actor fence as complete.
guc_risk="$(dbpsql -Atq <<'SQL'
BEGIN READ ONLY;
SET LOCAL ROLE history_app;
SET LOCAL app.owner_id='synthetic-owner-b';
SELECT count(*) FROM history_l1.conversations WHERE id='conv-b';
COMMIT;
SQL
)"
[[ "$guc_risk" == 1 ]] || { echo STOP_GUC_BOUNDARY_NOT_REPRODUCED >&2;exit 70; }
snapshot="$(dbpsql -Atc "
SELECT (SELECT count(*) FROM history_l1.conversations)||'|'||
       (SELECT count(*) FROM history_l1.messages)||'|'||
       (SELECT count(*) FROM history_l1.create_receipts)||'|'||
       (SELECT count(*) FROM history_l1.send_receipts)||'|'||
       (SELECT count(*) FROM history_l1.execution_attempts)||'|'||
       (SELECT count(*) FROM history_l1.answers)||'|'||
       (SELECT title FROM history_l1.conversations WHERE id='conv-a')||'|'||
       (SELECT title FROM history_l1.conversations WHERE id='conv-b')")"
[[ "$snapshot" == '2|2|2|2|2|2|changed A|title B' ]] || { echo STOP_INCONSISTENT_SNAPSHOT >&2;exit 70; }
python3 - "$LAB_WORK/history_rls_adversarial_receipt.json" <<'PY'
from pathlib import Path
import json,sys
r={
"contract_version":"f3.db.synthetic_history_rls_adversarial.v1",
"environment":"pg17.11_separate_disposable_lab_clone",
"owners":2,"tables":6,"rows_per_table":2,
"owner_a_visible_each":[1]*6,"owner_b_visible_each":[1]*6,"no_owner_visible_each":[0]*6,
"positive_owner_a_title_update":"PASS","foreign_owner_update":"NO_ROWS",
"negative_cases":{"forged_owner_insert":"RLS_DENIED","cross_owner_message_fk":"FK_DENIED",
"immutable_message_update":"GRANT_DENIED","immutable_answer_update":"GRANT_DENIED",
"forbidden_history_delete":"GRANT_DENIED","cross_owner_answer_fk":"FK_DENIED",
"duplicate_send":"UNIQUE_DENIED"},
"post_negative_snapshot":"NO_UNAUTHORIZED_CHANGES",
"direct_history_role_can_set_owner_guc":True,
"same_transaction_signed_actor_fence":"NOT_PROVEN_REQUIRES_REAL_API_IDP",
"real_mac_http":"NOT_RUN","external_dispatch":False,"module_gate":"NOT_ACCEPTED"}
Path(sys.argv[1]).write_text(json.dumps(r,sort_keys=True,indent=2)+"\n")
PY
chmod 0600 "$LAB_WORK/history_rls_adversarial_receipt.json"
admin -c "DROP DATABASE $probe WITH (FORCE)" >/dev/null
[[ "$(admin -c "SELECT count(*) FROM pg_database WHERE datname='$probe'")" == 0 ]] || exit 70
echo 'HISTORY_SIX_TABLE_TWO_OWNER_RLS=PASS'
echo 'HISTORY_SEVEN_NEGATIVE_CASES=7/7_PASS'
echo 'SIGNED_ACTOR_SQL_GUC_FENCE=NOT_PROVEN'
echo 'HISTORY_DISPOSABLE_PROBE_CLEANED=PASS'
