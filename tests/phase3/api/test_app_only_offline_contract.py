"""Offline signed APP_ONLY contract only; no network or engine authorization."""
import json
import unittest
from pathlib import Path
from jsonschema import Draft202012Validator, ValidationError
from apps.api.app_only_disabled_routes import app_only_route_allowed

ROOT = Path(__file__).resolve().parents[3]
CONTRACTS = ROOT / "packages/contracts"
PRODUCT = json.loads((CONTRACTS / "product.v1.schema.json").read_text())
DOC = json.loads((CONTRACTS / "product.app-only.openapi.v1.json").read_text())

def validator(name):
    return Draft202012Validator({"$defs": PRODUCT["$defs"], "$ref": "#/$defs/" + name})

def synthetic_source():
    # Metadata only; no resolution, real person, link, live Citation or Answer.
    return {"resolution_status": "unresolved", "source_type": "transcript",
            "source_id": "synthetic-source", "locator": None,
            "credited_author_name": "Synthetic author",
            "editorial_supervisor_name": "Synthetic editor",
            "speaker_name": "Synthetic speaker",
            "content_authority_type": "speaker", "attribution_status": "unknown",
            "display_title": "Synthetic fixture", "display_title_origin": "SYNTHETIC"}

class AppOnlyOfflineContractTests(unittest.TestCase):
    def test_openapi_version_and_routes(self):
        self.assertEqual(DOC["openapi"], "3.1.0")
        self.assertEqual(DOC["x-product-contract-version"], "product.v1")
        expected = {"/v1/conversations", "/v1/conversations/{conversation_id}/messages",
                    "/v1/message-requests/status", "/v1/messages"}
        self.assertEqual(set(DOC["paths"]), expected)
        for path in expected - {"/v1/messages"}:
            self.assertTrue(app_only_route_allowed({"method":"GET","path":path.replace("{conversation_id}","a")}))
            self.assertEqual(DOC["paths"][path]["get"]["security"],
                             [{"privateMTLS": [], "bffAssertion": []}])
        self.assertEqual(set(DOC["paths"]["/v1/messages"]["post"]["responses"]), {"401", "503"})
        self.assertFalse(app_only_route_allowed({"method":"POST","path":"/v1/conversations"}))

    def test_openapi_references_resolve_to_canonical_product_defs(self):
        def walk(value):
            if isinstance(value, dict):
                if "$ref" in value:
                    ref = value["$ref"]
                    self.assertTrue(ref.startswith("./product.v1.schema.json#/$defs/"))
                    self.assertIn(ref.rsplit("/", 1)[1], PRODUCT["$defs"])
                for child in value.values():
                    walk(child)
            elif isinstance(value, list):
                for child in value:
                    walk(child)
        walk(DOC)

    def test_openapi_query_bounds_match_canonical_schema(self):
        for path, kind in (("/v1/conversations","conversation_list_request"),
                          ("/v1/conversations/{conversation_id}/messages","conversation_messages_request"),
                          ("/v1/message-requests/status","message_request_status_query")):
            props = PRODUCT["$defs"][kind]["properties"]
            for param in DOC["paths"][path]["get"]["parameters"]:
                name = param["name"]
                expected = props[name]
                if name in ("cursor", "requested_conversation_id"):
                    expected = expected["oneOf"][0]
                self.assertEqual({k:v for k,v in param["schema"].items() if k!="default"}, expected)
                if name in ("conversation_id","client_message_id","idempotency_key"):
                    self.assertTrue(param["required"])

    def test_offline_no_docs_or_implicit_mutations(self):
        for path in ("/openapi.json", "/docs", "/redoc", "/v1/delete", "/v1/feedback"):
            self.assertFalse(app_only_route_allowed({"method":"GET","path":path}))
            self.assertFalse(app_only_route_allowed({"method":"POST","path":path}))

    def assert_field_roundtrip(self, field):
        payload = synthetic_source()
        validate = validator("source_attribution")
        validate.validate(payload)
        restored = json.loads(json.dumps(payload, ensure_ascii=False))
        validate.validate(restored)
        self.assertEqual(restored[field], payload[field])
        self.assertIsNone(restored["locator"])
        self.assertEqual(restored["attribution_status"], "unknown")
        del restored[field]
        with self.assertRaises(ValidationError):
            validate.validate(restored)

    def test_credited_author_field_required_and_separate(self):
        self.assert_field_roundtrip("credited_author_name")

    def test_editor_field_required_and_separate(self):
        self.assert_field_roundtrip("editorial_supervisor_name")
        source = synthetic_source()
        source["credited_author_name"] = None
        validator("source_attribution").validate(source)
        self.assertIsNone(source["credited_author_name"])
        self.assertEqual(source["editorial_supervisor_name"], "Synthetic editor")

    def test_transcript_speaker_required_and_separate(self):
        self.assert_field_roundtrip("speaker_name")

    def test_authority_and_attribution_fields_required(self):
        for field in ("content_authority_type", "attribution_status"):
            self.assert_field_roundtrip(field)
        for field in ("content_authority_type", "attribution_status"):
            bad = dict(synthetic_source(), **{field: "invented_verified_status"})
            with self.assertRaises(ValidationError):
                validator("source_attribution").validate(bad)

    def test_unresolved_metadata_cannot_carry_locator(self):
        source = synthetic_source()
        source["locator"] = {"kind":"transcript_timestamp","url":None,"page":None,"timestamp_ms":0}
        with self.assertRaises(ValidationError):
            validator("source_attribution").validate(source)

if __name__ == "__main__":
    unittest.main()
