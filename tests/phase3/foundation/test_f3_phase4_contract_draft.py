"""Design-only P3M25-A09: strict draft version and synthetic links. No runtime."""
from __future__ import annotations
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import unittest
from jsonschema import Draft202012Validator,ValidationError

ROOT=Path(__file__).resolve().parents[3]
SCHEMA=ROOT/"docs/operations/F3_PHASE4_EXTENSION_BOUNDARY_DRAFT.schema.json"
ENTITIES=("financial_profiles","assessments","goals","action_plans")
def fixture():
    entities={}
    for i,name in enumerate(ENTITIES):
        refs=[] if i==0 else [{"entity":ENTITIES[i-1],"id":"synthetic_"+ENTITIES[i-1],"owner_ref":"synthetic_owner_a"}]
        entities[name]={"entity":name,"id":"synthetic_"+name,"owner_ref":"synthetic_owner_a","revision":1,"refs":refs}
    return {"contract_version":"phase4.extension-boundary.draft.v1","status":"PROPOSAL_NOT_APPROVED","runtime_enabled":False,"entities":entities}

def validate(doc):
    Draft202012Validator(json.loads(SCHEMA.read_text())).validate(doc)
    records=doc["entities"]
    if len({r["id"] for r in records.values()})!=len(records):raise ValueError("DUPLICATE_SYNTHETIC_ID")
    owner=records["financial_profiles"]["owner_ref"]
    for r in records.values():
        if r["owner_ref"]!=owner:raise ValueError("CROSS_OWNER_DRAFT")
        for ref in r["refs"]:
            target=records[ref["entity"]]
            if ref["id"]!=target["id"] or ref["owner_ref"]!=owner:
                raise ValueError("UNRESOLVED_OR_FOREIGN_DRAFT_REF")
    return True

class FutureDesignBoundary(unittest.TestCase):
    def test_draft_schema_is_valid_and_synthetic_graph(self):
        Draft202012Validator.check_schema(json.loads(SCHEMA.read_text()))
        self.assertTrue(validate(fixture()))
    def test_unapproved_or_runtime_activation_denied(self):
        for edit in ({"status":"APPROVED"},{"runtime_enabled":True}):
            with self.assertRaises(ValidationError):validate({**fixture(),**edit})
    def test_foreign_contract_version_denied(self):
        for v in ("product.v1","phase4.extension-boundary.v2","phase4.extension-boundary.draft.v2"):
            with self.assertRaises(ValidationError):validate({**fixture(),"contract_version":v})
    def test_actual_personal_financial_payload_not_allowed(self):
        for field in ("email","balance","national_id","income","question","score","secret"):
            d=fixture();d["entities"]["financial_profiles"][field]="synthetic_forbidden"
            with self.assertRaises(ValidationError):validate(d)
    def test_no_non_synthetic_identity(self):
        d=fixture();d["entities"]["financial_profiles"]["owner_ref"]="real-owner"
        with self.assertRaises(ValidationError):validate(d)
    def test_invalid_reference_kind_rejected(self):
        d=fixture();d["entities"]["action_plans"]["refs"][0]["entity"]="financial_profiles"
        with self.assertRaises(ValidationError):validate(d)
    def test_cross_owner_rejected_even_with_structurally_valid_doc(self):
        d=fixture();d["entities"]["action_plans"]["refs"][0]["owner_ref"]="synthetic_other"
        with self.assertRaises(ValueError):validate(d)
    def test_unknown_ref_and_duplicate_id_rejected(self):
        d=fixture();d["entities"]["goals"]["refs"][0]["id"]="synthetic_unknown"
        with self.assertRaises(ValueError):validate(d)
        d=fixture();d["entities"]["goals"]["id"]=d["entities"]["assessments"]["id"]
        with self.assertRaises(ValueError):validate(d)
    def test_no_live_product_schema_or_migration_changes(self):
        # Compare frozen runtime trees with the same approved app-only base,
        # NOT just a string search through files or hypothetical data.
        base="f2b743a1588cac76fddafc36e3b489deb59d42ac"
        for p in ("packages/contracts","infra/postgres/migrations","apps/web","src/phase3"):
            self.assertEqual(subprocess.check_output(["git","rev-parse",base+":"+p],cwd=ROOT),
                             subprocess.check_output(["git","rev-parse","HEAD:"+p],cwd=ROOT))
        self.assertFalse((ROOT/"infra/postgres/migrations/011_product_answer_claims.up.sql").exists())
        self.assertTrue(SCHEMA.is_relative_to(ROOT/"docs/operations"))

if __name__=="__main__":
    suite=unittest.defaultTestLoader.loadTestsFromTestCase(FutureDesignBoundary)
    outcome=unittest.TextTestRunner(verbosity=2).run(suite)
    if not outcome.wasSuccessful():raise SystemExit(1)
    out=ROOT/"ci_receipts/f3_phase4_extension_contract_draft.json";out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps({"schema":"foundation.f3.phase4_boundary_draft.v1","source_sha":os.environ["GITHUB_SHA"],
        "run_id":os.environ["GITHUB_RUN_ID"],"schema_sha256":hashlib.sha256(SCHEMA.read_bytes()).hexdigest(),
        "tests":outcome.testsRun,"synthetic_entities":list(ENTITIES),"phase4_implemented":False,
        "runtime_enabled":False,"owner_approved":False,"accepted":False},indent=2)+"\n")
