#!/bin/bash
# Disposable fixture inside a Docker --network none namespace.
set -euo pipefail
install -d -m 0700 -o postgres -g postgres /tmp/staging-db /tmp/staging-sock
gosu postgres initdb -D /tmp/staging-db --auth-local=peer --auth-host=trust >/dev/null
gosu postgres pg_ctl -D /tmp/staging-db -o "-h 127.0.0.1 -k /tmp/staging-sock" -w start >/dev/null
trap 'gosu postgres pg_ctl -D /tmp/staging-db -m fast -w stop >/dev/null; exit' TERM INT
sql=(gosu postgres psql -X -h /tmp/staging-sock -v ON_ERROR_STOP=1)
"${sql[@]}" -q -c 'CREATE ROLE history_app; CREATE ROLE auth_mapper; CREATE ROLE auth_sessions; CREATE ROLE auth_revoker; CREATE ROLE auth_reauth; CREATE ROLE auth_trust_api; CREATE ROLE auth_replay_cleaner;'
"${sql[@]}" -q -f /work/infra/postgres/migrations/003_auth_session.up.sql \
  -f /work/infra/postgres/migrations/004_session_aware_fence.up.sql \
  -f /work/infra/postgres/migrations/005_service_assertion_replay.up.sql \
  -f /work/infra/nb23-v4/staging_idle_renewal.sql
"${sql[@]}" -q -c 'GRANT USAGE ON SCHEMA auth_l1 TO history_app; GRANT EXECUTE ON FUNCTION auth_l1.admit_session_fenced(text,text,bigint,integer),auth_l1.consume_service_assertion(text,bigint) TO history_app;'
echo SIGNED_IDLE_FIXTURE_READY
while :; do sleep 1 & wait $!; done
