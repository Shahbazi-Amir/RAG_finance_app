"""12 synthetic negative tests of CI-only Docker archive scope and provenance."""
from __future__ import annotations
import importlib.util
from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[3]
spec=importlib.util.spec_from_file_location("airgap",ROOT/"scripts/phase3/check_f3_oci_airgap_receipt.py")
mod=importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(mod)
SHA="a"*40
RUN="12345678"
def sample():
 return {"schema":"foundation.f3.tested_oci_airgap_reimport_smoke.v1",
   "git_sha":SHA,"run_id":RUN,"environment":"DISPOSABLE_CI_RUNNER_ONLY",
   "no_network_and_no_host_published_ports":True,
   "image_ids_before_and_after_archive_identical":True,
   "archive_sha256":"f"*64,"archive_size_bytes":9000000,
   "image_ids":{"api":"sha256:"+"1"*64,"web":"sha256:"+"2"*64},
   "web_send_503":True,"api_send_503":True,"api_ready_503":True,
   "api_live_200":True,"web_capability_send_disabled":True,
   "measured_local_round_trip_seconds":14,"backup_pg_restore":False,
   "mac_target_tested":False,"registry_manifest_digest":None,
   "signed_release":False,"approved_RPO_threshold":None,
   "approved_RTO_threshold":None,"owner_acceptance":False,
   "security_policy_approved":False,"release_state":"HOLD"}
class AirgapReceiptTests(unittest.TestCase):
 def test_positive_remains_hold(self):
  r=mod.check(sample(),SHA,RUN)
  self.assertEqual(r["release"],"HOLD")
  self.assertTrue(r["local_image_round_trip_verified"])
 def test_reject_old_git_sha(self):
  with self.assertRaises(ValueError):mod.check(sample(),"b"*40,RUN)
 def test_reject_wrong_run_id(self):
  with self.assertRaises(ValueError):mod.check(sample(),SHA,"999")
 def test_reject_invalid_sha(self):
  with self.assertRaises(ValueError):mod.check(sample(),"bad",RUN)
 def test_reject_fake_image_digest(self):
  x=sample();x["image_ids"]["web"]="fake"
  with self.assertRaises(ValueError):mod.check(x,SHA,RUN)
 def test_reject_identical_service_image_ids(self):
  x=sample();x["image_ids"]["api"]=x["image_ids"]["web"]
  with self.assertRaises(ValueError):mod.check(x,SHA,RUN)
 def test_reject_fake_registry_release(self):
  x=sample();x["registry_manifest_digest"]="sha256:"+"9"*64
  with self.assertRaises(ValueError):mod.check(x,SHA,RUN)
 def test_reject_mac_overclaim(self):
  x=sample();x["mac_target_tested"]=True
  with self.assertRaises(ValueError):mod.check(x,SHA,RUN)
 def test_reject_fake_owner(self):
  x=sample();x["owner_acceptance"]=True
  with self.assertRaises(ValueError):mod.check(x,SHA,RUN)
 def test_reject_missing_send_fence(self):
  x=sample();x["web_send_503"]=False
  with self.assertRaises(ValueError):mod.check(x,SHA,RUN)
 def test_reject_fake_real_database_restore(self):
  x=sample();x["backup_pg_restore"]=True
  with self.assertRaises(ValueError):mod.check(x,SHA,RUN)
 def test_reject_unapproved_RTO(self):
  x=sample();x["approved_RTO_threshold"]=60
  with self.assertRaises(ValueError):mod.check(x,SHA,RUN)
if __name__=="__main__":unittest.main()
