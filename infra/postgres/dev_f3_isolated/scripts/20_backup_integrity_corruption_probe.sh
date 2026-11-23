#!/usr/bin/env bash
# Negative backup integrity test on disposable PG lab artifact ONLY.
# Never restore corrupt data; exercise the pre-restore SHA-256 fail-closed
# gate using two independent defects: one flipped byte and truncation.
set -euo pipefail
source "$(dirname "$0")/_lib.sh"
require_lab_ready
secure_log
[[ "$LAB_PROJECT" == ragfinance_f3_db_lab_* && "$LAB_DB" == rag_finance_f3_lab ]] || { echo STOP_NOT_DISPOSABLE_LAB >&2;exit 70; }
[[ "$(dbpsql -Atc 'SELECT current_database()')" == rag_finance_f3_lab ]] || { echo STOP_NOT_SOURCE_LAB >&2;exit 70; }
source_dump="$LAB_WORK/backup.dump"
source_hash="$LAB_WORK/backup.dump.sha256"
[[ -s "$source_dump" && -s "$source_hash" && -s "$LAB_WORK/restore_receipt.txt" ]] || { echo STOP_ORIGINAL_BACKUP_AND_RESTORE_NOT_FOUND >&2;exit 70; }
shasum -a 256 -c "$source_hash" >/dev/null || { echo STOP_SOURCE_BACKUP_CORRUPTED >&2;exit 70; }
[[ "$(dbpsql -Atc "SELECT count(*) FROM db55_audit.migration_runs WHERE status='APPLIED'")" == 10 ]] || { echo STOP_LEDGER_INCOMPLETE >&2;exit 70; }
source_system_id="$(dbpsql -Atc 'SELECT system_identifier FROM pg_control_system()')"
restore_system_id="$(DB_SERVICE=restore-db DB_NAME=rag_finance_f3_lab_restore dbpsql -Atc 'SELECT system_identifier FROM pg_control_system()')"
[[ -n "$source_system_id" && -n "$restore_system_id" && "$source_system_id" != "$restore_system_id" ]] || { echo STOP_CLUSTER_NOT_INDEPENDENT >&2;exit 70; }
expected="$(awk 'NR==1{print $1}' "$source_hash")"
[[ "$expected" =~ ^[0-9a-f]{64}$ ]] || { echo STOP_SHA256_FORMAT >&2;exit 70; }
flip="$LAB_WORK/backup_single_byte_flipped_probe.dump"
trunc="$LAB_WORK/backup_truncated_probe.dump"
[[ ! -e "$flip" && ! -e "$trunc" ]] || { echo STOP_NEGATIVE_ARCHIVE_COLLISION >&2;exit 70; }
python3 - "$source_dump" "$flip" "$trunc" <<'PY'
from pathlib import Path
import sys
source,flip,trunc=map(Path,sys.argv[1:])
data=source.read_bytes()
assert len(data)>2048, "backup not large enough for meaningful negative"
offset=len(data)//2
changed=bytearray(data)
changed[offset]^=0x01
flip.write_bytes(changed)
trunc.write_bytes(data[:offset])
PY
chmod 0600 "$flip" "$trunc"
for case_path in "$flip" "$trunc"; do
  if printf '%s  %s\n' "$expected" "$case_path" | shasum -a 256 -c - > "$LAB_WORK/backup_negative_checksum.log" 2>&1; then
    echo 'STOP_MUTATED_OR_TRUNCATED_DUMP_PASSED_SHA256_CHECK' >&2; exit 70
  fi
  grep -Fqi 'FAILED' "$LAB_WORK/backup_negative_checksum.log" || { echo STOP_NEGATIVE_FAILED_FOR_UNEXPECTED_REASON >&2;exit 70; }
done
# Reconfirm original is untouched after both corrupt copies. No restore attempted
# from failed inputs, preserving the healthy source and existing restored cluster.
shasum -a 256 -c "$source_hash" >/dev/null || { echo STOP_BACKUP_SOURCE_CHANGED >&2;exit 70; }
source_after="$(dbpsql -Atc 'SELECT system_identifier FROM pg_control_system()')"
restore_after="$(DB_SERVICE=restore-db DB_NAME=rag_finance_f3_lab_restore dbpsql -Atc 'SELECT system_identifier FROM pg_control_system()')"
[[ "$source_after" == "$source_system_id" && "$restore_after" == "$restore_system_id" ]] || { echo STOP_CLUSTER_CHANGED_DURING_FAULT_TEST >&2;exit 70; }
python3 - "$LAB_WORK/backup_integrity_fault_receipt.json" "$source_dump" "$flip" "$trunc" "$expected" <<'PY'
import hashlib,json,sys
from pathlib import Path
out,good,flip,trunc=map(Path,sys.argv[1:5])
expected=sys.argv[5]
def h(p):return hashlib.sha256(p.read_bytes()).hexdigest()
assert h(good)==expected and h(flip)!=expected and h(trunc)!=expected
out.write_text(json.dumps({
 "contract_version":"f3.db.synthetic_backup_integrity_fault.v1",
 "environment":"PG17.11_automated_disposable_private_network",
 "source_backup_sha256":expected,
 "single_byte_changed_sha256_mismatch":"FAIL_CLOSED_BEFORE_RESTORE",
 "truncated_dump_sha256_mismatch":"FAIL_CLOSED_BEFORE_RESTORE",
 "healthy_dump_sha256_rechecked":"PASS",
 "healthy_source_and_independent_restore_cluster_ids_unchanged":True,
 "corrupt_archives_restored":False,
 "corrupt_restore_sql_attempts":0,
 "encrypted_offsite_backup":"NOT_TESTED",
 "pitr":"NOT_TESTED",
 "real_disaster_recovery":"NOT_TESTED",
 "rpo_rto_signed":"NOT_DEFINED",
 "module_gate":"NOT_ACCEPTED"
 },indent=2,sort_keys=True)+"\n")
PY
chmod 0600 "$LAB_WORK/backup_integrity_fault_receipt.json"
rm -- "$flip" "$trunc" "$LAB_WORK/backup_negative_checksum.log"
[[ ! -e "$flip" && ! -e "$trunc" ]] || { echo STOP_NEGATIVE_COPIES_NOT_CLEANED >&2;exit 70; }
echo 'BACKUP_ORIGINAL_SHA256_VERIFIED_BEFORE_AND_AFTER=PASS'
echo 'BACKUP_CORRUPTION_SHA256_FAIL_CLOSED=2/2_PASS'
echo 'BACKUP_HEALTHY_INDEPENDENT_CLUSTER_UNCHANGED=PASS'
echo 'BACKUP_CORRUPT_RESTORE=BLOCKED_BY_PRECHECK'
echo 'PRODUCTION_ENCRYPTED_RPO_RTO_AND_PITR=NOT_TESTED'
