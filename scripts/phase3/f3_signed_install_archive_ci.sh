#!/usr/bin/env bash
# Only disposable GitHub-hosted runner, only exact candidate tags, no target.
set -euo pipefail
umask 077
[[ "$CI" == true && "$GITHUB_ACTIONS" == true && "$RUNNER_OS" == Linux &&
   "$(id -un)" == runner && "$PWD" == "$GITHUB_WORKSPACE" &&
   "$GITHUB_WORKSPACE" == /home/runner/work/* && "$GITHUB_SHA" =~ ^[a-f0-9]{40}$ ]]
test "$(git rev-parse HEAD)" = "$GITHUB_SHA"
test ! -e infra/postgres/migrations/011_product_answer_claims.up.sql
api="api-f3-browser:$GITHUB_SHA"
web="f3-compose-browser-web:$GITHUB_SHA"
test "$API_F3_BROWSER_IMAGE" = "$api"
test "$F3_COMPOSE_BROWSER_WEB_IMAGE" = "$web"
tmp="$(mktemp -d "$RUNNER_TEMP/f3-signed-install.XXXXXXXX")"
trap 'rm -rf -- "$tmp"' EXIT
archive="$tmp/images.tar"
for tag in "$api" "$web"; do
  test "$(docker image inspect -f '{{index .Config.Labels "org.opencontainers.image.revision"}}' "$tag")" = "$GITHUB_SHA"
  test "$(docker image inspect -f '{{.Os}}/{{.Architecture}}' "$tag")" = linux/amd64
  test -z "$(docker ps -aq --filter "ancestor=$tag")"
done
api_id="$(docker image inspect -f '{{.Id}}' "$api")"
web_id="$(docker image inspect -f '{{.Id}}' "$web")"
[[ "$api_id" =~ ^sha256:[a-f0-9]{64}$ && "$web_id" =~ ^sha256:[a-f0-9]{64}$ ]]
test "$api_id" != "$web_id"
test "$(docker image inspect -f '{{.Config.User}}' "$api")" = 11001:11001
test "$(docker image inspect -f '{{.Config.User}}' "$web")" = 11003:11003
start="$(date +%s%N)"
docker image save -o "$archive" "$api" "$web"
bytes="$(stat -c %s "$archive")"
digest="$(sha256sum "$archive" | cut -d' ' -f1)"
[[ "$bytes" -gt 1000000 && "$digest" =~ ^[a-f0-9]{64}$ ]]
# Negative test: verify the same manifest against a tampered archive.
# Never send corrupted bytes to Docker. Restore precisely the original length.
printf X >> "$archive"
if printf '%s  %s\n' "$digest" "$archive" | sha256sum --check --status; then
  echo F3_ARCHIVE_TAMPER_NOT_REJECTED >&2; exit 1
fi
truncate -s "$bytes" "$archive"
printf '%s  %s\n' "$digest" "$archive" | sha256sum --check --status
docker image rm "$api" "$web" >/dev/null
for tag in "$api" "$web"; do
  if docker image inspect "$tag" >/dev/null 2>&1; then
    echo F3_EXACT_TAG_NOT_REMOVED >&2; exit 1
  fi
done
# Local load only; no registry push, pull, target or existing volume action.
docker image load -i "$archive" >/dev/null
test "$(docker image inspect -f '{{.Id}}' "$api")" = "$api_id"
test "$(docker image inspect -f '{{.Id}}' "$web")" = "$web_id"
elapsed="$(( ($(date +%s%N)-start)/1000000 ))"
mkdir -p ci_receipts
F3_ARCHIVE_HASH="$digest" F3_ARCHIVE_BYTES="$bytes" F3_INSTALL_MS="$elapsed" \
F3_API_IMAGE_ID="$api_id" F3_WEB_IMAGE_ID="$web_id" python - <<'PY'
import json,os
from pathlib import Path
d={"schema":"foundation.f3.signed_oci_archive_install_ci.v1",
   "source_sha":os.environ["GITHUB_SHA"],"run_id":os.environ["GITHUB_RUN_ID"],
   "run_attempt":os.environ["GITHUB_RUN_ATTEMPT"],
   "api_image_id":os.environ["F3_API_IMAGE_ID"],"web_image_id":os.environ["F3_WEB_IMAGE_ID"],
   "archive_sha256":os.environ["F3_ARCHIVE_HASH"],"archive_bytes":int(os.environ["F3_ARCHIVE_BYTES"]),
   "local_save_remove_load_ms":int(os.environ["F3_INSTALL_MS"]),
   "tampered_archive_rejected_before_load":True,"both_tags_absent_before_load":True,
   "exact_local_image_ids_restored":True,"scope":"DISPOSABLE_CI_LOCAL_INSTALL_ONLY",
   "registry_digest":None,"target_verified":False,"previous_release_rollback_verified":False,
   "accepted":False,"release":"HOLD"}
Path("ci_receipts/f3_signed_archive_install.json").write_text(json.dumps(d,indent=2)+"\n")
print("F3_SIGNED_EXACT_OCI_SAVE_REMOVE_LOAD_TAMPER_DENY_PASS")
PY
