"""Fail-closed verification: Docker local archive != signed registry or target restore."""
from __future__ import annotations
import argparse,json,re
from pathlib import Path
SHA=re.compile(r"^[0-9a-f]{40}$")
DIGEST=re.compile(r"^sha256:[a-f0-9]{64}$")
TRUE_KEYS=("no_network_and_no_host_published_ports",
 "image_ids_before_and_after_archive_identical","web_send_503","api_send_503",
 "api_ready_503","api_live_200","web_capability_send_disabled")
FALSE_KEYS=("backup_pg_restore","mac_target_tested","signed_release",
 "owner_acceptance","security_policy_approved")

def check(data:dict,sha:str,run:str)->dict:
 if not isinstance(data,dict) or not isinstance(sha,str) or not SHA.fullmatch(sha):
  raise ValueError("INVALID_RECEIPT_OR_SHA")
 if data.get("git_sha")!=sha or data.get("run_id")!=run:
  raise ValueError("CROSS_RUN_OR_CROSS_SHA")
 if data.get("schema")!="foundation.f3.tested_oci_airgap_reimport_smoke.v1" or data.get("environment")!="DISPOSABLE_CI_RUNNER_ONLY":
  raise ValueError("FORGED_ENVIRONMENT_SCOPE")
 imgs=data.get("image_ids")
 if not isinstance(imgs,dict) or set(imgs)!={"api","web"} or any(not isinstance(v,str) or not DIGEST.fullmatch(v) for v in imgs.values()) or imgs["api"]==imgs["web"]:
  raise ValueError("IMAGE_IDS_INVALID")
 ah=data.get("archive_sha256")
 if not isinstance(ah,str) or not re.fullmatch(r"[a-f0-9]{64}",ah):
  raise ValueError("ARCHIVE_HASH_INVALID")
 if type(data.get("archive_size_bytes")) is not int or data["archive_size_bytes"]<1000000:
  raise ValueError("ARCHIVE_LENGTH_INVALID")
 if type(data.get("measured_local_round_trip_seconds")) is not int or data["measured_local_round_trip_seconds"]<0:
  raise ValueError("TIMING_INVALID")
 for key in TRUE_KEYS:
  if data.get(key) is not True:raise ValueError("UNPROVEN_TEST_"+key)
 for key in FALSE_KEYS:
  if data.get(key) is not False:raise ValueError("FALSE_RELEASE_CLAIM_"+key)
 if (data.get("registry_manifest_digest") is not None or
     data.get("approved_RPO_threshold") is not None or
     data.get("approved_RTO_threshold") is not None or
     data.get("release_state")!="HOLD"):
  raise ValueError("INVALID_SCOPE_BOUNDARY")
 return {"schema":"foundation.f3.sanitized_airgap_receipt_verified.v1",
  "git_sha":sha,"run_id":run,"local_image_round_trip_verified":True,
  "mac_tested":False,"registry_digest":None,"owner_accepted":False,
  "local_round_trip_seconds":data["measured_local_round_trip_seconds"],
  "release":"HOLD"}

def main():
 p=argparse.ArgumentParser()
 p.add_argument("--receipt",type=Path,required=True)
 p.add_argument("--sha",required=True)
 p.add_argument("--run",required=True)
 p.add_argument("--out",type=Path,required=True)
 a=p.parse_args()
 result=check(json.loads(a.receipt.read_text()),a.sha,a.run)
 a.out.parent.mkdir(parents=True,exist_ok=True)
 a.out.write_text(json.dumps(result,sort_keys=True,indent=2)+"\n")
 print("F3_DISPOSABLE_DOCKER_AIRGAP_RECEIPT_VALIDATED_RELEASE_HOLD")

if __name__=="__main__":main()
