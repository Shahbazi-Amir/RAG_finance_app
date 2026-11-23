#!/usr/bin/env bash
# In ONE disposable CI runner, independently install/restore two exact DB code
# baselines. Each uses fresh Docker cluster IDs, Compose project/volumes and
# source worktree. NEVER run on a protected Mac demo database or host volume.
set -euo pipefail
umask 077
: "$GITHUB_WORKSPACE"
: "$RUNNER_TEMP"
repo="$GITHUB_WORKSPACE"
old=0e301a26096cb9f8c2b8e3fde3e20e9a1add48a5
new=996dfc9b66cf8cbd4b37b7a267d08cc5acd5deba
manifest=infra/postgres/dev_f3_isolated/MIGRATIONS_001_010_PINNED.tsv
rel=infra/postgres/dev_f3_isolated
[[ "$(git -C "$repo" rev-parse --is-inside-work-tree)" == true ]] || exit 70
for sha in "$old" "$new"; do
  git -C "$repo" cat-file -e "$sha^{commit}" || exit 70
done
for file in "$manifest" "$rel/compose.lab.yaml" "$rel/scripts/02_provision_roles.sh"; do
  cmp -s <(git -C "$repo" show "$old:$file") <(git -C "$repo" show "$new:$file") || {
    echo "STOP_RUNTIME_OR_SOURCE_PIN_DRIFT:$file" >&2;exit 70;
  }
done
[[ "$(git -C "$repo" rev-parse "$old:$rel/scripts/03_apply_pinned_001_010.sh")" == a30dbebe5b787db61b4f91c035d255f8160029d1 ]] || exit 70
[[ "$(git -C "$repo" rev-parse "$new:$rel/scripts/03_apply_pinned_001_010.sh")" == 9cc9458c55b82f03811b346259ccf2ae3dce318d ]] || exit 70
base="$(mktemp -d "$RUNNER_TEMP/f3_baseline_comparison_XXXXXXXX")"
[[ "$base" == "$RUNNER_TEMP"/f3_baseline_comparison_* ]] || exit 70
chmod 0700 "$base"
printf '%s\n' 'COMPARISON_CANDIDATE=NEW_DISPOSABLE_RUNNER_ONLY'
for sha in "$old" "$new"; do
  short="$(printf '%s' "$sha" | cut -c1-8)"
  tree="$base/source_$short"
  target="$base/lab_$short"
  out="$base/out_$short"
  mkdir -m 0700 "$out"
  git -C "$repo" worktree add --detach "$tree" "$sha" > "$base/worktree_$short.log" 2>&1
  export SOURCE_REPO="$tree" LAB_ROOT="$target"
  root="$tree/$rel"
  # Verify each BASELINE's own source/installer and role/DB55 code. Never
  # forward a new installer to an older baseline or mask its execution result.
  bash "$root/scripts/00_prepare_source.sh" > "$base/prepare_$short.log"
  bash "$root/scripts/01_create_isolated_lab.sh" > "$base/create_$short.log"
  bash "$root/scripts/02_provision_roles.sh" > "$base/roles_$short.log"
  bash "$root/scripts/03_apply_pinned_001_010.sh" > "$base/install_$short.log"
  bash "$root/scripts/03_apply_pinned_001_010.sh" > "$base/no_replay_$short.log"
  grep -Fq 'ALREADY_APPLIED_EXACT_PINS_NO_RERUN' "$base/no_replay_$short.log" || exit 70
  bash "$root/scripts/04_bridge_and_db55.sh" > "$base/db55_$short.log"
  grep -Fq 'DB55_PRIVATE_NO_DISPATCH_LAB=PASS' "$base/db55_$short.log" || exit 70
  bash "$root/scripts/05_test_roles_tls_rls.sh" > "$base/acl_$short.log"
  bash "$root/scripts/09_shared_stack_db_preflight.sh" > "$base/actual_code_$short.log"
  bash "$root/scripts/06_backup_restore_independent.sh" > "$base/restore_$short.log"
  grep -Fq 'RESTORE_INDEPENDENT_CLUSTER=PASS' "$base/restore_$short.log" || exit 70
  bash "$root/scripts/10_restored_stack_db_preflight.sh" > "$base/restored_code_$short.log"
  bash "$root/scripts/13_catalog_erd_inventory.sh" > "$base/catalog_$short.log"
  bash "$root/scripts/12_rollback_rls_constraints_probe.sh" > "$base/rollback_$short.log"
  bash "$root/scripts/14_synthetic_owner_lifecycle_restore.sh" > "$base/synthetic_$short.log"
  if [[ "$sha" == "$new" ]]; then
    bash "$root/scripts/15_populated_pre009_upgrade_restore.sh" > "$base/pre009_$short.log"
    bash "$root/scripts/16_fault_injected_migration_ledger.sh" > "$base/ledger_neg_$short.log"
    bash "$root/scripts/17_populated_query_plan_and_owner.sh" > "$base/plan_$short.log"
  fi
  GITHUB_SHA="$sha" GITHUB_WORKSPACE="$out" \
    bash "$root/scripts/11_export_sanitized_receipt.sh" > "$base/export_$short.log"
  [[ -s "$out/ci_receipts/f3_db_candidate_consumption.json" ]] || exit 70
  # Keep sanitized artifacts from each independent experiment, never dumps,
  # raw roles, credentials, PEM, postgresql logs, or test DB volumes.
  mkdir -m 0700 "$repo/ci_comparison"
  cp "$out/ci_receipts/f3_db_candidate_consumption.json" \
     "$repo/ci_comparison/baseline_$short.json"
  chmod 0600 "$repo/ci_comparison/baseline_$short.json"
  ALLOW_DELETE_F3_LAB=YES bash "$root/scripts/07_cleanup_lab_ONLY.sh" > "$base/cleanup_$short.log"
  grep -Fq 'ONLY_DISPOSABLE_LAB_CONTAINERS_AND_VOLUMES_CLEANED=YES' "$base/cleanup_$short.log" || exit 70
  git -C "$repo" worktree remove "$tree" >/dev/null
  echo "BASELINE_$short=FRESH_001_010_DB55_TLS_ROLES_INDEPENDENT_RESTORE_PASS"
done
python3 - "$repo/ci_comparison" "$old" "$new" <<'PY'
import json,sys
from pathlib import Path
folder=Path(sys.argv[1]); shas=sys.argv[2:]; cases=[]
ids=set()
for sha in shas:
    raw=folder/("baseline_"+sha[:8]+".json")
    x=json.loads(raw.read_text())
    assert x["source_commit_tested"] == sha
    assert x["postgres_version"] == "17.11"
    assert x["manifest_sha256"] == "9ff95a59570f5f6c6188479d9c37cf684ef836c599e89d9faa2bb0e17a4946f7"
    assert x["db55_phase"] == "private_no_dispatch"
    assert x["acl_rls_db55_backup_restore"] == "PASS_VERIFIED_BY_CI_GATE_SCRIPT"
    assert x["product_http_startup"] == "NOT_TESTED"
    assert x["c018_engine"] == "NOT_RUN" and x["gateway_calls"] == 0
    assert len(x["migration_ledger"]) == 10
    assert [m["version"] for m in x["migration_ledger"]] == [f"{i:03d}" for i in range(1,11)]
    for k in ("source","restore"):
        id_=x["cluster_ids"][k]
        assert id_ and id_ not in ids
        ids.add(id_)
    for where in ("client_preflight_primary","client_preflight_restored"):
        for role,count in (("product",2),("bootstrap",7)):
            assert x[where][role]["status"] == "PASS"
            assert x[where][role]["role_count"] == count
    cases.append(dict(executable_sha=sha,postgres_version=x["postgres_version"],
        manifest_sha256=x["manifest_sha256"], source_cluster_id=x["cluster_ids"]["source"],
        restore_cluster_id=x["cluster_ids"]["restore"], db55=x["db55_phase"],
        migration_count=len(x["migration_ledger"]),
        role_preflight_primary="2+7 PASS TLS verify-full",
        role_preflight_restore="2+7 PASS TLS verify-full",
        independent_restore=True, backup_sha256=x["backup_sha256"],
        full_http="NOT_TESTED", c018="NOT_RUN", gateway_calls=0))
assert cases[0]["manifest_sha256"] == cases[1]["manifest_sha256"]
result={
 "contract_version":"f3.db.two_baseline_independent_pg_comparison.v1",
 "environment":"one GitHub Actions runner, two sequential fully-disposable source+restore cluster pairs",
 "sample":"two synthetic owners per baseline; newly populated 2400/4800 only in newer baseline",
 "pins_identical":["20 migration source paths / manifest","postgres image digest/platform","role provisioner"],
 "installer_git_blobs":{"old":"a30dbebe5b787db61b4f91c035d255f8160029d1",
                        "new":"9cc9458c55b82f03811b346259ccf2ae3dce318d"},
 "four_cluster_ids_unique":len(ids)==4,
 "each_tested_with_own_code":True,
 "baseline_results":cases,
 "live_mac_e2e":"NOT_RUN",
 "retention_rpo_rto_pitr_acceptance":"NOT_CLAIMED",
 "module_gate_acceptance":"NOT_GRANTED"
}
(folder/"baseline_comparison_receipt.json").write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
PY
echo 'TWO_BASELINES_SAME_ISOLATED_CI_RUN=PASS'
echo 'TWO_BASELINES_FOUR_UNIQUE_CLUSTER_IDS=PASS'
echo 'MIGRATIONS_001_010_DB55_AND_RESTORE_BOTH_BASELINES=PASS'
echo 'TWO_BASELINE_MAC_L2=NOT_RUN'
