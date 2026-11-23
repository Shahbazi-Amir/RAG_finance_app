#!/usr/bin/env bash
# Usage: LAB_ROOT=... ./02_provision_roles.sh [lab-db | restore-db]
# Only creates narrowly scoped roles in a fresh disposable lab cluster.
set -euo pipefail
source "$(dirname "$0")/_lib.sh"
require_lab_ready
svc="${1:-lab-db}"
[[ "$svc" == lab-db || "$svc" == restore-db ]] || { echo 'STOP_NOT_LAB_SERVICE' >&2; exit 70; }
export DB_SERVICE="$svc"
if [[ "$svc" == restore-db ]]; then export DB_NAME=rag_finance_f3_lab_restore; else export DB_NAME=rag_finance_f3_lab; fi
secure_log
[[ "$(dbpsql -Atc 'SELECT current_database()')" == "$DB_NAME" ]] || { echo 'STOP_WRONG_FRESH_DB' >&2; exit 70; }
[[ "$(dbpsql -Atc "SELECT count(*) FROM pg_namespace WHERE nspname IN ('auth_l1','history_l1','db55_audit')")" == 0 ]] || { echo 'STOP_DB_NOT_FRESH_OR_ALREADY_PROVISIONED' >&2; exit 70; }
roles=(history_migrator auth_migrator history_app auth_revoker db55_lab_auditor
  auth_mapper auth_sessions auth_reauth auth_trust_api auth_replay_cleaner
  auth_reset_issuer auth_reset_executor auth_reset_lookup auth_reset_idp_recorder
  auth_login_bootstrap auth_login_issuer auth_login_binder auth_login_reader
  auth_login_cleaner auth_login_claim_reader)
role_list="'$(printf "%s," "${roles[@]}" | sed "s/,$//;s/,/','/g")'"
[[ "$(dbpsql -Atc "SELECT count(*) FROM pg_roles WHERE rolname IN ($role_list)")" == 0 ]] || { echo 'STOP_ROLE_NAMES_ALREADY_USED' >&2; exit 70; }
for role in "${roles[@]}"; do
  if [[ "$role" == history_migrator || "$role" == auth_migrator ]]; then
    printf 'CREATE ROLE %s NOLOGIN NOSUPERUSER BYPASSRLS NOINHERIT NOCREATEDB NOCREATEROLE;\n' "$role" | dbpsql >/dev/null
  else
    # Reuse the same lab test credential in the independent restore clone.
    cred="$LAB_WORK/${role}.password"
    [[ -e "$cred" ]] || openssl rand -hex 32 > "$cred"
    chmod 0600 "$cred"
    pass="$(cat "$cred")"
    [[ "$pass" =~ ^[a-f0-9]{64}$ ]] || { echo 'STOP_INVALID_TEST_PASSWORD' >&2; exit 70; }
    printf "CREATE ROLE %s LOGIN NOSUPERUSER NOBYPASSRLS NOINHERIT NOCREATEDB NOCREATEROLE PASSWORD '%s';\n" "$role" "$pass" | dbpsql >/dev/null
    if [[ "$svc" == lab-db ]]; then
      printf 'demo-db:5432:rag_finance_f3_lab:%s:%s\n' "$role" "$pass" >> "$LAB_SECRETS/pgpass"
    fi
  fi
done
chmod 0600 "$LAB_SECRETS/pgpass"
# Connect only to this explicit disposable lab database.
dbpsql <<SQL
REVOKE CONNECT,TEMP ON DATABASE "$DB_NAME" FROM PUBLIC;
GRANT CONNECT,CREATE ON DATABASE "$DB_NAME" TO history_migrator,auth_migrator;
GRANT CONNECT ON DATABASE "$DB_NAME" TO
  history_app,auth_revoker,db55_lab_auditor,
  auth_mapper,auth_sessions,auth_reauth,auth_trust_api,auth_replay_cleaner,
  auth_reset_issuer,auth_reset_executor,auth_reset_lookup,auth_reset_idp_recorder,
  auth_login_bootstrap,auth_login_issuer,auth_login_binder,
  auth_login_reader,auth_login_cleaner,auth_login_claim_reader;
SQL
if [[ "$svc" == lab-db ]]; then
  # Create a private immutable-intent ledger ahead of any migration.
  dbpsql <<'SQL'
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
CREATE TABLE db55_audit.bridge_runs (
  id integer PRIMARY KEY CHECK(id=1),
  bridge_sha1 char(40) NOT NULL,
  status text NOT NULL CHECK(status IN ('STARTED','APPLIED')),
  started_at timestamptz NOT NULL DEFAULT clock_timestamp(),
  applied_at timestamptz
);
REVOKE ALL ON ALL TABLES IN SCHEMA db55_audit FROM PUBLIC;
SQL
fi
printf 'F3_LAB_PROVISION_ROLES_SERVICE=%s ROLE_COUNT=%s PASS\n' "$svc" "${#roles[@]}"
