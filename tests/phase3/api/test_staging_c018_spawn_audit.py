"""Kernel pidfd + proc-start identity witness, not a synthetic C018 Runner test.

No question, argv, result, DSN or credentials are included in receipts/logs.
These tests require Linux. A separate audited Arvan C018 run is still required.
"""
from __future__ import annotations

import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import threading
import unittest

from src.phase3.rag_runtime.runner_spawn_audit import (
    LinuxRunnerSpawnAudit, SpawnEvidenceUnknown, observe_linux_exec,
)
from src.phase3.rag_runtime.staging_preflight import AttemptBinding, PreflightDenied


@unittest.skipUnless(sys.platform.startswith('linux') and hasattr(os, 'pidfd_open'),
                     'requires a Linux kernel with pidfd')
class C018SpawnAuditTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.root.chmod(0o700)
        self.file = self.root/'spawn-audit.sqlite3'
        self.audit = LinuxRunnerSpawnAudit(self.file)
        self.binding = AttemptBinding('a'*32, 'b'*32, 'c'*32)
        self.digest = '9'*64

    def test_01_os_pidfd_proc_start_verified_once(self):
        self.audit.intent(self.binding, self.digest)
        proc = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(0.5)'],
                                stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                                stderr=subprocess.DEVNULL)
        try:
            witness = observe_linux_exec(proc.pid, Path(sys.executable))
            self.assertEqual(witness.pid, proc.pid)
            self.assertGreater(witness.proc_start_ticks, 0)
            self.audit.observed(self.binding, witness)
            self.assertEqual(proc.wait(timeout=3), 0)
            self.audit.finished(self.binding, proc.returncode)
            record = self.audit.receipt(self.binding)
            self.assertEqual(record['state'], 'EXITED_OK')
            self.assertEqual(record['witnessed_exec_count'], 1)
            self.assertEqual(record['pid'], proc.pid)
            self.assertEqual(record['runner_sha256'], self.digest)
            self.assertNotIn('argv', record)
            self.assertNotIn('question', record)
            print('C018_OS_PIDFD_PROC_START_WITNESS_ONE_PASS', flush=True)
        finally:
            if proc.poll() is None:
                proc.kill()
                proc.wait()

    def test_02_intent_never_counts_as_exec(self):
        self.audit.intent(self.binding, self.digest)
        self.assertEqual(self.audit.receipt(self.binding)['state'], 'INTENT')
        self.assertIsNone(self.audit.receipt(self.binding)['witnessed_exec_count'])
        self.audit.unknown(self.binding)
        self.assertEqual(self.audit.receipt(self.binding)['state'], 'UNKNOWN')
        self.assertIsNone(self.audit.receipt(self.binding)['witnessed_exec_count'])

    def test_03_duplicate_attempt_intent_denied_after_restart(self):
        self.audit.intent(self.binding, self.digest)
        new_process_store = LinuxRunnerSpawnAudit(self.file)
        with self.assertRaises(PreflightDenied):
            new_process_store.intent(self.binding, self.digest)
        self.assertEqual(self.audit.receipt(self.binding)['state'], 'INTENT')

    def test_04_wrong_product_or_trace_binding_denied(self):
        self.audit.intent(self.binding, self.digest)
        for binding in (AttemptBinding('a'*32, '0'*32, 'c'*32),
                        AttemptBinding('a'*32, 'b'*32, '0'*32)):
            with self.assertRaises(SpawnEvidenceUnknown):
                self.audit.receipt(binding)

    def test_05_no_fabricated_pid_or_false_observation(self):
        self.audit.intent(self.binding, self.digest)
        with self.assertRaises(SpawnEvidenceUnknown):
            observe_linux_exec(999999999, Path(sys.executable))
        with self.assertRaises(SpawnEvidenceUnknown):
            self.audit.finished(self.binding, 0)
        self.assertIsNone(self.audit.receipt(self.binding)['witnessed_exec_count'])

    def test_06_permissions_symlink_and_path_rejected(self):
        self.assertEqual(stat.S_IMODE(self.file.stat().st_mode), 0o600)
        bad_dir = self.root/'world'
        bad_dir.mkdir(mode=0o700)
        bad_dir.chmod(0o755)
        with self.assertRaises(PreflightDenied):
            LinuxRunnerSpawnAudit(bad_dir/'audit.sqlite3')
        link = self.root/'link.sqlite3'
        link.symlink_to(self.file)
        with self.assertRaises(PreflightDenied):
            LinuxRunnerSpawnAudit(link)

    def test_07_parallel_duplicate_intents_only_one(self):
        barrier = threading.Barrier(2)
        values = []
        def attempt():
            barrier.wait()
            try:
                self.audit.intent(self.binding, self.digest)
                values.append('inserted')
            except PreflightDenied:
                values.append('denied')
        threads = [threading.Thread(target=attempt) for _ in range(2)]
        for thread in threads:thread.start()
        for thread in threads:thread.join(timeout=5)
        self.assertCountEqual(values, ['inserted', 'denied'])

    def test_08_failed_pre_spawn_is_not_exec_and_not_retryable(self):
        self.audit.intent(self.binding, self.digest)
        self.audit.failed_before_spawn(self.binding)
        result = self.audit.receipt(self.binding)
        self.assertEqual(result['state'], 'FAILED_BEFORE_SPAWN')
        self.assertIsNone(result['witnessed_exec_count'])
        with self.assertRaises(PreflightDenied):
            self.audit.intent(self.binding, self.digest)

    def test_09_only_bounded_ids_not_raw_input_or_output(self):
        with self.assertRaises(PreflightDenied):
            self.audit.intent(AttemptBinding('invalid', 'b'*32, 'c'*32), self.digest)
        with self.assertRaises(PreflightDenied):
            self.audit.intent(self.binding, 'wrong-hash')
        self.assertEqual(self.audit.filepath, self.file)
        self.assertFalse(self.file.stat().st_mode & 0o077)


if __name__ == '__main__':
    unittest.main(verbosity=2)
