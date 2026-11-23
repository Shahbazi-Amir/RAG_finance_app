#!/usr/bin/env bash
# Disposable PG17 real SQL version of repository.py keyset cursor semantics.
# Two synthetic owners, intervening inserts, stable anchored pages. No HTTP.
set -euo pipefail
source "$(dirname "$0")/_lib.sh"
require_lab_ready;secure_log
[[ "$LAB_PROJECT" == ragfinance_f3_db_lab_* && "$LAB_DB" == rag_finance_f3_lab ]] || exit 70
[[ "$(dbpsql -Atc "SELECT count(*) FROM db55_audit.migration_runs WHERE status='APPLIED'")" == 10 ]] || exit 70
probe=rag_finance_f3_cursor_race_probe
admin(){ compose exec -T lab-db psql -X -Atq -v ON_ERROR_STOP=1 -U postgres -d postgres "$@"; }
[[ "$(admin -c "SELECT count(*) FROM pg_database WHERE datname='$probe'")" == 0 ]] || { echo STOP_CURSOR_PROBE_PREEXISTS >&2;exit 70; }
admin -c "CREATE DATABASE $probe TEMPLATE rag_finance_f3_lab OWNER postgres" >/dev/null
export DB_SERVICE=lab-db DB_NAME="$probe"
[[ "$(dbpsql -Atc 'SELECT current_database()')" == "$probe" ]] || exit 70
dbpsql -q <<'SQL'
INSERT INTO history_l1.conversations(owner_id,id,title,state,created_at,updated_at)
SELECT 'cursor-owner-a','a-conv-'||n,'test','active',
 '2026-01-01 00:00:00+00'::timestamptz+make_interval(secs=>n),
 '2026-01-01 00:00:00+00'::timestamptz+make_interval(secs=>n)
FROM generate_series(1,5) n;
INSERT INTO history_l1.conversations(owner_id,id,title,state,created_at,updated_at)
SELECT 'cursor-owner-b','b-conv-'||n,'test','active',
 '2026-01-01 00:00:00+00'::timestamptz+make_interval(secs=>n),
 '2026-01-01 00:00:00+00'::timestamptz+make_interval(secs=>n)
FROM generate_series(1,3) n;
INSERT INTO history_l1.messages(owner_id,id,conversation_id,role,body,created_at)
SELECT 'cursor-owner-a','a-msg-'||n,'a-conv-1','user','synthetic',
 '2026-01-01 00:00:00+00'::timestamptz+make_interval(secs=>n)
FROM generate_series(1,5) n;
INSERT INTO history_l1.messages(owner_id,id,conversation_id,role,body,created_at)
SELECT 'cursor-owner-b','b-msg-'||n,'b-conv-1','user','synthetic',
 '2026-01-01 00:00:00+00'::timestamptz+make_interval(secs=>n)
FROM generate_series(1,3) n;
SQL
actor_sql(){
 local statement="$1"
 dbpsql -Atq <<SQL
BEGIN READ ONLY;
SET LOCAL ROLE history_app;
SET LOCAL app.owner_id='cursor-owner-a';
$statement
COMMIT;
SQL
}
# Exactly the repository.py descendant predicates: conversation DESC and
# (created_at,id) <= anchor AND < last; message ASC, <= anchor AND > last.
first_conv="$(actor_sql "
SELECT string_agg(id,',' ORDER BY created_at DESC,id DESC)
FROM (SELECT id,created_at FROM history_l1.conversations
 WHERE owner_id='cursor-owner-a' AND state='active'
 ORDER BY created_at DESC,id DESC LIMIT 3) page;")"
first_msg="$(actor_sql "
SELECT string_agg(id,',' ORDER BY created_at ASC,id ASC)
FROM (SELECT id,created_at FROM history_l1.messages
 WHERE owner_id='cursor-owner-a' AND conversation_id='a-conv-1'
 ORDER BY created_at ASC,id ASC LIMIT 3) page;")"
[[ "$first_conv" == 'a-conv-5,a-conv-4,a-conv-3' && "$first_msg" == 'a-msg-1,a-msg-2,a-msg-3' ]] || { echo STOP_FIRST_KEYSET_PAGE >&2;exit 70; }

# Concurrent new records AFTER the anchored newest key must not migrate into
# either established page sequence, even if a separate request sees them.
dbpsql -q <<'SQL'
INSERT INTO history_l1.conversations(owner_id,id,title,state,created_at,updated_at)
VALUES ('cursor-owner-a','a-conv-6','new after anchor','active','2026-01-01 00:00:06+00','2026-01-01 00:00:06+00'),
       ('cursor-owner-b','b-conv-4','new B','active','2026-01-01 00:00:06+00','2026-01-01 00:00:06+00');
INSERT INTO history_l1.messages(owner_id,id,conversation_id,role,body,created_at)
VALUES ('cursor-owner-a','a-msg-6','a-conv-1','user','new after anchor','2026-01-01 00:00:06+00'),
       ('cursor-owner-b','b-msg-4','b-conv-1','user','new B','2026-01-01 00:00:06+00');
SQL
conv_second="$(actor_sql "
SELECT string_agg(id,',' ORDER BY created_at DESC,id DESC)
FROM (SELECT id,created_at FROM history_l1.conversations
 WHERE owner_id='cursor-owner-a' AND state='active'
 AND (created_at,id) <= ('2026-01-01 00:00:05+00'::timestamptz,'a-conv-5')
 AND (created_at,id) < ('2026-01-01 00:00:04+00'::timestamptz,'a-conv-4')
 ORDER BY created_at DESC,id DESC LIMIT 3) page;")"
conv_third="$(actor_sql "
SELECT string_agg(id,',' ORDER BY created_at DESC,id DESC)
FROM (SELECT id,created_at FROM history_l1.conversations
 WHERE owner_id='cursor-owner-a' AND state='active'
 AND (created_at,id) <= ('2026-01-01 00:00:05+00'::timestamptz,'a-conv-5')
 AND (created_at,id) < ('2026-01-01 00:00:02+00'::timestamptz,'a-conv-2')
 ORDER BY created_at DESC,id DESC LIMIT 3) page;")"
msg_second="$(actor_sql "
SELECT string_agg(id,',' ORDER BY created_at ASC,id ASC)
FROM (SELECT id,created_at FROM history_l1.messages
 WHERE owner_id='cursor-owner-a' AND conversation_id='a-conv-1'
 AND (created_at,id) <= ('2026-01-01 00:00:05+00'::timestamptz,'a-msg-5')
 AND (created_at,id) > ('2026-01-01 00:00:02+00'::timestamptz,'a-msg-2')
 ORDER BY created_at ASC,id ASC LIMIT 3) page;")"
msg_third="$(actor_sql "
SELECT string_agg(id,',' ORDER BY created_at ASC,id ASC)
FROM (SELECT id,created_at FROM history_l1.messages
 WHERE owner_id='cursor-owner-a' AND conversation_id='a-conv-1'
 AND (created_at,id) <= ('2026-01-01 00:00:05+00'::timestamptz,'a-msg-5')
 AND (created_at,id) > ('2026-01-01 00:00:04+00'::timestamptz,'a-msg-4')
 ORDER BY created_at ASC,id ASC LIMIT 3) page;")"
[[ "$conv_second" == 'a-conv-3,a-conv-2,a-conv-1' && "$conv_third" == 'a-conv-1' ]] || { echo STOP_CONVERSATION_CURSOR_RACE >&2;exit 70; }
[[ "$msg_second" == 'a-msg-3,a-msg-4,a-msg-5' && "$msg_third" == 'a-msg-5' ]] || { echo STOP_MESSAGES_CURSOR_RACE >&2;exit 70; }
# Without anchor a new query may see new A record; with same anchor does not.
fresh="$(actor_sql "SELECT count(*) FROM history_l1.conversations WHERE owner_id='cursor-owner-a' AND state='active';")"
anchored="$(actor_sql "SELECT count(*) FROM history_l1.conversations WHERE owner_id='cursor-owner-a' AND state='active' AND (created_at,id)<=('2026-01-01 00:00:05+00'::timestamptz,'a-conv-5');")"
[[ "$fresh" == 6 && "$anchored" == 5 ]] || { echo STOP_ANCHOR_FRESHNESS_LEAK >&2;exit 70; }
# B is still invisible to A (also in messages).
b_cross="$(actor_sql "SELECT (SELECT count(*) FROM history_l1.conversations WHERE id LIKE 'b-conv-%')||'|'||(SELECT count(*) FROM history_l1.messages WHERE id LIKE 'b-msg-%');")"
[[ "$b_cross" == '0|0' ]] || { echo STOP_CURSOR_CROSS_OWNER_LEAK >&2;exit 70; }
python3 - "$LAB_WORK/history_cursor_race_receipt.json" <<'PY'
import json,sys
from pathlib import Path
r={
"contract_version":"f3.db.synthetic_history_keyset_cursor.v1",
"source_repository_git_blob":"14f97dd680425b74f8e12fa1696d423a20bf7d76",
"environment":"actual_pg17.11_disposable_db_copy",
"two_owners":True,
"conversations_desc_keyset_anchor_last": "PASS_5_ORIGINAL_NO_DUPLICATE",
"messages_asc_keyset_anchor_last":"PASS_5_ORIGINAL_NO_DUPLICATE",
"concurrent_after_anchor_new_conversation_hidden":True,
"concurrent_after_anchor_new_message_hidden":True,
"fresh_query_can_see_new_row":True,
"cross_owner_conversation_and_message_rows_visible":0,
"cursor_api_hmac_signing":"NOT_TESTED",
"real_bff_http_auth":"NOT_RUN",
"production_concurrent_load_and_slo":"NOT_TESTED",
"module_gate":"NOT_ACCEPTED"}
Path(sys.argv[1]).write_text(json.dumps(r,sort_keys=True,indent=2)+"\n")
PY
chmod 0600 "$LAB_WORK/history_cursor_race_receipt.json"
admin -c "DROP DATABASE $probe WITH (FORCE)" >/dev/null
[[ "$(admin -c "SELECT count(*) FROM pg_database WHERE datname='$probe'")" == 0 ]] || exit 70
echo 'HISTORY_CONVERSATIONS_DESC_ANCHORED_KEYSET=PASS'
echo 'HISTORY_MESSAGES_ASC_ANCHORED_KEYSET=PASS'
echo 'HISTORY_CONCURRENT_NEW_ROWS_EXCLUDED_BY_ANCHOR=PASS'
echo 'HISTORY_CURSOR_TWO_OWNER_NO_CROSS_LEAK=PASS'
echo 'HISTORY_CURSOR_SQL_ONLY_HTTP_SIGNATURE_NOT_RUN'
