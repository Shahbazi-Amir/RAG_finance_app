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
