"""Synthetic negative assertions. Never fabricate owner acceptance."""
from __future__ import annotations
from collections import Counter
import copy,hashlib,importlib.util,json
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[3]
spec=importlib.util.spec_from_file_location(
 "f3_evidence",ROOT/"scripts/phase3/verify_f3_evidence_bundle.py")
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
SHA="a"*40

def fixture():
    rows=[]
    for i in range(262):
        rows.append({
          "id":f"P3M{i%26:02}-A{i//26+1:02}","kind":"primary_activity",
          "owner":"TEST_OWNER","canonical_criterion":"SYNTHETIC",
          "dependency":"SYNTHETIC","app_only_slice":"UNAPPROVED",
          "implementation_status":"UNVERIFIED","tested_scope":"SYNTHETIC",
          "acceptance_status":"NOT_ACCEPTED_NO_INDEPENDENT_SIGNED_RECEIPT",
          "git_sha":"","run_or_env":"SYNTHETIC",
          "artifact_link":"","blocker":"TEST","next_action":"OWNER_APPROVAL",
          "generated_from_git_sha":SHA,"counts_as_activity":"true"})
    for i in range(26):
        row=copy.deepcopy(rows[i]);row.update(
           id=f"P3M{i:02}-GATE",kind="independent_module_gate",
           counts_as_activity="false");rows.append(row)
    for i in range(105):
        row=copy.deepcopy(rows[0]);row.update(
           id=f"P3OP{i//12+1:02}-R{i%12+1:02}",
           kind="operational_crosswalk_non_counting",counts_as_activity="false",
           dependency=rows[i%262]["id"]);rows.append(row)
    ledger={"generated_source_sha":SHA,
            "acceptance_claim":"NONE_GENERATED_LEDGER_IS_NOT_OWNER_ACCEPTANCE","rows":rows}
    raw=b'{"spdxVersion":"SPDX-2.3","packages":[{"name":"test"}]}'
    hash=hashlib.sha256(raw).hexdigest()
    spdx={kind:(hash,json.loads(raw)) for kind in ("api","web")}
    scan={"git_sha":SHA,"policy_approved":False,
         "release_decision":"HOLD_PENDING_SECURITY_OWNER_TRIAGE_AND_APPROVED_THRESHOLDS",
         "production_security_gate_accepted":False,
         "sboms":{kind:{"sha256":hash,"package_count":1,"registry_digest":None,
                        "local_image_id":"sha256"+"1"*64 if False else "sha256:"+"1"*64}
                  for kind in ("api","web")},
         "findings":{kind:{"by_severity":{"CRITICAL":0,"HIGH":0},
                         "total_vulnerabilities":0,"critical_high_fix_triage":[]}
                     for kind in ("api","web")}}
    secret={"git_sha":SHA,"rules":{},"total_potential_findings":0,
            "raw_report_uploaded":False,"security_gate_accepted":False,
            "owner_security_triage_complete":False}
    provenance={"git_sha":SHA,"approved_release":False,
                "human_signed_release":False,"registry_digest_verified":False,
                "local_images":{kind:{"registry_manifest_digest":None,
                    "local_content_image_id":"sha256:"+"2"*64}
                    for kind in ("api","web")}}
    return ledger,scan,spdx,secret,provenance

class EvidenceTests(unittest.TestCase):
    def setUp(self):
        self.args=list(fixture())
    def check(self):
        return mod.verify(*self.args,SHA)
    def test_bounded_positive_still_hold(self):
        x=self.check()
        self.assertEqual((x["ids"],x["activity_accepted"],x["gate_accepted"]),(393,0,0))
        self.assertEqual(x["release_decision"],"HOLD")
        self.assertFalse(x["security"]["web"]["registry_release_equivalence"])
    def test_reject_duplicate(self):
        self.args[0]["rows"][1]["id"]=self.args[0]["rows"][0]["id"]
        with self.assertRaises(mod.EvidenceError):self.check()
    def test_reject_missing_id(self):
        self.args[0]["rows"].pop()
        with self.assertRaises(mod.EvidenceError):self.check()
    def test_reject_orphan_mapping(self):
        self.args[0]["rows"][-1]["dependency"]="P3M99-A99"
        with self.assertRaises(mod.EvidenceError):self.check()
    def test_no_forged_acceptance(self):
        self.args[0]["rows"][0]["acceptance_status"]="ACCEPTED"
        with self.assertRaises(mod.EvidenceError):self.check()
    def test_witness_sha_not_inferred_from_ledger_sha(self):
        self.assertEqual(self.check()["per_id_witness_same_sha"],0)
        self.args[0]["rows"][0]["git_sha"]="b"*40
        self.assertEqual(self.check()["per_id_witness_old_sha"],1)
    def test_reject_cross_sha(self):
        self.args[1]["git_sha"]="b"*40
        with self.assertRaises(mod.EvidenceError):self.check()
    def test_reject_sbom_tamper(self):
        self.args[1]["sboms"]["api"]["sha256"]="f"*64
        with self.assertRaises(mod.EvidenceError):self.check()
    def test_reject_missing_critical_details(self):
        f=self.args[1]["findings"]["web"]
        f["by_severity"]["CRITICAL"]=1; f["total_vulnerabilities"]=1
        with self.assertRaises(mod.EvidenceError):self.check()
    def test_reject_secret_count_drift(self):
        self.args[3]["total_potential_findings"]=1
        with self.assertRaises(mod.EvidenceError):self.check()
    def test_reject_pretend_registry_release(self):
        self.args[4]["local_images"]["web"]["registry_manifest_digest"]="sha256:"+"9"*64
        with self.assertRaises(mod.EvidenceError):self.check()
    def test_reject_fake_security_signoff(self):
        self.args[1]["production_security_gate_accepted"]=True
        with self.assertRaises(mod.EvidenceError):self.check()

if __name__=="__main__":
    unittest.main()
