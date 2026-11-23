#!/usr/bin/env bash
# Disposal-only: clone current fresh verified lab database to a SEPARATE test DB;
# test evidence-preserving UP/DOWN of 009/010, History FK, NULL uniqueness and RLS.
# NEVER modify canonical accepted Mac DB, source lab database or source backup.
set -euo pipefail
source "$(dirname "$0")/_lib.sh"
require_lab_ready
secure_log
[[ "$LAB_PROJECT" == ragfinance_f3_db_lab_* ]] || { echo STOP_NOT_ISOLATED_PROJECT >&2; exit 70; }
[[ "$LAB_DB" == rag_finance_f3_lab ]] || { echo STOP_NOT_ISOLATED_BASE >&2; exit 70; }
[[ "$(dbpsql -Atc "SELECT current_database()")" == "$LAB_DB" ]] || { echo STOP_NOT_BASE_DB >&2; exit 70; }
[[ "$(dbpsql -Atc "SELECT count(*) FROM db55_audit.migration_runs WHERE status='APPLIED'")" == 10 ]] || { echo STOP_NO_BASE_LEDGER >&2;exit 70; }
[[ -f "$LAB_WORK/restore-tested.marker" ]] || { echo STOP_NO_INDEPENDENT_RESTORE >&2;exit 70; }
for name in \
  009_initial_login_attempt_binding.up.sql \
  009_initial_login_attempt_binding.down.sql \
  010_initial_login_claim_material.up.sql \
  010_initial_login_claim_material.down.sql; do
  [[ -s "$LAB_SOURCE/$name" ]] || { echo STOP_PINNED_SQL_NOT_PRESENT >&2;exit 70; }
done
probe_db=rag_finance_f3_rollback_probe
exists="$(compose exec -T lab-db psql -X -Atq -v ON_ERROR_STOP=1 -U postgres -d postgres -c \
 "SELECT count(*) FROM pg_database WHERE datname='rag_finance_f3_rollback_probe'")"
[[ "$exists" == 0 ]] || { echo STOP_PROBE_DB_PREEXISTS >&2;exit 70; }
# No client/service connections remain against source; template copy creates a fresh
# throwaway DATABASE in the already disposable lab PostgreSQL *volume*.
compose exec -T lab-db psql -X -q -v ON_ERROR_STOP=1 -U postgres -d postgres \
 -c "CREATE DATABASE rag_finance_f3_rollback_probe TEMPLATE rag_finance_f3_lab OWNER postgres;" >/dev/null
export DB_NAME="$probe_db"
[[ "$(dbpsql -Atc "SELECT current_database()")" == "$probe_db" ]] || { echo STOP_WRONG_PROBE_DB >&2;exit 70; }
[[ "$(dbpsql -Atc "SELECT count(*) FROM auth_l1.initial_login_attempts")" == 0 ]] || { echo STOP_PROBE_HAS_EXISTING_LOGIN_DATA >&2;exit 70; }
[[ "$(dbpsql -Atc "SELECT count(*) FROM history_l1.conversations")" == 0 ]] || { echo STOP_PROBE_HAS_EXISTING_HISTORY_DATA >&2;exit 70; }
# Two explicitly synthetic owners, never customer IDs or real PII.
dbpsql -q <<'SQL'
INSERT INTO history_l1.conversations(owner_id,id,title)
 VALUES ('synthetic-owner-a','synthetic-conv-a','synthetic title a'),
        ('synthetic-owner-b','synthetic-conv-b','synthetic title b');
INSERT INTO history_l1.messages(owner_id,id,conversation_id,role,body)
 VALUES ('synthetic-owner-a','synthetic-message-a','synthetic-conv-a','user','synthetic');
INSERT INTO history_l1.send_receipts
 (id,owner_id,requested_conversation_id,resolved_conversation_id,user_message_id,
  client_message_id,idempotency_key,payload_sha256,initial_request_id,initial_trace_id)
 VALUES ('synthetic-receipt-1','synthetic-owner-a',NULL,'synthetic-conv-a',
         'synthetic-message-a','synthetic-client-id','synthetic-key',
         repeat('1',64),'synthetic-request','synthetic-trace');
SQL
# Verify nullable *original* requested conversation identity is deduplicated.
if dbpsql -q -c "INSERT INTO history_l1.send_receipts
(id,owner_id,requested_conversation_id,resolved_conversation_id,user_message_id,
client_message_id,idempotency_key,payload_sha256,initial_request_id,initial_trace_id)
VALUES ('synthetic-receipt-2','synthetic-owner-a',NULL,'synthetic-conv-a',
'synthetic-message-a','synthetic-client-id','synthetic-key',repeat('1',64),'synthetic-request','synthetic-trace');" \
 > "$LAB_WORK/rollback-null-unique-negative.log" 2>&1; then
  echo STOP_NULL_UNIQUE_NOT_ENFORCED >&2; exit 70
fi
grep -Fq 'duplicate key' "$LAB_WORK/rollback-null-unique-negative.log" || { echo STOP_NULL_UNIQUE_WRONG_FAILURE >&2; exit 70; }
# Composite owner FK cannot refer to another owner's conversation.
if dbpsql -q -c "INSERT INTO history_l1.messages(owner_id,id,conversation_id,role,body)
 VALUES ('synthetic-owner-a','synthetic-forged-message','synthetic-conv-b','user','synthetic');" \
 > "$LAB_WORK/rollback-fk-negative.log" 2>&1; then
 echo STOP_CROSS_OWNER_FK_NOT_ENFORCED >&2; exit 70
fi
grep -Fq 'foreign key constraint' "$LAB_WORK/rollback-fk-negative.log" || { echo STOP_FK_NEGATIVE_WRONG_FAILURE >&2; exit 70; }
# In a single READ ONLY transaction, a scoped history_app sees only owner A.
owner_view="$(dbpsql -Atq <<'SQL'
BEGIN READ ONLY;
SET LOCAL ROLE history_app;
SET LOCAL app.owner_id='synthetic-owner-a';
SELECT count(*) FROM history_l1.conversations;
COMMIT;
SQL
)"
[[ "$owner_view" == 1 ]] || { echo STOP_HISTORY_OWNER_CROSS_READ >&2; exit 70; }
if dbpsql -q <<'SQL' > "$LAB_WORK/rollback-rls-negative.log" 2>&1; then
BEGIN;
SET LOCAL ROLE history_app;
SET LOCAL app.owner_id='synthetic-owner-a';
INSERT INTO history_l1.conversations(owner_id,id) VALUES('synthetic-owner-b','synthetic-write-intrusion');
COMMIT;
SQL
 echo STOP_HISTORY_CROSS_WRITE_ACCEPTED >&2;exit 70
fi
grep -Fq 'row-level security policy' "$LAB_WORK/rollback-rls-negative.log" || { echo STOP_HISTORY_RLS_WRONG_FAILURE >&2;exit 70; }
# Insert one synthetic record directly in the ONLY copied test DB to prove guarded
# rollback FAILS CLOSED on existing user-attempt evidence (no user data touched).
dbpsql -q <<'SQL'
INSERT INTO auth_l1.initial_login_attempts
(attempt_id,bff_principal,bff_attempt_id,start_key,request_sha256,state_sha256,
initiator_sha256,expected_issuer,pkce_envelope,nonce_envelope,expires_at)
VALUES
('aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa','synthetic-user',
 'bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb','synthetic-start',
 repeat('a',64),repeat('b',64),repeat('c',64),'https://idp.example.invalid',
 decode(repeat('11',32),'hex'),decode(repeat('22',32),'hex'),
 clock_timestamp()+interval '1 hour');
SQL
if dbpsql -c 'SET ROLE auth_migrator' -f /run/source/010_initial_login_claim_material.down.sql \
 > "$LAB_WORK/rollback-010-guard.log" 2>&1; then
 echo STOP_010_DOWN_ACCEPTED_LIVE_ATTEMPT >&2; exit 70
fi
grep -Fq LOGIN_010_DOWN_REFUSED_EVIDENCE_EXISTS "$LAB_WORK/rollback-010-guard.log" || { echo STOP_010_GUARD_FAILURE_NOT_PROVEN >&2; exit 70; }
if dbpsql -c 'SET ROLE auth_migrator' -f /run/source/009_initial_login_attempt_binding.down.sql \
 > "$LAB_WORK/rollback-009-guard.log" 2>&1; then
 echo STOP_009_DOWN_ACCEPTED_LIVE_ATTEMPT >&2; exit 70
fi
grep -Fq LOGIN_009_DOWN_REFUSED_EVIDENCE_EXISTS "$LAB_WORK/rollback-009-guard.log" || { echo STOP_009_GUARD_FAILURE_NOT_PROVEN >&2; exit 70; }
dbpsql -q -c "DELETE FROM auth_l1.initial_login_attempts
 WHERE attempt_id='aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa';" >/dev/null
# This is an EXPERIMENTAL fork. The cloned historical ledger must NOT be used
# for fresh admission after down/up; the test DB is destroyed below.
for step in \
  010_initial_login_claim_material.down.sql \
  009_initial_login_attempt_binding.down.sql \
  009_initial_login_attempt_binding.up.sql \
  010_initial_login_claim_material.up.sql; do
  dbpsql -c 'SET ROLE auth_migrator' -f "/run/source/$step" > "$LAB_WORK/rollback-$step.log" 2>&1 || {
    echo "STOP_GUARDED_DOWN_UP_FAILED_$step" >&2;exit 70;
  }
done
[[ "$(dbpsql -Atc "SELECT to_regprocedure('auth_l1.claim_initial_login_exchange_material(uuid,text,uuid,text,text)') IS NOT NULL")" == t ]] || { echo STOP_010_NOT_REINSTATED >&2;exit 70; }
dbpsql -c 'SET ROLE db55_lab_auditor' -v db55_phase=private_no_dispatch \
 -f /run/source/db55_verify_staging.sql > "$LAB_WORK/rollback-restored-db55.log" 2>&1 || {
 echo STOP_ROLLBACK_REUP_DB55 >&2; exit 70;
}
grep -Fq DB55_private_no_dispatch_DB_ROLE_SCHEMA_AND_FUNCTION_GATE_PASS \
 "$LAB_WORK/rollback-restored-db55.log" || { echo STOP_DB55_MARKER_ROLLBACK >&2;exit 70; }
# Never leave misleading copied legacy Ledger. Only this explicitly scoped disposable
# test DB is dropped, not source lab or accepted Mac demo.
compose exec -T lab-db psql -X -q -v ON_ERROR_STOP=1 -U postgres -d postgres \
 -c "DROP DATABASE rag_finance_f3_rollback_probe WITH (FORCE);" >/dev/null
echo 'P3M04_NULLS_NOT_DISTINCT_DUPLICATE=DENIED'
echo 'P3M04_COMPOSITE_CROSS_OWNER_FK=DENIED'
echo 'P3M06_OWNER_SCOPED_RLS_READ=PASS'
echo 'P3M06_CROSS_OWNER_RLS_WRITE=DENIED'
echo 'P3M04_009_010_DOWN_WITH_EVIDENCE=REFUSED'
echo 'P3M04_009_010_CLEAN_DOWN_UP=PASS'
echo 'P3M04_DB55_AFTER_ROLLBACK_REUP=PASS'
echo 'P3M04_ROLLBACK_PROBE_DB_DROPPED=PASS'
