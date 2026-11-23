#!/usr/bin/env bash
# Read-only, fail-closed preflight for an isolated candidate. NEVER deploys,
# pulls an image, mutates SQL, starts containers, or deletes a volume.
set -euo pipefail
abort(){ printf 'F3_APP_ONLY_PREFLIGHT_DENIED:%s\n' "$1" >&2; exit 73; }
project="${F3_PROJECT_NAME:-}"
[[ "$project" =~ ^f3-app-only-(ci|lab)-[a-z0-9][a-z0-9-]{7,48}$ ]] || abort PROJECT_NAMESPACE
[[ "$project" != *demo* && "$project" != *production* ]] || abort PROTECTED_NAME
ref="${F3_SOURCE_SHA:-}"
[[ "$ref" =~ ^[0-9a-f]{40}$ ]] || abort PIN_FORMAT
root="$(git rev-parse --show-toplevel 2>/dev/null)" || abort CHECKOUT_REQUIRED
[[ "$ref" == "$(git -C "$root" rev-parse HEAD)" ]] || abort SOURCE_SHA_DRIFT
tag="${F3_RELEASE_TAG:-}"
if [[ "${CI:-}" == true && "$tag" == ci ]]; then :;
else [[ "$tag" =~ ^[0-9a-f]{12,40}$ ]] || abort IMAGE_TAG_NOT_PINNED; fi
[[ -f "$root/infra/phase3_l1/compose.app-only.internal.yml" ]] || abort COMPOSE_NOT_FOUND
command -v docker >/dev/null || abort DOCKER_NOT_INSTALLED
docker compose version >/dev/null 2>&1 || abort COMPOSE_NOT_INSTALLED
file="$root/infra/phase3_l1/compose.app-only.internal.yml"
docker compose -f "$file" config -q || abort COMPOSE_INVALID
docker compose -f "$file" config --format json |
python3 -c '
import json,sys
doc=json.load(sys.stdin)
assert set(doc["services"])=={"api","web"}
assert doc["networks"]["private"]["internal"] is True
for service in doc["services"].values():
    assert service["read_only"] is True
    assert "ports" not in service
    assert service["environment"]["PHASE3_APP_MODE"]=="APP_ONLY"
    assert service["user"] in ("11001:11001","11003:11003")
    assert all(v.get("type")!="bind" for v in service.get("volumes",[]))
print("F3_APP_ONLY_TWO_SERVICE_NO_PUBLIC_PORTS_GUARD_PASS")
' || abort COMPOSE_NETWORK_SECURITY
if [[ "${1:-}" == --inspect-unused ]]; then
  [[ -z "$(docker compose -f "$file" ps -q 2>/dev/null)" ]] || abort EXISTING_PROJECT
fi
printf 'F3_APP_ONLY_PREFLIGHT_READ_ONLY_PASS sha=%s project=%s\n' "$ref" "$project"
