import hashlib
import json
import tempfile
import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "scripts"))
from f3_evidence_preflight import InvalidEvidence, REQ_RELEASE, verify_release, verify_receipt, main

SRC = "c488837b378d67ddde624dcd2a185e62fccbc30f"
TREE = "d923164848c9c36ea29f1d2c18733e204f68aa35"
SHA = "a" * 64


class EvidencePreflightTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def write(self, obj, name="receipt.json"):
        p = self.root / name
        p.write_text(json.dumps(obj), encoding="utf-8")
        return p

    def release(self):
        artifacts = []
        for kind in sorted(REQ_RELEASE):
            filename = f"proof/{kind}.json"
            p = self.root / filename
            p.parent.mkdir(parents=True, exist_ok=True)
            raw = kind.encode()
            p.write_bytes(raw)
            artifacts.append({"kind": kind, "path": filename, "sha256": hashlib.sha256(raw).hexdigest(), "size_bytes": len(raw)})
        return {"schema": "f3.phase2_release_intake.v1", "release_id": "release_20261123",
                "upstream_git_sha": SRC, "artifacts": artifacts}

    def receipt(self, stage):
        base = {"schema": "f3.target_receipt_intake.v1", "stage": stage,
                "source_sha": SRC, "source_tree": TREE, "environment": "MAC_ISOLATED_CANDIDATE",
                "arvan": "HOLD", "frozen_demo_untouched": True,
                "paid_gateway_calls_allowed": False,
                "ops_authorization_reference": "OPS-CANDIDATE-123",
                "operator_receipt_reference": "OPERATOR-SANITIZED-123"}
        if stage == "snapshot":
            base.update(dedicated_worktree="/worktree/isolated-f3-candidate", compose_project="f3_candidate_1123",
                        source_archive_sha256=SHA, isolated_volumes_and_ports=True)
        if stage == "build":
            base.update(engine_lock_and_wheelhouse_attested=True, images=[{"service": k, "image_id": "sha256:"+SHA,
                "sbom_sha256": SHA, "scan_receipt_sha256": SHA, "platform": "linux/amd64", "unresolved_critical": 0}
                for k in ("api", "web", "bootstrap")])
        if stage == "auth_l2":
            base.update(real_https=True, oidc_login=True, signed_bff_mtls_rs256=True,
                        pg_verified_two_owners=True, same_attempt_t1_t2=True,
                        send_http=202, replay_http=200, owner_b_http=404, revoked_http=401,
                        refresh_extra_post=0, refresh_get_only=True, no_dispatch=True)
        if stage == "c018":
            base.update(separate_c018_authorization_reference="OPS-SCOPED-RETRIEVAL-123",
                        index_copy_sha256=SHA, original_runner_sha256=SHA,
                        os_child_count=1, new_child_after_refresh=0, top_k=10, generation_calls=0,
                        refresh_extra_post=0, dispatch=False, answer=None,
                        state="CONTEXT_READY", same_attempt_trace=True)
        if stage == "restore":
            base.update(backup_sha256=SHA, encrypted_backup_sha256=SHA, qdrant_copy_sha256=SHA,
                        qdrant_restore_sha256=SHA, source_pg_cluster_id="001", restored_pg_cluster_id="002",
                        backup_encryption_key_reference="OPS-KMS-REF-123", separate_empty_restore_target=True,
                        restore_acl_rls_verified=True, deletion_tombstone_no_resurrection=True,
                        measured_rpo_seconds=3, measured_rto_seconds=10,
                        approved_rpo_seconds=5, approved_rto_seconds=20,
                        signed_rpo_rto_policy_reference="EMPLOYER-SIGNED-POLICY-REF")
        if stage == "load":
            base.update(approved_workload_policy_reference="EMPLOYER-WORKLOAD-REF", sample_requests=100,
                        p50_ms=90, p95_ms=250, p99_ms=380, approved_p95_ms=300,
                        error_rate_pct=0, approved_error_rate_pct=1)
        if stage == "trace":
            base.update(server_issued_trace_correlation=True, request_id_present=True, sanitized_log_coverage=True,
                        alert_trigger_and_resolution_tested=True, no_pii_or_secret_in_sampled_logs=True,
                        incident_runbook_exercised=True, redacted_trace_receipt_sha256=SHA)
        return base

    def run_receipt(self, d, stage):
        return verify_receipt(self.write(d), expected_sha=SRC, expected_tree=TREE, stage=stage)

    def assert_blocked(self, call):
        with self.assertRaises(InvalidEvidence):
            call()

    def test_release_valid_byte_integrity_only(self):
        d = self.release()
        x = verify_release(self.write(d), self.root)
        self.assertEqual(x["artifacts_verified"], 10)
        self.assertEqual(x["phase2_acceptance"], "NOT_ESTABLISHED")

    def test_release_tampered_byte(self):
        d = self.release()
        (self.root / "proof/data.json").write_text("tampered")
        self.assert_blocked(lambda: verify_release(self.write(d), self.root))

    def test_release_same_size_tamper(self):
        d = self.release()
        (self.root / "proof/data.json").write_bytes(b"data"[::-1])
        self.assert_blocked(lambda: verify_release(self.write(d), self.root))

    def test_release_missing_kind(self):
        d = self.release()
        d["artifacts"].pop()
        self.assert_blocked(lambda: verify_release(self.write(d), self.root))

    def test_release_duplicate_kind(self):
        d = self.release()
        d["artifacts"].append(dict(d["artifacts"][0]))
        self.assert_blocked(lambda: verify_release(self.write(d), self.root))

    def test_release_traversal(self):
        d = self.release()
        d["artifacts"][0]["path"] = "../x"
        self.assert_blocked(lambda: verify_release(self.write(d), self.root))

    def test_release_symlink_path(self):
        d = self.release()
        (self.root / "link").symlink_to(self.root / "proof", target_is_directory=True)
        d["artifacts"][0]["path"] = "link/" + d["artifacts"][0]["kind"] + ".json"
        self.assert_blocked(lambda: verify_release(self.write(d), self.root))

    def test_release_acceptance_flag_is_not_input(self):
        d = self.release()
        d["phase2_accepted_for_phase3"] = True
        self.assert_blocked(lambda: verify_release(self.write(d), self.root))

    def test_release_missing_manifest_cli_blocked(self):
        result = main(["--release", str(self.root / "not_present.json"), "--artifact-root", str(self.root)])
        self.assertEqual(result, 78)

    def test_each_stage_structure_is_precheck_not_acceptance(self):
        for stage in ("snapshot", "build", "auth_l2", "c018", "restore", "load", "trace"):
            with self.subTest(stage=stage):
                result = self.run_receipt(self.receipt(stage), stage)
                self.assertEqual(result["outcome"], "PRECHECK_ONLY_NOT_ACCEPTED")

    def test_wrong_integrated_sha_rejected(self):
        d = self.receipt("snapshot")
        d["source_sha"] = "b" * 40
        self.assert_blocked(lambda: self.run_receipt(d, "snapshot"))

    def test_frozen_demo_project_rejected(self):
        d = self.receipt("snapshot")
        d["compose_project"] = "rag_finance_f3_demo"
        self.assert_blocked(lambda: self.run_receipt(d, "snapshot"))

    def test_nonisolated_snapshot_rejected(self):
        d = self.receipt("snapshot")
        d["isolated_volumes_and_ports"] = False
        self.assert_blocked(lambda: self.run_receipt(d, "snapshot"))

    def test_arvan_or_gateway_rejected(self):
        for key, val in (("arvan", "LIVE"), ("paid_gateway_calls_allowed", True)):
            d = self.receipt("build")
            d[key] = val
            self.assert_blocked(lambda d=d: self.run_receipt(d, "build"))

    def test_build_non_amd64_rejected(self):
        d = self.receipt("build")
        d["images"][0]["platform"] = "linux/arm64"
        self.assert_blocked(lambda: self.run_receipt(d, "build"))

    def test_build_critical_cve_rejected(self):
        d = self.receipt("build")
        d["images"][0]["unresolved_critical"] = 1
        self.assert_blocked(lambda: self.run_receipt(d, "build"))

    def test_auth_wrong_owner_http_rejected(self):
        d = self.receipt("auth_l2")
        d["owner_b_http"] = 200
        self.assert_blocked(lambda: self.run_receipt(d, "auth_l2"))

    def test_auth_new_post_on_refresh_rejected(self):
        d = self.receipt("auth_l2")
        d["refresh_extra_post"] = 1
        self.assert_blocked(lambda: self.run_receipt(d, "auth_l2"))

    def test_c018_requires_separate_authorization(self):
        d = self.receipt("c018")
        del d["separate_c018_authorization_reference"]
        self.assert_blocked(lambda: self.run_receipt(d, "c018"))

    def test_c018_second_child_rejected(self):
        d = self.receipt("c018")
        d["new_child_after_refresh"] = 1
        self.assert_blocked(lambda: self.run_receipt(d, "c018"))

    def test_c018_dispatch_rejected(self):
        d = self.receipt("c018")
        d["dispatch"] = True
        self.assert_blocked(lambda: self.run_receipt(d, "c018"))

    def test_c018_generated_answer_rejected(self):
        d = self.receipt("c018")
        d["answer"] = "fabricated"
        self.assert_blocked(lambda: self.run_receipt(d, "c018"))

    def test_secret_keys_rejected(self):
        d = self.receipt("snapshot")
        d["private_key"] = "something"
        self.assert_blocked(lambda: self.run_receipt(d, "snapshot"))

    def test_restore_same_pg_cluster_rejected(self):
        d = self.receipt("restore")
        d["restored_pg_cluster_id"] = d["source_pg_cluster_id"]
        self.assert_blocked(lambda: self.run_receipt(d, "restore"))

    def test_restore_exceeds_rto_rejected(self):
        d = self.receipt("restore")
        d["measured_rto_seconds"] = 21
        self.assert_blocked(lambda: self.run_receipt(d, "restore"))

    def test_restore_no_tombstone_proof_rejected(self):
        d = self.receipt("restore")
        d["deletion_tombstone_no_resurrection"] = False
        self.assert_blocked(lambda: self.run_receipt(d, "restore"))

    def test_load_unapproved_threshold_rejected(self):
        d = self.receipt("load")
        del d["approved_workload_policy_reference"]
        self.assert_blocked(lambda: self.run_receipt(d, "load"))

    def test_load_high_p95_rejected(self):
        d = self.receipt("load")
        d["p95_ms"] = 350
        self.assert_blocked(lambda: self.run_receipt(d, "load"))

    def test_load_percentile_order_rejected(self):
        d = self.receipt("load")
        d["p50_ms"] = 251
        self.assert_blocked(lambda: self.run_receipt(d, "load"))

    def test_trace_pii_leak_rejected(self):
        d = self.receipt("trace")
        d["no_pii_or_secret_in_sampled_logs"] = False
        self.assert_blocked(lambda: self.run_receipt(d, "trace"))

    def test_trace_alert_unverified_rejected(self):
        d = self.receipt("trace")
        d["alert_trigger_and_resolution_tested"] = False
        self.assert_blocked(lambda: self.run_receipt(d, "trace"))

    def test_missing_required_receipt_cli_blocked(self):
        result = main(["--receipt", str(self.root / "not_present.json"), "--stage", "snapshot",
                       "--expected-sha", SRC, "--expected-tree", TREE])
        self.assertEqual(result, 78)


if __name__ == "__main__":
    unittest.main()
