"""The Web microsecond fix cannot forge a prior Foundation/DB owner decision."""
from __future__ import annotations
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[3]
spec=importlib.util.spec_from_file_location(
    "f3_history_micro_ledger",ROOT/"tests/phase3/integration/test_integrated_393_registry.py")
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
ORIGINAL=json.loads(mod.HISTORY_MICRO_DELTA.read_text(encoding="utf8"))

class MicrosecondPatchIntegrity(unittest.TestCase):
    def test_exact_microsecond_web_fix_and_frozen_owner_pending(self):
        row=mod.guarded_history_microsecond_source()
        self.assertEqual(row["candidate_blob_sha"],
                         "f0932d08ff37215111c04fea38f6503d4d3f41f1")
        self.assertEqual(row["historical_58_decision"],
                         "FOUNDATION_BASELINE_RETAINED_REQUIRES_OWNER_REVIEW")

    def reject(self,fn):
        doc=deepcopy(ORIGINAL)
        fn(doc)
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/"tampered-source.json"
            path.write_text(json.dumps(doc),encoding="utf8")
            with patch.object(mod,"HISTORY_MICRO_DELTA",path):
                with self.assertRaises((AssertionError,KeyError,ValueError)):
                    mod.guarded_history_microsecond_source()

    def test_no_approval_or_target_forgery(self):
        for field in ("owner_signed_acceptance","canonical_activity_accepted",
                      "module_gate_accepted"):
            with self.subTest(field=field):
                self.reject(lambda d,k=field:d.update({k:True}))
        self.reject(lambda d:d.update(scope_signed_ci_only=False))
        self.reject(lambda d:d.update(original_58_manifest_frozen=False))

    def test_no_ambiguous_blob_or_path_or_owner_decision(self):
        for field in ("candidate_blob_sha","historical_blob_sha","last_verified_parent_sha"):
            with self.subTest(field=field):
                self.reject(lambda d,k=field:d.update({k:"f"*40}))
        self.reject(lambda d:d.update(path="apps/web/app/page.tsx"))
        self.reject(lambda d:d.update(historical_58_decision="ACCEPTED"))
        self.reject(lambda d:d.update(negative_test_file="other.mjs"))
if __name__=="__main__":
    unittest.main()
