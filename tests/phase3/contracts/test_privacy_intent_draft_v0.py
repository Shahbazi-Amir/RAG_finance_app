"""Policy-neutral NON-EXECUTABLE consent/withdrawal/export draft v0 contract tests.

No acceptance, consent state, retention periods, export body, real user identity,
server endpoint, database mutation or production credential used by these tests.
"""
from __future__ import annotations
from copy import deepcopy
import json
from pathlib import Path
import unittest
from jsonschema import Draft202012Validator

ROOT=Path(__file__).resolve().parents[3]
DRAFT=ROOT/"packages/contracts/privacy_intent.draft.v0.schema.json"
EXISTING=ROOT/"packages/contracts/product.v1.schema.json"
DOC=json.loads(DRAFT.read_text(encoding="utf-8"))
CURRENT=json.loads(EXISTING.read_text(encoding="utf-8"))
CHECK=Draft202012Validator(DOC)
NONCE="0123456789abcdef0123456789abcdef"
VERSION="privacy_intent.draft.v0"
BASE={
 "consent_intent_draft":{
  "kind":"consent_intent_draft","contract_version":VERSION,
  "request_nonce":NONCE,"purpose_reference":"PURPOSE_PENDING_POLICY_01",
  "requested_action":"REQUEST_POLICY_REVIEW"},
 "withdrawal_intent_draft":{
  "kind":"withdrawal_intent_draft","contract_version":VERSION,
  "request_nonce":NONCE,"prior_consent_ref":"opaqueConsentReference_ABC123",
  "requested_action":"REQUEST_POLICY_REVIEW"},
 "export_intent_draft":{
  "kind":"export_intent_draft","contract_version":VERSION,
  "request_nonce":NONCE,"data_category_reference":"CATEGORY_PENDING_POLICY_01",
  "requested_action":"REQUEST_POLICY_REVIEW"},
 "privacy_policy_pending_receipt":{
  "kind":"privacy_policy_pending_receipt","contract_version":VERSION,
  "request_nonce":NONCE,"status":"POLICY_NOT_APPROVED",
  "request_accepted":False,"side_effects_performed":False},
}

class PrivacyIntentDraftTests(unittest.TestCase):
 def valid(self, obj):
  self.assertEqual(list(CHECK.iter_errors(obj)),[])
 def invalid(self,obj):
  self.assertTrue(list(CHECK.iter_errors(obj)),f"Unexpected acceptance: {obj}")
 def test_schema_is_draft_2020_12(self):
  Draft202012Validator.check_schema(DOC)
  self.assertEqual(DOC["$schema"],"https://json-schema.org/draft/2020-12/schema")
 def test_four_policy_pending_intent_kinds_only(self):
  self.assertEqual(set(DOC["$defs"]),{"consent_intent","withdrawal_intent","export_intent","policy_pending"})
  self.assertEqual(len(DOC["oneOf"]),4)
  self.assertIn("DRAFT ONLY",DOC["$comment"])
 def test_all_four_valid_syntax_examples(self):
  for obj in BASE.values():
   with self.subTest(kind=obj["kind"]):self.valid(obj)
 def test_no_product_v1_contract_mutation(self):
  self.assertEqual(CURRENT["$id"],"urn:ragfinance:product:v1")
  self.assertEqual(len(CURRENT["oneOf"]),24)
  self.assertEqual(CURRENT["$schema"],DOC["$schema"])
  self.assertIn("feedback",CURRENT["$defs"])
  self.assertIn("delete_command",CURRENT["$defs"])
 def test_no_privacy_draft_claims_to_be_product_v1(self):
  self.assertNotEqual(DOC["$id"],CURRENT["$id"])
  self.assertFalse(any(name in CURRENT["$defs"] for name in BASE))
 def test_missing_nonce_rejected(self):
  for obj in BASE.values():
   broken=deepcopy(obj);del broken["request_nonce"]
   self.invalid(broken)
 def test_nonhex_nonce_rejected(self):
  for bad in ("not-an-id","A"*32,"0"*31,"0"*33,"{user}",123,None):
   obj=deepcopy(BASE["consent_intent_draft"]);obj["request_nonce"]=bad
   self.invalid(obj)
 def test_wrong_version_and_unknown_kind_rejected(self):
  for field,value in (("contract_version","product.v1"),
                      ("kind","consent_authorized")):
   obj=deepcopy(BASE["consent_intent_draft"]);obj[field]=value
   self.invalid(obj)
 def test_unauthorized_action_cannot_be_represented(self):
  for action in ("APPROVE","CONSENT_GRANTED","PERFORM_EXPORT","EXECUTE",
                 "DELETE_ALL","AUTO_WITHDRAW",None):
   obj=deepcopy(BASE["consent_intent_draft"])
   obj["requested_action"]=action
   self.invalid(obj)
 def test_forged_acceptance_and_side_effects_rejected(self):
  for key,value in (("request_accepted",True),("side_effects_performed",True),
                    ("status","APPROVED"),("status","EXPORT_READY")):
   obj=deepcopy(BASE["privacy_policy_pending_receipt"]);obj[key]=value
   self.invalid(obj)
 def test_raw_export_data_not_allowed(self):
  obj=deepcopy(BASE["export_intent_draft"])
  obj["data"]={"bank_transactions":[{"amount":1}]}
  self.invalid(obj)
 def test_sensitive_identity_and_token_fields_rejected(self):
  for key,value in (("owner_user_id","alice"),("email","a@example.com"),
                    ("session_cookie","sensitive"),("api_key","sk-test"),
                    ("jwt","fake"),("address","private")):
   obj=deepcopy(BASE["consent_intent_draft"]);obj[key]=value
   self.invalid(obj)
 def test_unapproved_retention_and_deletion_values_rejected(self):
  for key,value in (("retention_days",30),("delete_at","tomorrow"),
                    ("automatic_erasure",True),("export_download_url","https://example.com")):
   obj=deepcopy(BASE["withdrawal_intent_draft"]);obj[key]=value
   self.invalid(obj)
 def test_unapproved_purpose_rejected(self):
  for value in ("","marketing ads",123,"PURPOSE-SPACE",None):
   obj=deepcopy(BASE["consent_intent_draft"])
   obj["purpose_reference"]=value
   self.invalid(obj)
 def test_missing_withdrawal_reference_rejected(self):
  for value in ("", "short", 10, None, "token space"):
   obj=deepcopy(BASE["withdrawal_intent_draft"])
   obj["prior_consent_ref"]=value
   self.invalid(obj)
 def test_draft_does_not_define_endpoints_or_effects(self):
  raw=DRAFT.read_text(encoding="utf-8")
  for prohibited in ('"/v1/privacy"','"export_payload"','"approved": true',
                     '"store_consent": true','"allow_delete": true'):
   self.assertNotIn(prohibited,raw)
 def test_extra_field_after_ack_rejected(self):
  obj=deepcopy(BASE["privacy_policy_pending_receipt"])
  obj["receipt_uri"]="/private"
  self.invalid(obj)

if __name__=="__main__":unittest.main()
