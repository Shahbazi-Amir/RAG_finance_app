#!/usr/bin/env bash
# After separate restore, re-open the actual source Product/Bootstrap DB verifier
# in distinct container clients, with real TLS verify-full for the restore hostname.
set -euo pipefail
source "$(dirname "$0")/_lib.sh"
require_lab_ready
secure_log
[[ "$LAB_PROJECT" == ragfinance_f3_db_lab_* ]] || { echo STOP_UNSAFE_PROJECT >&2;exit 70; }
[[ -s "$LAB_WORK/restore_receipt.txt" && -f "$LAB_WORK/restore-tested.marker" ]] || { echo STOP_RESTORE_EVIDENCE_ABSENT >&2;exit 70; }
[[ -s "$LAB_WORK/api-source/apps/api/private_staging_asgi.py" ]] || { echo STOP_API_SOURCE_ABSENT >&2;exit 70; }
[[ -s "$LAB_WORK/service-client-secrets/product/pgpass" && -s "$LAB_WORK/service-client-secrets/bootstrap/pgpass" ]] || { echo STOP_CLIENT_SECRETS_ABSENT >&2;exit 70; }
if [[ "$(DB_SERVICE=restore-db DB_NAME=rag_finance_f3_lab_restore dbpsql -Atc "SELECT current_database()")" != rag_finance_f3_lab_restore ]]; then
  echo STOP_WRONG_RESTORE_DATABASE >&2;exit 70
fi
# Reuse existing lab-only credentials; never mount the PostgreSQL superuser passfile.
for target in product bootstrap; do
  pgpass="$LAB_WORK/service-client-secrets/$target/pgpass"
  if [[ "$target" == product ]]; then
    roles=(history_app auth_revoker)
  else
    roles=(auth_trust_api auth_login_bootstrap auth_login_claim_reader auth_login_issuer auth_mapper auth_login_binder auth_login_reader)
  fi
  for role in "${roles[@]}"; do
    [[ -s "$LAB_WORK/$role.password" ]] || { echo STOP_RESTORE_PASSWORD_ABSENT >&2;exit 70; }
    printf 'restore-db:5432:rag_finance_f3_lab_restore:%s:%s\n' "$role" "$(cat "$LAB_WORK/$role.password")" >> "$pgpass"
  done
  chmod 0600 "$pgpass"
done
shared_compose() {
  docker compose -f "$BUNDLE_ROOT/compose.lab.yaml" -f "$BUNDLE_ROOT/compose.shared-witness.yaml" \
    --env-file "$LAB_ROOT/lab.env" -p "$LAB_PROJECT" "$@"
}
shared_compose config -q
for target in product bootstrap; do
  shared_compose run --no-deps --rm -T \
    -e PG_EXPECTED_HOST=restore-db -e PG_EXPECTED_DB=rag_finance_f3_lab_restore \
    "$target-db-witness" > "$LAB_WORK/restored-$target-db-witness.log" 2>&1 || {
      echo "STOP_RESTORED_$target_REAL_APP_CODE" >&2; exit 70;
    }
done
grep -Fq 'PRODUCT_API_REAL_DB_PREFLIGHT=2/2_PASS' "$LAB_WORK/restored-product-db-witness.log" || exit 70
grep -Fq 'BOOTSTRAP_API_REAL_DB_PREFLIGHT=7/7_PASS' "$LAB_WORK/restored-bootstrap-db-witness.log" || exit 70
echo 'RESTORED_PRODUCT_API_REAL_CODE_TLS_ROLE_PREFLIGHT=2/2_PASS'
echo 'RESTORED_BOOTSTRAP_API_REAL_CODE_TLS_ROLE_PREFLIGHT=7/7_PASS'
echo 'RESTORE_STACK_TLS_VERIFY_FULL=9/9_PASS'
echo 'RESTORED_DATABASE_ROLES_USED_BY_REAL_APP_CODE=PASS'
