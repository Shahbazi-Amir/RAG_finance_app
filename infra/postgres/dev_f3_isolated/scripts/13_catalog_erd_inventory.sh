#!/usr/bin/env bash
# Read-only PostgreSQL catalog inventory for physical ERD, data dictionary,
# constraints, indexes, owner scope and reproducible small-data EXPLAIN.
# No data or credentials in artifacts. Never claims real-scale plan acceptance.
set -euo pipefail
source "$(dirname "$0")/_lib.sh"
require_lab_ready
secure_log
[[ "$(dbpsql -Atc 'SELECT current_database()')" == rag_finance_f3_lab ]] || { echo STOP_NOT_LAB_DATABASE >&2;exit 70; }
[[ "$(dbpsql -Atc "SELECT count(*) FROM db55_audit.migration_runs WHERE status='APPLIED'")" == 10 ]] || exit 70
[[ "$(dbpsql -Atc 'SHOW server_version')" == 17.11* ]] || exit 70
tables="$(dbpsql -Atc "SELECT count(*) FROM pg_catalog.pg_class c JOIN pg_catalog.pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname IN('auth_l1','history_l1') AND c.relkind IN ('r','p')")"
[[ "$tables" == 14 ]] || { echo "STOP_ACTIVE_DATA_TABLE_DRIFT:$tables" >&2;exit 70; }
forced="$(dbpsql -Atc "SELECT count(*) FROM pg_catalog.pg_class c JOIN pg_catalog.pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname IN('auth_l1','history_l1') AND c.relkind IN ('r','p') AND c.relrowsecurity AND c.relforcerowsecurity")"
[[ "$forced" == "$tables" ]] || { echo "STOP_NON_FORCE_RLS_DATA_TABLE:$forced/$tables" >&2;exit 70; }
indexes="$(dbpsql -Atc "SELECT count(*) FROM pg_indexes WHERE schemaname IN ('auth_l1','history_l1')")"
[[ "$indexes" -gt 0 ]] || { echo STOP_NO_INDEXES >&2; exit 70; }
fks="$(dbpsql -Atc "SELECT count(*) FROM pg_constraint co JOIN pg_class c ON c.oid=co.conrelid JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname IN('auth_l1','history_l1') AND co.contype='f'")"
[[ "$fks" -ge 4 ]] || { echo "STOP_FK_COVERAGE_MISSING:$fks" >&2;exit 70; }
for index in conversation_order_idx message_order_idx one_attempt_per_send_receipt; do
  [[ "$(dbpsql -Atc "SELECT count(*) FROM pg_indexes WHERE schemaname='history_l1' AND indexname='$index'")" == 1 ]] || { echo "STOP_EXPECTED_CURSOR_UNIQUE_INDEX_$index" >&2;exit 70; }
done
# A one-line JSON document per table; no rows from application tables are read.
dbpsql -Atq <<'SQL' > "$LAB_WORK/physical_erd_data_dictionary.jsonl"
BEGIN READ ONLY;
SELECT row_to_json(info)
FROM (
  SELECT
    n.nspname AS schema_name,
    c.relname AS table_name,
    pg_get_userbyid(c.relowner) AS owner_role,
    c.relrowsecurity AS row_level_security,
    c.relforcerowsecurity AS force_row_level_security,
    (SELECT jsonb_agg(jsonb_build_object('name',a.attname,
                  'type',format_type(a.atttypid,a.atttypmod),
                  'not_null',a.attnotnull) ORDER BY a.attnum)
       FROM pg_attribute a WHERE a.attrelid=c.oid
         AND a.attnum>0 AND NOT a.attisdropped) AS columns,
    (SELECT COALESCE(jsonb_agg(jsonb_build_object('name',z.conname,
                 'type',z.contype,'definition',pg_get_constraintdef(z.oid)) ORDER BY z.conname),'[]'::jsonb)
       FROM pg_constraint z WHERE z.conrelid=c.oid) AS constraints,
    (SELECT COALESCE(jsonb_agg(jsonb_build_object('name',i.indexname,
                 'definition',i.indexdef) ORDER BY i.indexname),'[]'::jsonb)
       FROM pg_indexes i WHERE i.schemaname=n.nspname AND i.tablename=c.relname) AS indexes,
    (SELECT COALESCE(jsonb_agg(jsonb_build_object('name',p.policyname,
                  'operation',p.cmd,'roles',p.roles,
                  'using',p.qual,'with_check',p.with_check) ORDER BY p.policyname),'[]'::jsonb)
       FROM pg_policies p WHERE p.schemaname=n.nspname AND p.tablename=c.relname) AS policies
  FROM pg_class c
  JOIN pg_namespace n ON n.oid=c.relnamespace
  WHERE n.nspname IN ('auth_l1','history_l1') AND c.relkind IN ('r','p')
  ORDER BY n.nspname,c.relname
) AS info;
COMMIT;
SQL
[[ "$(grep -c '^{' "$LAB_WORK/physical_erd_data_dictionary.jsonl")" == 14 ]] || { echo STOP_INVENTORY_ROWS >&2;exit 70; }
# EXPLAIN-only: empty fixture cannot prove actual production latency or scan efficiency.
dbpsql -Atq <<'SQL' > "$LAB_WORK/query_plan_empty_fixture.txt"
BEGIN READ ONLY;
EXPLAIN (FORMAT JSON)
SELECT id,created_at FROM history_l1.conversations
 WHERE owner_id='synthetic-owner-a' AND state='active'
 ORDER BY created_at DESC,id DESC LIMIT 20;
EXPLAIN (FORMAT JSON)
SELECT id,created_at FROM history_l1.messages
 WHERE owner_id='synthetic-owner-a' AND conversation_id='synthetic-conv-a'
 ORDER BY created_at ASC,id ASC LIMIT 20;
COMMIT;
SQL
[[ -s "$LAB_WORK/query_plan_empty_fixture.txt" ]] || exit 70
shasum -a 256 "$LAB_WORK/physical_erd_data_dictionary.jsonl" \
 "$LAB_WORK/query_plan_empty_fixture.txt" > "$LAB_WORK/catalog_snapshot_sha256.txt"
echo 'SCHEMA_14_TABLES_CATALOG_SNAPSHOT=PASS'
echo "SCHEMA_14_TABLES_FORCE_RLS=14/14_PASS"
echo "SCHEMA_FOREIGN_KEY_COUNT=$fks"
echo "SCHEMA_INDEX_COUNT=$indexes"
echo 'SCHEMA_THREE_HISTORY_CURSOR_UNIQUE_INDEXES=PASS'
echo 'SCHEMA_EXPLAIN_EMPTY_FIXTURE=RECORDED_NOT_PRODUCTION_PLAN_PASS'
