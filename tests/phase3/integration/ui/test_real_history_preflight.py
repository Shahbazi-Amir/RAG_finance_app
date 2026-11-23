#!/usr/bin/env python3
"""Pure validation tests only; NEVER evidence of OIDC, PG or browser acceptance."""
import importlib.util
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[4]
MODULE = ROOT / "tests/phase3/integration/ui/real_signed_two_owner_history_journey.py"
spec = importlib.util.spec_from_file_location("ui_f3_strict_real_history", MODULE)
target = importlib.util.module_from_spec(spec)
spec.loader.exec_module(target)


class TestStrictBrowserPreflight(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="f3-unit-synthetic-receipt-")
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "unit-fixture.json"
        self.sha = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
        self.seed = {
            "kind": "ui_f3_actual_pg_two_owner_seed",
            "contract_version": "ui.pg_two_owner_seed.v1",
            "integrated_sha": self.sha,
            "pg_cluster_id_sha256": "a" * 64,
            "users": {
                "A": {"owner_id": "unit_a",
                      "conversation_ids": ["a1", "a2", "a3"],
                      "message_ids": {"a1": [f"msg{i:02}" for i in range(31)]}},
                "B": {"owner_id": "unit_b",
                      "conversation_ids": ["b1"],
                      "message_ids": {"b1": ["onlyb"]}}
            }
        }
        self.env = {
            "CI": "true", "GITHUB_ACTIONS": "true",
            "GITHUB_SHA": self.sha,
            "PHASE3_APP_MODE": "APP_ONLY",
            "UI_REAL_BROWSER_APPROVED": "true",
            "UI_REAL_IDP_ORIGIN": "http://127.0.0.1:8081",
            "UI_REAL_PG_SEED_RECEIPT": str(self.path),
            "UI_REAL_A_USERNAME": "temporary-unit-a",
            "UI_REAL_A_PASSWORD": "synthetic-not-a-real-credential",
            "UI_REAL_B_USERNAME": "temporary-unit-b",
            "UI_REAL_B_PASSWORD": "synthetic-not-a-real-credential",
        }

    def check(self, seed=None, override=None):
        self.path.write_text(json.dumps(seed if seed is not None else self.seed),
                             encoding="utf-8")
        with patch.dict(os.environ, {**self.env, **(override or {})}):
            return target.configured()

    def test_rejects_execution_outside_authorized_ci(self):
        with self.assertRaisesRegex(RuntimeError, "E2E_MUST_RUN_ON_DISPOSABLE"):
            self.check(override={"CI": "false"})

    def test_rejects_nonmatching_action_sha(self):
        with self.assertRaisesRegex(RuntimeError, "CHECKOUT_HEAD_NOT_GITHUB_ACTION_SHA"):
            self.check(override={"GITHUB_SHA": "0" * 40})

    def test_rejects_same_login_subject_even_if_seed_has_two_owners(self):
        with self.assertRaisesRegex(RuntimeError, "OIDC_TWO_DISTINCT_LOGIN"):
            self.check(override={"UI_REAL_B_USERNAME": self.env["UI_REAL_A_USERNAME"]})

    def test_rejects_cross_thread_message_reuse(self):
        altered = json.loads(json.dumps(self.seed))
        altered["users"]["B"]["message_ids"]["b1"] = ["msg00"]
        with self.assertRaisesRegex(RuntimeError, "PG_SEED_CROSS_THREAD"):
            self.check(seed=altered)

    def test_rejects_unknown_or_unapproved_idp(self):
        with self.assertRaisesRegex(RuntimeError, "DISPOSABLE_IDP_ORIGIN"):
            self.check(override={"UI_REAL_IDP_ORIGIN": "https://idp.example.org"})

    def test_rejects_untrusted_tls_or_missing_ingress(self):
        with patch.object(target.socket, "create_connection", side_effect=OSError("unit-only")):
            with self.assertRaisesRegex(RuntimeError, "HTTPS_INGRESS_CA_OR_IP_SAN_NOT_TRUSTED"):
                target.verify_ingress_ca_and_san()

    def test_valid_synthetic_shape_is_only_a_unit_preflight(self):
        receipt, idp, credentials, source_sha = self.check()
        self.assertEqual(source_sha, self.sha)
        self.assertEqual(idp, "http://127.0.0.1:8081")
        self.assertEqual(len(credentials), 2)
        self.assertEqual(len(receipt["users"]["A"]["message_ids"]["a1"]), 31)


if __name__ == "__main__":
    unittest.main()
