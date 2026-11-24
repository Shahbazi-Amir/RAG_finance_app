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
assert all(len(s)==64 and set(s)<set('0123456789abcdef') for s in secrets.values())
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
run_probe seed
run_probe before
dump="$LAB_WORK/f3_http_ab.dump"
compose exec -T lab-db pg_dump -U postgres -d "$src" -Fc > "$dump"
[[ -s "$dump" ]] || { echo STOP_EMPTY_SOURCE_AB_DUMP >&2; exit 70; }
shasum -a 256 "$dump" > "$dump.sha256"
chmod 0600 "$dump" "$dump.sha256"
shasum -a 256 -c "$dump.sha256" > /dev/null
admin restore-db -c "CREATE DATABASE $dst OWNER postgres" >/dev/null
admin restore-db -c "REVOKE CONNECT,TEMP ON DATABASE $dst FROM PUBLIC" >/dev/null
admin restore-db -c "GRANT CONNECT ON DATABASE $dst TO history_app,auth_mapper,auth_sessions,auth_revoker" >/dev/null
compose exec -T restore-db pg_restore -U postgres -d "$dst" < "$dump" > "$LAB_WORK/f3_http_ab_restore.log" 2>&1 || {
 echo STOP_AB_HTTP_RESTORE_FAILED >&2; exit 70;
}
[[ "$(DB_SERVICE=restore-db DB_NAME="$dst" dbpsql -Atc "SELECT count(*) FROM db55_audit.migration_runs WHERE status='APPLIED'")" == 10 ]] || exit 70
[[ "$(DB_SERVICE=lab-db DB_NAME="$src" dbpsql -Atc "SELECT count(*) FROM history_l1.conversations")" == 8 ]] || exit 70
[[ "$(DB_SERVICE=restore-db DB_NAME="$dst" dbpsql -Atc "SELECT count(*) FROM history_l1.conversations")" == 8 ]] || exit 70
src_id="$(DB_SERVICE=lab-db DB_NAME="$src" dbpsql -Atc 'SELECT system_identifier FROM pg_control_system()')"
dst_id="$(DB_SERVICE=restore-db DB_NAME="$dst" dbpsql -Atc 'SELECT system_identifier FROM pg_control_system()')"
[[ -n "$src_id" && -n "$dst_id" && "$src_id" != "$dst_id" ]] || exit 70
# Source and second cluster use the same ephemeral session value; a fresh
# signed proof must still pass DB session epoch/generation and durable replay.
run_probe after
[[ "$(DB_SERVICE=lab-db DB_NAME="$src" dbpsql -Atc "SELECT count(*) FROM history_l1.conversations")" == 8 ]] || exit 70
[[ "$(DB_SERVICE=restore-db DB_NAME="$dst" dbpsql -Atc "SELECT count(*) FROM history_l1.conversations")" == 8 ]] || exit 70
[[ "$(DB_SERVICE=restore-db DB_NAME="$dst" dbpsql -Atc "SELECT count(*) FROM history_l1.send_receipts")" == 0 ]] || exit 70
[[ "$(DB_SERVICE=restore-db DB_NAME="$dst" dbpsql -Atc "SELECT count(*) FROM history_l1.answers")" == 0 ]] || exit 70
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
 "two_owner_conversations":[5,3],
 "two_owner_messages":[4,2],
 "authenticated_session_revoke_after_restore":"A_DENIED_B_ALLOWED",
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
