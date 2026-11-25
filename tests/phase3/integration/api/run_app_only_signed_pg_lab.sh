#!/usr/bin/env bash
# Isolated ephemeral GitHub-hosted CI only. Never run against an existing stack.
set -euo pipefail
umask 077
[[ "${CI:-}" == true && "${GITHUB_ACTIONS:-}" == true ]] || { echo STOP_CI_ONLY; exit 70; }
: "${SOURCE_REPO:?}" "${LAB_ROOT:?}" "${RUNNER_TEMP:?}"
[[ "$LAB_ROOT" == "$RUNNER_TEMP"/f3-signed-api-* && ! -e "$LAB_ROOT" ]] || exit 70
cd "$SOURCE_REPO"
bundle=infra/postgres/dev_f3_isolated
for step in 00_prepare_source 01_create_isolated_lab 02_provision_roles 03_apply_pinned_001_010 04_bridge_and_db55 05_test_roles_tls_rls; do
  bash "$bundle/scripts/$step.sh"
done
source "$bundle/scripts/_lib.sh"
api_name="$LAB_PROJECT-api"
net="${LAB_PROJECT}_private"
cleanup() {
  docker rm -f "$api_name" >/dev/null 2>&1 || true
  compose down >/dev/null 2>&1 || true
}
trap cleanup EXIT
[[ "$(docker network inspect -f '{{.Internal}}' "$net")" == true ]] || exit 70
mkdir -m 700 "$LAB_ROOT/api-secrets" "$LAB_ROOT/bff-secrets"
python3 tests/phase3/integration/api/app_only_signed_pg_lab.py prepare "$LAB_ROOT"
# Seed only the fresh lab, never expose credentials or bearer values in SQL/log.
dbpsql -q < "$LAB_ROOT/bff-secrets/seed.sql" >/dev/null
[[ "$(dbpsql -Atc 'SELECT count(*) FROM db55_audit.migration_runs WHERE status=$$APPLIED$$')" == 10 ]] || exit 70
snapshot() {
  dbpsql -Atc "SELECT (SELECT count(*) FROM history_l1.conversations)||'|'||(SELECT count(*) FROM history_l1.messages)||'|'||(SELECT count(*) FROM history_l1.send_receipts)||'|'||(SELECT count(*) FROM history_l1.execution_attempts)||'|'||(SELECT count(*) FROM history_l1.answers)"
}
before="$(snapshot)"
sha="$(git rev-parse HEAD)"
image="f3-signed-pg:$sha"
docker build --platform linux/amd64 -f infra/phase3_l1/Dockerfile.api.signed \
  --build-arg BASE=docker.io/library/python:3.13.5 --build-arg "SOURCE_SHA=$sha" -t "$image" .
test "$(docker image inspect -f '{{.Config.User}}' "$image")" = '11001:11001'
sudo chown -R 11001:11001 "$LAB_ROOT/api-secrets"
docker run -d --name "$api_name" --network "$net" --network-alias app-only-api \
  --read-only --tmpfs /tmp:rw,nosuid,size=16m,uid=11001,gid=11001 \
  --cap-drop ALL --security-opt no-new-privileges --pids-limit 64 \
  -e API_CURSOR_KEY_FILE=/run/secrets/cursor.key -e API_CURSOR_TTL_SECONDS=300 \
  --mount "type=bind,src=$LAB_ROOT/api-secrets,dst=/run/secrets,readonly" "$image" >/dev/null
client() {
  docker run --rm --network "$net" --user "$(id -u):$(id -g)" --read-only \
    --cap-drop ALL --security-opt no-new-privileges \
    --mount "type=bind,src=$LAB_ROOT/bff-secrets,dst=/run/bff,readonly" \
    "$image" python3 tests/phase3/integration/api/app_only_signed_pg_lab.py "$1" /run/bff
}
client journey
after="$(snapshot)"
[[ "$before" == "$after" ]] || { echo STOP_DURABLE_HISTORY_CHANGED; exit 70; }
echo "SIGNED_LAB_HISTORY_COUNTS_BEFORE_AFTER_EQUAL=$after"
compose stop lab-db >/dev/null
client outage
echo "SIGNED_APP_ONLY_PG_HTTP_SHA=$sha"
echo 'SIGNED_APP_ONLY_PG_HTTP_LAB_PASS; SYNTHETIC_SESSIONS_NOT_IDP_OR_BROWSER'
