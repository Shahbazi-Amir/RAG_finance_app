#!/usr/bin/env bash
set -euo pipefail
BUNDLE_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
: "${LAB_ROOT:?Set LAB_ROOT to a NEW scratch folder outside accepted Mac demo paths}"
[[ -f "$LAB_ROOT/lab.env" ]] || { echo "STOP_LAB_ENV_ABSENT $LAB_ROOT" >&2; exit 70; }
# shellcheck disable=SC1091
source "$LAB_ROOT/lab.env"
[[ "$LAB_PROJECT" == ragfinance_f3_db_lab_* ]] || { echo 'STOP_UNEXPECTED_LAB_PROJECT' >&2; exit 70; }
[[ "$LAB_VOLUME" == rag_finance_f3_LAB_* ]] || { echo 'STOP_UNEXPECTED_LAB_VOLUME' >&2; exit 70; }
[[ "$LAB_RESTORE_VOLUME" == rag_finance_f3_RESTORE_* ]] || { echo 'STOP_UNEXPECTED_RESTORE_VOLUME' >&2; exit 70; }
[[ "$LAB_VOLUME" != 'rag_finance_f3_demo_pg17_20261121' && "$LAB_RESTORE_VOLUME" != 'rag_finance_f3_demo_pg17_20261121' ]] || { echo 'STOP_PROTECTED_DEMO_VOLUME' >&2; exit 70; }
[[ "$LAB_DB" == rag_finance_f3_lab ]] || { echo 'STOP_NOT_THE_LAB_DB' >&2; exit 70; }
[[ "$LAB_ROOT" != *PRODUCT_FIRST_START_PREP* && "$LAB_ROOT" != *CENTRAL_FIRST_START_20261121* ]] || { echo 'STOP_PROTECTED_DEMO_DIRECTORY' >&2; exit 70; }
compose(){ docker compose -f "$BUNDLE_ROOT/compose.lab.yaml" -p "$LAB_PROJECT" --env-file "$LAB_ROOT/lab.env" "$@"; }
dbpsql(){ local svc="${DB_SERVICE:-lab-db}" db="${DB_NAME:-rag_finance_f3_lab}"; compose exec -T "$svc" psql -X -v ON_ERROR_STOP=1 -U postgres -d "$db" "$@"; }
dbname(){ local svc="${DB_SERVICE:-lab-db}"; compose exec -T "$svc" psql -X -Atq -v ON_ERROR_STOP=1 -U postgres -d postgres -c 'SELECT current_setting('\''server_version'\'')'; }
require_lab_ready(){ command -v docker >/dev/null || { echo 'STOP_DOCKER_NOT_AVAILABLE' >&2; exit 70; }; test -s "$LAB_SECRETS/superuser_password" && test -s "$LAB_SECRETS/ca.crt" && test -d "$LAB_SOURCE" || { echo 'STOP_LAB_INPUTS_MISSING' >&2; exit 70; }; }
secure_log(){ mkdir -p "$LAB_WORK"; chmod 0700 "$LAB_WORK"; umask 077; }
