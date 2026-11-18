"""API53 isolated config tests: no PostgreSQL, IdP, Gateway, TLS or staging."""
import os
import tempfile
import sys
from unittest.mock import patch
import unittest
from pathlib import Path

from src.phase3.rag_runtime.staging_service_bootstrap import (
    PrivateStagingEngineConfig, build_private_no_dispatch_handler,
)
from src.phase3.rag_runtime.staging_preflight import (
    AttemptBinding, PreflightDenied, RunnerLayout,
)
from src.phase3.auth.staging_service_profile import (
    RUNNER_C018_SHA256, PrivateStagingProfile, StagingConfigDenied,
    db_attributes_approved,
)


class PrivateStagingProfileTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="synthetic-staging-config-")
        self.key = Path(self.temp.name) / "bff-public.pem"
        self.key.write_bytes(b"synthetic-public-key-not-a-real-rsa-key")
        self.key.chmod(0o600)
        self.proof_count = 0

        def trusted_transport(scope):
            self.proof_count += 1
            return scope.get("extensions", {}).get("verified_tls_peer") == "synthetic"

        self.profile = PrivateStagingProfile(
            issuer="urn:synthetic:issuer", audience="urn:synthetic:api",
            kid="staging-key-1", public_key_path=self.key,
            history_dsn="host=127.0.0.1 port=5432 dbname=staging_history user=history_app",
            revoke_dsn="host=127.0.0.1 port=5432 dbname=staging_history user=auth_revoker",
            peer_verifier=trusted_transport,
        )

    def tearDown(self):
        self.temp.cleanup()

    def test_pinned_engine_digest_and_reject_wrong_override(self):
        self.assertEqual(self.profile.runner_sha256, RUNNER_C018_SHA256)
        kwargs = dict(vars(self.profile))
        for bad in ("", "0"*64, "93133bfdf25e40684fd9120b82ec19c217695fdb632ed4a1f7d2bb2a3abcb17d"):
            with self.subTest(bad=bad), self.assertRaises(StagingConfigDenied):
                PrivateStagingProfile(**{**kwargs, "runner_sha256": bad})

    def test_public_key_only_read_with_file_mode_and_owner_guard(self):
        self.assertEqual(self.profile.load_public_key(), self.key.read_bytes())
        self.key.chmod(0o666)
        with self.assertRaises(StagingConfigDenied):
            self.profile.load_public_key()
        self.key.unlink()
        self.key.symlink_to(Path(self.temp.name) / "missing")
        with self.assertRaises(StagingConfigDenied):
            self.profile.load_public_key()

    def test_peer_check_refuses_http_unverified_and_missing_callback(self):
        self.assertFalse(self.profile.allowed_peer({"type": "http", "scheme": "http"}))
        self.assertFalse(self.profile.allowed_peer({"type": "http", "scheme": "https"}))
        self.assertFalse(self.profile.allowed_peer({
            "type":"http", "scheme":"https",
            "headers":[(b"x-forwarded-client-cert",b"synthetic")],
        }))
        self.assertTrue(self.profile.allowed_peer({
            "type":"http", "scheme":"https",
            "extensions":{"verified_tls_peer":"synthetic"},
        }))
        self.assertGreaterEqual(self.proof_count, 2)
        with self.assertRaises(StagingConfigDenied):
            PrivateStagingProfile(**{**vars(self.profile), "peer_verifier": None})

    def test_staged_database_role_allowlist_and_tls_restrictions(self):
        for op,role in (("history","history_app"),("revoke","auth_revoker")):
            local = {"host":"127.0.0.1","dbname":"staging_history","user":role}
            self.assertTrue(db_attributes_approved(local,op))
            self.assertFalse(db_attributes_approved({**local, "dbname":"history_ci"},op))
            self.assertFalse(db_attributes_approved({**local, "user":"postgres"},op))
            remote = {**local, "host":"db.example.invalid"}
            self.assertFalse(db_attributes_approved(remote,op))
            self.assertFalse(db_attributes_approved({**remote,"sslmode":"require"},op))
            self.assertTrue(db_attributes_approved({
                **remote, "sslmode":"verify-full", "sslrootcert":"/pinned/ca.pem"},op))
        self.assertFalse(db_attributes_approved({}, "history"))
        self.assertFalse(db_attributes_approved({}, "reset_all"))

    def test_no_secret_values_in_profile_repr_or_errors(self):
        self.assertNotIn("staging_history", repr(self.profile))
        self.assertNotIn("user=history_app", repr(self.profile))
        self.assertEqual(str(StagingConfigDenied()), "PRIVATE_STAGING_CONFIG_DENIED")
        with self.assertRaises(StagingConfigDenied):
            self.profile.dsn("admin")
        self.assertEqual(self.profile.dsn("history"), self.profile.history_dsn)


    def synthetic_engine_config(self):
        root = Path(self.temp.name)
        repo = root / "repo"
        artifacts = root / "artifacts"
        cache = root / "hf"
        (artifacts / "bundle").mkdir(parents=True, exist_ok=True)
        repo.mkdir(exist_ok=True)
        cache.mkdir(exist_ok=True)
        script = artifacts / "bundle" / "rag_engine.py"
        script.write_text("raise SystemExit('NO_RUNNER_EXECUTION')\n", encoding="utf-8")
        cfg = PrivateStagingEngineConfig(
            layout=RunnerLayout(Path(sys.executable), repo, artifacts,
                                "bundle/rag_engine.py", cache),
            engine_version="synthetic-C018-v1",
            ledger_file=root / "status.sqlite",
        )
        env = {"HF_HUB_CACHE": str(cache),
               "HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1"}
        return cfg, env

    def test_bootstrap_requires_exact_real_file_hash_and_offline_state(self):
        config, env = self.synthetic_engine_config()
        with self.assertRaises(PreflightDenied):
            build_private_no_dispatch_handler(
                profile=self.profile, config=config, environ=env)
        with patch(
            "src.phase3.rag_runtime.staging_service_bootstrap._matches_exact_file_sha",
            return_value=True,
        ):
            with self.assertRaises(PreflightDenied):
                build_private_no_dispatch_handler(
                    profile=self.profile, config=config,
                    environ={**env, "HF_HUB_OFFLINE": "0"})

    def test_bootstrap_synthetic_ledger_same_uid_owner_and_no_duplicate(self):
        # Explicitly synthetic hash stub: NOT evidence of real pinned script.
        config, env = self.synthetic_engine_config()
        with patch(
            "src.phase3.rag_runtime.staging_service_bootstrap._matches_exact_file_sha",
            return_value=True,
        ):
            handler = build_private_no_dispatch_handler(
                profile=self.profile, config=config, environ=env)
        attempt = AttemptBinding("a"*32,"b"*32,"c"*32)
        self.assertTrue(handler.reserve("owner_A",attempt))
        self.assertFalse(handler.reserve("owner_A",attempt))
        self.assertEqual(handler.read("owner_A",attempt.engine_request_id)["state"],"QUEUED")
        self.assertEqual(handler.read("owner_B",attempt.engine_request_id)["state"],"NOT_RECORDED")
        self.assertEqual(config.engine_version,"synthetic-C018-v1")

    def test_staged_engine_config_version_and_ledger_requirements(self):
        config, _ = self.synthetic_engine_config()
        with self.assertRaises(PreflightDenied):
            PrivateStagingEngineConfig(config.layout, "", config.ledger_file)
        with self.assertRaises(PreflightDenied):
            PrivateStagingEngineConfig(config.layout, "v1", Path("relative.sqlite"))
        with self.assertRaises(PreflightDenied):
            PrivateStagingEngineConfig(config.layout, "v1", config.ledger_file, 301)


if __name__ == "__main__":
    unittest.main(verbosity=2)
