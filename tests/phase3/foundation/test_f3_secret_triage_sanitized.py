"""Negative tests for safe source path triage with zero raw credential output."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / "scripts/phase3/summarize_f3_secret_findings.py"
spec = importlib.util.spec_from_file_location("safe_secret_triage", SOURCE)
mod = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(mod)
SHA = "f" * 40


class GitleaksTriageTests(unittest.TestCase):
    def test_empty_is_safe_but_still_not_security_approved(self):
        out = mod.summarize([], SHA)
        self.assertEqual(out["potential_findings_total"], 0)
        self.assertEqual(out["security_release_gate"], "HOLD_PENDING_REVIEW")
        self.assertEqual(out["scanner_scope"], "CHECKED_OUT_FILES_ONLY_NO_GIT_HISTORY")

    def test_exact_count_and_cohort_not_fixture_clearance(self):
        out = mod.summarize([
            {"RuleID":"generic-api-key", "File":"./tests/fixtures/demo.py", "StartLine":11},
            {"RuleID":"generic-api-key", "File":"apps/api/runtime.py", "StartLine":21},
            {"RuleID":"generic-api-key", "File":"apps/api/runtime.py", "StartLine":22},
        ], SHA)
        self.assertEqual(out["potential_findings_total"], 3)
        self.assertEqual(sum(out["by_cohort"].values()), 3)
        self.assertEqual(out["by_rule"]["generic-api-key"], 3)
        self.assertEqual(len(out["source_locations"]), 2)
        self.assertTrue(all(x["security_review"]=="OPEN_NOT_EXEMPTED"
                            for x in out["source_locations"]))

    def test_never_copy_secret_match_author_commit_or_excerpt(self):
        secret = "SHOULD_NEVER_APPEAR_IN_OUTPUT_777"
        row = {"RuleID":"generic-api-key","File":"src/app.py","StartLine":9,
               "Secret":secret,"Match":secret,"Line":secret,"Author":secret,
               "Commit":secret,"Entropy":secret,"Description":secret}
        out = mod.summarize([row],SHA)
        encoded = json.dumps(out)
        self.assertNotIn(secret, encoded)
        for field in ("Secret","Match","Line","Author","Commit","Entropy"):
            self.assertNotIn('"' + field + '"', encoded)

    def test_path_traversal_and_absolute_path_redacted(self):
        for path in ("../secrets", "/home/runner/private.env", "..\\secret",
                     "apps//secret", "test@secret.com", ""):
            sanitized=mod.sanitize_path(path)
            if path == "apps//secret":
                # Double slash should not leak outside the repository.
                self.assertTrue(sanitized.startswith("apps/"))
            else:
                self.assertEqual(sanitized,"REDACTED_UNKNOWN_PATH")

    def test_bad_rule_cannot_inject_secret(self):
        out=mod.summarize([{"RuleID":"\nSECRET_VALUE_!","File":"tests/t.py"}], SHA)
        self.assertEqual(out["by_rule"],{"REDACTED_UNKNOWN_RULE":1})

    def test_sha_mismatch_and_malformed_fail_closed(self):
        with self.assertRaises(ValueError):
            mod.summarize([], "not-a-commit")
        with self.assertRaises(ValueError):
            mod.summarize({"not":"list"}, SHA)
        with self.assertRaises(ValueError):
            mod.summarize(["not-a-dict"],SHA)

    def test_never_claim_closed_if_findings_are_zero(self):
        out=mod.summarize([],SHA)
        self.assertIn("HOLD",out["security_release_gate"])
        self.assertTrue(out["all_test_fixture_matches_require_review"])


if __name__=="__main__":
    unittest.main()
