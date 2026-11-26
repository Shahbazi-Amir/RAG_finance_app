"""Offline unit tests of detector semantics; never product/CI acceptance evidence."""
import importlib.util
import io
import json
import tempfile
import unittest
from pathlib import Path

path = Path(__file__).resolve().parents[4] / "scripts/phase3/f3_lab_log_guard.py"
spec = importlib.util.spec_from_file_location("f3_lab_log_guard", path)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class GuardTests(unittest.TestCase):
    def setUp(self):
        self.marker = b"synthetic-" + b"x" * 24
        self.candidates = [("lab_secret", self.marker)]

    def test_clean(self):
        self.assertEqual(mod.scan(io.BytesIO(b"service ready"), self.candidates)["result"], "NO_LITERAL_MATCHES")

    def test_literal_leak(self):
        result = mod.scan(io.BytesIO(b"prefix" + self.marker), self.candidates)
        self.assertEqual(result["result"], "LEAK_FOUND")
        self.assertEqual(result["matches"], {"lab_secret": 1})
        self.assertNotIn(self.marker.decode(), json.dumps(result))

    def test_empty_is_not_pass(self):
        self.assertEqual(mod.scan(io.BytesIO(b"  "), self.candidates)["result"], "INCOMPLETE_EMPTY_LOG")

    def test_truncated_is_not_pass(self):
        self.assertEqual(mod.scan(io.BytesIO(b"a" * 20), self.candidates, max_bytes=10)["result"], "INCOMPLETE_LOG_LIMIT")

    def test_exact_limit_is_checked(self):
        self.assertEqual(mod.scan(io.BytesIO(b"a" * 20), self.candidates, max_bytes=20)["bytes_checked"], 20)

    def test_key_header(self):
        raw = b"-----BEGIN RSA " + b"PRIVATE KEY-----"
        self.assertEqual(mod.scan(io.BytesIO(raw), self.candidates)["matches"], {"private_key_header": 1})

    def test_empty_candidate_rejected(self):
        with self.assertRaises(ValueError):
            mod.scan(io.BytesIO(b"ready"), [("lab_secret", b"")])

    def test_no_candidates_rejected(self):
        with self.assertRaises(ValueError):
            mod.scan(io.BytesIO(b"ready"), [])

    def test_multiple_classes(self):
        other = b"synthetic-user-" + b"a" * 20
        result = mod.scan(io.BytesIO(self.marker + other), self.candidates + [("synthetic_identity", other)])
        self.assertEqual(result["matches"], {"lab_secret": 1, "synthetic_identity": 1})

    def test_actual_file_layout_loaded_without_echo(self):
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp)
            root = work / "browser-journey"
            for p in ("web", "bootstrap", "browser"):
                (root / p).mkdir(parents=True)
            for p in ("web/proof", "web/csrf", "web/alias", "bootstrap/seal"):
                (root / p).write_bytes(self.marker)
            for role in mod.ROLE_FILES:
                (work / (role + ".password")).write_bytes(self.marker)
            users = {k: {f: self.marker.decode() + k + f for f in ("username", "password", "subject")} for k in ("a", "b")}
            (root / "browser/users.json").write_text(json.dumps(users))
            self.assertEqual(len(mod.secret_values(root, work)), 21)
            (work / "history_app.password").unlink()
            with self.assertRaises(FileNotFoundError):
                mod.secret_values(root, work)


if __name__ == "__main__":
    unittest.main()
