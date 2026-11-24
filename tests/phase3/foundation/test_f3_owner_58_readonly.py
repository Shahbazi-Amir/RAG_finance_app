"""Negative tests on the exact frozen 58-path register; no code execution."""
from __future__ import annotations
from copy import deepcopy
import importlib.util,json
from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[3]
spec=importlib.util.spec_from_file_location("a",ROOT/"scripts/phase3/verify_f3_owner_58_readonly.py")
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
DOC=json.loads((ROOT/"coordination/integration/FOUR_PR_58_PATH_THREE_WAY_AUDIT_20261124.json").read_text())

class FrozenAuditTests(unittest.TestCase):
 def test_actual_frozen_58_16_are_consistent_without_owner_pass(self):
  x=mod.check_manifest(DOC)
  self.assertEqual(len(x),16)
  self.assertFalse(DOC["p0_1_accepted"])
 def test_count_cannot_auto_increase(self):
  x=deepcopy(DOC);x["summary"]["retained_pending"]=15
  with self.assertRaises(mod.SourceAuditError):mod.check_manifest(x)
 def test_no_duplicate_source_path(self):
  x=deepcopy(DOC);x["paths"][1]["path"]=x["paths"][0]["path"]
  with self.assertRaises(mod.SourceAuditError):mod.check_manifest(x)
 def test_no_unknown_decision_class(self):
  x=deepcopy(DOC);x["paths"][0]["decision"]="ACCEPTED"
  with self.assertRaises(mod.SourceAuditError):mod.check_manifest(x)
 def test_no_forged_owner_acceptance(self):
  x=deepcopy(DOC);x["paths"][0]["owner_signed_acceptance"]=True
  with self.assertRaises(mod.SourceAuditError):mod.check_manifest(x)
 def test_path_traversal_denied(self):
  for p in ("../../secrets","/etc/passwd","-danger",".git/credentials","file\\secret"):
   with self.subTest(p=p):
    with self.assertRaises(mod.SourceAuditError):mod.safe_path(p)
 def test_missing_blob_sha_denied(self):
  x=deepcopy(DOC);x["paths"][0]["source_options"][0]["blob_sha"]="unknown"
  with self.assertRaises(mod.SourceAuditError):mod.check_manifest(x)
 def test_missing_origin_sha_denied(self):
  x=deepcopy(DOC);x["paths"][0]["source_options"][0]["commit_sha"]="unknown"
  with self.assertRaises(mod.SourceAuditError):mod.check_manifest(x)
 def test_source_owner_must_be_known(self):
  x=deepcopy(DOC);x["paths"][0]["source_options"][0]["owner"]="invented"
  with self.assertRaises(mod.SourceAuditError):mod.check_manifest(x)
 def test_unique_line_counts_not_semantic_claim(self):
  x=mod.unique_source_lines("A\nA\n B\n","A\n C\n")
  self.assertEqual(x["owner_only_nonempty_line_kinds"],1)
  self.assertEqual(x["same_nonempty_line_kinds"],1)
  self.assertEqual(x["candidate_only_nonempty_line_kinds"],1)
 def test_whitespace_only_lines_not_counted(self):
  x=mod.unique_source_lines(" \n  A  \n","A\n\n")
  self.assertEqual(x["owner_only_nonempty_line_kinds"],0)
 def test_source_count_guard_not_authorization(self):
  x=mod.check_manifest(DOC)
  self.assertTrue(all(r["decision"]=="FOUNDATION_BASELINE_RETAINED_REQUIRES_OWNER_REVIEW" for r in x))

if __name__=="__main__":unittest.main()
