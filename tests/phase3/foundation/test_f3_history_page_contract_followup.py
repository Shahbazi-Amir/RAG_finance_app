"""Reject invented follow-up evidence while preserving the #118 parent record."""
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[3]
spec=importlib.util.spec_from_file_location("history_page_contract_registry",
    ROOT/"tests/phase3/integration/test_integrated_393_registry.py")
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
PARENT=json.loads(mod.HISTORY_MICRO_DELTA.read_text(encoding="utf8"))
ORIGINAL=json.loads(mod.HISTORY_PAGE_FOLLOWUP.read_text(encoding="utf8"))
class PageContractFollowup(unittest.TestCase):
    def test_parent_frozen_and_exact_child(self):
        self.assertEqual(mod.guarded_history_microsecond_source(),PARENT)
        self.assertEqual(mod.guarded_history_page_followup(PARENT,
            "b9ebe6659c334e02ae24a46a0b07f3a65ffa02a0"),ORIGINAL)
    def test_reject_mutated_pins_and_false_acceptance(self):
        for key in ORIGINAL:
            with self.subTest(key=key):
                d=deepcopy(ORIGINAL)
                d[key]=not d[key] if isinstance(d[key],bool) else "tampered"
                with tempfile.TemporaryDirectory() as tmp:
                    path=Path(tmp)/"bad.json"
                    path.write_text(json.dumps(d),encoding="utf8")
                    with patch.object(mod,"HISTORY_PAGE_FOLLOWUP",path):
                        with self.assertRaises(AssertionError):
                            mod.guarded_history_page_followup(PARENT,"b9ebe6659c334e02ae24a46a0b07f3a65ffa02a0")
    def test_reject_actual_blob_drift(self):
        with self.assertRaises(AssertionError):
            mod.guarded_history_page_followup(PARENT,"0"*40)
if __name__=="__main__":
    unittest.main()
