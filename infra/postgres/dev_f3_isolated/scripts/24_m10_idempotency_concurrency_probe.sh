#!/usr/bin/env bash
# P3M10-A10 bounded DB concurrency/idempotency; no real API retry or HTTP crash claim.
# Only new disposable clone of the isolated lab; no Mac, Gateway, 011, 012+.
set -euo pipefail
source "$(dirname "$0")/_lib.sh"
require_lab_ready; secure_log
[[ "$LAB_PROJECT" == ragfinance_f3_db_lab_* && "$LAB_DB" == rag_finance_f3_lab ]] || exit 70
[[ -f "$LAB_WORK/restore-tested.marker" ]] || exit 70
[[ "$(dbpsql -Atc "SELECT count(*) FROM db55_audit.migration_runs WHERE status='APPLIED'")" == 10 ]] || exit 70
probe=rag_finance_f3_m10_idempotency_probe
admin(){ DB_SERVICE=lab-db DB_NAME=postgres dbpsql -Atq "$@"; }
[[ "$(admin -c "SELECT count(*) FROM pg_database WHERE datname='$probe'")" == 0 ]] || exit 70
admin -c "CREATE DATABASE $probe TEMPLATE rag_finance_f3_lab OWNER postgres" >/dev/null
export DB_SERVICE=lab-db DB_NAME="$probe"
# Database ACL lives on pg_database (not cloned by TEMPLATE).
admin -c "REVOKE CONNECT,TEMP ON DATABASE $probe FROM PUBLIC" >/dev/null
admin -c "GRANT CONNECT ON DATABASE $probe TO history_app" >/dev/null
dbpsql -q <<'SQL'
INSERT INTO history_l1.conversations(owner_id,id,title)
VALUES ('race-owner-a','race-conv-a','synthetic'),('race-owner-b','race-conv-b','synthetic');
INSERT INTO history_l1.messages(owner_id,id,conversation_id,role,body)
VALUES ('race-owner-a','race-msg-a','race-conv-a','user','synthetic'),
       ('race-owner-b','race-msg-b','race-conv-b','user','synthetic');
SQL
# Both real PostgreSQL sessions start while previous winner has an uncommitted
# matching NULLS NOT DISTINCT unique key. Exactly one should COMMIT.
concurrent(){
 local id="$1"
 dbpsql -q <<SQL
BEGIN;
SET LOCAL ROLE history_app;
SET LOCAL app.owner_id='race-owner-a';
INSERT INTO history_l1.send_receipts
 (id,owner_id,requested_conversation_id,resolved_conversation_id,
  user_message_id,client_message_id,idempotency_key,payload_sha256,
  initial_request_id,initial_trace_id)
VALUES ('$id','race-owner-a',NULL,'race-conv-a','race-msg-a',
 'race-shared-client','race-shared-key',repeat('a',64),'req-synthetic','trace-synthetic');
SELECT pg_sleep(2);
COMMIT;
SQL
}
concurrent race-receipt-one > "$LAB_WORK/m10_race_one_private.log" 2>&1 &
one=$!
sleep 0.15
concurrent race-receipt-two > "$LAB_WORK/m10_race_two_private.log" 2>&1 &
two=$!
rc1=0; rc2=0
wait "$one" || rc1=$?
wait "$two" || rc2=$?
if [[ "$rc1" == 0 && "$rc2" != 0 ]]; then
 grep -Fq "duplicate key" "$LAB_WORK/m10_race_two_private.log" || { echo STOP_M10_UNEXPECTED_SECOND_ERROR >&2;exit 70; }
elif [[ "$rc1" != 0 && "$rc2" == 0 ]]; then
 grep -Fq "duplicate key" "$LAB_WORK/m10_race_one_private.log" || { echo STOP_M10_UNEXPECTED_FIRST_ERROR >&2;exit 70; }
else echo STOP_M10_NOT_EXACTLY_ONE_WINNER >&2;exit 70; fi
[[ "$(dbpsql -Atc "SELECT count(*) FROM history_l1.send_receipts")" == 1 ]] || exit 70
winner="$(dbpsql -Atc "SELECT id FROM history_l1.send_receipts WHERE owner_id='race-owner-a'")"
[[ "$winner" == race-receipt-one || "$winner" == race-receipt-two ]] || exit 70
# Treat lost HTTP acknowledgment as a SIMULATED replay after durable commit:
# another physical insert with same original owner/NULL/client/key must fail.
if dbpsql -q <<'SQL' > "$LAB_WORK/m10_ack_lost_retry_negative.log" 2>&1; then
BEGIN;
SET LOCAL ROLE history_app;
SET LOCAL app.owner_id='race-owner-a';
INSERT INTO history_l1.send_receipts
 (id,owner_id,requested_conversation_id,resolved_conversation_id,
 user_message_id,client_message_id,idempotency_key,payload_sha256,
 initial_request_id,initial_trace_id)
VALUES ('race-receipt-lost-ack','race-owner-a',NULL,'race-conv-a',
 'race-msg-a','race-shared-client','race-shared-key',repeat('a',64),
 'req-synthetic','trace-synthetic');
COMMIT;
SQL
 echo STOP_M10_REPLAY_WROTE_TWICE >&2;exit 70
fi
grep -Fq "duplicate key" "$LAB_WORK/m10_ack_lost_retry_negative.log" || exit 70
# Another owner legitimately uses exactly the same client/key without collision.
dbpsql -q <<'SQL' > "$LAB_WORK/m10_owner_b_private.log" 2>&1
BEGIN;
SET LOCAL ROLE history_app;
SET LOCAL app.owner_id='race-owner-b';
INSERT INTO history_l1.send_receipts
 (id,owner_id,requested_conversation_id,resolved_conversation_id,
  user_message_id,client_message_id,idempotency_key,payload_sha256,
  initial_request_id,initial_trace_id)
VALUES ('race-receipt-b','race-owner-b',NULL,'race-conv-b','race-msg-b',
 'race-shared-client','race-shared-key',repeat('a',64),'req-b','trace-b');
COMMIT;
SQL
[[ "$(dbpsql -Atc "SELECT count(*) FROM history_l1.send_receipts")" == 2 ]] || exit 70
# A single send may have exactly one execution reservation.
dbpsql -q -c "INSERT INTO history_l1.execution_attempts
 (owner_id,id,send_receipt_id,attempt_request_id,attempt_trace_id,reserved_answer_id)
 VALUES ('race-owner-a','race-attempt-first','$winner','req-a','trace-a','answer-a')" >/dev/null
if dbpsql -q -c "INSERT INTO history_l1.execution_attempts
 (owner_id,id,send_receipt_id,attempt_request_id,attempt_trace_id,reserved_answer_id)
 VALUES ('race-owner-a','race-attempt-second','$winner','req-b','trace-b','answer-b')" \
 > "$LAB_WORK/m10_attempt_negative.log" 2>&1; then
 echo STOP_M10_SECOND_ATTEMPT_ACCEPTED >&2;exit 70
fi
grep -Fq "duplicate key" "$LAB_WORK/m10_attempt_negative.log" || exit 70
[[ "$(dbpsql -Atc "SELECT count(*) FROM history_l1.execution_attempts")" == 1 ]] || exit 70
count_scoped(){
 local owner="$1"
 dbpsql -Atq <<SQL
BEGIN READ ONLY;
SET LOCAL ROLE history_app;
SET LOCAL app.owner_id='$owner';
SELECT count(*) FROM history_l1.send_receipts;
COMMIT;
SQL
}
[[ "$(count_scoped race-owner-a)" == 1 && "$(count_scoped race-owner-b)" == 1 ]] || exit 70
[[ "$(count_scoped '')" == 0 ]] || exit 70
admin -c "DROP DATABASE $probe WITH (FORCE)" >/dev/null
[[ "$(admin -c "SELECT count(*) FROM pg_database WHERE datname='$probe'")" == 0 ]] || exit 70
[[ "$(DB_NAME=rag_finance_f3_lab dbpsql -Atc "SELECT count(*) FROM history_l1.send_receipts")" == 0 ]] || exit 70
cat > "$LAB_WORK/m10_idempotency_concurrency_receipt.json" <<'JSON'
{
 "contract_version":"f3.db.synthetic_m10_client_idempotency_concurrency.v1",
 "environment":"real_pg17.11_only_disposable_clone",
 "concurrent_sql_clients":2,
 "concurrent_insert_commits":1,
 "concurrent_duplicate_key_denials":1,
 "nullable_request_idempotency_key":"NULLS_NOT_DISTINCT_CONFIRMED",
 "simulated_lost_ack_replay":"DENIED_NO_SECOND_COMMIT",
 "cross_owner_same_client_key":"ALLOWED_SCOPED",
 "one_attempt_per_send_receipt":"SECOND_DENIED",
 "owner_a_visible_receipts":1,
 "owner_b_visible_receipts":1,
 "unset_owner_visible_receipts":0,
 "clone_removed":true,
 "source_lab_unchanged":true,
 "real_http_retry_or_crash":"NOT_RUN",
 "signed_idp_same_tx_actor":"NOT_PROVEN",
 "module_gate":"NOT_ACCEPTED"
}
JSON
chmod 0600 "$LAB_WORK/m10_idempotency_concurrency_receipt.json"
echo 'M10_A10_TWO_CLIENT_UNCOMMITTED_UNIQUE_RACE=1_WIN_1_DENIED'
echo 'M10_A10_DURABLE_SIMULATED_LOST_ACK_REPLAY=DENIED'
echo 'M10_A10_CROSS_OWNER_SAME_KEY_ALLOWED=PASS'
echo 'M10_A10_EXACT_ONE_ATTEMPT_PER_SEND=PASS'
echo 'M10_A10_RLS_A_B_UNSET=PASS'
echo 'M10_A10_CLONE_REMOVED=PASS'
echo 'M10_A10_REAL_SIGNED_HTTP_CRASH_REPLAY=NOT_RUN'
