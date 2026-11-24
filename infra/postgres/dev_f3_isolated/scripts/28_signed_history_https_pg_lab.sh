#!/usr/bin/env bash
# Bounded DB+API HTTPS witness on disposable PG17.11 001–010/DB55 lab.
# Does not run a real OIDC provider, browser, engine, migration 011 or target.
set -euo pipefail
source "$(dirname "$0")/_lib.sh"
require_lab_ready; secure_log
[[ "$LAB_PROJECT" == ragfinance_f3_db_lab_* && "$LAB_DB" == rag_finance_f3_lab ]] || { echo STOP_NOT_DB_LAB >&2; exit 70; }
[[ -s "$LAB_WORK/restore_receipt.txt" && -f "$LAB_WORK/restore-tested.marker" ]] || { echo STOP_INDEPENDENT_RESTORE_NOT_READY >&2; exit 70; }
[[ "$(dbpsql -Atc "SELECT count(*) FROM db55_audit.migration_runs WHERE status='APPLIED'")" == 10 ]] || exit 70
[[ -n "$SOURCE_REPO" ]] || { echo STOP_NO_SOURCE_REPO >&2; exit 70; }
[[ -f "$SOURCE_REPO/tests/phase3/integration/api/f3_app_only_https_pg_ab_lab.py" ]] || exit 70
[[ ! -f "$SOURCE_REPO/infra/postgres/migrations/011_product_answer_claims.up.sql" ]] || exit 70
src=rag_finance_f3_http_ab_source
dst=rag_finance_f3_http_ab_restored
admin() {
 local svc="$1"; shift
 DB_SERVICE="$svc" DB_NAME=postgres dbpsql -Atq "$@"
}
[[ "$(admin lab-db -c "SELECT count(*) FROM pg_database WHERE datname='$src'")" == 0 ]] || exit 70
[[ "$(admin restore-db -c "SELECT count(*) FROM pg_database WHERE datname='$dst'")" == 0 ]] || exit 70
probe_dir="$LAB_WORK/app_only_https_probe"
[[ ! -e "$probe_dir" && ! -e "$LAB_WORK/f3_http_ab.dump" ]] || { echo STOP_ALREADY_EXISTING_PROBE >&2; exit 70; }
mkdir -m 0700 "$probe_dir"
cp "$LAB_SECRETS/ca.crt" "$probe_dir/pg_ca.crt"
chmod 0600 "$probe_dir/pg_ca.crt"
# Pass only ephemeral test role credentials; never emit or upload this private directory.
LAB_WORK="$LAB_WORK" F3_HTTP_PROBE="$probe_dir" python3 - <<'PY'
import json,os
from pathlib import Path
w=Path(os.environ['LAB_WORK'])
p=Path(os.environ['F3_HTTP_PROBE'])/'role_passwords.json'
roles=('history_app','auth_mapper','auth_sessions','auth_revoker')
secrets={role:(w/(role+'.password')).read_text().strip() for role in roles}
assert all(len(s)==64 and set(s).issubset(set('0123456789abcdef')) for s in secrets.values())
fd=os.open(str(p),os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
with os.fdopen(fd,'w') as out:json.dump(secrets,out)
PY
sudo chown -R 11001:11001 "$probe_dir"
[[ "$(stat -c '%a' "$probe_dir")" == 700 ]] || { echo STOP_UNSAFE_PROBE_DIR >&2; exit 70; }
admin lab-db -c "CREATE DATABASE $src TEMPLATE rag_finance_f3_lab OWNER postgres" >/dev/null
admin lab-db -c "REVOKE CONNECT,TEMP ON DATABASE $src FROM PUBLIC" >/dev/null
admin lab-db -c "GRANT CONNECT ON DATABASE $src TO history_app,auth_mapper,auth_sessions,auth_revoker" >/dev/null
[[ "$(DB_SERVICE=lab-db DB_NAME="$src" dbpsql -Atc "SELECT count(*) FROM db55_audit.migration_runs WHERE status='APPLIED'")" == 10 ]] || exit 70
[[ "$(DB_SERVICE=lab-db DB_NAME="$src" dbpsql -Atc "SELECT count(*) FROM history_l1.conversations")" == 0 ]] || exit 70
# CI-only API container exactly from this checkout, no generated/mounted engine.
sha="$(git -C "$SOURCE_REPO" rev-parse HEAD)"
[[ "$sha" =~ ^[a-f0-9]{40}$ ]] || exit 70
short_sha="$(printf '%s' "$sha" | cut -c1-12)"
image="f3-api-https-ab-lab:$short_sha"
docker build --pull=false -f "$SOURCE_REPO/infra/phase3_l1/Dockerfile.api" --build-arg "SOURCE_SHA=$sha" -t "$image" "$SOURCE_REPO" > "$LAB_WORK/app_only_https_build.log" 2>&1 || {
 echo STOP_APP_ONLY_HTTPS_IMAGE_BUILD >&2; exit 70;
}
[[ "$(docker image inspect "$image" -f '{{ .Config.User }}')" == '11001:11001' ]] || { echo STOP_API_IMAGE_NOT_NONROOT >&2; exit 70; }
network="$LAB_PROJECT"_private
docker network inspect "$network" > /dev/null
docker network inspect "$network" -f '{{ .Internal }}' | grep -Fxq 'true' || exit 70
run_probe(){
 docker run --rm --network "$network" --read-only \
  --security-opt no-new-privileges:true \
  --pids-limit 96 --memory 512m \
  --tmpfs /tmp:rw,noexec,nosuid,size=16m \
  --mount "type=bind,src=$probe_dir,dst=/run/f3_http_probe" \
  -e F3_ISOLATED_DB_HTTP=YES \
  -e PYTHONPATH=/srv/release \
  "$image" python3 /srv/release/tests/phase3/integration/api/f3_app_only_https_pg_ab_lab.py "$1"
}
m10_db=rag_finance_f3_m10_process_crash
[[ "$(admin lab-db -c "SELECT count(*) FROM pg_database WHERE datname='$m10_db'")" == 0 ]] || exit 70
admin lab-db -c "CREATE DATABASE $m10_db TEMPLATE rag_finance_f3_lab OWNER postgres" >/dev/null
admin lab-db -c "REVOKE CONNECT,TEMP ON DATABASE $m10_db FROM PUBLIC" >/dev/null
admin lab-db -c "GRANT CONNECT ON DATABASE $m10_db TO history_app" >/dev/null
run_probe m10_process
run_probe concurrent_repository
admin lab-db -c "DROP DATABASE $m10_db WITH (FORCE)" >/dev/null
[[ "$(admin lab-db -c "SELECT count(*) FROM pg_database WHERE datname='$m10_db'")" == 0 ]] || exit 70
run_probe seed
# Distinct clone: ordinary source/restore baseline remains byte-exact.
keyset_db=rag_finance_f3_http_ab_keyset
[[ "$(admin lab-db -c "SELECT count(*) FROM pg_database WHERE datname='$keyset_db'")" == 0 ]] || exit 70
admin lab-db -c "CREATE DATABASE $keyset_db TEMPLATE $src OWNER postgres" >/dev/null
admin lab-db -c "REVOKE CONNECT,TEMP ON DATABASE $keyset_db FROM PUBLIC" >/dev/null
admin lab-db -c "GRANT CONNECT ON DATABASE $keyset_db TO history_app,auth_mapper,auth_sessions,auth_revoker" >/dev/null
run_probe verify_keyset
admin lab-db -c "DROP DATABASE $keyset_db WITH (FORCE)" >/dev/null
[[ "$(admin lab-db -c "SELECT count(*) FROM pg_database WHERE datname='$keyset_db'")" == 0 ]] || exit 70
run_probe snapshot_source
run_probe role_matrix_source
run_probe snapshot_source
run_probe before

# REAL Next/Web productRequest TypeScript in a separate Node22 container,
# signing HTTPS mTLS requests for server-side synthetic session data. No
# browser context/cookie injection or fake HTTP responses.
bff_dir="$LAB_WORK/real_web_bff_private"
[[ ! -e "$bff_dir" ]] || { echo STOP_BFF_PRIVATE_DIR_PREEXISTS >&2; exit 70; }
mkdir -m 0700 "$bff_dir"
for pair in 'signer.key:signer.key' 'ca.pem:ca.pem' 'bff.pem:bff.pem' 'bff.key:bff.key' 'session_state.json:actors.json'; do
 from="$probe_dir/private/${pair%%:*}"
 to="$bff_dir/${pair#*:}"
 sudo cp "$from" "$to"
done
sudo chmod 0600 "$bff_dir"/*
sudo chown -R 11003:11003 "$bff_dir"
# Obtain the exact immutable Node image once, not once per replay phase.
# A transient registry timeout must not invalidate a local verified digest.
node_image='public.ecr.aws/docker/library/node@sha256:47725aca53d3295ec2d3be8f62726599b3033cc262edc2c7e429909b3ac599fc'
node_ready=0
for attempt in 1 2 3; do
 if timeout 120 docker pull --quiet "$node_image" > /dev/null; then
  node_ready=1; break
 fi
 echo "DB_LAB_PINNED_NODE_PULL_RETRY_${attempt}" >&2
 sleep "$((attempt*2))"
done
[[ "$node_ready" == 1 ]] || { echo STOP_PINNED_NODE_REGISTRY_UNAVAILABLE >&2; exit 70; }
docker image inspect "$node_image" --format '{{range .RepoDigests}}{{println .}}{{end}}' | grep -Fxq "$node_image" || {
 echo STOP_PINNED_NODE_DIGEST_MISMATCH >&2; exit 70;
}
echo DB_LAB_NODE_PIN_ONCE_VERIFIED_NO_REPLAY_PULL=PASS
run_bff(){
local phase="$1"
api_bff_name="f3-bff-api-$short_sha"
docker run -d --name "$api_bff_name" --no-healthcheck \
  --network "$network" --read-only --security-opt no-new-privileges:true \
  --pids-limit 96 --memory 512m --tmpfs /tmp:rw,noexec,nosuid,size=16m \
  --mount "type=bind,src=$probe_dir,dst=/run/f3_http_probe" \
  -e API_RUNNER_EXECUTION_MODE=APP_ONLY \
  -e F3_ISOLATED_DB_HTTP=YES \
  -e PYTHONPATH=/srv/release \
  "$image" /bin/sh -c 'export API_CURSOR_KEY="$(cat /run/f3_http_probe/private/cursor.key)"; export API_CURSOR_TTL_SECONDS=300; exec python3 -m apps.api.private_app_only_asgi --config /run/f3_http_probe/private/server-config.json' >/dev/null
trap 'docker rm -f "$api_bff_name" >/dev/null 2>&1 || true' EXIT
api_bff_ready=0
for n in $(seq 1 45); do
 if docker exec "$api_bff_name" python3 /srv/release/tests/phase3/integration/api/f3_app_only_https_pg_ab_lab.py ready200 >/dev/null 2>&1; then
  api_bff_ready=1; break
 fi
 sleep 1
done
if [[ "$api_bff_ready" != 1 ]]; then
  # Report only allowlisted categories, never raw private logs, tokens or DSNs.
  state="$(docker inspect "$api_bff_name" --format '{{.State.Status}}' 2>/dev/null || true)"
  exit_code="$(docker inspect "$api_bff_name" --format '{{.State.ExitCode}}' 2>/dev/null || true)"
  denied="$(docker logs "$api_bff_name" 2>&1 | grep -c 'APP_ONLY_STARTUP_DENIED' || true)"
  bound="$(docker logs "$api_bff_name" 2>&1 | grep -c 'Uvicorn running on' || true)"
  oom="$(docker inspect "$api_bff_name" --format '{{.State.OOMKilled}}' 2>/dev/null || true)"
  echo "BFF_API_DIAG_STATE=$state EXIT=$exit_code DENIED_COUNT=$denied LISTEN_COUNT=$bound OOM=$oom" >&2
  echo STOP_BFF_SOURCE_API_NOT_READY >&2
  exit 70
fi
docker run --pull=never --rm --network "container:$api_bff_name" --user 11003:11003 \
  --read-only --security-opt no-new-privileges:true --pids-limit 96 --memory 384m \
  --mount "type=bind,src=$SOURCE_REPO,dst=/repo,readonly" \
  --mount "type=bind,src=$bff_dir,dst=/tmp,readonly" \
  -e CI=true -e AUTH_CI_DEMO_MODE=true -e PHASE3_APP_MODE=APP_ONLY \
  -e AUTH_CI_PRODUCT_ORIGIN=https://127.0.0.1:18443 \
  -e AUTH_CI_PRODUCT_SIGN_KEY=/tmp/signer.key \
  -e AUTH_CI_BOOTSTRAP_CA=/tmp/ca.pem \
  -e AUTH_CI_BOOTSTRAP_CERT=/tmp/bff.pem \
  -e AUTH_CI_BOOTSTRAP_KEY=/tmp/bff.key \
  -e AUTH_CI_PRODUCT_ISSUER=urn:rag-finance:synthetic-bff \
  -e AUTH_CI_PRODUCT_AUDIENCE=urn:rag-finance:api:internal-ci \
  -e AUTH_CI_PRODUCT_KID=ci-rsa-1 \
  "$node_image" node --experimental-strip-types \
  /repo/tests/phase3/integration/ui/f3_app_only_bff_product_request_pg.mjs "$phase"
docker rm -f "$api_bff_name" >/dev/null
trap - EXIT
echo "APP_ONLY_REAL_NEXT_BFF_${phase^^}_TO_ACTUAL_MTLS_SIGNED_PG_HISTORY=PASS"
}
run_bff before
run_probe snapshot_source
run_probe catalog_source
echo APP_ONLY_REAL_NEXT_BFF_SOURCE_TO_ACTUAL_MTLS_SIGNED_PG_HISTORY=PASS
dump="$LAB_WORK/f3_http_ab.dump"
compose exec -T lab-db pg_dump -U postgres -d "$src" -Fc > "$dump"
[[ -s "$dump" ]] || { echo STOP_EMPTY_SOURCE_AB_DUMP >&2; exit 70; }
shasum -a 256 "$dump" > "$dump.sha256"
chmod 0600 "$dump" "$dump.sha256"
shasum -a 256 -c "$dump.sha256" > /dev/null
# Actual damaged pg_dump, not just cryptographic envelope corruption.
# No app listener can connect to this scratch target.
fault_db=rag_finance_f3_http_ab_corrupt_probe
[[ "$(admin restore-db -c "SELECT count(*) FROM pg_database WHERE datname='$fault_db'")" == 0 ]] || exit 70
admin restore-db -c "CREATE DATABASE $fault_db OWNER postgres" >/dev/null
admin restore-db -c "REVOKE CONNECT,TEMP ON DATABASE $fault_db FROM PUBLIC" >/dev/null
bad_dump="$LAB_WORK/f3_http_ab_truncated.dump"
[[ ! -e "$bad_dump" ]] || exit 70
size="$(stat -c %s "$dump")"
[[ "$size" -gt 4096 ]] || exit 70
# Find the shortest prefix containing a readable archive TOC. The amount
# of catalog metadata varies with migrations; a fixed percent can truncate
# the TOC itself. Preserve that TOC and intentionally remove the data tail.
touch "$bad_dump"
chmod 0600 "$bad_dump"
lo=1
hi="$size"
while (( lo < hi )); do
 mid=$(((lo+hi)/2))
 head -c "$mid" "$dump" > "$bad_dump"
 if compose exec -T restore-db pg_restore --list < "$bad_dump" > "$LAB_WORK/f3_corrupt_toc.private" 2>&1; then
  hi="$mid"
 else
  lo=$((mid+1))
 fi
done
[[ "$lo" -lt "$size" ]] || { echo STOP_NO_VALID_TRUNCATED_TOC >&2; exit 70; }
head -c "$lo" "$dump" > "$bad_dump"
compose exec -T restore-db pg_restore --list < "$bad_dump" > "$LAB_WORK/f3_corrupt_toc.private" 2>&1
if compose exec -T restore-db pg_restore --single-transaction --exit-on-error -U postgres -d "$fault_db" < "$bad_dump" > "$LAB_WORK/f3_corrupt_restore.private" 2>&1; then
 echo STOP_CORRUPT_ARCHIVE_ACCEPTED >&2; exit 70
fi
[[ "$(DB_SERVICE=restore-db DB_NAME="$fault_db" dbpsql -Atc "SELECT count(*) FROM pg_namespace WHERE nspname IN ('history_l1','auth_l1','db55_audit')")" == 0 ]] || exit 70
echo DB_PG_RESTORE_TRUNCATED_VALID_TOC_DENIED_NO_PARTIAL_SCHEMA=PASS
# The same pristine scratch DB must subsequently accept the authentic archive
# atomically. This is explicit lab recovery, not auto-retry of migration intent.
compose exec -T restore-db pg_restore --single-transaction --exit-on-error -U postgres -d "$fault_db" < "$dump" > "$LAB_WORK/f3_clean_retry_restore.private" 2>&1
[[ "$(DB_SERVICE=restore-db DB_NAME="$fault_db" dbpsql -Atc "SELECT count(*) FROM db55_audit.migration_runs WHERE status='APPLIED'")" == 10 ]] || exit 70
[[ "$(DB_SERVICE=restore-db DB_NAME="$fault_db" dbpsql -Atc 'SELECT count(*) FROM history_l1.conversations')" == 8 ]] || exit 70
admin restore-db -c "DROP DATABASE $fault_db WITH (FORCE)" >/dev/null
[[ "$(admin restore-db -c "SELECT count(*) FROM pg_database WHERE datname='$fault_db'")" == 0 ]] || exit 70
rm "$bad_dump" "$LAB_WORK/f3_corrupt_toc.private" "$LAB_WORK/f3_corrupt_restore.private" "$LAB_WORK/f3_clean_retry_restore.private"
echo DB_PG_RESTORE_ATOMIC_CLEAN_RECOVERY_10_LEDGER_8_CONVERSATIONS=PASS
sudo install -o 11001 -g 11001 -m 0600 "$dump" "$probe_dir/private/aead_input.dump"
run_probe authenticated_backup
[[ ! -e "$probe_dir/private/aead_verified_restore.dump" ]] || exit 70
run_probe reopen_backup
admin restore-db -c "CREATE DATABASE $dst OWNER postgres" >/dev/null
admin restore-db -c "REVOKE CONNECT,TEMP ON DATABASE $dst FROM PUBLIC" >/dev/null
admin restore-db -c "GRANT CONNECT ON DATABASE $dst TO history_app,auth_mapper,auth_sessions,auth_revoker" >/dev/null
sudo cat "$probe_dir/private/aead_verified_restore.dump" | compose exec -T restore-db pg_restore --single-transaction --exit-on-error -U postgres -d "$dst" > "$LAB_WORK/f3_http_ab_restore.log" 2>&1 || {
 echo STOP_AB_HTTP_RESTORE_FAILED >&2; exit 70;
}
sudo rm "$probe_dir/private/aead_verified_restore.dump"
[[ ! -e "$probe_dir/private/aead_key_material/key.bin" ]] || exit 70
# Drop redundant plaintext dump only after successful independent restore.
rm "$dump"
echo DB_AUTHENTICATED_BACKUP_ACTUAL_PG_RESTORE=PASS
[[ "$(DB_SERVICE=restore-db DB_NAME="$dst" dbpsql -Atc "SELECT count(*) FROM db55_audit.migration_runs WHERE status='APPLIED'")" == 10 ]] || exit 70
[[ "$(DB_SERVICE=lab-db DB_NAME="$src" dbpsql -Atc "SELECT count(*) FROM history_l1.conversations")" == 8 ]] || exit 70
[[ "$(DB_SERVICE=restore-db DB_NAME="$dst" dbpsql -Atc "SELECT count(*) FROM history_l1.conversations")" == 8 ]] || exit 70
src_id="$(DB_SERVICE=lab-db DB_NAME="$src" dbpsql -Atc 'SELECT system_identifier FROM pg_control_system()')"
dst_id="$(DB_SERVICE=restore-db DB_NAME="$dst" dbpsql -Atc 'SELECT system_identifier FROM pg_control_system()')"
[[ -n "$src_id" && -n "$dst_id" && "$src_id" != "$dst_id" ]] || exit 70
# Source and second cluster use the same ephemeral session value; a fresh
# signed proof must still pass DB session epoch/generation and durable replay.
run_probe catalog_restore
run_probe snapshot_restore
run_probe role_matrix_restore
run_probe snapshot_restore
run_probe after
run_bff after
run_probe snapshot_restore
run_probe revoke
run_bff revoked
run_probe snapshot_restore
# The HTTPS listener is a separate nonroot process. Keep it running across a
# deliberate outage of ONLY this disposable restore-db container, then restore
# that same lab cluster. This is dependency readiness, NOT full machine DR.
probe_name="f3-app-only-ready-$short_sha"
docker run -d --name "$probe_name" --no-healthcheck \
  --network "$network" --read-only --security-opt no-new-privileges:true \
  --pids-limit 96 --memory 512m --tmpfs /tmp:rw,noexec,nosuid,size=16m \
  --mount "type=bind,src=$probe_dir,dst=/run/f3_http_probe" \
  -e API_RUNNER_EXECUTION_MODE=APP_ONLY \
  -e PYTHONPATH=/srv/release \
  -e F3_ISOLATED_DB_HTTP=YES \
  "$image" python3 -m apps.api.private_app_only_asgi \
  --config /run/f3_http_probe/private/server-config.json \
  > /dev/null
trap 'docker rm -f "$probe_name" > /dev/null 2>&1 || true' EXIT
ready=0
for n in $(seq 1 45); do
 if docker exec "$probe_name" python3 /srv/release/tests/phase3/integration/api/f3_app_only_https_pg_ab_lab.py ready200 > /dev/null 2>&1; then
  ready=1; break
 fi
 sleep 1
done
[[ "$ready" == 1 ]] || { echo STOP_API_READY_BEFORE_OUTAGE >&2; exit 70; }
echo APP_ONLY_RUNNING_MTLS_API_READY_BEFORE_PG_OUTAGE_200=PASS
compose --profile restore stop restore-db > /dev/null
docker exec "$probe_name" python3 /srv/release/tests/phase3/integration/api/f3_app_only_https_pg_ab_lab.py ready503
echo APP_ONLY_RUNNING_MTLS_API_READY_AFTER_PG_LOSS_503=PASS
compose --profile restore up -d --no-deps restore-db > /dev/null
db_ready=0
for n in $(seq 1 45); do
 if [[ "$(DB_SERVICE=restore-db DB_NAME="$dst" dbpsql -Atc 'SELECT 1' 2>/dev/null || true)" == 1 ]]; then
  db_ready=1; break
 fi
 sleep 1
done
[[ "$db_ready" == 1 ]] || { echo STOP_PG_RESTORE_SERVICE_NOT_RESTARTED >&2; exit 70; }
docker exec "$probe_name" python3 /srv/release/tests/phase3/integration/api/f3_app_only_https_pg_ab_lab.py ready200
echo APP_ONLY_RUNNING_MTLS_API_READY_RECOVERED_PG_200=PASS
docker rm -f "$probe_name" >/dev/null
trap - EXIT
[[ "$(DB_SERVICE=lab-db DB_NAME="$src" dbpsql -Atc "SELECT count(*) FROM history_l1.conversations")" == 8 ]] || exit 70
[[ "$(DB_SERVICE=restore-db DB_NAME="$dst" dbpsql -Atc "SELECT count(*) FROM history_l1.conversations")" == 8 ]] || exit 70
[[ "$(DB_SERVICE=restore-db DB_NAME="$dst" dbpsql -Atc "SELECT count(*) FROM history_l1.send_receipts")" == 0 ]] || exit 70
[[ "$(DB_SERVICE=restore-db DB_NAME="$dst" dbpsql -Atc "SELECT count(*) FROM history_l1.answers")" == 0 ]] || exit 70
run_probe verify_revoked_restored
# Deliberate unclean exit of ONLY the isolated restore service. A real client
# has an uncommitted row before SIGKILL; source service and volume stay intact.
restore_cid="$(compose --profile restore ps -q restore-db)"
[[ "$restore_cid" =~ ^[0-9a-f]{64}$ ]] || exit 70
[[ "$(docker inspect -f '{{ index .Config.Labels "com.docker.compose.project" }}' "$restore_cid")" == "$LAB_PROJECT" ]] || exit 70
[[ "$(docker inspect -f '{{ index .Config.Labels "com.docker.compose.service" }}' "$restore_cid")" == restore-db ]] || exit 70
[[ "$(docker inspect -f '{{range .Mounts}}{{if eq .Destination "/var/lib/postgresql/data"}}{{.Name}}{{end}}{{end}}' "$restore_cid")" == "$LAB_RESTORE_VOLUME" ]] || exit 70
[[ "$(docker inspect -f '{{.Config.Image}}' "$restore_cid")" == public.ecr.aws/docker/library/postgres@sha256:73bedc9eaa0121b92b9b26bb52e5141b3f6f37479c7ef913c0160455763ca80a ]] || exit 70
[[ "$restore_cid" != "$(compose ps -q lab-db)" ]] || exit 70
crash_client="f3-pg-crash-client-$short_sha"
docker run -d --name "$crash_client" --network "$network" --read-only \
  --security-opt no-new-privileges:true --pids-limit 96 --memory 512m \
  --tmpfs /tmp:rw,noexec,nosuid,size=16m \
  --mount "type=bind,src=$probe_dir,dst=/run/f3_http_probe" \
  -e F3_ISOLATED_DB_HTTP=YES -e PYTHONPATH=/srv/release "$image" \
  python3 /srv/release/tests/phase3/integration/api/f3_app_only_https_pg_ab_lab.py hold_pg_crash >/dev/null
trap 'docker rm -f "$crash_client" >/dev/null 2>&1 || true' EXIT
for n in $(seq 1 40); do
 sudo test -f "$probe_dir/private/pg_crash_tx_open" && break
 sleep .25
done
sudo test -f "$probe_dir/private/pg_crash_tx_open" || exit 70
# Independent administrator cannot see uncommitted row.
[[ "$(DB_SERVICE=restore-db DB_NAME="$dst" dbpsql -Atc "SELECT count(*) FROM history_l1.conversations WHERE id='f3-uncommitted-pg-crash'")" == 0 ]] || exit 70
docker kill --signal KILL "$restore_cid" >/dev/null
[[ "$(docker inspect -f '{{.State.ExitCode}}' "$restore_cid")" == 137 ]] || exit 70
[[ "$(timeout 30 docker wait "$crash_client")" == 0 ]] || exit 70
sudo test -f "$probe_dir/private/pg_crash_tx_disconnected" || exit 70
docker rm "$crash_client" >/dev/null
trap - EXIT
docker start "$restore_cid" >/dev/null
for n in $(seq 1 45); do
 if [[ "$(DB_SERVICE=restore-db DB_NAME="$dst" dbpsql -Atc 'SELECT 1' 2>/dev/null || true)" == 1 ]]; then break; fi
 sleep 1
done
[[ "$(DB_SERVICE=restore-db DB_NAME="$dst" dbpsql -Atc 'SELECT system_identifier FROM pg_control_system()')" == "$dst_id" ]] || exit 70
[[ "$(DB_SERVICE=lab-db DB_NAME="$src" dbpsql -Atc 'SELECT system_identifier FROM pg_control_system()')" == "$src_id" ]] || exit 70
[[ "$(DB_SERVICE=restore-db DB_NAME="$dst" dbpsql -Atc "SELECT count(*) FROM db55_audit.migration_runs WHERE status='APPLIED'")" == 10 ]] || exit 70
run_probe verify_pg_crash
echo DB_REAL_PG_SIGKILL_EXIT137_SAME_VOLUME_RECOVERY=PASS
run_probe stale_snapshot
# Backup *after* revocation, then restore into a fresh clone on the other
# independent cluster. No attempt to activate a stale pre-revocation backup.
revoked_copy=rag_finance_f3_http_ab_revoked_copy
[[ "$(admin lab-db -c "SELECT count(*) FROM pg_database WHERE datname='$revoked_copy'")" == 0 ]] || exit 70
revoked_dump="$LAB_WORK/f3_http_ab_post_revoke.dump"
[[ ! -e "$revoked_dump" ]] || exit 70
compose exec -T restore-db pg_dump -U postgres -d "$dst" -Fc > "$revoked_dump"
[[ -s "$revoked_dump" ]] || exit 70
chmod 0600 "$revoked_dump"
shasum -a 256 "$revoked_dump" > "$revoked_dump.sha256"
shasum -a 256 -c "$revoked_dump.sha256" >/dev/null
admin lab-db -c "CREATE DATABASE $revoked_copy OWNER postgres" >/dev/null
admin lab-db -c "REVOKE CONNECT,TEMP ON DATABASE $revoked_copy FROM PUBLIC" >/dev/null
admin lab-db -c "GRANT CONNECT ON DATABASE $revoked_copy TO history_app,auth_mapper,auth_sessions,auth_revoker" >/dev/null
compose exec -T lab-db pg_restore --exit-on-error -U postgres -d "$revoked_copy" < "$revoked_dump" > "$LAB_WORK/revoked_copy_restore.log" 2>&1
[[ "$(DB_SERVICE=lab-db DB_NAME="$revoked_copy" dbpsql -Atc "SELECT count(*) FROM db55_audit.migration_runs WHERE status='APPLIED'")" == 10 ]] || exit 70
[[ "$(DB_SERVICE=lab-db DB_NAME="$revoked_copy" dbpsql -Atc 'SELECT system_identifier FROM pg_control_system()')" != "$dst_id" ]] || exit 70
run_probe snapshot_revoked_copy
run_probe verify_revoked_copy
run_probe snapshot_revoked_copy
admin lab-db -c "DROP DATABASE $revoked_copy WITH (FORCE)" >/dev/null
[[ "$(admin lab-db -c "SELECT count(*) FROM pg_database WHERE datname='$revoked_copy'")" == 0 ]] || exit 70
echo DB_POST_REVOKE_BACKUP_INDEPENDENT_RESTORE_CLEANUP=PASS
# Sanitized receipt only; never publish keys, role passwords, opaque session
# tokens, service config, internal logs, or the raw pg_dump.
export F3_HTTP_DUMP_SHA="$(awk '{print $1}' "$dump.sha256")"
export F3_HTTP_GIT_SHA="$sha"
python3 - <<'PY'
import json,os
from pathlib import Path
p=Path(os.environ["GITHUB_WORKSPACE"])/"ci_receipts"/"app_only_https_pg_ab_restore.json"
p.parent.mkdir(exist_ok=True)
report={
 "contract_version":"f3.app_only.real_mtls_signed_history_pg_ab_lab.v1",
 "source_git_sha":os.environ["F3_HTTP_GIT_SHA"],
 "environment":"real_isolated_pg17.11_api_container_mtls_loopback",
 "idp":"NOT_RUN_SYNTHETIC_DB_MAPPED_SUBJECTS",
 "browser":"NOT_RUN",
 "bff":"SYNTHETIC_RS256_SIGNER_AND_REAL_X509_CLIENT_CERT",
 "private_api_listener":"REAL_UVICORN_H11_MTLS",
 "postgres_service":"history_app_TLS_VERIFY_FULL_CA_SAN",
 "real_signed_http_history":"SOURCE_AND_INDEPENDENT_RESTORE",
 "real_web_product_request_bff":"ACTUAL_NEXT_SOURCE_NODE22_SIGNED_MTLS_TWO_OWNERS",
 "bff_restore_replay":"BEFORE_AFTER_REFRESH_AND_REVOKED_A401_B200",
 "sql_independent_history_snapshot":"EXACT_PARITY_SOURCE_RESTORE_A5_B3_M4_M2_ZERO_SEND",
 "m10_process_crash":"REAL_SIGKILL_T1_T2_PRE_POST_COMMIT_REPLAY_IDS_STABLE",
 "m10_process_crash_scope":"TRUSTED_REPOSITORY_FIXTURE_NOT_HTTP_SEND_NO_DISPATCH",
 "concurrent_repository":"CREATE_T1_T2_SIX_REAL_SESSIONS_EACH_EXACTLY_ONE",
 "repository_negative_matrix":"NINE_FOREIGN_UNKNOWN_CONFLICT_DENIALS_ZERO_MUTATION",
 "repository_terminal_replay":"UNKNOWN_CANCELLED_STABLE_ATTEMPT_ZERO_ANSWER_NO_OWNER_LEAK",
 "backup_aead":"AES256_GCM_ACTUAL_PG_RESTORE_WRONG_KEY_TAMPER_TRUNCATION_AAD_DENIED",
 "backup_key_custody":"EPHEMERAL_MODE0600_FILE_REMOVED_NOT_PRODUCTION_KMS_OR_RETENTION",
 "backup_independent_process":"ENCRYPT_PROCESS_EXIT_SEPARATE_DECRYPT_PROCESS_WRONG_KEY_DENIED_ACTUAL_RESTORE",
 "backup_plaintext_cleanup":"ORIGINAL_DUMP_AND_VERIFIED_RESTORE_REMOVED_AFTER_SUCCESS",
 "stale_snapshot_witness":"REAL_READ_ONLY_SESSION_DIVERGENCE_NO_STALE_LISTENER_ADMISSION",
 "post_outage_revocation_recheck":"A401_B200_FOREIGN_UNKNOWN404",
 "atomic_corrupt_restore":"TRUNCATED_VALID_TOC_REJECTED_NO_PARTIAL_SCHEMA_CLEAN_RESTORE_10_LEDGER_8_CONVERSATIONS",
 "http_keyset_later_insert":"SIGNED_CURSOR_OLD_ANCHOR_STABLE_REFRESH_SEES_LATER_INSERT",
 "title_immutable_history":"DIRECT_SCOPED_TITLE_UPDATE_SIGNED_HTTP_MESSAGE_BYTES_UNCHANGED_FOREIGN_ZERO",
 "enumeration_equivalence":"SIGNED_FOREIGN_KNOWN_UNKNOWN_404_CODE_CATEGORY_CACHE_PARITY",
 "role_write_matrix":"26_SOURCE_26_RESTORED_ACTUAL_SQL_DENIALS_ZERO_MUTATION",
 "pg_unclean_crash":"REAL_RESTORE_PG_SIGKILL_EXIT137_UNCOMMITTED_ROW_ROLLED_BACK_SAME_VOLUME_AND_LEDGER_REVOKE_HISTORY_PARITY",
 "catalog_parity":"SIX_TABLES_COLUMNS_CONSTRAINTS_INDEXES_RLS_EXACT_SOURCE_RESTORE",
 "keyset_index_paths":"FORCED_PLANNER_ELIGIBILITY_NOT_LATENCY_BENCHMARK",
 "post_revoke_backup_restore":"NEW_DB_OTHER_CLUSTER_A401_B200_HISTORY_PARITY",
 "stale_pre_revoke_backup_admission":"NOT_AUTHORIZED_REQUIRES_OWNER_SECURITY_POLICY",
 "two_owner_conversations":[5,3],
 "two_owner_messages":[4,2],
 "authenticated_session_revoke_after_restore":"A_DENIED_B_ALLOWED",
 "real_mtls_api_dependency_readiness":"200_THEN_503_PG_DOWN_THEN_200_RECOVERED",
 "cross_owner_detail":"404",
 "no_cert_wrong_leaf":"REJECTED",
 "send_without_engine":"503_ZERO_DURABLE_WRITES",
 "source_restore_distinct_pg_clusters":True,
 "source_and_restored_history_equal":True,
 "backup_sha256":os.environ["F3_HTTP_DUMP_SHA"],
 "migrations":"001-010",
 "engine_calls":0,"migration_011":"NOT_RUN",
 "identity_same_tx_bound_to_real_oidc":"NOT_PROVEN",
 "target_mac_or_arvan":"NOT_RUN",
 "module_gates":"NOT_ACCEPTED"
}
p.write_text(json.dumps(report,sort_keys=True,indent=2)+"\n")
PY
chmod 0600 "$GITHUB_WORKSPACE/ci_receipts/app_only_https_pg_ab_restore.json"
admin lab-db -c "DROP DATABASE $src WITH (FORCE)" >/dev/null
admin restore-db -c "DROP DATABASE $dst WITH (FORCE)" >/dev/null
[[ "$(admin lab-db -c "SELECT count(*) FROM pg_database WHERE datname='$src'")" == 0 ]] || exit 70
[[ "$(admin restore-db -c "SELECT count(*) FROM pg_database WHERE datname='$dst'")" == 0 ]] || exit 70
echo F3_APP_ONLY_REAL_SIGNED_HTTPS_API_PG_AB_RESTORE_LAB=PASS
echo F3_APP_ONLY_NO_REAL_IDP_NO_BROWSER_NO_ENGINE_NO_011
