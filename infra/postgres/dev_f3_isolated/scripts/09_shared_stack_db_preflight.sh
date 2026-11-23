#!/usr/bin/env bash
# Build real API-code DB authority witnesses and run on private shared Docker network.
# This is NOT full API HTTP startup: C018/Keycloak/BFF unavailable in DB-only CI.
set -euo pipefail
source "$(dirname "$0")/_lib.sh"
require_lab_ready
secure_log
: "${SOURCE_REPO:?Set local readonly Git checkout}"
[[ "$LAB_PROJECT" == ragfinance_f3_db_lab_* ]] || { echo STOP_WRONG_PROJECT >&2; exit 70; }
[[ "$(dbpsql -Atc "SELECT current_database()")" == "rag_finance_f3_lab" ]] || { echo STOP_WRONG_DB >&2; exit 70; }
[[ "$(dbpsql -Atc "SELECT count(*) FROM db55_audit.migration_runs WHERE status='APPLIED'")" == 10 ]] || { echo STOP_NEED_001_010 >&2; exit 70; }
[[ "$(dbpsql -Atc "SELECT status FROM db55_audit.bridge_runs WHERE id=1")" == APPLIED ]] || { echo STOP_NEED_DB55_BRIDGE >&2; exit 70; }
[[ ! -e "$LAB_WORK/api-source" && ! -e "$LAB_WORK/service-client-secrets" ]] || { echo STOP_PREEXISTING_CLIENT_TEST_STATE >&2; exit 70; }
code_ref=c5e271d0fab8ab34c92a2da933ba6b194d1f1e9a
git -C "$SOURCE_REPO" cat-file -e "$code_ref^{commit}" || { echo STOP_PINNED_API_COMMIT_UNAVAILABLE >&2; exit 70; }
mkdir -p "$LAB_WORK/api-source" "$LAB_WORK/service-client-secrets/product" "$LAB_WORK/service-client-secrets/bootstrap"
chmod 0700 "$LAB_WORK/service-client-secrets/"{product,bootstrap}
git -C "$SOURCE_REPO" archive "$code_ref" | tar -xf - -C "$LAB_WORK/api-source"
for spec in \
  "apps/api/private_staging_asgi.py:6072e7586d922737117dee27d61798df0cb9a6fc" \
  "apps/api/private_staging_bootstrap_asgi.py:3df807f53c865ebb29f8e8f26d0a8819149b46f9" \
  "src/phase3/auth/staging_service_profile.py:5fc1f3f64708ebb5f6756d5cf4d37d3acf9167b3"; do
  path="${spec%:*}"; want="${spec#*:}"
  [[ "$(git hash-object "$LAB_WORK/api-source/$path")" == "$want" ]] || { echo STOP_PINNED_API_MODULE_MISMATCH >&2; exit 70; }
done
cp "$LAB_SECRETS/ca.crt" "$LAB_WORK/service-client-secrets/product/ca.crt"
cp "$LAB_SECRETS/ca.crt" "$LAB_WORK/service-client-secrets/bootstrap/ca.crt"
for target in product bootstrap; do
  : > "$LAB_WORK/service-client-secrets/$target/pgpass"
done
roles_product=(history_app auth_revoker)
roles_bootstrap=(auth_trust_api auth_login_bootstrap auth_login_claim_reader auth_login_issuer auth_mapper auth_login_binder auth_login_reader)
for role in "${roles_product[@]}"; do
  [[ -s "$LAB_WORK/$role.password" ]] || { echo STOP_MISSING_PRODUCT_PASSWORD_FILE >&2;exit 70; }
  printf 'demo-db:5432:rag_finance_f3_lab:%s:%s\n' "$role" "$(cat "$LAB_WORK/$role.password")" >> "$LAB_WORK/service-client-secrets/product/pgpass"
done
for role in "${roles_bootstrap[@]}"; do
  [[ -s "$LAB_WORK/$role.password" ]] || { echo STOP_MISSING_BOOTSTRAP_PASSWORD_FILE >&2;exit 70; }
  printf 'demo-db:5432:rag_finance_f3_lab:%s:%s\n' "$role" "$(cat "$LAB_WORK/$role.password")" >> "$LAB_WORK/service-client-secrets/bootstrap/pgpass"
done
chmod 0600 "$LAB_WORK/service-client-secrets/"{product,bootstrap}/{ca.crt,pgpass}
[[ "$(wc -l < "$LAB_WORK/service-client-secrets/product/pgpass")" == 2 ]] || exit 70
[[ "$(wc -l < "$LAB_WORK/service-client-secrets/bootstrap/pgpass")" == 7 ]] || exit 70
{
  printf 'LAB_API_SRC=%q\n' "$LAB_WORK/api-source"
  printf 'LAB_API_PRODUCT_SECRETS=%q\n' "$LAB_WORK/service-client-secrets/product"
  printf 'LAB_API_BOOTSTRAP_SECRETS=%q\n' "$LAB_WORK/service-client-secrets/bootstrap"
} >> "$LAB_ROOT/lab.env"
chmod 0600 "$LAB_ROOT/lab.env"
shared_compose() {
  docker compose -f "$BUNDLE_ROOT/compose.lab.yaml" -f "$BUNDLE_ROOT/compose.shared-witness.yaml" \
    --env-file "$LAB_ROOT/lab.env" -p "$LAB_PROJECT" "$@"
}
shared_compose config -q
shared_compose build product-db-witness bootstrap-db-witness > "$LAB_WORK/shared_client_build.log" 2>&1 || {
  echo STOP_SHARED_CLIENT_IMAGE_BUILD >&2;exit 70;
}
for target in product bootstrap; do
  if ! shared_compose run --no-deps --rm -T "$target-db-witness" > "$LAB_WORK/$target-db-witness.log" 2>&1; then
    echo "STOP_REAL_${target}_DB_CODE_PREFLIGHT_FAILED" >&2
    exit 70
  fi
done
grep -Fq 'PRODUCT_API_REAL_DB_PREFLIGHT=2/2_PASS' "$LAB_WORK/product-db-witness.log" || { echo STOP_PRODUCT_REAL_SOURCE_MARKER >&2;exit 70; }
grep -Fq 'BOOTSTRAP_API_REAL_DB_PREFLIGHT=7/7_PASS' "$LAB_WORK/bootstrap-db-witness.log" || { echo STOP_BOOTSTRAP_REAL_SOURCE_MARKER >&2;exit 70; }
shared_compose images > "$LAB_WORK/shared_client_image_receipt.txt"
echo 'PINNED_REAL_API_SOURCE_MODULES=3/3_PASS'
echo 'PRODUCT_API_REAL_DB_PREFLIGHT=2/2_PASS'
echo 'BOOTSTRAP_API_REAL_DB_PREFLIGHT=7/7_PASS'
echo 'SHARED_PRIVATE_DOCKER_NETWORK_ROLE_SEPARATION=PASS'
echo 'NEGATIVE_WRONG_ROLE_AND_WEAK_TLS=4/4_DENIED'
echo 'REAL_HTTP_API_BOOTSTRAP_STARTUP=NOT_ATTEMPTED_NO_C018_IDP'
