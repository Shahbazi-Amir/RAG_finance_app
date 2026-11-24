"""Negative owner-signoff/manifest-forgery tests for exact #110 source delta.

Owner decisions and canonical 42/58 snapshots are *not* changed or accepted.
"""
from __future__ import annotations
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[3]
SPEC=importlib.util.spec_from_file_location(
    "tested_ui_ledger",ROOT/"tests/phase3/integration/test_integrated_393_registry.py")
MOD=importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MOD)
SOURCE=json.loads(MOD.UI_TRANSFER.read_text(encoding="utf-8"))

class StrictReviewedUiDelta(unittest.TestCase):
    def test_actual_nine_blob_exact_source(self):
        rows=MOD.reviewed_ui_overrides()
        self.assertEqual(len(rows),9)
        self.assertEqual(sum(x["historical_42_path"] for x in rows.values()),3)
        self.assertEqual(sum(x["historical_58_path"] for x in rows.values()),4)
        self.assertFalse(SOURCE["p0_1_accepted"])

    def mutated_fails(self, change):
        doc=deepcopy(SOURCE)
        change(doc)
        with tempfile.TemporaryDirectory() as temp:
            dest=Path(temp)/"ui-transfer.json"
            dest.write_text(json.dumps(doc),encoding="utf-8")
            with patch.object(MOD,"UI_TRANSFER",dest):
                with self.assertRaises((AssertionError,KeyError,ValueError)):
                    MOD.reviewed_ui_overrides()

    def test_no_owner_or_target_acceptance_injection(self):
        self.mutated_fails(lambda d:d.update(owner_signed_acceptance=True))
        self.mutated_fails(lambda d:d.update(p0_1_accepted=True))
        self.mutated_fails(lambda d:d.update(target_verified=True))
        self.mutated_fails(lambda d:d["rows"][0].update(owner_signed_acceptance=True))

    def test_no_unreviewed_path_or_sha_or_provenance(self):
        self.mutated_fails(lambda d:d["rows"][0].update(path="../.git/secrets"))
        self.mutated_fails(lambda d:d["rows"][0].update(source_blob_sha="0"*40))
        self.mutated_fails(lambda d:d["rows"][0].update(previous_blob_sha="none"))
        self.mutated_fails(lambda d:d.update(tested_source_sha="1"*40))
        self.mutated_fails(lambda d:d.update(source_ci_runs=[]))

    def test_historical_owner_decision_remains_open(self):
        self.mutated_fails(lambda d:d["rows"][7].update(
            historical_58_decision="ACCEPTED"))
        self.mutated_fails(lambda d:d["rows"][7].update(
            historical_58_path=False))
        self.mutated_fails(lambda d:d["rows"].pop())
        self.mutated_fails(lambda d:d["rows"].append(deepcopy(d["rows"][0])))

if __name__=="__main__":
    unittest.main()
