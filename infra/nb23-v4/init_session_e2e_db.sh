#!/bin/bash
# Docker entrypoint hook for the disposable history_ci database.
set -euo pipefail
test "${POSTGRES_DB:-}" = history_ci
sql=(psql -X -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB")
for role in history_migrator history_app auth_mapper auth_sessions auth_revoker auth_reauth \
    auth_trust_api auth_replay_cleaner auth_reset_executor auth_reset_idp_recorder \
    auth_reset_issuer auth_reset_lookup auth_login_binder auth_login_bootstrap \
    auth_login_claim_reader auth_login_cleaner auth_login_issuer auth_login_reader; do
    "${sql[@]}" -q -c "CREATE ROLE $role NOLOGIN"
done
"${sql[@]}" -q -c 'GRANT CREATE ON DATABASE history_ci TO history_migrator'
for part in run_001_008 run_009 run_010; do
    "${sql[@]}" -q -f "/run/ops/migrations/$part.psql"
done
"${sql[@]}" -q -c 'GRANT USAGE ON SCHEMA auth_l1 TO history_app'
"${sql[@]}" -q -f /run/ops/staging_idle_renewal.sql
echo ISOLATED_SESSION_SCHEMA_READY
