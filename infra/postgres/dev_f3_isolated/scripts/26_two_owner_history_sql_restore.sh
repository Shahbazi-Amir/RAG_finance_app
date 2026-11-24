#!/usr/bin/env bash
# DB-only: two SYNTHETIC subjects, TLS history_app list/detail/keyset RLS,
# before/after logical restore to a separate disposable PG17.11 cluster.
# An owner GUC is NOT a validated OIDC identity. No HTTP, engine or 011.
set -euo pipefail
source "$(dirname "$0")/_lib.sh"
require_lab_ready; secure_log
[[ "$LAB_PROJECT" == ragfinance_f3_db_lab_* && "$LAB_DB" == rag_finance_f3_lab ]] || exit 70
[[ -s "$LAB_WORK/restore_receipt.txt" && -f "$LAB_WORK/restore-tested.marker" ]] || { echo STOP_RESTORE_CLUSTER_NOT_READY >&2; exit 70; }
[[ "$(dbpsql -Atc "SELECT count(*) FROM db55_audit.migration_runs WHERE status='APPLIED'")" == 10 ]] || exit 70
src=rag_finance_f3_ab_history_source
dst=rag_finance_f3_ab_history_restored
admin(){ local svc="$1"; shift; DB_SERVICE="$svc" DB_NAME=postgres dbpsql -Atq "$@"; }
[[ "$(admin lab-db -c "SELECT count(*) FROM pg_database WHERE datname='$src'")" == 0 ]] || exit 70
[[ "$(admin restore-db -c "SELECT count(*) FROM pg_database WHERE datname='$dst'")" == 0 ]] || exit 70
[[ ! -e "$LAB_WORK/ab_history_before.txt" && ! -e "$LAB_WORK/ab_history_source.dump" ]] || exit 70
admin lab-db -c "CREATE DATABASE $src TEMPLATE rag_finance_f3_lab OWNER postgres" >/dev/null
admin lab-db -c "REVOKE CONNECT,TEMP ON DATABASE $src FROM PUBLIC" >/dev/null
admin lab-db -c "GRANT CONNECT ON DATABASE $src TO history_app" >/dev/null
export DB_SERVICE=lab-db DB_NAME="$src"
[[ "$(dbpsql -Atc "SELECT count(*) FROM history_l1.conversations")" == 0 ]] || exit 70
# Fixture-only superuser seed; all assertions below use real restricted LOGIN.
dbpsql -q <<'SQL'
INSERT INTO history_l1.conversations(owner_id,id,title,state,created_at,updated_at)
SELECT 'ci-subject-a-unverified','ab-a-'||n,'synthetic A','active',
'2026-01-01 00:00:00+00'::timestamptz+make_interval(secs=>n),
'2026-01-01 00:00:00+00'::timestamptz+make_interval(secs=>n)
FROM generate_series(1,5) n;
INSERT INTO history_l1.conversations(owner_id,id,title,state,created_at,updated_at)
SELECT 'ci-subject-b-unverified','ab-b-'||n,'synthetic B','active',
'2026-01-01 00:00:00+00'::timestamptz+make_interval(secs=>n),
'2026-01-01 00:00:00+00'::timestamptz+make_interval(secs=>n)
FROM generate_series(1,3) n;
INSERT INTO history_l1.messages(owner_id,id,conversation_id,role,body,created_at)
SELECT 'ci-subject-a-unverified','ab-a-msg-'||n,'ab-a-1','user','synthetic A',
'2026-01-01 00:00:00+00'::timestamptz+make_interval(secs=>n)
FROM generate_series(1,4) n;
INSERT INTO history_l1.messages(owner_id,id,conversation_id,role,body,created_at)
SELECT 'ci-subject-b-unverified','ab-b-msg-'||n,'ab-b-1','user','synthetic B',
'2026-01-01 00:00:00+00'::timestamptz+make_interval(secs=>n)
FROM generate_series(1,2) n;
SQL
[[ -s "$LAB_WORK/history_app.password" ]] || exit 70
{
 printf 'demo-db:5432:%s:history_app:%s\n' "$src" "$(cat "$LAB_WORK/history_app.password")"
 printf 'restore-db:5432:%s:history_app:%s\n' "$dst" "$(cat "$LAB_WORK/history_app.password")"
} > "$LAB_WORK/ab_history.pgpass"
chmod 0600 "$LAB_WORK/ab_history.pgpass"
# Real SCRAM authentication + TLS verify-full SAN, never SET ROLE postgres.
role_sql(){
 local svc="$1" host="$2" db="$3" owner="$4" sql="$5"
 {
  printf 'BEGIN READ ONLY;\n'
  if [[ "$owner" != UNSET ]]; then printf "SET LOCAL app.owner_id='%s';\n" "$owner"; fi
  printf '%s\nCOMMIT;\n' "$sql"
 } | compose exec -T "$svc" env PGPASSFILE=/run/work/ab_history.pgpass \
   PGSSLMODE=verify-full PGSSLROOTCERT=/run/lab_secrets/ca.crt \
   psql -X -Atq -v ON_ERROR_STOP=1 -h "$host" -p 5432 -U history_app -d "$db"
}
check(){
 local svc="$1" host="$2" db="$3" owner="$4" sql="$5" want="$6" label="$7"
 local got; got="$(role_sql "$svc" "$host" "$db" "$owner" "$sql")"
 [[ "$got" == "$want" ]] || { echo "STOP_SQL_ASSERT:$label" >&2;exit 70; }
 printf '%s=%s\n' "$label" "$got"
}
snapshot(){
 local svc="$1" host="$2" db="$3" stage="$4" out="$5"
 {
  check "$svc" "$host" "$db" ci-subject-a-unverified \
    "SELECT current_user||'|'||(SELECT ssl::text FROM pg_stat_ssl WHERE pid=pg_backend_pid());" 'history_app|true' tls_role
  check "$svc" "$host" "$db" ci-subject-a-unverified \
    "SELECT string_agg(id,',' ORDER BY created_at DESC,id DESC) FROM history_l1.conversations WHERE state='active';" 'ab-a-5,ab-a-4,ab-a-3,ab-a-2,ab-a-1' a_list
  check "$svc" "$host" "$db" ci-subject-b-unverified \
    "SELECT string_agg(id,',' ORDER BY created_at DESC,id DESC) FROM history_l1.conversations WHERE state='active';" 'ab-b-3,ab-b-2,ab-b-1' b_list
  check "$svc" "$host" "$db" ci-subject-a-unverified \
    "SELECT string_agg(id,',' ORDER BY created_at DESC,id DESC) FROM (SELECT id,created_at FROM history_l1.conversations WHERE state='active' ORDER BY created_at DESC,id DESC LIMIT 2) p;" 'ab-a-5,ab-a-4' a_page1
  check "$svc" "$host" "$db" ci-subject-a-unverified \
    "SELECT string_agg(id,',' ORDER BY created_at DESC,id DESC) FROM (SELECT id,created_at FROM history_l1.conversations WHERE state='active' AND (created_at,id)<('2026-01-01 00:00:04+00'::timestamptz,'ab-a-4') ORDER BY created_at DESC,id DESC LIMIT 2) p;" 'ab-a-3,ab-a-2' a_page2
  check "$svc" "$host" "$db" ci-subject-a-unverified \
    "SELECT string_agg(id,',' ORDER BY created_at DESC,id DESC) FROM (SELECT id,created_at FROM history_l1.conversations WHERE state='active' AND (created_at,id)<('2026-01-01 00:00:02+00'::timestamptz,'ab-a-2') ORDER BY created_at DESC,id DESC LIMIT 2) p;" 'ab-a-1' a_page3
  check "$svc" "$host" "$db" ci-subject-b-unverified \
    "SELECT string_agg(id,',' ORDER BY created_at DESC,id DESC) FROM (SELECT id,created_at FROM history_l1.conversations WHERE state='active' ORDER BY created_at DESC,id DESC LIMIT 2) p;" 'ab-b-3,ab-b-2' b_page1
  check "$svc" "$host" "$db" ci-subject-b-unverified \
    "SELECT string_agg(id,',' ORDER BY created_at DESC,id DESC) FROM (SELECT id,created_at FROM history_l1.conversations WHERE state='active' AND (created_at,id)<('2026-01-01 00:00:02+00'::timestamptz,'ab-b-2') ORDER BY created_at DESC,id DESC LIMIT 2) p;" 'ab-b-1' b_page2
  check "$svc" "$host" "$db" ci-subject-a-unverified "SELECT count(*) FROM history_l1.conversations WHERE id='ab-a-3';" 1 a_detail
  check "$svc" "$host" "$db" ci-subject-b-unverified "SELECT count(*) FROM history_l1.conversations WHERE id='ab-b-2';" 1 b_detail
  check "$svc" "$host" "$db" ci-subject-b-unverified "SELECT count(*) FROM history_l1.conversations WHERE id='ab-a-3';" 0 b_denied_a
  check "$svc" "$host" "$db" ci-subject-a-unverified "SELECT count(*) FROM history_l1.conversations WHERE id='ab-b-2';" 0 a_denied_b
  check "$svc" "$host" "$db" UNSET "SELECT count(*) FROM history_l1.conversations;" 0 no_owner
  check "$svc" "$host" "$db" ci-subject-a-unverified "SELECT count(*) FROM history_l1.messages WHERE conversation_id='ab-a-1';" 4 a_messages
  check "$svc" "$host" "$db" ci-subject-b-unverified "SELECT count(*) FROM history_l1.messages WHERE conversation_id='ab-b-1';" 2 b_messages
  check "$svc" "$host" "$db" ci-subject-b-unverified "SELECT count(*) FROM history_l1.messages WHERE conversation_id='ab-a-1';" 0 b_denied_a_msgs
  check "$svc" "$host" "$db" ci-subject-a-unverified "SELECT (SELECT count(*) FROM history_l1.send_receipts)||'|'||(SELECT count(*) FROM history_l1.execution_attempts)||'|'||(SELECT count(*) FROM history_l1.answers);" '0|0|0' a_no_send
  check "$svc" "$host" "$db" ci-subject-b-unverified "SELECT (SELECT count(*) FROM history_l1.send_receipts)||'|'||(SELECT count(*) FROM history_l1.execution_attempts)||'|'||(SELECT count(*) FROM history_l1.answers);" '0|0|0' b_no_send
 } > "$out"
 [[ "$(wc -l < "$out")" == 18 ]] || { echo "STOP_BAD_SNAPSHOT:$stage" >&2;exit 70; }
 echo "AB_HISTORY_$stage=18_SQL_ASSERTIONS_PASS"
}
snapshot lab-db demo-db "$src" BEFORE "$LAB_WORK/ab_history_before.txt"
dump="$LAB_WORK/ab_history_source.dump"
compose exec -T lab-db pg_dump -U postgres -d "$src" -Fc > "$dump"
[[ -s "$dump" ]] || exit 70
shasum -a 256 "$dump" > "$LAB_WORK/ab_history_source.dump.sha256"
chmod 0600 "$dump" "$LAB_WORK/ab_history_source.dump.sha256"
shasum -a 256 -c "$LAB_WORK/ab_history_source.dump.sha256" >/dev/null
admin restore-db -c "CREATE DATABASE $dst OWNER postgres" >/dev/null
admin restore-db -c "REVOKE CONNECT,TEMP ON DATABASE $dst FROM PUBLIC" >/dev/null
admin restore-db -c "GRANT CONNECT ON DATABASE $dst TO history_app" >/dev/null
compose exec -T restore-db pg_restore -U postgres -d "$dst" < "$dump" > "$LAB_WORK/ab_history_pg_restore.log" 2>&1 || { echo STOP_AB_PG_RESTORE >&2;exit 70; }
[[ "$(DB_SERVICE=restore-db DB_NAME="$dst" dbpsql -Atc "SELECT count(*) FROM db55_audit.migration_runs WHERE status='APPLIED'")" == 10 ]] || exit 70
snapshot restore-db restore-db "$dst" AFTER "$LAB_WORK/ab_history_after.txt"
cmp -s "$LAB_WORK/ab_history_before.txt" "$LAB_WORK/ab_history_after.txt" || { echo STOP_SQL_RESTORE_PARITY >&2;exit 70; }
src_id="$(DB_SERVICE=lab-db DB_NAME="$src" dbpsql -Atc 'SELECT system_identifier FROM pg_control_system()')"
dst_id="$(DB_SERVICE=restore-db DB_NAME="$dst" dbpsql -Atc 'SELECT system_identifier FROM pg_control_system()')"
[[ -n "$src_id" && -n "$dst_id" && "$src_id" != "$dst_id" ]] || exit 70
for svc in lab-db restore-db; do
 if [[ "$svc" == lab-db ]];then d="$src";else d="$dst";fi
 [[ "$(DB_SERVICE="$svc" DB_NAME="$d" dbpsql -Atc "SELECT count(*) FROM history_l1.conversations")" == 8 ]] || exit 70
 [[ "$(DB_SERVICE="$svc" DB_NAME="$d" dbpsql -Atc "SELECT count(*) FROM history_l1.messages")" == 6 ]] || exit 70
 [[ "$(DB_SERVICE="$svc" DB_NAME="$d" dbpsql -Atc "SELECT count(*) FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='history_l1' AND c.relkind='r' AND c.relrowsecurity AND c.relforcerowsecurity")" == 6 ]] || exit 70
done
export AB_DUMP_SHA="$(shasum -a 256 "$dump" | awk '{print $1}')"
export AB_SQL_SHA="$(shasum -a 256 "$LAB_WORK/ab_history_before.txt" | awk '{print $1}')"
export AB_RECEIPT="$LAB_WORK/ab_history_restore_receipt.json"
python3 - <<'PY'
import json,os
from pathlib import Path
r={
 "contract_version":"f3.db.two_owner_history_sql_restore.v1",
 "environment":"real_postgresql_17.11_disposable_ci_only",
 "subjects":"TWO_SYNTHETIC_NOT_AUTHENTICATED_BY_IDP",
 "role":"history_app","transport":"SCRAM_TLS_VERIFY_FULL_CA_SAN",
 "migrations":"001-010","migration_011":"NOT_RUN",
 "owners":2,"owner_a_conversations":5,"owner_b_conversations":3,
 "owner_a_messages":4,"owner_b_messages":2,
 "before_sql_assertions":18,"after_sql_assertions":18,
 "before_after_sql_snapshot_sha256":os.environ["AB_SQL_SHA"],
 "backup_sha256":os.environ["AB_DUMP_SHA"],
 "source_restore_independent_clusters":True,
 "source_restore_exact_sql_parity":True,
 "restored_history_force_rls_tables":6,
 "cross_owner_and_no_owner_denied":"PASS_BOTH_CLUSTERS",
 "no_send_rows_in_fixture":"PASS_BOTH_CLUSTERS",
 "signed_oidc_actor_same_transaction":"NOT_PROVEN",
 "real_http_history_refresh_send_revoke":"NOT_RUN",
 "production_rpo_rto":"NOT_DEFINED","module_gate":"NOT_ACCEPTED"}
Path(os.environ["AB_RECEIPT"]).write_text(json.dumps(r,sort_keys=True,indent=2)+"\n")
PY
chmod 0600 "$LAB_WORK/ab_history_restore_receipt.json"
mkdir -p "$GITHUB_WORKSPACE/ci_receipts"
install -m 0600 "$LAB_WORK/ab_history_restore_receipt.json" "$GITHUB_WORKSPACE/ci_receipts/ab_history_restore_receipt.json"
admin lab-db -c "DROP DATABASE $src WITH (FORCE)" >/dev/null
admin restore-db -c "DROP DATABASE $dst WITH (FORCE)" >/dev/null
[[ "$(admin lab-db -c "SELECT count(*) FROM pg_database WHERE datname='$src'")" == 0 ]] || exit 70
[[ "$(admin restore-db -c "SELECT count(*) FROM pg_database WHERE datname='$dst'")" == 0 ]] || exit 70
echo 'AB_HISTORY_BEFORE_AFTER_18_REAL_TLS_SERVICE_SQL_ASSERTIONS=PASS'
echo 'AB_HISTORY_A_B_DETAIL_KEYSET_CROSS_OWNER_RLS=PASS'
echo 'AB_HISTORY_INDEPENDENT_RESTORE_EXACT_PARITY=PASS'
echo 'AB_HISTORY_DISPOSABLE_CLONES_REMOVED=PASS'
echo 'AB_HISTORY_IDP_SIGNED_HTTP_NOT_RUN'
