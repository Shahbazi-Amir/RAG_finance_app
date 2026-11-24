"""Read-only regression checks: exact CI source recovery, no leaked cursor key.

The executable 200→503→200 proof remains the isolated Docker/PG Actions job.
This test prevents the second API process from silently diverging at startup.
"""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "infra/postgres/dev_f3_isolated/scripts/28_signed_history_https_pg_lab.sh"
WORKFLOW = ROOT / ".github/workflows/f3-84-one-sha-signed-oci-browser-restored.yml"

class AppOnlyRestoredApiParity(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.script = SCRIPT.read_text(encoding="utf-8")
        cls.workflow = WORKFLOW.read_text(encoding="utf-8")

    def test_bff_and_restored_api_consume_same_private_ephemeral_cursor(self):
        self.assertEqual(self.script.count(
            'export API_CURSOR_KEY="$(cat /run/f3_http_probe/private/cursor.key)"'), 2)
        self.assertEqual(self.script.count("export API_CURSOR_TTL_SECONDS=300"), 2)
        self.assertNotIn("-e API_CURSOR_KEY=", self.script)

    def test_restore_api_readiness_is_strict_200_503_200(self):
        for marker in ("STOP_API_READY_BEFORE_OUTAGE",
                       "APP_ONLY_RUNNING_MTLS_API_READY_BEFORE_PG_OUTAGE_200",
                       "APP_ONLY_RUNNING_MTLS_API_READY_AFTER_PG_LOSS_503",
                       "APP_ONLY_RUNNING_MTLS_API_READY_RECOVERED_PG_200",
                       "compose --profile restore stop restore-db",
                       "compose --profile restore up -d --no-deps restore-db"):
            with self.subTest(marker=marker):
                self.assertIn(marker, self.script)

    def test_no_private_config_or_server_log_uploaded(self):
        self.assertIn("PG_RESTORE_PROBE_DIAG_STATE", self.script)
        self.assertIn("APP_ONLY_STARTUP_DENIED", self.script)
        self.assertNotIn("docker logs \"$probe_name\"", self.script)
        self.assertIn('"GITHUB_WORKSPACE"', self.script)

    def test_browser_to_sql_before_after_restore_is_enforced(self):
        self.assertNotIn("git fetch --no-tags", self.workflow)
        for marker in (
            "F3_84_CANDIDATE_NO_REMOTE_OVERLAY_EXACT_EIGHT_SOURCE_BLOBS_PASS",
            "API_F3_BROWSER_REAL_OIDC_COOKIE_AB_PASS",
            "API_F3_BROWSER_PG_HTTP_DOM_PAGE2_AB_PASS",
            "API_F3_RESTORED_PG_REAL_TLS_VERIFY_FULL_PASS",
            "API_F3_BROWSER_RESTORED_VOLUME_PG_HTTP_DOM_AB_PASS",
            "API_F3_BROWSER_COMMITTED_REVOKE_AB_PASS",
            "F3_84_ACTUAL_BROWSER_SQL_BEFORE_AFTER_RESTORE_SAME_SHA_PASS",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, self.workflow)

if __name__=="__main__":
    unittest.main()
