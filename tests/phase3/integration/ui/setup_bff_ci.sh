#!/usr/bin/env bash
# Only ephemeral role/DB and TLS credentials; never upload runner files.
set -euo pipefail
[[ "$CI" == true && "$GITHUB_ACTIONS" == true && "$PGHOST" == 127.0.0.1 ]] || exit 1
[[ "$BFF_TLS_DIR" == "$RUNNER_TEMP/bff-tls" ]] || exit 1
umask 077
export PGUSER=postgres PGPASSWORD=synthetic_ci_only_not_a_secret
psql -d postgres -v ON_ERROR_STOP=1 <<'SQL'
CREATE ROLE history_migrator LOGIN BYPASSRLS PASSWORD 'synthetic_mig_only';
CREATE ROLE history_app LOGIN NOSUPERUSER NOBYPASSRLS NOINHERIT NOCREATEDB NOCREATEROLE PASSWORD 'synthetic_app_only';
CREATE ROLE auth_migrator LOGIN BYPASSRLS PASSWORD 'synthetic_auth_migrator_only';
GRANT pg_read_all_stats TO auth_migrator;
CREATE ROLE auth_mapper LOGIN NOSUPERUSER NOBYPASSRLS NOINHERIT NOCREATEDB NOCREATEROLE PASSWORD 'synthetic_mapper_only';
CREATE ROLE auth_sessions LOGIN NOSUPERUSER NOBYPASSRLS NOINHERIT NOCREATEDB NOCREATEROLE PASSWORD 'synthetic_session_only';
CREATE ROLE auth_revoker LOGIN NOSUPERUSER NOBYPASSRLS NOINHERIT NOCREATEDB NOCREATEROLE PASSWORD 'synthetic_revoker_only';
CREATE ROLE auth_reauth LOGIN NOSUPERUSER NOBYPASSRLS NOINHERIT NOCREATEDB NOCREATEROLE PASSWORD 'synthetic_reauth_only';
CREATE ROLE auth_trust_api LOGIN NOSUPERUSER NOBYPASSRLS NOINHERIT NOCREATEDB NOCREATEROLE PASSWORD 'synthetic_trust_only';
CREATE ROLE auth_replay_cleaner LOGIN NOSUPERUSER NOBYPASSRLS NOINHERIT NOCREATEDB NOCREATEROLE PASSWORD 'synthetic_cleaner_only';
CREATE ROLE auth_trust_denied LOGIN NOSUPERUSER NOBYPASSRLS NOINHERIT NOCREATEDB NOCREATEROLE PASSWORD 'synthetic_denied_only';
CREATE DATABASE history_ci;
CREATE DATABASE history_api_ci;
CREATE DATABASE history_no005_ci;
GRANT CONNECT,CREATE ON DATABASE history_ci TO history_migrator,auth_migrator;
GRANT CONNECT,CREATE ON DATABASE history_no005_ci TO auth_migrator;
GRANT CONNECT,CREATE ON DATABASE history_api_ci TO history_migrator;
GRANT CONNECT ON DATABASE history_ci TO history_app,auth_mapper,auth_sessions,auth_revoker,auth_reauth,auth_trust_api,auth_replay_cleaner,auth_trust_denied;
GRANT CONNECT ON DATABASE history_no005_ci TO auth_trust_api;
GRANT CONNECT ON DATABASE history_api_ci TO history_app;
SQL
export PGUSER=history_migrator PGPASSWORD=synthetic_mig_only
for db in history_ci history_api_ci; do
  psql -d "$db" -v ON_ERROR_STOP=1 -f infra/postgres/migrations/001_history_l1.up.sql
  psql -d "$db" -v ON_ERROR_STOP=1 -f infra/postgres/migrations/002_one_attempt.up.sql
done
export PGUSER=auth_migrator PGPASSWORD=synthetic_auth_migrator_only
for mig in 003_auth_session 004_session_aware_fence 005_service_assertion_replay; do
  psql -d history_ci -v ON_ERROR_STOP=1 -f "infra/postgres/migrations/$mig.up.sql"
done
for mig in 003_auth_session 004_session_aware_fence; do
  psql -d history_no005_ci -v ON_ERROR_STOP=1 -f "infra/postgres/migrations/$mig.up.sql"
done
psql -d history_no005_ci -v ON_ERROR_STOP=1 -c 'GRANT USAGE ON SCHEMA auth_l1 TO auth_trust_api'
psql -d history_ci -v ON_ERROR_STOP=1 <<'SQL'
GRANT USAGE ON SCHEMA auth_l1 TO auth_trust_denied;
CREATE SCHEMA auth_trust_ci;
REVOKE ALL ON SCHEMA auth_trust_ci FROM PUBLIC;
CREATE TABLE auth_trust_ci.protected_actions(marker text PRIMARY KEY,owner_id text NOT NULL);
GRANT USAGE ON SCHEMA auth_trust_ci TO auth_trust_api;
GRANT INSERT ON auth_trust_ci.protected_actions TO auth_trust_api;
CREATE SCHEMA service_replay_ci;
REVOKE ALL ON SCHEMA service_replay_ci FROM PUBLIC;
CREATE TABLE service_replay_ci.protected_actions(marker text PRIMARY KEY);
GRANT USAGE ON SCHEMA service_replay_ci TO auth_trust_api;
GRANT INSERT ON service_replay_ci.protected_actions TO auth_trust_api;
CREATE SCHEMA auth_fence_ci;
REVOKE ALL ON SCHEMA auth_fence_ci FROM PUBLIC;
CREATE TABLE auth_fence_ci.protected_actions(owner_id text NOT NULL,marker text PRIMARY KEY);
GRANT USAGE ON SCHEMA auth_fence_ci TO auth_sessions;
GRANT INSERT ON auth_fence_ci.protected_actions TO auth_sessions;
SQL
mkdir -p "$BFF_TLS_DIR"
openssl genpkey -algorithm RSA -pkeyopt rsa_keygen_bits:2048 -out "$BFF_TLS_DIR/signer.key" >/dev/null 2>&1
openssl pkey -in "$BFF_TLS_DIR/signer.key" -pubout -out "$BFF_TRUST_PUBKEY_FILE" >/dev/null 2>&1
openssl req -x509 -newkey rsa:2048 -nodes -days 1 -subj '/CN=synthetic-bff-ca' \
 -keyout "$BFF_TLS_DIR/ca.key" -out "$BFF_TLS_DIR/ca.crt" >/dev/null 2>&1
openssl req -newkey rsa:2048 -nodes -subj '/CN=127.0.0.1' \
 -keyout "$BFF_TLS_DIR/api.key" -out "$BFF_TLS_DIR/api.csr" >/dev/null 2>&1
printf 'subjectAltName=IP:127.0.0.1\nextendedKeyUsage=serverAuth\n' > "$BFF_TLS_DIR/api.ext"
openssl x509 -req -days 1 -in "$BFF_TLS_DIR/api.csr" -CA "$BFF_TLS_DIR/ca.crt" \
 -CAkey "$BFF_TLS_DIR/ca.key" -CAcreateserial -out "$BFF_TLS_DIR/api.crt" \
 -extfile "$BFF_TLS_DIR/api.ext" >/dev/null 2>&1
openssl req -newkey rsa:2048 -nodes -subj '/CN=synthetic-bff-client' \
 -keyout "$BFF_TLS_DIR/client.key" -out "$BFF_TLS_DIR/client.csr" >/dev/null 2>&1
printf 'extendedKeyUsage=clientAuth\n' > "$BFF_TLS_DIR/client.ext"
openssl x509 -req -days 1 -in "$BFF_TLS_DIR/client.csr" -CA "$BFF_TLS_DIR/ca.crt" \
 -CAkey "$BFF_TLS_DIR/ca.key" -CAcreateserial -out "$BFF_TLS_DIR/client.crt" \
 -extfile "$BFF_TLS_DIR/client.ext" >/dev/null 2>&1
openssl req -x509 -newkey rsa:2048 -nodes -days 1 -subj '/CN=synthetic-rogue-ca' \
 -keyout "$BFF_TLS_DIR/rogue-ca.key" -out "$BFF_TLS_DIR/rogue-ca.crt" >/dev/null 2>&1
openssl req -newkey rsa:2048 -nodes -subj '/CN=synthetic-rogue-client' \
 -keyout "$BFF_TLS_DIR/rogue-client.key" -out "$BFF_TLS_DIR/rogue-client.csr" >/dev/null 2>&1
openssl x509 -req -days 1 -in "$BFF_TLS_DIR/rogue-client.csr" \
 -CA "$BFF_TLS_DIR/rogue-ca.crt" -CAkey "$BFF_TLS_DIR/rogue-ca.key" \
 -CAcreateserial -out "$BFF_TLS_DIR/rogue-client.crt" >/dev/null 2>&1
echo 'EPHEMERAL_DB_AND_MTLS_FIXTURES_READY'
