#!/usr/bin/env bash
# One fresh installation. Any interrupted migration remains STARTED and is NEVER auto-retried.
set -euo pipefail
source "$(dirname "$0")/_lib.sh"
require_lab_ready
secure_log
[[ "$(dbpsql -Atc 'SELECT current_database()')" == rag_finance_f3_lab ]] || { echo 'STOP_WRONG_DATABASE' >&2; exit 70; }
[[ "$(dbpsql -Atc 'SHOW server_version')" == 17.11* ]] || { echo 'STOP_PG17_11_REQUIRED' >&2; exit 70; }
[[ "$(dbpsql -Atc "SELECT count(*) FROM pg_catalog.pg_tables WHERE schemaname='db55_audit' AND tablename='migration_runs'")" == 1 ]] || { echo 'STOP_LEDGER_ABSENT' >&2; exit 70; }
( cd "$LAB_SOURCE" && shasum -a 256 -c SHA256SUMS >/dev/null ) || { echo 'STOP_SOURCE_MUTATED' >&2; exit 70; }
[[ "$(grep -c $'\tUP\t' "$LAB_SOURCE/manifest.tsv")" == 10 ]] || { echo 'STOP_NOT_TEN_UP_MIGRATIONS' >&2; exit 70; }
count="$(dbpsql -Atc 'SELECT count(*) FROM db55_audit.migration_runs')"
if [[ "$count" == 10 ]]; then
  # Strict idempotence: matching text in a Ledger is NOT proof that any SQL
  # was actually installed. Check exact 10 pins, SHA256, PG cluster identity,
  # completion transaction, and real physical tables/RLS/functions FIRST.
  cluster_id="$(dbpsql -Atc 'SELECT system_identifier FROM pg_control_system()')"
  expected="$(
    while IFS=$'\t' read -r ver direction commit path blob; do
      [[ "$direction" == UP ]] || continue
      sql="$LAB_SOURCE/$(basename "$path")"
      sha="$(shasum -a 256 "$sql" | awk '{print $1}')"
      printf '%s|%s|%s|%s|APPLIED|%s\n' "$ver" "$commit" "$blob" "$sha" "$cluster_id"
    done < <(tail -n +2 "$LAB_SOURCE/manifest.tsv")
  )"
  actual="$(dbpsql -Atc "SELECT trim(version)||'|'||trim(source_commit)||'|'||
    trim(git_blob_sha1)||'|'||trim(sql_sha256)||'|'||status||'|'||cluster_system_id
    FROM db55_audit.migration_runs ORDER BY version")"
  [[ "$expected" == "$actual" ]] || { echo STOP_EXISTING_LEDGER_SOURCE_CLUSTER_OR_DIGEST_DRIFT >&2; exit 70; }
  [[ "$(dbpsql -Atc "SELECT count(*) FROM db55_audit.migration_runs
      WHERE status='APPLIED' AND applied_at IS NOT NULL AND
      applied_at>=started_at AND applied_txid IS NOT NULL")" == 10 ]] || {
    echo STOP_EXISTING_LEDGER_NOT_COMMITTED >&2;exit 70;
  }
  physical="$(dbpsql -Atc "SELECT
    (SELECT count(*) FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
      WHERE n.nspname IN ('auth_l1','history_l1') AND c.relkind IN ('r','p'))=14
    AND (SELECT count(*) FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
      WHERE n.nspname IN ('auth_l1','history_l1') AND c.relkind IN ('r','p')
        AND c.relrowsecurity AND c.relforcerowsecurity)=14
    AND (SELECT count(*) FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace
      WHERE n.nspname IN ('auth_l1','history_l1'))>=30
    AND to_regclass('auth_l1.initial_login_attempts') IS NOT NULL
    AND to_regclass('history_l1.send_receipts') IS NOT NULL")"
  [[ "$physical" == t ]] || { echo STOP_EXISTING_LEDGER_WITH_SCHEMA_DRIFT_OR_MISSING_SQL >&2; exit 70; }
  echo 'MIGRATIONS=ALREADY_APPLIED_EXACT_PINS_NO_RERUN'
  exit 0
fi
[[ "$count" == 0 ]] || { echo 'STOP_PARTIAL_LEDGER_MANUAL_RECONCILIATION' >&2; exit 70; }
[[ "$(dbpsql -Atc "SELECT count(*) FROM pg_namespace WHERE nspname IN ('history_l1','auth_l1')")" == 0 ]] || { echo 'STOP_PREEXISTING_SCHEMA_NO_RERUN' >&2; exit 70; }
while IFS=$'\t' read -r ver direction commit path blob <&3; do
  [[ "$direction" == 'UP' ]] || continue
  file="${path##*/}"
  sql="$LAB_SOURCE/$file"
  [[ "$file" != 011* && -s "$sql" ]] || { echo 'STOP_MISSING_OR_011_SQL' >&2; exit 70; }
  [[ "$(git hash-object "$sql")" == "$blob" ]] || { echo "STOP_BLOB_MISMATCH_$ver" >&2; exit 70; }
  sha256="$(shasum -a 256 "$sql" | awk '{print $1}')"
  role=auth_migrator
  if [[ "$ver" == '001' || "$ver" == '002' ]]; then role=history_migrator; fi
  # Commit the durable STARTED intent BEFORE running each migration. Transactional or
  # crash ambiguity cannot be auto-replayed; snapshots must be discarded/reconciled.
  printf "INSERT INTO db55_audit.migration_runs(version,source_commit,git_blob_sha1,sql_sha256,status,cluster_system_id) VALUES('%s','%s','%s','%s','STARTED',(SELECT system_identifier::text FROM pg_control_system()));\n" \
    "$ver" "$commit" "$blob" "$sha256" | dbpsql >/dev/null
  if ! dbpsql -c "SET ROLE $role" -f "/run/source/$file" > "$LAB_WORK/migration_$ver.log" 2>&1; then
    echo "STOP_MIGRATION_${ver}_FAILED_INTENT_RECORDED_NO_AUTORETRY" >&2
    exit 70
  fi
  dbpsql <<SQL
UPDATE db55_audit.migration_runs
SET status='APPLIED', applied_at=clock_timestamp(), applied_txid=txid_current()
WHERE version='$ver' AND status='STARTED' AND git_blob_sha1='$blob';
SQL
  echo "MIGRATION_${ver}=APPLIED_PINNED"
done 3< <(tail -n +2 "$LAB_SOURCE/manifest.tsv")
[[ "$(dbpsql -Atc "SELECT count(*) FROM db55_audit.migration_runs WHERE status='APPLIED'")" == 10 ]] || { echo 'STOP_NOT_TEN_APPLIED' >&2; exit 70; }
[[ "$(dbpsql -Atc "SELECT count(*) FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace WHERE n.nspname='history_l1' OR n.nspname='auth_l1'")" -ge 1 ]] || { echo 'STOP_MISSING_FUNCTIONS' >&2; exit 70; }
echo 'F3_LAB_MIGRATIONS_001_010_APPLIED=PASS'
