"""Validate the canonical counted register (262+26+105) and no fake Gate acceptance."""
import json
from pathlib import Path
import re
import unittest

ROOT=Path(__file__).resolve().parents[3]
RECORD=ROOT/"coordination/f3_execution/app_only_393_evidence_register.json"
FIELDS=("id owner canonical_criterion dependency app_only_slice implementation_status "
        "tested_scope acceptance_status git_sha run_or_env artifact_link blocker next_action").split()

class CanonicalAppOnlyRegister(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data=json.loads(RECORD.read_text(encoding="utf-8"))
        cls.rows=cls.data["records"]
    def test_393_unique_and_exact_denominators(self):
        self.assertEqual(len(self.rows),393)
        self.assertEqual(len({r["id"] for r in self.rows}),393)
        self.assertEqual(self.data["counts"],{"activity":262,"gate":26,"operational_overlay":105})
    def test_every_row_has_owner_and_required_columns(self):
        for r in self.rows:
            self.assertTrue(all(k in r for k in FIELDS),r["id"])
            self.assertTrue(all(isinstance(r[k],str) and r[k].strip() for k in FIELDS),r["id"])
    def test_no_gates_or_rows_promoted_from_l1(self):
        self.assertTrue(all(r["acceptance_status"]=="NOT_ACCEPTED" for r in self.rows))
        self.assertEqual(self.data["gates_accepted"],0)
        self.assertEqual(self.data["full_baseline"]["accepted"],0)
    def test_id_formats(self):
        types={"activity":r"P3M\d{2}-A\d{2}",
               "gate":r"P3M\d{2}-GATE",
               "operational_overlay":r"P3OP\d{2}-R\d{2}"}
        for r in self.rows:
            self.assertRegex(r["id"],"^"+types[r["kind"]]+"$")
    def test_overlay_mappings_only_reference_real_activities(self):
        ids={r["id"] for r in self.rows if r["kind"]=="activity"}
        for r in self.rows:
            if r["kind"]=="operational_overlay":
                self.assertTrue(set(r["mapped_activity_ids"]).issubset(ids),r["id"])
