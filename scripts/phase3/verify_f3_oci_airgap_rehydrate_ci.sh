#!/usr/bin/env bash
# Test actual disposable local Docker save/remove/load; NOT a Mac or prod rollback.
set -euo pipefail
if [[ "$CI" != true || "$GITHUB_ACTIONS" != true || "$RUNNER_OS" != Linux ||
      "$GITHUB_WORKSPACE" != /home/runner/work/* || "$PWD" != "$GITHUB_WORKSPACE" ||
      "$(uname -s)" != Linux || "$(id -un)" != runner ]]; then
  echo F3_AIRGAP_DISPOSABLE_GHA_ONLY >&2; exit 78
fi
if [[ ! "$GITHUB_SHA" =~ ^[a-f0-9]{40}$ ||
      "$(git rev-parse HEAD)" != "$GITHUB_SHA" ]]; then
  echo F3_AIRGAP_EXACT_SOURCE_MISMATCH >&2; exit 78
fi
test ! -e infra/postgres/migrations/011_product_answer_claims.up.sql
api=rag-f3-app-only-api:ci
web=rag-f3-app-only-web:ci
for img in "$api" "$web"; do
  test "$(docker image inspect -f '{{index .Config.Labels "org.opencontainers.image.revision"}}' "$img")" = "$GITHUB_SHA"
  test "$(docker image inspect -f '{{.Os}}/{{.Architecture}}' "$img")" = linux/amd64
done
api_id="$(docker image inspect -f '{{.Id}}' "$api")"
web_id="$(docker image inspect -f '{{.Id}}' "$web")"
[[ "$api_id" =~ ^sha256:[a-f0-9]{64}$ && "$web_id" =~ ^sha256:[a-f0-9]{64}$ ]]
test "$api_id" != "$web_id"
test "$(docker image inspect -f '{{.Config.User}}' "$api")" = 11001:11001
test "$(docker image inspect -f '{{.Config.User}}' "$web")" = 11003:11003
tmp="$(mktemp -d "$RUNNER_TEMP/f3_airgap_XXXXXXXX")"
c_api="f3-airgap-api-$GITHUB_RUN_ID-$GITHUB_RUN_ATTEMPT"
c_web="f3-airgap-web-$GITHUB_RUN_ID-$GITHUB_RUN_ATTEMPT"
cleanup() {
  docker rm -f "$c_web" "$c_api" >/dev/null 2>&1 || true
  rm -rf -- "$tmp"
}
trap cleanup EXIT
archive="$tmp/app-only-images.tar"
start="$(date +%s)"
docker image save -o "$archive" "$api" "$web"
test -s "$archive"
archive_sha="$(sha256sum "$archive" | cut -d' ' -f1)"
archive_bytes="$(stat -c %s "$archive")"
[[ "$archive_sha" =~ ^[a-f0-9]{64}$ && "$archive_bytes" -gt 1000000 ]]
docker image rm "$api" "$web" >/dev/null
if docker image inspect "$api" >/dev/null 2>&1 ||
   docker image inspect "$web" >/dev/null 2>&1; then
  echo F3_AIRGAP_IMAGE_TAG_NOT_REMOVED >&2; exit 1
fi
test "$(sha256sum "$archive" | cut -d' ' -f1)" = "$archive_sha"
docker image load -i "$archive" >/dev/null
test "$(docker image inspect -f '{{.Id}}' "$api")" = "$api_id"
test "$(docker image inspect -f '{{.Id}}' "$web")" = "$web_id"
docker run -d --name "$c_api" --network none --read-only --cap-drop ALL \
  --security-opt no-new-privileges --pids-limit 64 --memory 256m \
  --user 11001:11001 --tmpfs /tmp:rw,noexec,nosuid,size=16m,uid=11001,gid=11001 \
  "$api" >/dev/null
docker run -d --name "$c_web" --network none --read-only --cap-drop ALL \
  --security-opt no-new-privileges --pids-limit 128 --memory 512m \
  --user 11003:11003 --tmpfs /tmp:rw,nosuid,size=32m,uid=11003,gid=11003 \
  --tmpfs /srv/release/apps/web/.next/cache:rw,nosuid,size=64m,uid=11003,gid=11003 \
  "$web" >/dev/null
for i in $(seq 1 70); do
  if docker exec "$c_api" python3 -c "import urllib.request;urllib.request.urlopen('http://127.0.0.1:8080/health/live',timeout=2)" >/dev/null 2>&1;then break;fi
  sleep 1
done
for i in $(seq 1 70); do
  if docker exec "$c_web" node -e "fetch('http://127.0.0.1:3000/api/product-capabilities').then(r=>process.exit(r.ok?0:1)).catch(()=>process.exit(1))" >/dev/null 2>&1;then break;fi
  sleep 1
done
docker exec -i "$c_api" python3 - <<'PY'
import json,urllib.request
from urllib.error import HTTPError
base='http://127.0.0.1:8080'
with urllib.request.urlopen(base+'/health/live',timeout=5) as r:
    o=json.loads(r.read())
    assert r.status==200 and o['process_alive'] is True and o['application_ready'] is False
for path in ('/health/ready','/v1/messages'):
    request=urllib.request.Request(base+path,
       data=b'{invalid-json'+b'X'*65536 if path.endswith('messages') else None,
       method='POST' if path.endswith('messages') else 'GET')
    try:
        urllib.request.urlopen(request,timeout=5)
        raise AssertionError('APP_ONLY_DID_NOT_FAIL_CLOSED')
    except HTTPError as e:
        assert e.code==503,(path,e.code)
print('F3_REIMPORT_REAL_API_LIVE200_READY503_SEND503_PASS')
PY
docker exec "$c_web" node -e '
(async()=>{
 const b="http://127.0.0.1:3000";
 const r=await fetch(b+"/api/product-capabilities"),j=await r.json();
 if(!r.ok||j.send_mode!=="DISABLED"||j.engine_available!==false||j.generation_available!==false) process.exit(1);
 const denied=await fetch(b+"/api/history/messages",{method:"POST",headers:{"content-type":"application/json"},body:"{invalid-json"});
 const x=await denied.json();
 if(denied.status!==503||x.error!=="ENGINE_NOT_AVAILABLE")process.exit(2);
 console.log("F3_REIMPORT_NEXT_DISABLED_SEND503_PASS");
})().catch(()=>process.exit(3));'
for cid in "$c_api" "$c_web"; do
  test -z "$(docker port "$cid" 2>/dev/null)"
  test "$(docker inspect -f '{{.HostConfig.ReadonlyRootfs}}' "$cid")" = true
done
elapsed=$(( $(date +%s)-start ))
mkdir -p ci_receipts/foundation
F3_API_ID="$api_id" F3_WEB_ID="$web_id" F3_ARCHIVE_SHA="$archive_sha" \
F3_ARCHIVE_BYTES="$archive_bytes" F3_ELAPSED="$elapsed" python3 - <<'PY'
import json,os
from pathlib import Path
doc={
 "schema":"foundation.f3.tested_oci_airgap_reimport_smoke.v1",
 "git_sha":os.environ["GITHUB_SHA"],"run_id":os.environ["GITHUB_RUN_ID"],
 "environment":"DISPOSABLE_CI_RUNNER_ONLY",
 "no_network_and_no_host_published_ports":True,
 "image_ids_before_and_after_archive_identical":True,
 "archive_sha256":os.environ["F3_ARCHIVE_SHA"],
 "archive_size_bytes":int(os.environ["F3_ARCHIVE_BYTES"]),
 "image_ids":{"api":os.environ["F3_API_ID"],"web":os.environ["F3_WEB_ID"]},
 "web_send_503":True,"api_send_503":True,"api_ready_503":True,
 "api_live_200":True,"web_capability_send_disabled":True,
 "measured_local_round_trip_seconds":int(os.environ["F3_ELAPSED"]),
 "backup_pg_restore":False,"mac_target_tested":False,
 "registry_manifest_digest":None,"signed_release":False,
 "approved_RPO_threshold":None,"approved_RTO_threshold":None,
 "owner_acceptance":False,"security_policy_approved":False,
 "release_state":"HOLD"}
Path("ci_receipts/foundation/oci_airgap_restore_ci.json").write_text(
 json.dumps(doc,indent=2,sort_keys=True)+"\n")
print("F3_DOCKER_SAVE_REMOVE_LOAD_REAL_HTTP_CI_PASS_NOT_TARGET_ROLLBACK")
PY
