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



UI_TRANSFER=ROOT/"coordination/integration/F3_84_REVIEWED_UI_SOURCE_TRANSFER_20261124.json"

def reviewed_ui_overrides():
    """Exact, independently CI-tested source delta; NOT an acceptance override.

    Historical #84 42-blob/58-path manifests remain byte-for-byte frozen.
    Any unlisted path, arbitrary hash, changed owner decision or forged
    ACCEPTED bit must fail rather than silently fall through.
    """
    d=json.loads(UI_TRANSFER.read_text(encoding="utf-8"))
    assert d["schema"]=="foundation.f3.reviewed_ui_source_transfer.v1"
    assert d["root_candidate_sha"]=="0fd1066945ef91a3913e040ab4c350bb645ea502"
    assert d["foundation_parent_sha"]=="9f708c73439ab790a1b402e2c8dc78e45df3d717"
    assert d["tested_source_sha"]=="ed28a6840d5e8714ff7d943ad6215534992e6a7b"
    assert d["source_ci_runs"]==[45396172643,45396172648]
    assert d["scope"]=="EXACT_TESTED_UI_SOURCE_TRANSFER_NOT_OWNER_ACCEPTANCE"
    assert (d["p0_1_accepted"],d["owner_signed_acceptance"],d["target_verified"])==(False,False,False)
    rows=d["rows"]
    assert isinstance(rows,list) and len(rows)==9
    expected={
        "apps/web/src/mock/transport.ts",
        "apps/web/src/ui/answer-visibility.ts",
        "apps/web/src/ui/owner-fence.ts",
        "apps/web/src/ui/product-chat.tsx",
        "apps/web/src/ui/source-locator.ts",
        "tests/phase3/ui/live-answer-provenance-gate.test.mjs",
        "tests/phase3/ui/owner-fence.test.mjs",
        "tests/phase3/ui/product-chat-client.test.mjs",
        "tests/phase3/ui/source-display.test.mjs",
    }
    assert {r["path"] for r in rows}==expected
    assert {r["path"] for r in rows if r["historical_42_path"]}=={
        "apps/web/src/ui/answer-visibility.ts",
        "apps/web/src/ui/product-chat.tsx",
        "apps/web/src/ui/source-locator.ts"}
    assert {r["path"] for r in rows if r["historical_58_path"]}=={
        "apps/web/src/ui/answer-visibility.ts",
        "apps/web/src/ui/product-chat.tsx",
        "apps/web/src/ui/source-locator.ts",
        "tests/phase3/ui/product-chat-client.test.mjs"}
    for row in rows:
        assert row["owner_signed_acceptance"] is False
        assert row["source_blob_sha"]==row["candidate_blob_sha"]
        assert re.fullmatch(r"[0-9a-f]{40}",row["source_blob_sha"])
        if row["previous_blob_sha"] is not None:
            assert re.fullmatch(r"[0-9a-f]{40}",row["previous_blob_sha"])
        else:
            assert row["path"]=="tests/phase3/ui/live-answer-provenance-gate.test.mjs"
        if row["historical_58_path"]:
            assert row["historical_58_decision"] in {
                "FOUNDATION_SECURITY_COMPAT",
                "EXACT_SOURCE_SELECTED",
                "FOUNDATION_BASELINE_RETAINED_REQUIRES_OWNER_REVIEW"}
        else:
            assert row["historical_58_decision"] is None
        actual=subprocess.run(["git","hash-object",row["path"]],
            cwd=ROOT,capture_output=True,text=True,check=True).stdout.strip()
        assert actual==row["source_blob_sha"],row["path"]
    return {r["path"]:r for r in rows}



BROWSER31_DELTA=ROOT/"coordination/integration/F3_84_BROWSER_31_MESSAGE_SOURCE_EXTENSION_20261124.json"

def verified_candidate_browser31_source():
    """Explicitly permitted *test harness* extension, never an API-source merge."""
    d=json.loads(BROWSER31_DELTA.read_text(encoding="utf-8"))
    assert d["schema"]=="foundation.f3.browser_31_page2_before_after_pg_restore.v1"
    assert d["parent_verified_sha"]=="9cacaede2fd67b5cf13331c7650532b8b408a8dc"
    assert d["root_84_sha"]=="0fd1066945ef91a3913e040ab4c350bb645ea502"
    assert d["path"]=="tests/phase3/integration/api/test_app_only_browser_journey.py"
    assert d["historical_signed_api_owner_blob_sha"]=="52e0f1632cb8573a80911e0b1c8dfba8ff2055e4"
    assert d["candidate_blob_sha"]=="a12c64c75361577b94a8d42bf24714dcc16864e5"
    assert all(d[k] is True for k in (
        "not_new_source_witness_rows","not_a_phase3_activity_acceptance",
        "uses_only_disposable_ci_pg"))
    assert all(d[k] is False for k in (
        "owner_signed_acceptance","target_verified","engine_enabled",
        "migration_011_applied"))
    expected=[
        "31 PostgreSQL fixture messages owned by verified Keycloak owner A",
        "React DOM first 30 + cursor last message; exact IDs/texts before restore",
        "fresh-volume PostgreSQL TLS restored full 31 parity and same React DOM cursor page",
        "320px real signed browser drawer focus/Escape and Send disabled",
    ]
    assert d["bounded_new_scope"]==expected
    actual=subprocess.run(["git","hash-object",d["path"]],
        cwd=ROOT,capture_output=True,text=True,check=True).stdout.strip()
    assert actual==d["candidate_blob_sha"]
    return d




HISTORY_PAGE_FOLLOWUP=ROOT/"coordination/integration/F3_84_HISTORY_PAGE_CONTRACT_FOLLOWUP_20261124.json"
def guarded_history_page_followup(parent,actual):
    """One explicit child of #118; never rewrite frozen owner/source records."""
    d=json.loads(HISTORY_PAGE_FOLLOWUP.read_text(encoding="utf8"))
    assert set(d)=={"schema","parent_sha","path","previous_blob_sha","candidate_blob_sha","tests","canonical_ids","scope","owner_signed_acceptance","target_verified","canonical_activity_accepted","module_gate_accepted","original_58_manifest_frozen"}
    assert d["schema"]=="foundation.f3.history_page_contract_followup.v1"
    assert d["parent_sha"]=="4e326e4efe477fc4c0e30eecab077ae668656555"
    assert d["path"]==parent["path"]=="apps/web/src/history/client.ts"
    assert d["previous_blob_sha"]==parent["candidate_blob_sha"]=="f0932d08ff37215111c04fea38f6503d4d3f41f1"
    assert d["candidate_blob_sha"]==actual=="b9ebe6659c334e02ae24a46a0b07f3a65ffa02a0"
    assert d["tests"]=="tests/phase3/ui/history-page-contract-guard.test.mjs"
    assert d["canonical_ids"]==["P3M13-A04","P3M15-A03","P3M14-A09","P3M13-A02"]
    assert d["scope"]=="LOCAL_CODE_CHANGE_CI_PENDING_NO_OWNER_ACCEPTANCE"
    assert d["original_58_manifest_frozen"] is True
    assert all(d[k] is False for k in ("owner_signed_acceptance","target_verified",
        "canonical_activity_accepted","module_gate_accepted"))
    return d


HISTORY_MICRO_DELTA=ROOT/"coordination/integration/F3_84_HISTORY_MICROSECOND_REVIEW_DELTA_20261124.json"
def guarded_history_microsecond_source():
    """Exact one-path functional UI patch; one of 16 review decisions stays open."""
    d=json.loads(HISTORY_MICRO_DELTA.read_text(encoding="utf-8"))
    assert d["schema"]=="foundation.f3.web_history_microsecond_source_extension.v1"
    assert d["root_84_sha"]=="0fd1066945ef91a3913e040ab4c350bb645ea502"
    assert d["last_verified_parent_sha"]=="9cacaede2fd67b5cf13331c7650532b8b408a8dc"
    assert d["path"]=="apps/web/src/history/client.ts"
    assert d["historical_58_decision"]=="FOUNDATION_BASELINE_RETAINED_REQUIRES_OWNER_REVIEW"
    assert d["historical_blob_sha"]=="6e057e4d097dd76f36bc41843b17c63dfb96e313"
    assert d["candidate_blob_sha"]=="f0932d08ff37215111c04fea38f6503d4d3f41f1"
    assert d["negative_test_file"]=="tests/phase3/ui/history-microsecond-ordering.test.mjs"
    assert d["scope_signed_ci_only"] is True and d["original_58_manifest_frozen"] is True
    assert d["source_behavior"]==(
        "PostgreSQL microsecond-accurate chronological checks on signed History message "
        "and conversation page results")
    assert all(d[k] is False for k in (
        "owner_signed_acceptance","canonical_activity_accepted","module_gate_accepted"))
    p=subprocess.run(["git","hash-object",d["path"]],
       cwd=ROOT,capture_output=True,text=True,check=True)
    guarded_history_page_followup(d,p.stdout.strip())
    return d


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
        ui=reviewed_ui_overrides()
        preserved=0
        for file in manifest["candidate_tree_selected_changes"]:
            self.assertTrue(re.fullmatch(r"[0-9a-f]{40}",file["source_blob_sha"]))
            self.assertTrue(re.fullmatch(r"[0-9a-f]{40}",file["integrated_blob_sha"]))
            result=subprocess.run(["git","hash-object",file["path"]],
                                  cwd=ROOT,capture_output=True,text=True,check=True)
            if file["path"] in ui:
                item=ui[file["path"]]
                self.assertTrue(item["historical_42_path"])
                self.assertEqual(item["previous_blob_sha"],file["integrated_blob_sha"])
                self.assertEqual(result.stdout.strip(),item["source_blob_sha"],file["path"])
            else:
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
        ui=reviewed_ui_overrides()
        micro=guarded_history_microsecond_source()
        # The historical #84 audit remains frozen. A later tested source
        # transfer may change a pending path, but cannot change its original
        # owner decision or turn it into acceptance.
        transfer_path=ROOT/"coordination/integration/F3_SIGNED_API_SOURCE_TRANSFER_20261124.json"
        browser_31=verified_candidate_browser31_source()
        overrides={}
        if transfer_path.is_file():
            transfer=json.loads(transfer_path.read_text(encoding="utf-8"))
            self.assertEqual(transfer["schema"],"foundation.f3.explicit_signed_api_transfer.v1")
            self.assertEqual(transfer["root_candidate_sha"],"0fd1066945ef91a3913e040ab4c350bb645ea502")
            self.assertEqual(transfer["source_sha"],"23db3da6367e6a8279072ee96b56a2bd4b7f0fbc")
            self.assertFalse(transfer["p0_1_accepted"])
            self.assertEqual(len(transfer["rows"]),10)
            self.assertEqual(len({r["path"] for r in transfer["rows"]}),10)
            for item in transfer["rows"]:
                self.assertFalse(item["owner_signed_acceptance"])
                self.assertTrue(re.fullmatch(r"[0-9a-f]{40}",item["source_blob_sha"]))
                self.assertEqual(item["candidate_blob_sha"],item["source_blob_sha"])
                actual=subprocess.run(["git","hash-object",item["path"]],cwd=ROOT,
                    capture_output=True,text=True,check=True).stdout.strip()
                if item["path"]==browser_31["path"]:
                    # Only this already-owned test-harness file is allowed to
                    # advance beyond the frozen API owner source blob. The
                    # original manifest remains unchanged and owner review open.
                    self.assertEqual(item["source_blob_sha"],
                                     browser_31["historical_signed_api_owner_blob_sha"])
                    self.assertEqual(actual,browser_31["candidate_blob_sha"])
                else:
                    self.assertEqual(actual,item["source_blob_sha"],item["path"])
                self.assertEqual(item["historical_58_path"],
                                 item["path"] in {r["path"] for r in records})
                if item["historical_58_path"]:
                    overrides[item["path"]]=item
            self.assertEqual(set(overrides),{"apps/api/product_session_api.py"})
        for row in records:
            self.assertFalse(row["owner_signed_acceptance"])
            self.assertTrue(row["source_options"])
            self.assertTrue(all(re.fullmatch(r"[0-9a-f]{40}",x["commit_sha"])
                                and re.fullmatch(r"[0-9a-f]{40}",x["blob_sha"])
                                for x in row["source_options"]))
            blob=subprocess.run(["git","hash-object",row["path"]],
                                cwd=ROOT,text=True,capture_output=True,check=True).stdout.strip()
            if row["path"] in overrides:
                # Preserve the original 16 open decisions; explicitly pin
                # the replacement blob to a tested API-owner source.
                item=overrides[row["path"]]
                self.assertEqual(row["decision"],"FOUNDATION_BASELINE_RETAINED_REQUIRES_OWNER_REVIEW")
                self.assertEqual(item["previous_blob_sha"],row["integrated_blob_sha"])
                self.assertEqual(blob,item["source_blob_sha"])
                self.assertEqual(row["integrated_blob_sha"],row["foundation_blob_sha"])
                self.assertFalse(row["selected_owner_blobs"])
                continue
            if row["path"]==micro["path"]:
                # Real source bugfix, but still among the original 16
                # owner-retained conflicts. Never modify the 58-row verdict.
                self.assertEqual(row["decision"],micro["historical_58_decision"])
                self.assertEqual(row["integrated_blob_sha"],micro["historical_blob_sha"])
                followup=guarded_history_page_followup(micro,blob)
                self.assertEqual(blob,followup["candidate_blob_sha"])
                self.assertFalse(row["owner_signed_acceptance"])
                continue
            if row["path"] in ui:
                item=ui[row["path"]]
                self.assertTrue(item["historical_58_path"])
                self.assertEqual(item["previous_blob_sha"],row["integrated_blob_sha"])
                self.assertEqual(item["historical_58_decision"],row["decision"])
                self.assertEqual(blob,item["source_blob_sha"])
                # In particular, one formerly retained UI test remains
                # owner-pending; moving its code never provides owner signoff.
                self.assertFalse(item["owner_signed_acceptance"])
                continue
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
