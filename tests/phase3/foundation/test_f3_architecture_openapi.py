"""Bounded source architecture and exact versioned internal L1 OpenAPI view.

No endpoint is activated; no live engine or approved architecture is claimed.
"""
import ast
import copy
from pathlib import Path
import re
import unittest
from jsonschema import Draft202012Validator
from apps.api import history_api

ROOT=Path(__file__).resolve().parents[3]
def pointers(doc,node):
    if isinstance(node,dict):
        for k,v in node.items():
            if k=="$ref" and isinstance(v,str) and v.startswith("#/"):
                target=doc
                for part in v[2:].split("/"):
                    part=part.replace("~1","/").replace("~0","~")
                    if not isinstance(target,dict) or part not in target:
                        raise ValueError("DANGLING_OPENAPI_POINTER")
                    target=target[part]
            else:pointers(doc,v)
    elif isinstance(node,list):
        for value in node:pointers(doc,value)

def verify(doc):
    if doc.get("openapi")!="3.1.0":raise ValueError("WRONG_OPENAPI_VERSION")
    paths=doc["paths"]
    required={"/v1/conversations":{"get","post"},"/v1/messages":{"post"},
              "/v1/conversations/{conversation_id}/messages":{"get"},
              "/v1/message-requests/status":{"get"}}
    if set(paths)!=set(required):raise ValueError("OPENAPI_PATH_DRIFT")
    for path,methods in required.items():
        for method in methods:
            if paths[path][method].get("x-product-contract-version")!="product.v1":
                raise ValueError("PRODUCT_VERSION_DRIFT")
    pointers(doc,doc)
    embedded=copy.deepcopy(doc["components"]["schemas"]["ProductContract"])
    def undo(node):
        if isinstance(node,dict):
            for k,v in node.items():
                if k=="$ref" and isinstance(v,str):
                    node[k]=v.replace("#/components/schemas/ProductContract/$defs/","#/$defs/")
                else:undo(v)
        elif isinstance(node,list):
            for v in node:undo(v)
    undo(embedded)
    if embedded!=history_api.SCHEMA:raise ValueError("DTO_FORK")
    Draft202012Validator.check_schema(embedded)
    return True

def forbid_python(source,prefixes):
    for node in ast.walk(ast.parse(source)):
        if isinstance(node,ast.Import): names=[x.name for x in node.names]
        elif isinstance(node,ast.ImportFrom) and not node.level:names=[node.module or ""]
        else:continue
        if any(name==p or name.startswith(p+".") for name in names for p in prefixes):
            raise ValueError("FORBIDDEN_DOMAIN_IMPORT")
    return True

class ArchitectureAndOpenAPI(unittest.TestCase):
    def test_internal_openapi_exact_canonical_contract_and_negative_mutations(self):
        doc=history_api.app.openapi()
        self.assertTrue(verify(doc))
        for key,value in (("openapi","3.0.0"),):
            altered=copy.deepcopy(doc);altered[key]=value
            with self.assertRaises(ValueError):verify(altered)
        altered=copy.deepcopy(doc)
        altered["paths"]["/v1/conversations"]["get"]["x-product-contract-version"]="product.v0"
        with self.assertRaises(ValueError):verify(altered)
        altered=copy.deepcopy(doc)
        altered["paths"]["/v1/conversations"]["get"]["responses"]["200"]["content"]["application/json"]["schema"]["$ref"]="#/missing"
        with self.assertRaises(ValueError):verify(altered)

    def test_app_only_composition_and_web_client_domain_boundary(self):
        api=(ROOT/"apps/api/private_app_only_asgi.py").read_text()
        forbidden=("src.phase3.rag_runtime","qdrant_client","openai","anthropic")
        self.assertTrue(forbid_python(api,forbidden))
        for p in forbidden:
            with self.assertRaises(ValueError):forbid_python("import "+p,forbidden)
        web=(ROOT/"apps/web/src/history/client.ts").read_text()
        self.assertIn("fetch('/api/history/'+path",web)
        imports=re.findall(r"""(?:from|import)\s*['"]([^'"]+)['"]""",web)
        self.assertFalse(any(x in {"pg","psycopg","openai","qdrant-client"} or x.startswith(("node:","@prisma/")) for x in imports))

if __name__=="__main__":unittest.main()
