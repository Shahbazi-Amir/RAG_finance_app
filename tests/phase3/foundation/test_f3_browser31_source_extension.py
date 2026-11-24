"""Negative source/owner constraints for the 31-message genuine browser SQL witness.

No artifact here upgrades a canonical activity, module Gate, or original API
owner review; new browser CI is required on the candidate's exact Git SHA.
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
spec=importlib.util.spec_from_file_location(
    "f3_browser31_ledger",ROOT/"tests/phase3/integration/test_integrated_393_registry.py")
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
ORIGINAL=json.loads(mod.BROWSER31_DELTA.read_text(encoding="utf8"))

class Browser31SourceAttestation(unittest.TestCase):
    def test_exact_new_blob_is_the_only_attested_change(self):
        self.assertEqual(
            mod.verified_candidate_browser31_source()["candidate_blob_sha"],
            "a12c64c75361577b94a8d42bf24714dcc16864e5")

    def reject(self, fn):
        doc=deepcopy(ORIGINAL)
        fn(doc)
        with tempfile.TemporaryDirectory() as temp:
            file=Path(temp)/"test-delta.json"
            file.write_text(json.dumps(doc),encoding="utf8")
            with patch.object(mod,"BROWSER31_DELTA",file):
                with self.assertRaises((AssertionError,KeyError,ValueError)):
                    mod.verified_candidate_browser31_source()

    def test_never_accept_engine_sql011_or_destination(self):
        for field in ("owner_signed_acceptance","target_verified",
                      "engine_enabled","migration_011_applied"):
            with self.subTest(field=field):
                self.reject(lambda x,k=field:x.update({k:True}))
        for field in ("not_new_source_witness_rows","not_a_phase3_activity_acceptance",
                      "uses_only_disposable_ci_pg"):
            with self.subTest(field=field):
                self.reject(lambda x,k=field:x.update({k:False}))

    def test_no_owner_blob_or_root_sha_forgery(self):
        for key in ("parent_verified_sha","root_84_sha",
                    "historical_signed_api_owner_blob_sha","candidate_blob_sha"):
            with self.subTest(field=key):
                self.reject(lambda x,k=key:x.update({k:"0"*40}))

    def test_no_unreviewed_source_path_or_weakening_scope(self):
        self.reject(lambda x:x.update(path="../.git/config"))
        self.reject(lambda x:x["bounded_new_scope"].pop())
        self.reject(lambda x:x["bounded_new_scope"].append("MAC_APPROVED"))

if __name__=="__main__":
    unittest.main()
