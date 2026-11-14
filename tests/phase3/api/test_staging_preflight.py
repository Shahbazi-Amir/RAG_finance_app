"""Offline unit tests; cannot dispatch, SSH, call Keycloak, or read secrets."""
from __future__ import annotations

import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from src.phase3.rag_runtime.staging_preflight import (
    AttemptBinding, CONTRACT_EXPECTED, GATEWAY_SETTING_NAMES,
    OFFLINE_REQUIRED, PreflightDenied, RunnerLayout,
    bind_persisted_attempt, inspect_no_dispatch, main,
)


class PinnedStagingPreflight(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="synthetic-runner-preflight-")
        root = Path(self.tmp.name)
        self.root = root
        self.python = root / "venv" / "bin" / "python"
        self.repo = root / "RAG_finance"
        self.artifacts = root / "outputs"
        self.cache = root / "hf" / "hub"
        self.relative = "MVP_engine_bundles/synthetic-bundle/rag_engine.py"
        self.engine = self.artifacts / self.relative
        for target in (self.python.parent, self.repo, self.engine.parent, self.cache):
            target.mkdir(parents=True, exist_ok=True)
        self.python.write_text("#!/usr/bin/env python3\n", encoding="ascii")
        self.python.chmod(0o700)
        self.engine.write_text("raise RuntimeError('MUST_NOT_IMPORT_OR_DISPATCH')\n",
                               encoding="ascii")
        self.layout = RunnerLayout(self.python, self.repo, self.artifacts,
                                   self.relative, self.cache)
        self.env = {
            **OFFLINE_REQUIRED,
            "ARVAN_GATEWAY_URL": "synthetic-DO-NOT-PRINT-ENDPOINT",
            "ARVAN_GATEWAY_API_KEY": "synthetic-DO-NOT-PRINT-SECRET",
        }

    def tearDown(self):
        self.tmp.cleanup()

    def test_preflight_only_static_checks_never_imports_runner_or_secrets(self):
        with patch("subprocess.run", side_effect=AssertionError("NO_DISPATCH")), \
             patch("subprocess.Popen", side_effect=AssertionError("NO_DISPATCH")):
            report = inspect_no_dispatch(self.layout, self.env)
        self.assertTrue(all(report["filesystem"].values()))
        self.assertTrue(all(report["offline_environment"].values()))
        self.assertEqual(report["engine_result_contract_requested"], CONTRACT_EXPECTED)
        self.assertTrue(all(report["gateway_settings_present_only"].values()))
        self.assertFalse(report["dispatch_performed"])
        self.assertFalse(report["gateway_call_performed"])
        self.assertFalse(report["ops_secret_store_verified"])
        self.assertFalse(report["runner_cli_and_result_schema_verified"])
        self.assertFalse(report["ready_for_dispatch"])
        serialized = json.dumps(report, sort_keys=True)
        self.assertNotIn("synthetic-DO-NOT-PRINT-ENDPOINT", serialized)
        self.assertNotIn("synthetic-DO-NOT-PRINT-SECRET", serialized)
        self.assertNotIn(str(self.root), serialized)
        self.assertEqual(set(report["gateway_settings_present_only"]),
                         set(GATEWAY_SETTING_NAMES))

    def test_missing_and_wrong_offline_environment_is_not_ready(self):
        wrong = dict(self.env, HF_HUB_OFFLINE="0", TRANSFORMERS_OFFLINE="0")
        report = inspect_no_dispatch(self.layout, wrong)
        self.assertFalse(report["offline_environment"]["HF_HUB_OFFLINE"])
        self.assertFalse(report["offline_environment"]["TRANSFORMERS_OFFLINE"])
        self.engine.unlink()
        report = inspect_no_dispatch(self.layout, self.env)
        self.assertFalse(report["filesystem"]["runner_present_confined"])
        self.assertFalse(report["ready_for_dispatch"])

    def test_symlink_escape_and_parent_traversal_fail_closed(self):
        self.engine.unlink()
        outside = self.root / "synthetic-outside.py"
        outside.write_text("pass\n")
        self.engine.symlink_to(outside)
        self.assertFalse(
            inspect_no_dispatch(self.layout, self.env)["filesystem"]["runner_present_confined"])
        malicious = RunnerLayout(
            self.python, self.repo, self.artifacts,
            "../synthetic-outside.py", self.cache)
        with self.assertRaises(PreflightDenied):
            malicious.runner()

    def test_binding_only_from_committed_t2_identity_not_browser(self):
        row = {
            "id": "a" * 32, "attempt_request_id": "b" * 32,
            "attempt_trace_id": "c" * 32,
            "state": "attempt_pending",
            "owner_id": "MUST_NEVER_LEAK_OWNER",
        }
        binding = bind_persisted_attempt(row)
        self.assertIsInstance(binding, AttemptBinding)
        self.assertEqual(binding.engine_request_id, row["id"])
        self.assertEqual(binding.product_request_id, row["attempt_request_id"])
        self.assertEqual(binding.trace_id, row["attempt_trace_id"])
        self.assertEqual(binding, bind_persisted_attempt(dict(row)))
        self.assertNotIn("MUST_NEVER_LEAK_OWNER", repr(binding))
        for bad in (
            {**row, "state": "attempt_unknown"},
            {**row, "id": "browser-supplied"},
            {**row, "attempt_trace_id": "xxx"},
            {},
        ):
            with self.assertRaises(PreflightDenied):
                bind_persisted_attempt(bad)

    def test_cli_requires_no_dispatch_and_reports_only_safe_bools(self):
        with patch(
            "src.phase3.rag_runtime.staging_preflight.RunnerLayout.pinned",
            return_value=self.layout,
        ), patch.dict("os.environ", self.env, clear=True):
            output = io.StringIO()
            with redirect_stdout(output):
                rc = main(["--no-dispatch"])
            self.assertEqual(rc, 0)
            report = json.loads(output.getvalue())
            self.assertFalse(report["dispatch_performed"])
            self.assertFalse(report["ready_for_dispatch"])
            with redirect_stdout(io.StringIO()), self.assertRaises(SystemExit):
                main(["--dispatch"])

    def test_user_question_and_raw_engine_result_are_never_logged(self):
        payload = {
            "question": "SYNTHETIC_PRIVATE_QUESTION_NEVER_LOG",
            "model_output": "SYNTHETIC_RAW_ANSWER_NEVER_LOG",
        }
        with redirect_stdout(io.StringIO()) as captured:
            report = inspect_no_dispatch(self.layout, self.env)
            print(json.dumps(report))
        self.assertNotIn(payload["question"], captured.getvalue())
        self.assertNotIn(payload["model_output"], captured.getvalue())


if __name__ == "__main__":
    unittest.main(verbosity=2)
