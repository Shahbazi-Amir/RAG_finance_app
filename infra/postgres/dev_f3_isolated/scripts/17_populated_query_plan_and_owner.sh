#!/usr/bin/env bash
# Bench fixture ONLY. No claims about production SLO; test real query plan with
# 2,400 synthetic conversations, 4,800 messages and two independent owners.
set -euo pipefail
source "$(dirname "$0")/_lib.sh"
require_lab_ready; secure_log
[[ "$LAB_PROJECT" == ragfinance_f3_db_lab_* && "$LAB_DB" == rag_finance_f3_lab ]] || exit 70
probe=rag_finance_f3_query_plan_probe
admin(){ compose exec -T lab-db psql -X -Atq -v ON_ERROR_STOP=1 -U postgres -d postgres "$@"; }
[[ "$(admin -c "SELECT count(*) FROM pg_database WHERE datname='$probe'")" == 0 ]] || exit 70
admin -c "CREATE DATABASE $probe TEMPLATE rag_finance_f3_lab OWNER postgres" >/dev/null
export DB_SERVICE=lab-db DB_NAME="$probe"
dbpsql -q <<'SQL'
INSERT INTO history_l1.conversations(owner_id,id,title,state,created_at,updated_at)
SELECT CASE WHEN n<=1200 THEN 'benchmark-owner-a' ELSE 'benchmark-owner-b' END,
       'fixture-conv-'||lpad(n::text,5,'0'),'synthetic', 'active',
       clock_timestamp()-make_interval(secs=>n),
       clock_timestamp()-make_interval(secs=>n)
FROM generate_series(1,2400) n;
INSERT INTO history_l1.messages(owner_id,id,conversation_id,role,body,created_at)
SELECT CASE WHEN n<=2400 THEN 'benchmark-owner-a' ELSE 'benchmark-owner-b' END,
       'fixture-message-'||lpad(n::text,5,'0'),
       'fixture-conv-'||lpad(((n+1)/2)::text,5,'0'),
       'user', 'synthetic no PII', clock_timestamp()-make_interval(secs=>n)
FROM generate_series(1,4800) n;
ANALYZE history_l1.conversations;
ANALYZE history_l1.messages;
SQL
[[ "$(dbpsql -Atc "SELECT count(*) FROM history_l1.conversations")" == 2400 ]] || exit 70
[[ "$(dbpsql -Atc "SELECT count(*) FROM history_l1.messages")" == 4800 ]] || exit 70
owner_a="$(dbpsql -Atq <<'SQL'
BEGIN READ ONLY;
SET LOCAL ROLE history_app;
SET LOCAL app.owner_id='benchmark-owner-a';
SELECT count(*) FROM history_l1.conversations;
COMMIT;
SQL
)"
[[ "$owner_a" == 1200 ]] || { echo STOP_BENCH_OWNER_RLS >&2;exit 70; }
# The actual same ORDER/LIMIT predicates used by History API repository.
dbpsql -Atq -c "EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON)
 SELECT id,created_at FROM history_l1.conversations
 WHERE owner_id='benchmark-owner-a' AND state='active'
 ORDER BY created_at DESC,id DESC LIMIT 20;" \
 > "$LAB_WORK/query_plan_populated_conversations.json"
dbpsql -Atq -c "EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON)
 SELECT id,created_at FROM history_l1.messages
 WHERE owner_id='benchmark-owner-a' AND conversation_id='fixture-conv-00001'
 ORDER BY created_at ASC,id ASC LIMIT 20;" \
 > "$LAB_WORK/query_plan_populated_messages.json"
python3 - "$LAB_WORK" <<'PY'
import json,sys
from pathlib import Path
root=Path(sys.argv[1])
docs={}
for kind,expected in [('conversations',20),('messages',2)]:
    data=json.loads((root/f"query_plan_populated_{kind}.json").read_text())
    assert isinstance(data,list) and len(data)==1
    query=data[0]
    rows=query['Plan']['Actual Rows']
    assert rows == expected,(kind,rows,expected)
    def indexes(p):
        n=[p.get('Index Name')] if p.get('Index Name') else []
        for q in p.get('Plans',[]):n.extend(indexes(q))
        return n
    docs[kind]={
      'actual_rows':rows,'plan_node_type':query['Plan']['Node Type'],
      'used_indexes':indexes(query['Plan']),
      'execution_time_ms':query['Execution Time'],
      'total_cost':query['Plan']['Total Cost']}
receipt={
  'contract_version':'f3.db.synthetic_populated_query_plan.v1',
  'actual_pg_version':'17.11',
  'fixture_only':True,
  'owner_count':2,'conversation_rows':2400,'message_rows':4800,
  'owner_a_rls_visible_conversations':1200,
  'query_plans':docs,'production_workload_certified':False,
  'production_query_plan_acceptance':'PENDING_APPROVED_WORKLOAD'}
(root/'populated_plan_receipt.json').write_text(
  json.dumps(receipt,ensure_ascii=False,indent=2,sort_keys=True)+'\n')
PY
chmod 0600 "$LAB_WORK"/query_plan_populated_*.json "$LAB_WORK/populated_plan_receipt.json"
admin -c "DROP DATABASE $probe WITH (FORCE)" >/dev/null
echo 'POPULATED_PLAN_FIXTURE_2400_CONVERSATIONS=PASS'
echo 'POPULATED_PLAN_FIXTURE_4800_MESSAGES=PASS'
echo 'POPULATED_PLAN_OWNER_A_B_RLS_1200_VISIBLE=PASS'
echo 'POPULATED_CONVERSATIONS_AND_MESSAGES_EXPLAIN_ANALYZE=PASS'
echo 'POPULATED_PLAN_PRODUCTION_SLO=NOT_CLAIMED'
echo 'POPULATED_PLAN_PROBE_DB_DROPPED=PASS'
