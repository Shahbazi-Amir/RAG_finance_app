"""Narrow source dependency and /v1 surface guards for the app-only slice.
Not an approved architecture decision or full import graph audit.
"""
import ast
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[4]
MODULES=("src/phase3/storage/postgres/repository.py",
         "src/phase3/auth/bootstrap_oidc.py",
         "src/phase3/storage/postgres/auth_session.py",
         "src/phase3/storage/postgres/service_replay.py")
FORBIDDEN=("apps","src.phase3.rag_runtime")
def reverse_dependencies(source):
    tree=ast.parse(source)
    names=[]
    for n in ast.walk(tree):
        if isinstance(n,ast.Import): names.extend(a.name for a in n.names)
        elif isinstance(n,ast.ImportFrom) and n.level==0 and n.module:
            names.append(n.module)
    return sorted({x for x in names if any(x==p or x.startswith(p+".") for p in FORBIDDEN)})

def history_routes(source):
    wanted={"session_conversations":"/v1/conversations",
            "session_messages":"/v1/conversations/{conversation_id}/messages",
            "session_message_status":"/v1/message-requests/status"}
    found={}
    for n in ast.parse(source).body:
        if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) and n.name in wanted:
            paths=[d.args[0].value for d in n.decorator_list
                   if isinstance(d,ast.Call) and isinstance(d.func,ast.Attribute)
                   and d.func.attr=="get" and isinstance(d.func.value,ast.Name)
                   and d.func.value.id=="app" and len(d.args)==1
                   and isinstance(d.args[0],ast.Constant) and isinstance(d.args[0].value,str)]
            if paths!=[wanted[n.name]] or n.name in found:
                raise ValueError("signed History route changed")
            found[n.name]=paths[0]
    if found!=wanted:raise ValueError("signed History route missing")
    return found

class Tests(unittest.TestCase):
    def test_actual_lower_layer_no_reverse_import(self):
        for p in MODULES:
            with self.subTest(path=p):
                self.assertEqual(reverse_dependencies((ROOT/p).read_text()),[])
    def test_reverse_edges_negative(self):
        for s in ("import apps.api.history_api", "from apps import api",
                  "if False:\n import src.phase3.rag_runtime",
                  "def f():\n from src.phase3.rag_runtime.x import y"):
            with self.subTest(source=s):self.assertTrue(reverse_dependencies(s))
    def test_allowed_edges(self):
        self.assertEqual(reverse_dependencies("import hashlib\nfrom src.phase3.storage.postgres import auth_session"),[])
    def test_actual_signed_v1_history(self):
        self.assertEqual(len(history_routes((ROOT/"apps/api/product_session_api.py").read_text())),3)
    def test_changed_route_denied(self):
        s=(ROOT/"apps/api/product_session_api.py").read_text()
        with self.assertRaises(ValueError):history_routes(s.replace('@app.get("/v1/conversations")','@app.get("/v2/conversations")'))
    def test_missing_route_denied(self):
        with self.assertRaises(ValueError):history_routes("def session_conversations():pass")
if __name__=="__main__":unittest.main()
