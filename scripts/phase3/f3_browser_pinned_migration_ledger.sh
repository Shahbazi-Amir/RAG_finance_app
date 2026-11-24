#!/usr/bin/env bash
# Source this ONLY in the disposable browser CI install step. Mirrors the
# approved 03 installer's durable intent/APPLIED semantics for history_ci.
# This is NOT a DB55 bridge installation or a historical ledger repair.
[[ "${CI:-}" == true && "${GITHUB_ACTIONS:-}" == true && "${GITHUB_RUN_ID:-}" =~ ^[0-9]+$ ]] || return 70
[[ "${PGHOST:-}" == 127.0.0.1 && "${PGPORT:-}" == 5432 && "${AUTH_MIG_DSN:-}" == *dbname=history_ci* ]] || return 70
[[ -n "${PGPASSWORD:-}" && -n "${GITHUB_WORKSPACE:-}" ]] || return 70
F3_LEDGER_ADMIN_PASSWORD="$PGPASSWORD"
F3_LEDGER_MANIFEST="$GITHUB_WORKSPACE/infra/postgres/dev_f3_isolated/MIGRATIONS_001_010_PINNED.tsv"
F3_LEDGER_MANIFEST_SHA=9ff95a59570f5f6c6188479d9c37cf684ef836c599e89d9faa2bb0e17a4946f7
f3_ledger_admin() {
  PGUSER=postgres PGPASSWORD="$F3_LEDGER_ADMIN_PASSWORD" psql -X -d history_ci -v ON_ERROR_STOP=1 "$@"
}
f3_ledger_init() {
  [[ "$(sha256sum "$F3_LEDGER_MANIFEST" | awk '{print $1}')" == "$F3_LEDGER_MANIFEST_SHA" ]] || return 70
  [[ "$(f3_ledger_admin -Atq -c 'SHOW server_version')" == 17.11* ]] || return 70
  [[ "$(f3_ledger_admin -Atq -c "SELECT count(*) FROM pg_namespace WHERE nspname IN ('history_l1','auth_l1','db55_audit')")" == 0 ]] || return 70
  [[ "$(grep -c $'\tUP\t' "$F3_LEDGER_MANIFEST")" == 10 ]] || return 70
  # Exact source commits must exist; no trust in a filename alone.
  git cat-file -e 'd93dcf7cbf9290acd4cd3aa0164ef05689049da4^{commit}' ||
    git fetch --no-tags --depth=1 https://github.com/Shahbazi-Amir/RAG_finance_app.git d93dcf7cbf9290acd4cd3aa0164ef05689049da4
  while IFS=$'\t' read -r ver direction source path blob; do
    [[ "$direction" == UP ]] || continue
    [[ "$ver" =~ ^00[1-9]$|^010$ && "$path" == infra/postgres/migrations/"$ver"_*.up.sql ]] || return 70
    [[ "$(git rev-parse "$source:$path")" == "$blob" && "$(git hash-object "$GITHUB_WORKSPACE/$path")" == "$blob" ]] || return 70
  done < <(tail -n +2 "$F3_LEDGER_MANIFEST")
  f3_ledger_admin <<'SQL'
CREATE SCHEMA db55_audit AUTHORIZATION postgres;
REVOKE ALL ON SCHEMA db55_audit FROM PUBLIC;
CREATE TABLE db55_audit.migration_runs (
  version char(3) PRIMARY KEY CHECK (version BETWEEN '001' AND '010'),
  source_commit char(40) NOT NULL,
  git_blob_sha1 char(40) NOT NULL,
  sql_sha256 char(64) NOT NULL,
  status text NOT NULL CHECK (status IN ('STARTED','APPLIED')),
  started_at timestamptz NOT NULL DEFAULT clock_timestamp(),
  applied_at timestamptz,
  applied_txid bigint,
  cluster_system_id text NOT NULL
);
REVOKE ALL ON ALL TABLES IN SCHEMA db55_audit FROM PUBLIC;
SQL
}
# Hash exact rows of every existing active table, before and after each UP.
# Only a synthetic disposable DB; no row value or raw SQL output is exported.
f3_preserved_table_digest() {
  local table="$1"
  [[ "$table" =~ ^(history_l1|auth_l1)\.[a-z_][a-z0-9_]*$ ]] || { echo STOP_UNEXPECTED_ACTIVE_TABLE_IDENTIFIER >&2; return 70; }
  f3_ledger_admin -Atq -c "SELECT coalesce(jsonb_agg(to_jsonb(t) ORDER BY to_jsonb(t)::text),'[]'::jsonb)::text FROM $table t" | sha256sum | awk '{print $1}'
}
f3_ledger_apply() {
  local ver="$1" path="$2" row source blob sha count role prev existing table before after
  local -A preserved=()
  shift 2
  [[ "$ver" =~ ^00[1-9]$|^010$ && "$path" == infra/postgres/migrations/"$ver"_*.up.sql ]] || return 70
  row="$(awk -F '\t' -v v="$ver" '$1==v && $2=="UP" {print $3" "$4" "$5}' "$F3_LEDGER_MANIFEST")"
  read -r source expected_path blob <<<"$row"
  [[ "$expected_path" == "$path" && "$source" =~ ^[a-f0-9]{40}$ && "$blob" =~ ^[a-f0-9]{40}$ ]] || return 70
  [[ "$(git rev-parse "$source:$path")" == "$blob" && "$(git hash-object "$path")" == "$blob" ]] || return 70
  sha="$(sha256sum "$path" | awk '{print $1}')"
  prev=$((10#$ver-1))
  count="$(f3_ledger_admin -Atq -c "SELECT count(*) FROM db55_audit.migration_runs WHERE status='APPLIED'")"
  [[ "$count" == "$prev" && "$(f3_ledger_admin -Atq -c 'SELECT count(*) FROM db55_audit.migration_runs')" == "$prev" ]] || return 70
  role=auth_migrator
  [[ "$ver" == 001 || "$ver" == 002 ]] && role=history_migrator
  [[ "${PGUSER:-}" == "$role" ]] || return 70
  existing="$(f3_ledger_admin -Atq -c "SELECT schemaname||'.'||tablename FROM pg_tables WHERE schemaname IN ('history_l1','auth_l1') ORDER BY 1")"
  if [[ "$ver" != 001 ]]; then
    [[ -n "$existing" ]] || return 70
    [[ "$(f3_ledger_admin -Atq -c 'SELECT count(*) FROM history_l1.conversations')" -gt 0 ]] || return 70
    if (( 10#$ver >= 4 )); then
      [[ "$(f3_ledger_admin -Atq -c 'SELECT count(*) FROM auth_l1.sessions')" -gt 0 ]] || return 70
    fi
    while IFS= read -r table; do
      [[ -n "$table" ]] || continue
      before="$(f3_preserved_table_digest "$table")"
      [[ "$before" =~ ^[a-f0-9]{64}$ ]] || return 70
      preserved["$table"]="$before"
    done <<< "$existing"
  fi
  # Record STARTED before the real psql command. Never create APPLIED on a
  # failed command. A crash/partial ledger must stop, not be auto-replayed.
  f3_ledger_admin -q -c "INSERT INTO db55_audit.migration_runs(version,source_commit,git_blob_sha1,sql_sha256,status,cluster_system_id) VALUES('$ver','$source','$blob','$sha','STARTED',(SELECT system_identifier::text FROM pg_control_system()))"
  if ! psql -X -d history_ci "$@" -v ON_ERROR_STOP=1 -f "$path"; then
    echo "STOP_BROWSER_MIGRATION_${ver}_FAILED_INTENT_RETAINED" >&2
    return 70
  fi
  if [[ "$ver" != 001 ]]; then
    for table in "${!preserved[@]}"; do
      after="$(f3_preserved_table_digest "$table")"
      [[ "$after" == "${preserved[$table]}" ]] || { echo "STOP_BROWSER_MIGRATION_${ver}_PREEXISTING_ROW_DRIFT" >&2; return 70; }
    done
    echo "F3_DB_DATA_BEARING_UP_${ver}_EXACT_EXISTING_ROWS=PASS"
    printf '%s\n' "$ver" >> "$RUNNER_TEMP/f3-data-bearing-up-verified.txt"
  fi
  f3_ledger_admin -q -c "UPDATE db55_audit.migration_runs SET status='APPLIED',applied_at=clock_timestamp(),applied_txid=txid_current() WHERE version='$ver' AND status='STARTED' AND git_blob_sha1='$blob'"
  [[ "$(f3_ledger_admin -Atq -c "SELECT count(*) FROM db55_audit.migration_runs WHERE status='APPLIED'")" == "$((prev+1))" ]] || return 70
  echo "F3_BROWSER_ACTUAL_MIGRATION_${ver}_PINNED_APPLIED=PASS"
}
f3_ledger_complete() {
  [[ "$(f3_ledger_admin -Atq -c "SELECT count(*) FROM db55_audit.migration_runs WHERE status='APPLIED' AND applied_txid IS NOT NULL AND applied_at>=started_at")" == 10 ]] || return 70
  # Do not conflate this installer wrapper with DB55 bridge acceptance.
  echo F3_BROWSER_PINNED_001_010_ACTUAL_EXECUTION_LEDGER=PASS
  [[ "$(cat "$RUNNER_TEMP/f3-data-bearing-up-verified.txt")" == "$(printf '%03d\n' {2..10})" ]] || return 70
  echo F3_DB_DATA_BEARING_UP_002_010_NINE_MIGRATIONS=PASS
  unset F3_LEDGER_ADMIN_PASSWORD
}
