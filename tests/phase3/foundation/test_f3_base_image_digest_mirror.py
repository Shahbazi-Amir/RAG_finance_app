"""Immutable platform-digest OCI mirror guard for 429 recovery."""
from pathlib import Path
import re, unittest
ROOT=Path(__file__).resolve().parents[3]
PINS={"Dockerfile.api":("python","f3dac913ab53b78c64f26d5518fcd7043d5a1a46522d6a493b598c3ed12f62a6"),
"Dockerfile.api.signed_history":("python","f3dac913ab53b78c64f26d5518fcd7043d5a1a46522d6a493b598c3ed12f62a6"),
"Dockerfile.web":("node","47725aca53d3295ec2d3be8f62726599b3033cc262edc2c7e429909b3ac599fc")}
class DigestGuard(unittest.TestCase):
 def test_registry_change_does_not_modify_digest(self):
  for file,(image,digest) in PINS.items():
   s=(ROOT/"infra/phase3_l1"/file).read_text(encoding="utf-8")
   self.assertEqual(re.findall(r"^ARG BASE=(.+)$",s,re.M),[f"docker.io/library/{image}@sha256:{digest}"])
   self.assertIn("FROM "+chr(36)+"{BASE}",s)
 def test_no_unpinned_tag_or_latest(self):
  for file in PINS:
   s=(ROOT/"infra/phase3_l1"/file).read_text()
   self.assertNotIn("latest",s)
   self.assertNotIn("public.ecr.aws/docker/library",s)
 def test_signed_api_base_and_minimal_api_base_same(self):
  self.assertEqual(PINS["Dockerfile.api"],PINS["Dockerfile.api.signed_history"])
 def test_digests_are_sha256_length(self):
  self.assertEqual({len(v[1]) for v in PINS.values()},{64})
  self.assertTrue(all(re.fullmatch("[a-f0-9]{64}",digest) for _,digest in PINS.values()))
if __name__=="__main__": unittest.main()
