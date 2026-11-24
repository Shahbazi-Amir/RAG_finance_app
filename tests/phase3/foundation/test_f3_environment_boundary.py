"""Source boundary regression: no credentials in example, no reverse imports.
Scope is the independent PostgreSQL storage domain, not an approved entire
architecture or production config. These are source-specific negative tests.
"""
import ast
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[3]

def safe_example(text):
    allowed={"PHASE3_APP_MODE":"APP_ONLY","API_RUNNER_EXECUTION_MODE":"APP_ONLY"}
    result={}
    for raw in text.splitlines():
        line=raw.strip()
        if not line or line.startswith("#"):continue
        name,sep,value=line.partition("=")
        if not sep or name in result or name not in allowed or value!=allowed[name]:
            raise ValueError("ENV_EXAMPLE_UNSAFE_OR_UNKNOWN")
        result[name]=value
    if result!=allowed:raise ValueError("ENV_EXAMPLE_INCOMPLETE")
    return result

def check_storage_imports(source):
    tree=ast.parse(source)
    for node in ast.walk(tree):
        names=[]
        if isinstance(node,ast.Import):names=[a.name for a in node.names]
        if isinstance(node,ast.ImportFrom) and not node.level:
            names=[node.module or ""]
        for name in names:
            if name=="apps" or name.startswith(("apps.","src.phase3.auth","src.phase3.rag_runtime","tests.")):
                raise ValueError("STORAGE_REVERSE_IMPORT")
    return True

class FoundationEnvironmentBoundary(unittest.TestCase):
    def test_checked_in_env_example_is_explicitly_nonsecret(self):
        sample=(ROOT/".env.example").read_text(encoding="utf-8")
        self.assertEqual(set(safe_example(sample)),{"PHASE3_APP_MODE","API_RUNNER_EXECUTION_MODE"})
        for suffix in ("\nDB_DSN=synthetic-forbidden","\nOPENAI_API_KEY=synthetic-forbidden",
                       "\nPHASE3_APP_MODE=ENGINE_ENABLED","\nUNKNOWN=value"):
            with self.assertRaises(ValueError):safe_example(sample+suffix)

    def test_real_storage_domain_has_no_reverse_application_import(self):
        files=sorted((ROOT/"src/phase3/storage/postgres").glob("*.py"))
        self.assertGreaterEqual(len(files),6)
        for f in files:self.assertTrue(check_storage_imports(f.read_text(encoding="utf-8")))
        for source in ("from apps.api import history_api","import src.phase3.rag_runtime.staging_no_dispatch",
                       "from src.phase3.auth import service_proof","import tests.phase3.api"):
            with self.assertRaises(ValueError):check_storage_imports(source)

if __name__=="__main__":
    unittest.main()
