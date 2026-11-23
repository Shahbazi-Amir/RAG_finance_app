#!/usr/bin/env bash
# Public CI artifact contains only sanitized schema/role evidence, no password/DSN/PEM.
set -euo pipefail
source "$(dirname "$0")/_lib.sh"
require_lab_ready
secure_log
[[ -s "$LAB_WORK/restore_receipt.txt" && -s "$LAB_WORK/backup.dump.sha256" ]] || { echo STOP_NO_RESTORE_RECEIPT >&2;exit 70; }
for file in \
  product-db-witness.log bootstrap-db-witness.log \
  restored-product-db-witness.log restored-bootstrap-db-witness.log; do
  [[ -s "$LAB_WORK/$file" ]] || { echo STOP_MISSING_REAL_CODE_PROOF >&2; exit 70; }
done
[[ "$(dbpsql -Atc "SELECT count(*) FROM db55_audit.migration_runs WHERE status='APPLIED'")" == 10 ]] || exit 70
dbpsql -Atc "SELECT row_to_json(t) FROM
  (SELECT version, source_commit, git_blob_sha1, sql_sha256, status,
          started_at, applied_at, applied_txid, cluster_system_id
    FROM db55_audit.migration_runs ORDER BY version) t" > "$LAB_WORK/migration_ledger_sanitized.jsonl"
export F3_EVIDENCE_WORK="$LAB_WORK"
python3 - <<'PY'
import hashlib
import json
import os
from pathlib import Path

w = Path(os.environ["F3_EVIDENCE_WORK"])
def client(mode, restored=False):
    path = w / (("restored-" if restored else "")+mode+"-db-witness.log")
    events=[]
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("{"):
            try:
                doc=json.loads(line)
            except ValueError:
                continue
            if doc.get("contract") == "f3.db.shared_stack.db_authority.v1":
                events.append(doc)
    if len(events)!=1:
        raise ValueError("missing precise witness")
    doc=events[0]
    if (doc.get("mode") != mode or doc.get("status") != "PASS" or
        doc.get("role_count") != (2 if mode=="product" else 7) or
        any(set(role.keys()) != {"role","ssl","tls_version","postgres","user_verified"} or
            role["ssl"] != "verify-full" or role["user_verified"] is not True
            for role in doc["roles"])):
        raise ValueError("invalid code witness")
    if doc.get("asgi_http_listener_started") is not False:
        raise ValueError("incorrect HTTP claim")
    if doc.get("runner_calls") != 0 or doc.get("gateway_calls") != 0:
        raise ValueError("unexpected external execution")
    return doc

metadata={}
for line in (w/"restore_receipt.txt").read_text().splitlines():
    k,sep,v=line.partition("=")
    if sep:
        metadata[k]=v
source_id=(w/"source_cluster_id.txt").read_text().strip()
if metadata.get("SOURCE_CLUSTER_ID") != source_id or not metadata.get("RESTORE_CLUSTER_ID"):
    raise ValueError("invalid cluster identity")
if source_id == metadata["RESTORE_CLUSTER_ID"]:
    raise ValueError("restore is not independent")
ledger=[json.loads(line) for line in (w/"migration_ledger_sanitized.jsonl").read_text().splitlines()]
if len(ledger)!=10 or [str(l["version"]) for l in ledger]!=[f"{i:03}" for i in range(1,11)]:
    raise ValueError("bad ledger")
if any(l["status"]!="APPLIED" or not l["applied_txid"] or
       not l["sql_sha256"] or l["cluster_system_id"] != source_id for l in ledger):
    raise ValueError("bad applied ledger data")
backup_sha=(w/"backup.dump.sha256").read_text().split()[0]
if len(backup_sha)!=64:
    raise ValueError("bad backup hash")
source={mode:client(mode) for mode in ("product","bootstrap")}
restore={mode:client(mode,True) for mode in ("product","bootstrap")}
for mode in ("product","bootstrap"):
    if source[mode]["db"]!="rag_finance_f3_lab" or restore[mode]["db"]!="rag_finance_f3_lab_restore":
        raise ValueError("mismatched client destination")

receipt={
"contract_version":"foundation.f3_db_candidate_shared.v1",
"outcome":"PASS_DB_CLIENT_PREFLIGHT_ONLY",
"source_commit_tested":os.environ.get("GITHUB_SHA","NO_CI_SHA"),
"ci_run_id":os.environ.get("GITHUB_RUN_ID","NO_CI_RUN"),
"ci_run_attempt":os.environ.get("GITHUB_RUN_ATTEMPT","NO_CI_ATTEMPT"),
"host":"github-actions-ubuntu-24.04-isolated-docker",
"database_primary":"rag_finance_f3_lab",
"database_restore":"rag_finance_f3_lab_restore",
"cluster_ids":{"source":source_id,"restore":metadata["RESTORE_CLUSTER_ID"],"independent":True},
"schema_object_counts":metadata.get("OBJECT_COUNTS"),
"postgres_version":"17.11",
"postgres_image":"public.ecr.aws/docker/library/postgres@sha256:73bedc9eaa0121b92b9b26bb52e5141b3f6f37479c7ef913c0160455763ca80a",
"platform":"linux/amd64",
"source_api_commit":"c5e271d0fab8ab34c92a2da933ba6b194d1f1e9a",
"db55_phase":"private_no_dispatch",
"manifest_sha256":"9ff95a59570f5f6c6188479d9c37cf684ef836c599e89d9faa2bb0e17a4946f7",
"migration_ledger":ledger,
"backup_sha256":backup_sha,
"client_preflight_primary":source,
"client_preflight_restored":restore,
"acl_rls_db55_backup_restore":"PASS_VERIFIED_BY_CI_GATE_SCRIPT",
"migration_011":"EXCLUDED",
"accepted_mac_demo_database_touched":False,
"accepted_mac_demo_volume_touched":False,
"product_http_startup":"NOT_TESTED",
"bootstrap_http_startup":"NOT_TESTED",
"auth_oidc_real":"NOT_TESTED",
"c018_engine":"NOT_RUN",
"gateway_calls":0,
"secret_values_in_receipt":False,
}
out = Path(os.environ["GITHUB_WORKSPACE"])/"ci_receipts"
out.mkdir(parents=True,exist_ok=True)
target=out/"f3_db_candidate_consumption.json"
target.write_text(json.dumps(receipt,ensure_ascii=False,indent=2,sort_keys=True)+"\n",encoding="utf-8")
print("SANITIZED_FOUNDATION_CANDIDATE_CONSUMPTION_RECEIPT=PASS")
print("SANITIZED_RECEIPT_SHA256="+hashlib.sha256(target.read_bytes()).hexdigest())
PY

# Append source catalog evidence to the same artifact set; no table data or credentials.
catalog="$LAB_WORK/physical_erd_data_dictionary.jsonl"
plans="$LAB_WORK/query_plan_empty_fixture.txt"
[[ -s "$catalog" && -s "$plans" && -s "$LAB_WORK/catalog_snapshot_sha256.txt" ]] || {
  echo STOP_CATALOG_EVIDENCE_NOT_COLLECTED >&2; exit 70;
}
[[ "$(grep -c '^{' "$catalog")" == 14 ]] || { echo STOP_CATALOG_NOT_FOURTEEN_TABLES >&2;exit 70; }
( cd "$LAB_WORK" && shasum -a 256 -c catalog_snapshot_sha256.txt ) >/dev/null || {
  echo STOP_CATALOG_SHA256_MISMATCH >&2;exit 70;
}
install -m 0600 "$catalog" "$GITHUB_WORKSPACE/ci_receipts/physical_erd_data_dictionary.jsonl"
install -m 0600 "$plans" "$GITHUB_WORKSPACE/ci_receipts/query_plan_empty_fixture.txt"
install -m 0600 "$LAB_WORK/catalog_snapshot_sha256.txt" "$GITHUB_WORKSPACE/ci_receipts/catalog_snapshot_sha256.txt"
echo 'CATALOG_14_TABLES_SHA256_EXPORT=PASS'

# Separate tiny synthetic-owner lifecycle receipt from the read-only catalog dump.
synthetic_receipt="$LAB_WORK/synthetic_owner_restore_receipt.json"
[[ -s "$synthetic_receipt" ]] || { echo STOP_SYNTHETIC_OWNER_RESTORE_RECEIPT_MISSING >&2;exit 70; }
python3 - "$synthetic_receipt" <<'PY2'
import json,sys
from pathlib import Path
x=json.loads(Path(sys.argv[1]).read_text())
assert x["contract_version"]=="f3.db.synthetic_owner_restore.v1"
assert x["source_and_restored_history_rows_equal"] is True
assert x["synthetic_conversations"]==2 and x["synthetic_messages"]==2
assert x["restored_owner_rls"]=="PASS" and x["restored_db55_and_ledger"]=="PASS"
assert x["deletion_requested_soft_state_restored"] is True
assert x["deleted_owner_active_rows_after_restore"]==0
assert type(x["elapsed_monotonic_ms"]) is int and x["elapsed_monotonic_ms"] > 0
assert x["hard_delete_tombstone_policy"]=="NOT_APPROVED"
PY2
install -m 0600 "$synthetic_receipt" "$GITHUB_WORKSPACE/ci_receipts/synthetic_owner_restore_receipt.json"
echo 'SANITIZED_SYNTHETIC_OWNER_RESTORE_RECEIPT=PASS'

# Real second-cluster negative installer audit; only synthetic marker JSON.
ledger="$LAB_WORK/ledger_fault_injection_receipt.json"
[[ -s "$ledger" ]] || { echo STOP_LEDGER_FAULT_WITNESS_MISSING >&2;exit 70; }
python3 - "$ledger" <<'PY'
import json,sys
from pathlib import Path
v=json.loads(Path(sys.argv[1]).read_text())
assert v["contract_version"] == "f3.db.ledger_fault_injection.v1"
for k in ("partial_STARTED","duplicate_primary_key","sha256_mismatch",
          "missing_applied_metadata","forged_complete_ledger_without_schema"):
    assert v[k] in ("FAIL_CLOSED_NO_RETRY","REJECTED")
assert v["second_lab_containers_volumes_removed"] is True
assert v["existing_main_lab_untouched"] is True
PY
install -m 0600 "$ledger" "$GITHUB_WORKSPACE/ci_receipts/ledger_fault_injection_receipt.json"
echo 'SANITIZED_LEDGER_FAULT_INJECTION_RECEIPT=PASS'

# Real EXPLAIN ANALYZE with nonempty two-owner synthetic data. No customer rows.
for file in populated_plan_receipt.json query_plan_populated_conversations.json query_plan_populated_messages.json; do
  [[ -s "$LAB_WORK/$file" ]] || { echo "STOP_POPULATED_PLAN_FILE_$file" >&2;exit 70; }
  install -m 0600 "$LAB_WORK/$file" "$GITHUB_WORKSPACE/ci_receipts/$file"
done
python3 - "$GITHUB_WORKSPACE/ci_receipts/populated_plan_receipt.json" <<'PY'
import json,sys
from pathlib import Path
r=json.loads(Path(sys.argv[1]).read_text())
assert r["contract_version"] == "f3.db.synthetic_populated_query_plan.v1"
assert r["conversation_rows"] == 2400 and r["message_rows"] == 4800
assert r["owner_a_rls_visible_conversations"] == 1200
assert r["query_plans"]["conversations"]["actual_rows"] == 20
assert r["query_plans"]["messages"]["actual_rows"] == 2
assert r["production_workload_certified"] is False
PY
echo 'SANITIZED_TWO_OWNER_POPULATED_EXPLAIN_RECEIPT=PASS'

# Additional real-PG adversarial History/write/owner boundary receipt.
# No customer data, DSNs, secrets, raw SQL or direct private table contents.
adversarial="$LAB_WORK/history_rls_adversarial_receipt.json"
[[ -s "$adversarial" ]] || { echo STOP_HISTORY_ADVERSARIAL_RECEIPT_MISSING >&2;exit 70; }
python3 - "$adversarial" <<'PY'
import json,sys
from pathlib import Path
r=json.loads(Path(sys.argv[1]).read_text())
assert r["contract_version"]=="f3.db.synthetic_history_rls_adversarial.v1"
assert r["owners"]==2 and r["tables"]==6 and r["rows_per_table"]==2
assert r["owner_a_visible_each"]==[1]*6 and r["owner_b_visible_each"]==[1]*6
assert r["no_owner_visible_each"]==[0]*6
assert r["positive_owner_a_title_update"]=="PASS"
assert r["foreign_owner_update"]=="NO_ROWS"
assert len(r["negative_cases"])==7
assert all(x.endswith("_DENIED") for x in r["negative_cases"].values())
assert r["post_negative_snapshot"]=="NO_UNAUTHORIZED_CHANGES"
assert r["direct_history_role_can_set_owner_guc"] is True
assert r["same_transaction_signed_actor_fence"]=="NOT_PROVEN_REQUIRES_REAL_API_IDP"
assert r["real_mac_http"]=="NOT_RUN" and r["external_dispatch"] is False
assert r["module_gate"]=="NOT_ACCEPTED"
PY
install -m 0600 "$adversarial" "$GITHUB_WORKSPACE/ci_receipts/history_rls_adversarial_receipt.json"
echo 'HISTORY_READ_WRITE_OWNER_FK_AND_DEDUPE_NEGATIVE_RECEIPT=PASS'
echo 'HISTORY_TRUSTED_ACTOR_FENCE_SIGNED_HTTP=NOT_RUN'

# Original backup corruption/truncation fail-closed preflight evidence.
# No corrupt dump or clean raw pg_dump is ever attached to public CI artifacts.
backup_fault="$LAB_WORK/backup_integrity_fault_receipt.json"
[[ -s "$backup_fault" ]] || { echo STOP_BACKUP_INTEGRITY_FAULT_RECEIPT_MISSING >&2;exit 70; }
python3 - "$backup_fault" <<'PY'
import json,sys
from pathlib import Path
r=json.loads(Path(sys.argv[1]).read_text())
assert r["contract_version"]=="f3.db.synthetic_backup_integrity_fault.v1"
assert r["single_byte_changed_sha256_mismatch"]=="FAIL_CLOSED_BEFORE_RESTORE"
assert r["truncated_dump_sha256_mismatch"]=="FAIL_CLOSED_BEFORE_RESTORE"
assert r["healthy_dump_sha256_rechecked"]=="PASS"
assert r["healthy_source_and_independent_restore_cluster_ids_unchanged"] is True
assert r["corrupt_archives_restored"] is False and r["corrupt_restore_sql_attempts"]==0
assert r["encrypted_offsite_backup"]=="NOT_TESTED" and r["pitr"]=="NOT_TESTED"
assert r["real_disaster_recovery"]=="NOT_TESTED"
assert r["rpo_rto_signed"]=="NOT_DEFINED" and r["module_gate"]=="NOT_ACCEPTED"
PY
install -m 0600 "$backup_fault" "$GITHUB_WORKSPACE/ci_receipts/backup_integrity_fault_receipt.json"
echo 'BACKUP_CORRUPT_AND_TRUNCATED_NEGATIVE_RECEIPT=PASS'
echo 'BACKUP_PRODUCTION_PITR_AND_ENCRYPTION_GATE=NOT_TESTED'

# Anchored History keyset cursor real-SQL two-owner and insert-race receipt.
cursor="$LAB_WORK/history_cursor_race_receipt.json"
[[ -s "$cursor" ]] || { echo STOP_HISTORY_CURSOR_RACE_RECEIPT_MISSING >&2;exit 70; }
python3 - "$cursor" <<'PY'
import json,sys
from pathlib import Path
r=json.loads(Path(sys.argv[1]).read_text())
assert r["contract_version"]=="f3.db.synthetic_history_keyset_cursor.v1"
assert r["source_repository_git_blob"]=="14f97dd680425b74f8e12fa1696d423a20bf7d76"
assert r["two_owners"] is True
assert r["conversations_desc_keyset_anchor_last"]=="PASS_5_ORIGINAL_NO_DUPLICATE"
assert r["messages_asc_keyset_anchor_last"]=="PASS_5_ORIGINAL_NO_DUPLICATE"
assert r["concurrent_after_anchor_new_conversation_hidden"] is True
assert r["concurrent_after_anchor_new_message_hidden"] is True
assert r["fresh_query_can_see_new_row"] is True
assert r["cross_owner_conversation_and_message_rows_visible"]==0
assert r["cursor_api_hmac_signing"]=="NOT_TESTED"
assert r["real_bff_http_auth"]=="NOT_RUN" and r["module_gate"]=="NOT_ACCEPTED"
PY
install -m 0600 "$cursor" "$GITHUB_WORKSPACE/ci_receipts/history_cursor_race_receipt.json"
echo 'HISTORY_KEYSET_TWO_OWNER_ANCHOR_AND_INSERT_RACE_RECEIPT=PASS'
echo 'HISTORY_SIGNED_CURSOR_HTTP_AND_REAL_CONCURRENT_LOAD=NOT_RUN'

# Exact source/independent restore SQL catalog parity and two RLS drift negatives.
# The private catalog is not exported; only the SHA256 and bounded status are.
parity="$LAB_WORK/restore_catalog_parity_receipt.json"
[[ -s "$parity" ]] || { echo STOP_RESTORE_CATALOG_PARITY_MISSING >&2; exit 70; }
python3 - "$parity" <<'PY'
import json,sys
from pathlib import Path
r=json.loads(Path(sys.argv[1]).read_text())
assert r["contract_version"]=="f3.db.synthetic_restore_catalog_parity.v1"
assert r["restore_equals_source"] is True
assert r["source_table_count"]==14 and r["checked_roles"]==9
assert r["negative_no_force_rls"]=="DETECTED_IN_DISPOSABLE_CLONE"
assert r["negative_disabled_rls"]=="DETECTED_IN_DISPOSABLE_CLONE"
assert r["negative_probe_removed"] and r["original_clusters_unchanged"]
assert r["mac_runtime"]=="NOT_RUN" and r["signed_actor_fence"]=="NOT_TESTED"
assert r["module_gate"]=="NOT_ACCEPTED"
PY
install -m 0600 "$parity" "$GITHUB_WORKSPACE/ci_receipts/restore_catalog_parity_receipt.json"
echo 'RESTORE_CATALOG_PARITY_13TH_SANITIZED_RECEIPT=PASS'

# M04-A07 exact empty 001-010 down/reinstall consistency + populated independent restore.
m04="$LAB_WORK/m04_migration_full_cycle_receipt.json"
[[ -s "$m04" ]] || { echo STOP_M04_A07_CONSISTENCY_MISSING >&2;exit 70; }
python3 - "$m04" <<'PY'
import json,sys
from pathlib import Path
r=json.loads(Path(sys.argv[1]).read_text())
assert r["contract_version"]=="f3.db.p3m04_a07_full_cycle.v1"
assert r["full_empty_001_010_down_and_forward"]=="PASS_10_DOWN_10_UP"
assert r["source_equals_roundtrip"] is True
assert r["schema_only_source_sha256"]==r["schema_only_roundtrip_sha256"]
assert len(r["schema_only_source_sha256"])==64
assert r["new_probe_ledger_applied"]==10 and r["force_rls_tables_after_roundtrip"]==14
assert r["db55_after_roundtrip"]=="PASS_PRIVATE_NO_DISPATCH"
assert r["populated_pre009_upgrade"]=="PASS_TWO_OWNERS_BOTH_CLUSTERS_009_010"
assert r["populated_restore"]=="PASS_SEPARATE_PG_CLUSTER"
assert r["data_bearing_001_003_destructive_reverse"]=="NOT_PERMITTED"
assert r["probe_removed"] is True and r["original_lab_untouched"] is True
assert r["mac_runtime"]=="NOT_RUN" and r["module_gate"]=="NOT_ACCEPTED"
PY
install -m 0600 "$m04" "$GITHUB_WORKSPACE/ci_receipts/m04_migration_full_cycle_receipt.json"
echo 'M04_A07_14TH_SANITIZED_CONSISTENCY_RECEIPT=PASS'

# Synthetic DB-only simultaneous duplicate/NULL idempotency, not HTTP end-to-end.
m10="$LAB_WORK/m10_idempotency_concurrency_receipt.json"
[[ -s "$m10" ]] || { echo STOP_M10_CONCURRENCY_RECEIPT_ABSENT >&2;exit 70; }
python3 - "$m10" <<'PY'
import json,sys
from pathlib import Path
r=json.loads(Path(sys.argv[1]).read_text())
assert r["contract_version"]=="f3.db.synthetic_m10_client_idempotency_concurrency.v1"
assert r["concurrent_sql_clients"]==2
assert r["concurrent_insert_commits"]==1 and r["concurrent_duplicate_key_denials"]==1
assert r["nullable_request_idempotency_key"]=="NULLS_NOT_DISTINCT_CONFIRMED"
assert r["simulated_lost_ack_replay"]=="DENIED_NO_SECOND_COMMIT"
assert r["cross_owner_same_client_key"]=="ALLOWED_SCOPED"
assert r["one_attempt_per_send_receipt"]=="SECOND_DENIED"
assert r["owner_a_visible_receipts"]==1 and r["owner_b_visible_receipts"]==1
assert r["unset_owner_visible_receipts"]==0
assert r["clone_removed"] is True and r["source_lab_unchanged"] is True
assert r["real_http_retry_or_crash"]=="NOT_RUN"
assert r["signed_idp_same_tx_actor"]=="NOT_PROVEN"
assert r["module_gate"]=="NOT_ACCEPTED"
PY
install -m 0600 "$m10" "$GITHUB_WORKSPACE/ci_receipts/m10_idempotency_concurrency_receipt.json"
echo 'M10_A10_15TH_SANITIZED_DB_CONCURRENCY_RECEIPT=PASS'

# Real process SIGKILL on a synthetic independent PostgreSQL restore cluster.
pg_crash="$LAB_WORK/pg_crash_recovery_receipt.json"
[[ -s "$pg_crash" ]] || { echo STOP_PG_CRASH_RECOVERY_RECEIPT_ABSENT >&2;exit 70; }
python3 - "$pg_crash" <<'PY'
import json,sys
from pathlib import Path
r=json.loads(Path(sys.argv[1]).read_text())
assert r["contract_version"]=="f3.db.synthetic_pg17_crash_and_wal_recovery.v1"
assert r["fault"]=="SIGKILL_POSTGRES_CONTAINER"
assert r["database_offline_connection_denied"] is True
assert r["postgres_wal_recovery"]=="PASS"
assert r["source_and_restore_cluster_ids_stable"] is True
assert r["committed_conversations_after"]==2 and r["committed_messages_after"]==2
assert r["uncommitted_insert_after"]==0
assert r["owner_a_visible"]==1 and r["owner_b_visible"]==1 and r["no_owner_visible"]==0
assert r["force_rls_tables_after_restart"]==14 and r["db55_after_restart"]=="PASS"
assert r["prior_corrupt_backup_pre_restore_negatives"]=="2_OF_2_FAILED_CLOSED"
assert r["original_backup_sha256_intact"] and r["test_probe_removed"]
assert r["mac_runtime"]=="NOT_RUN" and r["full_machine_failure"]=="NOT_RUN"
assert r["offsite_encrypted_key_custody"]=="NOT_DEFINED"
assert r["pitr"]=="NOT_RUN" and r["approved_rpo_rto"]=="NOT_DEFINED"
assert r["module_gate"]=="NOT_ACCEPTED"
PY
install -m 0600 "$pg_crash" "$GITHUB_WORKSPACE/ci_receipts/pg_crash_recovery_receipt.json"
echo 'M22_A09_16TH_SANITIZED_PG_CRASH_RECOVERY_RECEIPT=PASS'
