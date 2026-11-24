#!/usr/bin/env bash
# PR #86 continuation: exercise two synthetic owners on the SAME real TLS
# history_app PostgreSQL connection, including fail-closed and pooling risks.
# NO OIDC claims, signed actor, API, engine, migration 011 or target DB.
set -euo pipefail
source "$(dirname "$0")/_lib.sh"
require_lab_ready
secure_log
[[ "$LAB_PROJECT" == ragfinance_f3_db_lab_* && "$LAB_DB" == rag_finance_f3_lab ]] || { echo STOP_NOT_LAB >&2; exit 70; }
[[ "$(dbpsql -Atc "SELECT count(*) FROM db55_audit.migration_runs WHERE status='APPLIED'")" == 10 ]] || { echo STOP_NO_PINNED_LEDGER >&2; exit 70; }
probe=rag_finance_f3_actor_tx_pool_probe
admin(){ DB_SERVICE=lab-db DB_NAME=postgres dbpsql -Atq "$@"; }
[[ "$(admin -c "SELECT count(*) FROM pg_database WHERE datname='$probe'")" == 0 ]] || { echo STOP_PROBE_PREEXISTS >&2; exit 70; }
[[ ! -e "$LAB_WORK/actor_tx_pool_receipt.json" && ! -e "$LAB_WORK/actor_tx_pool.pgpass" ]] || { echo STOP_PROBE_RECEIPT_PREEXISTS >&2; exit 70; }
admin -c "CREATE DATABASE $probe TEMPLATE rag_finance_f3_lab OWNER postgres" >/dev/null
admin -c "REVOKE CONNECT,TEMP ON DATABASE $probe FROM PUBLIC" >/dev/null
admin -c "GRANT CONNECT ON DATABASE $probe TO history_app" >/dev/null
export DB_SERVICE=lab-db DB_NAME="$probe"
[[ "$(dbpsql -Atc "SELECT count(*) FROM history_l1.conversations")" == 0 ]] || exit 70
# Seed is restricted to newly-created disposable copy, not customer database.
dbpsql -q <<'SQL'
INSERT INTO history_l1.conversations(owner_id,id,title,state)
VALUES ('pool-owner-a-unverified','pool-conv-a','artificial A','active'),
       ('pool-owner-b-unverified','pool-conv-b','artificial B','active');
INSERT INTO history_l1.messages(owner_id,id,conversation_id,role,body)
VALUES ('pool-owner-a-unverified','pool-msg-a','pool-conv-a','user','artificial A'),
       ('pool-owner-b-unverified','pool-msg-b','pool-conv-b','user','artificial B');
SQL
[[ -s "$LAB_WORK/history_app.password" ]] || { echo STOP_NO_SERVICE_PASS >&2; exit 70; }
printf 'demo-db:5432:%s:history_app:%s\n' "$probe" "$(cat "$LAB_WORK/history_app.password")" > "$LAB_WORK/actor_tx_pool.pgpass"
chmod 0600 "$LAB_WORK/actor_tx_pool.pgpass"
# Actual SCRAM TCP login + CA/SAN verify-full. SET LOCAL is intentionally
# exercised in one physical session; no superuser SET ROLE in read probes.
service_sql(){
 compose exec -T lab-db env PGPASSFILE=/run/work/actor_tx_pool.pgpass \
   PGSSLMODE=verify-full PGSSLROOTCERT=/run/lab_secrets/ca.crt \
   psql -X -Atq -v ON_ERROR_STOP=1 -h demo-db -p 5432 -U history_app -d "$probe"
}
actual="$(service_sql <<'SQL'
SELECT current_user||'|'||(SELECT ssl::text FROM pg_stat_ssl WHERE pid=pg_backend_pid());
BEGIN READ ONLY;
SET LOCAL app.owner_id='pool-owner-a-unverified';
SELECT count(*) FROM history_l1.conversations;
SELECT count(*) FROM history_l1.conversations WHERE id='pool-conv-a';
COMMIT;
BEGIN READ ONLY;
SELECT count(*) FROM history_l1.conversations;
COMMIT;
BEGIN READ ONLY;
SET LOCAL app.owner_id='pool-owner-b-unverified';
SELECT count(*) FROM history_l1.conversations;
SELECT count(*) FROM history_l1.conversations WHERE id='pool-conv-a';
COMMIT;
BEGIN READ ONLY;
SELECT count(*) FROM history_l1.conversations;
COMMIT;
SQL
)"
expected="$(printf 'history_app|true\n1\n1\n0\n1\n0\n0')"
[[ "$actual" == "$expected" ]] || { echo STOP_TRANSACTION_OWNER_LEAK_OR_TLS >&2; exit 70; }
# A fresh physical client cannot inherit an actor from the previous client.
unset_owner="$(service_sql <<'SQL'
BEGIN READ ONLY;
SELECT count(*) FROM history_l1.conversations;
COMMIT;
SQL
)"
[[ "$unset_owner" == 0 ]] || { echo STOP_NEW_CONNECTION_OWNER_LEAK >&2; exit 70; }
refresh="$(service_sql <<'SQL'
BEGIN READ ONLY;
SET LOCAL app.owner_id='pool-owner-a-unverified';
SELECT count(*) FROM history_l1.conversations;
COMMIT;
BEGIN READ ONLY;
SELECT count(*) FROM history_l1.conversations;
COMMIT;
SQL
)"
[[ "$refresh" == "$(printf '1\n0')" ]] || { echo STOP_REFRESH_OLD_OWNER >&2; exit 70; }
# This MUST be recorded as an unresolved trust gap, never as secure actor auth.
spoof="$(service_sql <<'SQL'
BEGIN READ ONLY;
SET LOCAL app.owner_id='pool-owner-b-unverified';
SELECT count(*) FROM history_l1.conversations WHERE id='pool-conv-b';
COMMIT;
SQL
)"
[[ "$spoof" == 1 ]] || { echo STOP_GUC_RISK_UNEXPECTED >&2; exit 70; }
# Permanent SET leaks between pooled transactions, even when the request uses
# SET LOCAL later. We reproduce the risk and RESET in the same SQL session.
persistent="$(service_sql <<'SQL'
SET app.owner_id='pool-owner-a-unverified';
BEGIN READ ONLY;
SET LOCAL app.owner_id='pool-owner-b-unverified';
SELECT count(*) FROM history_l1.conversations WHERE id='pool-conv-b';
COMMIT;
BEGIN READ ONLY;
SELECT count(*) FROM history_l1.conversations WHERE id='pool-conv-a';
COMMIT;
RESET app.owner_id;
BEGIN READ ONLY;
SELECT count(*) FROM history_l1.conversations;
COMMIT;
SQL
)"
[[ "$persistent" == "$(printf '1\n1\n0')" ]] || { echo STOP_UNEXPECTED_PERSISTENT_GUC_BEHAVIOR >&2; exit 70; }
[[ "$(dbpsql -Atc "SELECT (SELECT count(*) FROM history_l1.conversations)||'|'||(SELECT count(*) FROM history_l1.messages)||'|'||(SELECT count(*) FROM history_l1.send_receipts)||'|'||(SELECT count(*) FROM history_l1.execution_attempts)||'|'||(SELECT count(*) FROM history_l1.answers)")" == '2|2|0|0|0' ]] || { echo STOP_TX_PROBE_MUTATED_DATA >&2; exit 70; }
export F3_TX_RECEIPT="$LAB_WORK/actor_tx_pool_receipt.json"
python3 - <<'PY'
import json, os
from pathlib import Path
r={
 "contract_version":"f3.db.history_transaction_actor_scope.v1",
 "environment":"real_disposable_pg17.11_lab",
 "database_login":"history_app_via_scram_tls_verify_full",
 "subjects":"two_synthetic_not_idp_attested",
 "same_connection_a_then_unset_then_b_then_unset":"PASS_1_0_1_0",
 "cross_owner_explicit_id_query_in_b_context":"ZERO_FOR_A",
 "separate_connection_with_unset_owner":"ZERO_ROWS",
 "same_session_refresh_without_inherited_owner":"PASS",
 "underlying_direct_sql_guc_is_spoofable":True,
 "signed_actor_binding":"NOT_PROVEN_BLOCKS_LIVE_HISTORY",
 "owner_guc_spoof_is_a_security_pass":False,
 "persistent_set_cross_transaction_leak_reproduced":True,
 "reset_clears_persistent_owner_for_next_transaction":True,
 "api_connection_checkout_clearance":"NOT_PROVEN",
 "fixtures_conversations":2,"fixtures_messages":2,
 "send_receipts":0,"execution_attempts":0,"answers":0,
 "phase3_011":"NOT_RUN",
 "browser_http_oidc":"NOT_RUN",
 "gate":"NOT_ACCEPTED"
}
Path(os.environ["F3_TX_RECEIPT"]).write_text(json.dumps(r,sort_keys=True,indent=2)+"\n")
PY
chmod 0600 "$F3_TX_RECEIPT"
mkdir -p "$GITHUB_WORKSPACE/ci_receipts"
install -m 0600 "$F3_TX_RECEIPT" "$GITHUB_WORKSPACE/ci_receipts/actor_tx_pool_receipt.json"
admin -c "DROP DATABASE $probe WITH (FORCE)" >/dev/null
[[ "$(admin -c "SELECT count(*) FROM pg_database WHERE datname='$probe'")" == 0 ]] || exit 70
echo ACTOR_GUC_TRANSACTION_LOCAL_A_B_UNSET_NO_LEAK=PASS
echo ACTOR_GUC_OTHER_CONNECTION_UNSET_NO_LEAK=PASS
echo ACTOR_GUC_REAL_TLS_LIMITED_LOGIN=PASS
echo ACTOR_GUC_IMPERSONATION_RISK=CONFIRMED_REQUIRES_SIGNED_API
echo ACTOR_PERSISTENT_SET_POOL_LEAK=CONFIRMED_REQUIRES_CHECKOUT_RESET
echo ACTOR_GUC_FIXTURE_NO_WRITE=PASS
echo ACTOR_GUC_ISOLATED_CLONE_REMOVED=PASS
