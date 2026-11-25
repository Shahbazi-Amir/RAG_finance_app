#!/usr/bin/env bash
# Shared journey SQL oracle. Only the existing disposable PG17.11 lab.
# Never use on target/demo. Owner IDs are obtained from auth_l1 identity mapping,
# not injected into Web/BFF or inferred from browser headers.
set -euo pipefail
source "$(dirname "$0")/_lib.sh"
require_lab_ready; secure_log
stage="${1:?seed|before|after-refresh|after-send|after-restore}"
case "$stage" in seed|before|after-refresh|after-send|after-restore) ;; *) exit 64;; esac
: "${SOURCE_REPO:?checkout required}"
sha="$(git -C "$SOURCE_REPO" rev-parse HEAD)"
[[ "$sha" =~ ^[a-f0-9]{40}$ ]] || exit 70
[[ -z "$(git -C "$SOURCE_REPO" status --porcelain --untracked-files=no)" ]] || { echo STOP_DIRTY_SOURCE; exit 70; }
svc=lab-db; db=rag_finance_f3_lab; host=demo-db
if [[ "$stage" == after-restore ]]; then
  svc=restore-db; db=rag_finance_f3_lab_restore; host=restore-db
  [[ -f "$LAB_WORK/restore-tested.marker" && -s "$LAB_WORK/backup.dump.sha256" ]] || exit 70
  shasum -a 256 -c "$LAB_WORK/backup.dump.sha256" >/dev/null
fi
admin(){ DB_SERVICE="$svc" DB_NAME="$db" dbpsql -Atq "$@"; }
[[ "$(admin -c 'SELECT current_database()')" == "$db" ]] || exit 70
[[ "$(admin -c 'SHOW server_version_num')" == 170011 ]] || exit 70
[[ "$(admin -c "SELECT string_agg(version,',' ORDER BY version) FROM db55_audit.migration_runs WHERE status='APPLIED'")" == 001,002,003,004,005,006,007,008,009,010 ]] || exit 70
[[ "$(admin -c "SELECT count(*) FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname IN ('auth_l1','history_l1') AND c.relkind='r' AND c.relrowsecurity AND c.relforcerowsecurity")" == 14 ]] || exit 70
[[ "$(admin -c "SELECT count(*) FROM pg_roles WHERE rolname='history_app' AND NOT (rolsuper OR rolbypassrls OR rolinherit OR rolcreatedb OR rolcreaterole)")" == 1 ]] || exit 70
[[ "$(admin -c "SELECT status FROM db55_audit.bridge_runs WHERE id=1")" == APPLIED ]] || exit 70
# Passwords stay in a private lab-only passfile; no DSN secrets in CLI/log/receipt.
passfile="$LAB_WORK/journey-$svc.pgpass"
for role in history_app auth_mapper; do
  [[ -s "$LAB_WORK/$role.password" ]] || exit 70
done
[[ ! -L "$passfile" ]] || exit 70
: > "$passfile"; chmod 0600 "$passfile"
for role in history_app auth_mapper; do
  printf '%s:5432:%s:%s:%s\n' "$host" "$db" "$role" "$(cat "$LAB_WORK/$role.password")" >> "$passfile"
done
trap 'rm -f -- "$passfile"' EXIT
role_sql(){
  local role="$1"; shift
  compose exec -T -u root "$svc" psql -X -Atq -v ON_ERROR_STOP=1 \
    "host=$host port=5432 dbname=$db user=$role sslmode=verify-full sslrootcert=/run/lab_secrets/ca.crt passfile=/run/work/$(basename "$passfile")" "$@"
}
[[ "$(role_sql history_app -c "SELECT current_user||'|'||ssl::text FROM pg_stat_ssl WHERE pid=pg_backend_pid()")" == history_app\|true ]] || exit 70
identity="$LAB_WORK/journey-identities.tsv"
# This is private input, never an artifact. In shared mode Foundation passes
# issuer + subjects observed by trusted OIDC callback. In SQL-only CI use
# explicit synthetic subjects and actual auth_mapper; never claim real IdP.
if [[ "$stage" == seed ]]; then
  [[ ! -e "$identity" && ! -e "$LAB_WORK/journey-before.json" ]] || exit 70
  mode="${JOURNEY_IDENTITY_MODE:?verified-idp or sql-only-ci}"
  if [[ "$mode" == sql-only-ci ]]; then
    [[ "${CI:-}" == true && "${GITHUB_ACTIONS:-}" == true ]] || exit 70
    issuer='https://synthetic.invalid/f3-shared-journey'
    sub_a='sql-only-A'; sub_b='sql-only-B'
    for sub in "$sub_a" "$sub_b"; do
      role_sql auth_mapper -v issuer="$issuer" -v sub="$sub" <<'SQL' >/dev/null
SELECT auth_l1.map_identity(:'issuer',:'sub');
SQL
    done
  elif [[ "$mode" == verified-idp ]]; then
    : "${JOURNEY_ISSUER:?trusted callback issuer}" "${JOURNEY_SUB_A:?trusted callback A}" "${JOURNEY_SUB_B:?trusted callback B}"
    issuer="$JOURNEY_ISSUER"; sub_a="$JOURNEY_SUB_A"; sub_b="$JOURNEY_SUB_B"
  else exit 64; fi
  [[ "$sub_a" != "$sub_b" ]] || exit 70
  for value in "$issuer" "$sub_a" "$sub_b"; do
    [[ "$value" != *$'\n'* && "$value" != *$'\r'* && "$value" != *$'\t'* && -n "$value" ]] || exit 70
  done
  printf '%s\t%s\t%s\t%s\n' "$mode" "$issuer" "$sub_a" "$sub_b" > "$identity"
  chmod 0600 "$identity"
fi
[[ -f "$identity" && ! -L "$identity" ]] || exit 70
IFS=$'\t' read -r mode issuer sub_a sub_b < "$identity"
lookup(){
  admin -v issuer="$issuer" -v sub="$1" <<'SQL'
SELECT l.owner_id FROM auth_l1.identity_links l JOIN auth_l1.owners o USING(owner_id)
WHERE l.issuer=:'issuer' AND l.subject=:'sub' AND o.state='active';
SQL
}
a="$(lookup "$sub_a")"; b="$(lookup "$sub_b")"
[[ "$a" =~ ^[a-f0-9-]{36}$ && "$b" =~ ^[a-f0-9-]{36}$ && "$a" != "$b" ]] || { echo STOP_IDENTITY_MAPPING; exit 70; }
mapping_hash="$(printf '%s\n%s\n' "$a" "$b" | shasum -a 256 | awk '{print $1}')"
cluster="$(admin -c 'SELECT system_identifier FROM pg_control_system()')"
[[ "$cluster" =~ ^[0-9]+$ ]] || exit 70
if [[ "$stage" == seed ]]; then
  # Only seed empty History; no pre-existing data or receipt is overwritten.
  [[ "$(admin -c "SELECT (SELECT count(*) FROM history_l1.conversations)+(SELECT count(*) FROM history_l1.messages)+(SELECT count(*) FROM history_l1.create_receipts)+(SELECT count(*) FROM history_l1.send_receipts)+(SELECT count(*) FROM history_l1.execution_attempts)+(SELECT count(*) FROM history_l1.answers)")" == 0 ]] || { echo STOP_NOT_EMPTY_HISTORY; exit 70; }
  role_sql history_app -v a="$a" -v b="$b" <<'SQL' >/dev/null
BEGIN;
\set owner :a
\set label a
SELECT set_config('app.owner_id',:'owner',true) AS scope \gset
INSERT INTO history_l1.conversations(owner_id,id,title,state,created_at,updated_at)
SELECT :'owner', :'label'||'0000000-0000-4000-8000-00000000000'||n,
       'journey-'||:'label'||'-'||n, 'active',
       '2026-01-01T00:00:00Z'::timestamptz+make_interval(secs=>CASE WHEN n=1 THEN 1 ELSE 2 END),
       '2026-01-01T00:00:00Z'::timestamptz+make_interval(secs=>CASE WHEN n=1 THEN 1 ELSE 2 END)
FROM generate_series(1,3) n;
INSERT INTO history_l1.messages(owner_id,id,conversation_id,role,body,created_at)
SELECT :'owner', :'label'||'1000000-0000-4000-8000-00000000000'||n,
       :'label'||'0000000-0000-4000-8000-000000000003','user','journey-'||:'label'||'-message-'||n,
       '2026-01-01T00:00:00Z'::timestamptz+make_interval(secs=>CASE WHEN n=1 THEN 1 ELSE 2 END)
FROM generate_series(1,3) n;
\set owner :b
\set label b
SELECT set_config('app.owner_id',:'owner',true) AS scope \gset
INSERT INTO history_l1.conversations(owner_id,id,title,state,created_at,updated_at)
SELECT :'owner', :'label'||'0000000-0000-4000-8000-00000000000'||n,
       'journey-'||:'label'||'-'||n, 'active',
       '2026-01-01T00:00:00Z'::timestamptz+make_interval(secs=>CASE WHEN n=1 THEN 1 ELSE 2 END),
       '2026-01-01T00:00:00Z'::timestamptz+make_interval(secs=>CASE WHEN n=1 THEN 1 ELSE 2 END)
FROM generate_series(1,3) n;
INSERT INTO history_l1.messages(owner_id,id,conversation_id,role,body,created_at)
SELECT :'owner', :'label'||'1000000-0000-4000-8000-00000000000'||n,
       :'label'||'0000000-0000-4000-8000-000000000003','user','journey-'||:'label'||'-message-'||n,
       '2026-01-01T00:00:00Z'::timestamptz+make_interval(secs=>CASE WHEN n=1 THEN 1 ELSE 2 END)
FROM generate_series(1,3) n;
COMMIT;
SQL
  printf '%s\n' "$mapping_hash" > "$LAB_WORK/journey-mapping.sha256"
  printf '%s\n' "$cluster" > "$LAB_WORK/journey-source-cluster"
  printf '%s\n' "$sha" > "$LAB_WORK/journey-source-sha"
  echo JOURNEY_SEED_SQL_COMMITTED_TWO_MAPPED_OWNERS
  exit 0
fi
[[ "$(cat "$LAB_WORK/journey-mapping.sha256")" == "$mapping_hash" && "$(cat "$LAB_WORK/journey-source-sha")" == "$sha" ]] || exit 70
if [[ "$stage" == after-restore ]]; then
  [[ "$(cat "$LAB_WORK/journey-source-cluster")" != "$cluster" ]] || exit 70
else
  [[ "$(cat "$LAB_WORK/journey-source-cluster")" == "$cluster" ]] || exit 70
fi
out="$LAB_WORK/journey-$stage.json"
[[ ! -e "$out" ]] || exit 70
# Global counts independently catch unexpected writes even to a third owner.
# Never return actual rows from the privileged connection.
global_counts="$(admin -c "SELECT json_build_array((SELECT count(*) FROM history_l1.conversations),(SELECT count(*) FROM history_l1.messages),(SELECT count(*) FROM history_l1.create_receipts),(SELECT count(*) FROM history_l1.send_receipts),(SELECT count(*) FROM history_l1.execution_attempts),(SELECT count(*) FROM history_l1.answers))")"
[[ "$(printf '%s' "$global_counts" | tr -d ' ')" == '[6,6,0,0,0,0]' ]] || { echo STOP_UNEXPECTED_GLOBAL_HISTORY_WRITE; exit 70; }
for label in a b; do
  owner="$a"; foreign=b
  if [[ "$label" == b ]]; then owner="$b"; foreign=a; fi
  role_sql history_app -v owner="$owner" -v label="$label" -v foreign="$foreign" <<'SQL' > "$LAB_WORK/journey-$stage-$label.private"
BEGIN ISOLATION LEVEL REPEATABLE READ READ ONLY;
SET LOCAL TIME ZONE 'UTC';
SELECT set_config('app.owner_id',:'owner',true) AS scope \gset
WITH first_page AS (
 SELECT id,title,created_at FROM history_l1.conversations WHERE state='active'
 ORDER BY created_at DESC,id DESC LIMIT 2
), last_key AS (SELECT created_at,id FROM first_page ORDER BY created_at,id LIMIT 1),
second_page AS (
 SELECT c.id,c.title FROM history_l1.conversations c,last_key k
 WHERE c.state='active' AND (c.created_at,c.id)<(k.created_at,k.id)
 ORDER BY c.created_at DESC,c.id DESC LIMIT 2
)
SELECT jsonb_build_object(
 'list',(SELECT jsonb_agg(jsonb_build_array(id,title) ORDER BY created_at DESC,id DESC) FROM history_l1.conversations WHERE state='active'),
 'page1',(SELECT jsonb_agg(id ORDER BY created_at DESC,id DESC) FROM first_page),
 'page2',(SELECT jsonb_agg(id ORDER BY id DESC) FROM second_page),
 'detail',(SELECT jsonb_agg(jsonb_build_array(id,body,role) ORDER BY created_at,id) FROM history_l1.messages WHERE conversation_id=:'label'||'0000000-0000-4000-8000-000000000003'),
 'counts',jsonb_build_array((SELECT count(*) FROM history_l1.conversations),(SELECT count(*) FROM history_l1.messages),(SELECT count(*) FROM history_l1.create_receipts),(SELECT count(*) FROM history_l1.send_receipts),(SELECT count(*) FROM history_l1.execution_attempts),(SELECT count(*) FROM history_l1.answers)),
 'foreign',jsonb_build_array((SELECT count(*) FROM history_l1.conversations WHERE id=:'foreign'||'0000000-0000-4000-8000-000000000003'),(SELECT count(*) FROM history_l1.messages WHERE conversation_id=:'foreign'||'0000000-0000-4000-8000-000000000003')));
COMMIT;
BEGIN READ ONLY;
SELECT jsonb_build_array((SELECT count(*) FROM history_l1.conversations),(SELECT count(*) FROM history_l1.messages));
COMMIT;
SQL
done
# No user IDs, tokens, DSNs or raw logs in receipts. Validate exact synthetic
# data and absence of foreign rows before writing any public-safe JSON.
python3 -B "$BUNDLE_ROOT/scripts/journey_receipt.py" "$LAB_WORK" "$stage" "$mode" "$sha"
