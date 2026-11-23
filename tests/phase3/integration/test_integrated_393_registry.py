"""Full cardinality and source-exact ledger reconciliation (no approvals inferred)."""
from __future__ import annotations

import csv
import json
import re
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
LEDGER = ROOT / "coordination/integration/PHASE3_393_CANONICAL_APP_ONLY_EXECUTION_LEDGER_20261124.csv"
MAIN = ROOT / "coordination/handoffs/UI_F3_CANONICAL_262_ACTIVITIES_26_GATES.csv"
OP = ROOT / "coordination/handoffs/UI_F3_OPERATIONAL_105_MAP_80_FOCUS.csv"
FIELDS = (
    "id", "entry_kind", "canonical_counted", "owner", "canonical_criterion",
    "dependency", "app_only_slice", "implementation_status", "tested_scope",
    "acceptance_status", "git_sha", "run_or_env", "artifact_link", "blocker",
    "next_action",
)

def read(path: Path):
    with path.open(encoding="utf-8-sig", newline="") as f:
        reader=csv.DictReader(f)
        assert reader.fieldnames
        rows=list(reader)
        assert all(None not in row for row in rows),path
        return reader.fieldnames,rows


class LedgerTest(unittest.TestCase):
    def test_all_393_source_ids_one_to_one(self):
        header,rows=read(LEDGER)
        self.assertEqual(header,list(FIELDS))
        self.assertEqual(len(rows),393)
        ids=[r["id"] for r in rows]
        self.assertEqual(len(set(ids)),393)
        _,main=read(MAIN)
        _,op=read(OP)
        act={r["id"] for r in main if r["type"]=="P3M_ACTIVITY"}
        gates={r["id"]+"-GATE" for r in main if r["type"]=="P3M_INDEPENDENT_GATE"}
        mapped={r["id"] for r in op}
        self.assertEqual((len(act),len(gates),len(mapped)),(262,26,105))
        self.assertEqual(set(ids),act|gates|mapped)
        self.assertEqual(len(act|gates|mapped),393)

    def test_exact_canonical_criteria_and_provenance_not_reinterpreted(self):
        _,rows=read(LEDGER)
        index={r["id"]:r for r in rows}
        _,original=read(MAIN)
        for r in original:
            key=r["id"]+("-GATE" if r["type"]=="P3M_INDEPENDENT_GATE" else "")
            self.assertEqual(index[key]["canonical_criterion"],r["specific_requirement"])
            self.assertEqual(index[key]["git_sha"],r["registry_sha"])
            self.assertEqual(index[key]["dependency"],r["owner_and_dependency"])
        _,overlay=read(OP)
        for r in overlay:
            self.assertEqual(index[r["id"]]["canonical_criterion"],r["criterion"])
            self.assertEqual(index[r["id"]]["dependency"],r["mapped_original_P3M_IDs"])
            self.assertEqual(index[r["id"]]["canonical_counted"],"NO")

    def test_pinned_four_pr_blob_manifest_and_fail_closed_resolutions(self):
        manifest=json.loads((ROOT/"coordination/integration/FOUR_PR_APP_ONLY_PINNED_SOURCE_MANIFEST_20261124.json")
                            .read_text(encoding="utf-8"))
        self.assertEqual(manifest["contract_version"],"integration.f3.app_only.v1")
        self.assertEqual(len(manifest["candidate_tree_selected_changes"]),42)
        self.assertEqual(set(manifest["parent_branches_exact_shas"]),
                         {"fd","ui","api","db"})
        self.assertNotEqual(manifest["generated_from_tree_sha"],
                            manifest["generated_from_commit_sha"])
        expected=set(manifest["source_resolutions"])
        self.assertEqual(len(expected),6)
        preserved=0
        for file in manifest["candidate_tree_selected_changes"]:
            self.assertTrue(re.fullmatch(r"[0-9a-f]{40}",file["source_blob_sha"]))
            self.assertTrue(re.fullmatch(r"[0-9a-f]{40}",file["integrated_blob_sha"]))
            result=subprocess.run(["git","hash-object",file["path"]],
                                  cwd=ROOT,capture_output=True,text=True,check=True)
            self.assertEqual(result.stdout.strip(),file["integrated_blob_sha"],file["path"])
            if file["path"] in expected:
                self.assertEqual(file["resolution"],"FOUNDATION_SECURITY_COMPAT")
                preserved+=1
            else:
                self.assertEqual(file["resolution"],"SOURCE_PRESERVED")
        self.assertEqual(preserved,6)
        self.assertFalse(manifest["acceptance"]["real_postgresql_oidc_mac_l2_verified"])
        self.assertFalse(manifest["acceptance"]["full_phase3_accepted"])

    def test_all_58_divergences_have_exact_blobs_and_open_owner_decisions(self):
        manifest_path=ROOT/"coordination/integration/FOUR_PR_58_PATH_THREE_WAY_AUDIT_20261124.json"
        audit=json.loads(manifest_path.read_text(encoding="utf-8"))
        self.assertEqual(audit["contract_version"],"integration.f3.three_way_audit.v1")
        self.assertFalse(audit["p0_1_accepted"])
        summary=audit["summary"]
        self.assertEqual(summary["total_unique_divergent_paths"],58)
        self.assertEqual(summary["source_selected"],36)
        self.assertEqual(summary["foundation_security"],6)
        self.assertEqual(summary["retained_pending"],16)
        self.assertEqual(summary["custom"],0)
        records=audit["paths"]
        self.assertEqual(len({row["path"] for row in records}),58)
        for row in records:
            self.assertFalse(row["owner_signed_acceptance"])
            self.assertTrue(row["source_options"])
            self.assertTrue(all(re.fullmatch(r"[0-9a-f]{40}",x["commit_sha"])
                                and re.fullmatch(r"[0-9a-f]{40}",x["blob_sha"])
                                for x in row["source_options"]))
            blob=subprocess.run(["git","hash-object",row["path"]],
                                cwd=ROOT,text=True,capture_output=True,check=True).stdout.strip()
            self.assertEqual(blob,row["integrated_blob_sha"],row["path"])
            if row["decision"]=="EXACT_SOURCE_SELECTED":
                self.assertTrue(row["selected_owner_blobs"])
                self.assertIn(blob,[x["blob_sha"] for x in row["source_options"]])
            elif row["decision"] in {
                "FOUNDATION_SECURITY_COMPAT",
                "FOUNDATION_BASELINE_RETAINED_REQUIRES_OWNER_REVIEW",
            }:
                self.assertEqual(blob,row["foundation_blob_sha"],row["path"])
                self.assertFalse(row["selected_owner_blobs"])
            else:
                self.fail("unreviewed divergent path: "+row["path"])

    def test_no_acceptance_without_real_receipts(self):
        _,rows=read(LEDGER)
        self.assertEqual(sum(r["acceptance_status"]=="ACCEPTED" for r in rows),0)
        self.assertTrue(all(r["acceptance_status"]=="NOT_ACCEPTED" for r in rows))
        self.assertTrue(all(r["app_only_slice"]=="UNFROZEN_CENTRAL_DECISION" for r in rows))
        self.assertTrue(all(r["owner"] and r["canonical_criterion"]
                            and r["dependency"] and r["next_action"] for r in rows))
        self.assertTrue(all(re.fullmatch(r"[0-9a-f]{40}",r["git_sha"]) for r in rows))
        self.assertTrue(all(r["entry_kind"] in {
            "MAIN_ACTIVITY","MODULE_GATE","OPERATIONAL_CROSSWALK"
        } for r in rows))


if __name__=="__main__":
    unittest.main()
