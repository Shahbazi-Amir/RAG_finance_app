#!/usr/bin/env bash
# Destructive ONLY for this newly generated, explicitly named lab and restore volumes.
set -euo pipefail
source "$(dirname "$0")/_lib.sh"
[[ "${ALLOW_DELETE_F3_LAB:-NO}" == 'YES' ]] || { echo 'STOP_SET_ALLOW_DELETE_F3_LAB_YES' >&2; exit 70; }
for vol in "$LAB_VOLUME" "$LAB_RESTORE_VOLUME"; do
  if docker volume inspect "$vol" >/dev/null 2>&1; then
    owner="$(docker volume inspect -f '{{ index .Labels "com.docker.compose.project" }}' "$vol")"
    [[ "$owner" == "$LAB_PROJECT" ]] || { echo "STOP_VOLUME_NOT_OWNED_BY_PROJECT:$vol" >&2; exit 70; }
  fi
done
compose --profile restore down --volumes --remove-orphans
printf '%s\n' 'ONLY_DISPOSABLE_LAB_CONTAINERS_AND_VOLUMES_CLEANED=YES' 'ACCEPTED_MAC_DEMO_DATABASE_UNTOUCHED=YES'
