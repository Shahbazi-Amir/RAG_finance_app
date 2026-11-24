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
node_image='public.ecr.aws/docker/library/node@sha256:47725aca53d3295ec2d3be8f62726599b3033cc262edc2c7e429909b3ac599fc'
docker pull --quiet "$node_image" > /dev/null
docker run --rm --network "container:$api_bff_name" --user 11003:11003 \
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
sudo install -o 11001 -g 11001 -m 0600 "$dump" "$probe_dir/private/aead_input.dump"
run_probe authenticated_backup
[[ ! -e "$probe_dir/private/aead_verified_restore.dump" ]] || exit 70
run_probe reopen_backup
admin restore-db -c "CREATE DATABASE $dst OWNER postgres" >/dev/null
admin restore-db -c "REVOKE CONNECT,TEMP ON DATABASE $dst FROM PUBLIC" >/dev/null
admin restore-db -c "GRANT CONNECT ON DATABASE $dst TO history_app,auth_mapper,auth_sessions,auth_revoker" >/dev/null
sudo cat "$probe_dir/private/aead_verified_restore.dump" | compose exec -T restore-db pg_restore -U postgres -d "$dst" > "$LAB_WORK/f3_http_ab_restore.log" 2>&1 || {
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
