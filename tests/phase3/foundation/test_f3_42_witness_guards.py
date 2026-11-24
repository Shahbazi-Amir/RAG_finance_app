"""Synthetic negative tests for 42 added witnesses and zero Gate promotion."""
from __future__ import annotations
import copy
import importlib.util
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[3]
spec=importlib.util.spec_from_file_location(
  "f3_witnesses",ROOT/"scripts/phase3/emit_f3_42_source_ci_witnesses.py")
mod=importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(mod)
SHA="a"*40
RUN="123456789"
WORKFLOW=(
 "npm --prefix apps/web run test\n"
 "python -m unittest discover -s tests/phase3/api\n"
 "python -m unittest discover -s tests/phase3/contracts\n"
 "bash scripts/19_history_rls_negative_matrix.sh\n"
 "Grype scan exact API image SPDX after test\n"
 "Grype scan exact Web image SPDX after test\n"
)
# For actual positive and path markers, invoke the real source-backed matrix
# in the full CI after jobs succeed; this fixture focuses on malicious changes.
class WitnessGuards(unittest.TestCase):
    def test_refuse_fabricated_git_sha(self):
        with self.assertRaises(AssertionError):
            mod.attest({}, {}, "bad-sha", RUN, WORKFLOW)
    def test_refuse_fabricated_run_id(self):
        with self.assertRaises(AssertionError):
            mod.attest({}, {}, SHA, "run-1", WORKFLOW)
    def test_refuse_nonexistent_file(self):
        with self.assertRaises(AssertionError):
            mod.verified_repo_file("missing/a.py","test")
    def test_refuse_parent_path_traversal(self):
        with self.assertRaises(AssertionError):
            mod.verified_repo_file("../private.txt","x")
    def test_refuse_absolute_path(self):
        with self.assertRaises(AssertionError):
            mod.verified_repo_file("/etc/hosts","x")
    def test_refuse_marker_not_in_source(self):
        with self.assertRaises(AssertionError):
            mod.verified_repo_file("tests/phase3/ui/source-display.test.mjs",
                                   "REAL_WITNESS_DOES_NOT_EXIST")
    def test_refuse_fake_baseline(self):
        original={"generated_source_sha":SHA,"counts":{"activities":2},
                  "acceptance_claim":"NONE_GENERATED_LEDGER_IS_NOT_OWNER_ACCEPTANCE",
                  "rows":[]}
        with self.assertRaises((AssertionError,KeyError)):
            mod.attest(original,{"schema":"fake","rows":[]},SHA,RUN,WORKFLOW)
    def test_no_automatic_promotion_flag_in_implementation(self):
        content=(ROOT/"scripts/phase3/emit_f3_42_source_ci_witnesses.py").read_text()
        self.assertIn('"new_owner_accepted":0',content)
        self.assertIn('"new_complete_canonical_activities":0',content)
        self.assertIn('"security_release":"HOLD_PENDING_SECURITY_OWNER_TRIAGE"',content)
    def test_matrix_declares_42_unique_nonapprovals(self):
        import json
        d=json.loads((ROOT/"coordination/integration/F3_42_NEW_BOUNDED_CI_LAB_SLICES.json").read_text())
        self.assertEqual(len(d["rows"]),42)
        self.assertEqual(len(set(x["id"] for x in d["rows"])),42)
        self.assertTrue(all(x["owner_acceptance"] is False and
                            x["target_verified"] is False and
                            x["full_criterion_satisfied"] is False for x in d["rows"]))
    def test_42_all_match_actual_source_markers(self):
        import json
        d=json.loads((ROOT/"coordination/integration/F3_42_NEW_BOUNDED_CI_LAB_SLICES.json").read_text())
        self.assertTrue(all(mod.verified_repo_file(x["source_file"],
                 x["literal_assertion"]) for x in d["rows"]))

if __name__=="__main__":
    unittest.main()
