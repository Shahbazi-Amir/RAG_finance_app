#!/bin/bash
set -euo pipefail
install -d -m 0700 -o postgres -g postgres /tmp/staging-db /tmp/staging-sock
gosu postgres initdb -D /tmp/staging-db --auth-local=peer --auth-host=reject >/dev/null
gosu postgres pg_ctl -D /tmp/staging-db -o "-h '' -k /tmp/staging-sock" -w start >/dev/null
trap 'gosu postgres pg_ctl -D /tmp/staging-db -m fast -w stop >/dev/null' EXIT
sql=(gosu postgres psql -X -h /tmp/staging-sock -v ON_ERROR_STOP=1)
"${sql[@]}" -q -c 'CREATE ROLE history_app; CREATE ROLE auth_mapper; CREATE ROLE auth_sessions; CREATE ROLE auth_revoker; CREATE ROLE auth_reauth;'
"${sql[@]}" -q -f /work/infra/postgres/migrations/003_auth_session.up.sql \
  -f /work/infra/postgres/migrations/004_session_aware_fence.up.sql \
  -f /work/infra/nb23-v4/staging_idle_renewal.sql \
  -f /work/infra/nb23-v4/test_staging_idle_renewal.sql
"${sql[@]}" -At >/tmp/revoke.out <<'SQL' &
BEGIN;
SET ROLE auth_sessions;
SELECT auth_l1.revoke_one(repeat('a',64),0);
\! touch /tmp/revoke-locked
SELECT pg_sleep(2);
COMMIT;
SQL
revoker=$!
for _ in {1..50}; do
  [ -e /tmp/revoke-locked ] && break
  sleep 0.1
done
test -e /tmp/revoke-locked
renewed=$("${sql[@]}" -qAt -c "SET ROLE history_app; SELECT auth_l1.admit_and_renew_staging_session('test-a',repeat('a',64),0,0)")
wait "$revoker"
grep -Fxq t /tmp/revoke.out
test "$renewed" = f
echo 'Concurrent revoke wins over waiting renewal PASS'
