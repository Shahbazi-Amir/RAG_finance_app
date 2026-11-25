import copy
import unittest
from apps.api import history_api
from apps.api.private_history_contract import signed_history_openapi
from jsonschema import Draft202012Validator,ValidationError

class SignedHistoryContract(unittest.TestCase):
    def test_exact_three_read_paths_and_version(self):
        doc=signed_history_openapi()
        self.assertEqual(doc["openapi"],"3.1.0")
        self.assertEqual(doc["info"]["version"],"product.v1")
        self.assertEqual(set(doc["paths"]),{"/v1/conversations","/v1/conversations/{conversation_id}/messages","/v1/message-requests/status"})
        self.assertTrue(all(set(v)=={"get"} for v in doc["paths"].values()))
    def test_mtls_and_assertion_required_together(self):
        doc=signed_history_openapi()
        for v in doc["paths"].values():
            self.assertEqual(v["get"]["security"],[{"TrustedBFFTLS":[],"BFFAssertion":[]}])
            self.assertTrue(all(r["headers"]["Cache-Control"]["schema"]["const"]=="no-store" for r in v["get"]["responses"].values()))
        self.assertEqual(doc["components"]["securitySchemes"]["TrustedBFFTLS"]["type"],"mutualTLS")
    def test_exact_original_contract_and_resolvable_refs(self):
        doc=signed_history_openapi()
        self.assertEqual(doc["components"]["schemas"]["ProductContract"],history_api.openapi()["components"]["schemas"]["ProductContract"])
        def refs(v):
            if isinstance(v,dict):
                for k,x in v.items():
                    if k=="$ref":
                        self.assertTrue(x.startswith("#/"))
                        node=doc
                        for key in x[2:].split("/"):node=node[key.replace("~1","/").replace("~0","~")]
                    else:refs(x)
            elif isinstance(v,list):
                for x in v:refs(x)
        refs(doc)
    def test_version_wrong_owner_field_and_extra_secret_rejected(self):
        base=history_api.SCHEMA
        schema={"$schema":base["$schema"],"$defs":base["$defs"],"$ref":"#/$defs/conversation_page"}
        check=Draft202012Validator(schema)
        valid={"kind":"conversation_page","contract_version":"product.v1","scope_user_id":"owner_fixture",
               "items":[],"page":{"limit":20,"has_more":False,"next_cursor":None}}
        check.validate(valid)
        for edit in ({"contract_version":"product.v2"},{"scope_user_id":None},{"secret":"canary"}):
            with self.assertRaises(ValidationError):check.validate({**valid,**edit})
    def test_independent_copy_original_is_not_rewritten(self):
        original=copy.deepcopy(history_api.openapi())
        signed_history_openapi()["paths"].clear()
        self.assertEqual(original,history_api.openapi())
