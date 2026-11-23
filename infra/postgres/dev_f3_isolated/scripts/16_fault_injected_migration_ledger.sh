#!/usr/bin/env bash
# Deterministic negative tests of ACTUAL 03 installer on a NEW isolated cluster.
# No accepted Mac demo or main test cluster is modified. Fake ledgers are test-only.
set -euo pipefail
source "$(dirname "$0")/_lib.sh"
require_lab_ready; secure_log
[[ "$LAB_PROJECT" == ragfinance_f3_db_lab_* && "$LAB_DB" == rag_finance_f3_lab ]] || exit 70
parent_work="$LAB_WORK"
second_lab="$LAB_WORK/ledger_fault_probe_$(openssl rand -hex 4)"
[[ ! -e "$second_lab" ]] || exit 70
(
  export LAB_ROOT="$second_lab"
  bash "$BUNDLE_ROOT/scripts/00_prepare_source.sh" > "$parent_work/ledger_fault_prepare.log"
  bash "$BUNDLE_ROOT/scripts/01_create_isolated_lab.sh" > "$parent_work/ledger_fault_start.log"
  bash "$BUNDLE_ROOT/scripts/02_provision_roles.sh" > "$parent_work/ledger_fault_roles.log"
  echo 'LEDGER_FAULT_STAGE=ISOLATED_CLUSTER_PROVISIONED'
  source "$BUNDLE_ROOT/scripts/_lib.sh"
  require_lab_ready
  [[ "$(dbpsql -Atc 'SELECT current_database()')" == rag_finance_f3_lab ]] || exit 70
  [[ "$(dbpsql -Atc 'SELECT count(*) FROM db55_audit.migration_runs')" == 0 ]] || exit 70
  [[ "$(dbpsql -Atc "SELECT count(*) FROM pg_namespace WHERE nspname in ('auth_l1','history_l1')")" == 0 ]] || exit 70
  cluster="$(dbpsql -Atc 'SELECT system_identifier FROM pg_control_system()')"
  echo 'LEDGER_FAULT_STAGE=LEDGER_EMPTY_CHECKED'
  # STARTED recorded; interrupted/ambiguous migration is intentionally NOT
  # silently retried, even on an otherwise empty database.
  row="$(awk -F '\t' '$1=="001" && $2=="UP" {print $0}' "$LAB_SOURCE/manifest.tsv")"
  IFS=$'\t' read -r ver direction commit path blob <<< "$row"
  sha="$(shasum -a 256 "$LAB_SOURCE/$(basename "$path")" | awk '{print $1}')"
  dbpsql -q -c "INSERT INTO db55_audit.migration_runs
  (version,source_commit,git_blob_sha1,sql_sha256,status,cluster_system_id)
  VALUES('001','$commit','$blob','$sha','STARTED','$cluster');" >/dev/null
  if bash "$BUNDLE_ROOT/scripts/03_apply_pinned_001_010.sh" > "$LAB_WORK/partial_probe.log" 2>&1; then
    echo STOP_PARTIAL_LEDGER_WAS_REPLAYED >&2;exit 70
  fi
  grep -Fq STOP_PARTIAL_LEDGER_MANUAL_RECONCILIATION "$LAB_WORK/partial_probe.log" || {
    echo STOP_PARTIAL_LEDGER_FAILED_FOR_OTHER_REASON >&2;exit 70;
  }
  [[ "$(dbpsql -Atc "SELECT status FROM db55_audit.migration_runs WHERE version='001'")" == STARTED ]] || exit 70
  [[ "$(dbpsql -Atc "SELECT count(*) FROM pg_namespace WHERE nspname in ('auth_l1','history_l1')")" == 0 ]] || exit 70
  echo 'LEDGER_FAULT_STAGE=STARTED_REJECTED'
  dbpsql -q -c "DELETE FROM db55_audit.migration_runs WHERE version='001';" >/dev/null
  # Populate the FULL 10-entry ledger with *matching* pins, cluster ID, time
  # and TX ID but NEVER apply SQL. Old installer would incorrectly return
  # ALREADY_APPLIED; hardened installer must check actual 14 tables + RLS.
  while IFS=$'\t' read -r ver direction commit path blob <&3; do
    [[ "$direction" == UP ]] || continue
    sha="$(shasum -a 256 "$LAB_SOURCE/$(basename "$path")" | awk '{print $1}')"
    dbpsql -q -c "INSERT INTO db55_audit.migration_runs
    (version,source_commit,git_blob_sha1,sql_sha256,status,cluster_system_id,started_at,applied_at,applied_txid)
    VALUES('$ver','$commit','$blob','$sha','APPLIED','$cluster',clock_timestamp()-interval '1 minute',clock_timestamp(),1);" >/dev/null
  done 3< <(tail -n +2 "$LAB_SOURCE/manifest.tsv")
  echo 'LEDGER_FAULT_STAGE=TEN_FAKE_APPLIED_INSERTED'
  count_check="$(dbpsql -Atc "SELECT count(*) FROM db55_audit.migration_runs")" || {
    echo STOP_LEDGER_FAKE_COUNT_QUERY_FAILED >&2;exit 70;
  }
  echo "LEDGER_FAULT_FAKE_ROW_COUNT=$count_check"
  [[ "$count_check" == 10 ]] || { echo STOP_LEDGER_FAKE_TEN_NOT_WRITTEN >&2;exit 70; }
  if dbpsql -q -c "INSERT INTO db55_audit.migration_runs
  (version,source_commit,git_blob_sha1,sql_sha256,status,cluster_system_id)
  VALUES('001','$commit','$blob','$sha','STARTED','$cluster');" > "$LAB_WORK/duplicate_probe.log" 2>&1; then
    echo STOP_DUPLICATE_LEDGER_ROW_ALLOWED >&2;exit 70
  fi
  if ! grep -Eiq 'duplicate key|unique constraint|23505' "$LAB_WORK/duplicate_probe.log"; then
    echo 'STOP_DUPLICATE_NEGATIVE_WRONG_SQL_FAILURE' >&2
    # Fixture IDs and values only, NO real user data or credentials.
    tail -n 8 "$LAB_WORK/duplicate_probe.log" >&2
    exit 70
  fi
  [[ "$(dbpsql -Atc "SELECT count(*) FROM db55_audit.migration_runs")" == 10 ]] || {
    echo STOP_DUPLICATE_LEDGER_COUNT_DRIFT >&2;exit 70;
  }
  echo 'LEDGER_FAULT_STAGE=DUPLICATE_REJECTED'
  # SOURCE SHA or cluster mismatch must not be silently accepted.
  dbpsql -q -c "UPDATE db55_audit.migration_runs SET sql_sha256=repeat('e',64) WHERE version='001';" >/dev/null
  if bash "$BUNDLE_ROOT/scripts/03_apply_pinned_001_010.sh" > "$LAB_WORK/digest_probe.log" 2>&1; then
    echo STOP_MISMATCHED_DIGEST_ACCEPTED >&2;exit 70
  fi
  grep -Fq STOP_EXISTING_LEDGER_SOURCE_CLUSTER_OR_DIGEST_DRIFT "$LAB_WORK/digest_probe.log" || exit 70
  dbpsql -q -c "UPDATE db55_audit.migration_runs SET sql_sha256='$(
    awk -F '\t' '$1=="001" && $2=="UP" {print $4}' "$LAB_SOURCE/manifest.tsv" | xargs -n1 basename |
    while read -r n; do shasum -a 256 "$LAB_SOURCE/$n" | awk '{print $1}'; done)' WHERE version='001';" >/dev/null
  # The source witness is intact, but completion metadata may be incomplete.
  echo 'LEDGER_FAULT_STAGE=DIGEST_REJECTED'
  dbpsql -q -c "UPDATE db55_audit.migration_runs SET applied_at=NULL WHERE version='001';" >/dev/null
  if bash "$BUNDLE_ROOT/scripts/03_apply_pinned_001_010.sh" > "$LAB_WORK/commit_probe.log" 2>&1; then
    echo STOP_UNCOMMITTED_LEDGER_ACCEPTED >&2;exit 70
  fi
  grep -Fq STOP_EXISTING_LEDGER_NOT_COMMITTED "$LAB_WORK/commit_probe.log" || exit 70
  echo 'LEDGER_FAULT_STAGE=COMMIT_METADATA_REJECTED'
  dbpsql -q -c "UPDATE db55_audit.migration_runs SET applied_at=clock_timestamp() WHERE version='001';" >/dev/null
  if bash "$BUNDLE_ROOT/scripts/03_apply_pinned_001_010.sh" > "$LAB_WORK/forged_full_probe.log" 2>&1; then
    echo STOP_FORGED_FULL_LEDGER_ACCEPTED >&2;exit 70
  fi
  grep -Fq STOP_EXISTING_LEDGER_WITH_SCHEMA_DRIFT_OR_MISSING_SQL "$LAB_WORK/forged_full_probe.log" || exit 70
  [[ "$(dbpsql -Atc "SELECT count(*) FROM pg_namespace WHERE nspname in ('auth_l1','history_l1')")" == 0 ]] || exit 70
  echo 'LEDGER_FAULT_STAGE=FORGED_LEDGER_WITHOUT_SCHEMA_REJECTED'
  export ALLOW_DELETE_F3_LAB=YES
  bash "$BUNDLE_ROOT/scripts/07_cleanup_lab_ONLY.sh" > "$parent_work/ledger_fault_cleanup.log"
)
echo 'LEDGER_FAULT_STAGE=SECOND_LAB_CLEANED'
cat > "$parent_work/ledger_fault_injection_receipt.json" <<'JSON'
{
  "contract_version": "f3.db.ledger_fault_injection.v1",
  "scope": "second disposable cluster, no original demo, no migrations applied",
  "partial_STARTED": "FAIL_CLOSED_NO_RETRY",
  "duplicate_primary_key": "REJECTED",
  "sha256_mismatch": "REJECTED",
  "missing_applied_metadata": "REJECTED",
  "forged_complete_ledger_without_schema": "REJECTED",
  "existing_main_lab_untouched": true,
  "second_lab_containers_volumes_removed": true,
  "admission_from_forged_ledger": "NOT_ALLOWED"
}
JSON
chmod 0600 "$parent_work/ledger_fault_injection_receipt.json"
echo 'LEDGER_PARTIAL_STARTED_FAIL_CLOSED=PASS'
echo 'LEDGER_DUPLICATE_VERSION_REJECTED=PASS'
echo 'LEDGER_SOURCE_DIGEST_DRIFT_REJECTED=PASS'
echo 'LEDGER_MISSING_COMMIT_METADATA_REJECTED=PASS'
echo 'LEDGER_FORGED_FULL_WITHOUT_SCHEMA_REJECTED=PASS'
echo 'LEDGER_FAULT_LAB_CLEANUP=PASS'
