"""Persistent operational-only no-dispatch outcome; never a Product Answer.

SQLite ledger is an isolated, single-host private-service artifact, NOT
history_l1, and NOT a DB-owned paid dispatch CAS/outbox. The staging service
must explicitly install this handler after Ops config review. A service crash
never triggers auto-resend; stale queued/running states show UNKNOWN.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import sqlite3
import stat
from contextlib import contextmanager
import time
from pathlib import Path

from src.phase3.rag_runtime.staging_no_dispatch import (
    ApprovedNoDispatchCLI, invoke_pinned_no_dispatch,
)
from src.phase3.rag_runtime.result_contract_gate import validate_no_dispatch_context_ready
from src.phase3.rag_runtime.retrieved_sources import (
    EvidenceDenied, CONTRACT as SOURCES_CONTRACT,
    from_c018_stdout, unavailable_receipt, validate_public_receipt,
)
from src.phase3.rag_runtime.runner_spawn_audit import (
    LinuxRunnerSpawnAudit, SpawnEvidenceUnknown,
)
from src.phase3.rag_runtime.staging_preflight import (
    AttemptBinding, PreflightDenied, RunnerLayout,
)

STATES = frozenset({"QUEUED", "RUNNING", "CONTEXT_READY", "FAILED", "UNKNOWN"})


class NoDispatchLedger:
    """No question, result JSON, raw citations, keys or answers are persisted."""

    def __init__(self, filepath: Path):
        if not isinstance(filepath, Path) or not filepath.is_absolute():
            raise PreflightDenied()
        folder = filepath.parent
        try:
            d = folder.stat()
            if (not stat.S_ISDIR(d.st_mode) or d.st_uid != os.geteuid()
                    or stat.S_IMODE(d.st_mode) & 0o077
                    or filepath.is_symlink()):
                raise PreflightDenied()
            if not filepath.exists():
                fd = os.open(str(filepath), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
                os.close(fd)
            info = filepath.stat()
            if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.geteuid()
                    or stat.S_IMODE(info.st_mode) != 0o600):
                raise PreflightDenied()
        except OSError:
            raise PreflightDenied() from None
        self.filepath = filepath
        with self._connect() as conn:
            conn.execute("""CREATE TABLE IF NOT EXISTS outcomes (
                attempt_id TEXT PRIMARY KEY,
                owner_id TEXT NOT NULL,
                product_request_id TEXT NOT NULL,
                trace_id TEXT NOT NULL,
                state TEXT NOT NULL CHECK (
                  state IN ('QUEUED','RUNNING','CONTEXT_READY','FAILED','UNKNOWN')
                ),
                top10_count INTEGER,
                generation_calls INTEGER,
                question_hash_match INTEGER,
                updated_at INTEGER NOT NULL
            )""")
            conn.execute("""CREATE TABLE IF NOT EXISTS retrieval_receipts (
                attempt_id TEXT PRIMARY KEY,
                owner_id TEXT NOT NULL,
                trace_id TEXT NOT NULL,
                receipt_json TEXT NOT NULL,
                receipt_sha256 TEXT NOT NULL
            )""")

    @contextmanager
    def _connect(self):
        conn = sqlite3.connect(str(self.filepath), timeout=10)
        try:
            conn.execute("PRAGMA synchronous=FULL")
            conn.execute("PRAGMA busy_timeout=10000")
            yield conn
            conn.commit()
        except BaseException:
            conn.rollback()
            raise
        finally:
            conn.close()

    @staticmethod
    def _valid_owner(owner_id):
        return isinstance(owner_id, str) and 1 <= len(owner_id) <= 256

    def reserve(self, owner_id: str, binding: AttemptBinding) -> bool:
        if not self._valid_owner(owner_id) or not isinstance(binding, AttemptBinding):
            raise PreflightDenied()
        with self._connect() as conn:
            cur = conn.execute("""INSERT OR IGNORE INTO outcomes
                (attempt_id,owner_id,product_request_id,trace_id,state,updated_at)
                VALUES (?,?,?,?,'QUEUED',?)""",
                (binding.engine_request_id, owner_id, binding.product_request_id,
                 binding.trace_id, int(time.time())))
            if cur.rowcount != 1:
                # Any existing row is permanently non-requeueable even after
                # FAILED, UNKNOWN, service restarts or parallel POSTs.
                existing = conn.execute(
                    "SELECT owner_id,trace_id FROM outcomes WHERE attempt_id=?",
                    (binding.engine_request_id,)).fetchone()
                if existing is None or existing != (owner_id, binding.trace_id):
                    raise PreflightDenied()
                return False
            return True

    def _transition(self, owner_id, binding, from_state, to_state, *,
                    top10=None, generation=None, matched=None):
        if to_state not in STATES:
            raise PreflightDenied()
        with self._connect() as conn:
            cur = conn.execute("""UPDATE outcomes
                SET state=?,top10_count=?,generation_calls=?,
                    question_hash_match=?,updated_at=?
                WHERE attempt_id=? AND owner_id=? AND trace_id=? AND state=?""",
                (to_state, top10, generation, matched, int(time.time()),
                 binding.engine_request_id, owner_id, binding.trace_id, from_state))
            return cur.rowcount == 1

    def start(self, owner, binding):
        return self._transition(owner, binding, "QUEUED", "RUNNING")

    def succeed(self, owner, binding, summary, receipt=None):
        if receipt is None:
            # Retain exact behavior for historical operational-only tests.
            return self._transition(
                owner, binding, "RUNNING", "CONTEXT_READY",
                top10=summary["top10_count"], generation=0, matched=1)
        if (not isinstance(receipt, dict)
                or receipt.get("contract_version") != SOURCES_CONTRACT
                or receipt.get("attempt_id") != binding.engine_request_id
                or receipt.get("attempt_trace_id") != binding.trace_id):
            raise PreflightDenied()
        try:
            validate_public_receipt(receipt)
            encoded = json.dumps(receipt, sort_keys=True, separators=(",", ":"),
                                 ensure_ascii=False, allow_nan=False)
        except (TypeError, ValueError, EvidenceDenied):
            raise PreflightDenied() from None
        if len(encoded.encode("utf-8")) > 65536:
            raise PreflightDenied()
        digest = hashlib.sha256(encoded.encode("utf-8")).hexdigest()
        # One durable SQLite transaction: CONTEXT_READY and immutable sources.
        # On failure both writes roll back; never auto-execute the Runner again.
        with self._connect() as conn:
            cur = conn.execute("""UPDATE outcomes
                SET state='CONTEXT_READY', top10_count=?, generation_calls=0,
                    question_hash_match=1, updated_at=?
                WHERE attempt_id=? AND owner_id=? AND trace_id=? AND state='RUNNING'""",
                (summary["top10_count"], int(time.time()),
                 binding.engine_request_id, owner, binding.trace_id))
            if cur.rowcount != 1:
                return False
            conn.execute("""INSERT INTO retrieval_receipts
                (attempt_id, owner_id, trace_id, receipt_json, receipt_sha256)
                VALUES (?,?,?,?,?)""",
                (binding.engine_request_id, owner, binding.trace_id, encoded, digest))
        return True

    def fail(self, owner, binding, *, unknown=False):
        return self._transition(
            owner, binding, "RUNNING", "UNKNOWN" if unknown else "FAILED")

    def read(self, owner_id: str, attempt_id: str, *, max_age_s: int = 300) -> dict:
        if (not self._valid_owner(owner_id) or not isinstance(attempt_id, str)
                or len(attempt_id) != 32):
            raise PreflightDenied()
        with self._connect() as conn:
            row = conn.execute("""SELECT state,top10_count,generation_calls,
                    question_hash_match,updated_at FROM outcomes
                    WHERE attempt_id=? AND owner_id=?""",
                    (attempt_id, owner_id)).fetchone()
        if row is None:
            return {"state": "NOT_RECORDED", "top10_count": None,
                    "generation_calls": None, "question_hash_match": None}
        state, top10, calls, matched, updated = row
        if state in ("QUEUED", "RUNNING") and time.time()-updated > max_age_s:
            state = "UNKNOWN"  # observation only; never requeue
        return {"state": state, "top10_count": top10,
                "generation_calls": calls,
                "question_hash_match": bool(matched) if matched is not None else None}

    def read_sources(self, owner_id: str, attempt_id: str, trace_id: str) -> dict | None:
        if (not self._valid_owner(owner_id)
                or not isinstance(attempt_id, str) or len(attempt_id) != 32
                or not isinstance(trace_id, str) or len(trace_id) != 32):
            raise PreflightDenied()
        with self._connect() as conn:
            row = conn.execute("""SELECT r.receipt_json, r.receipt_sha256
                FROM retrieval_receipts r JOIN outcomes o
                ON o.attempt_id=r.attempt_id
                WHERE r.attempt_id=? AND r.owner_id=? AND r.trace_id=?
                AND o.owner_id=? AND o.trace_id=? AND o.state='CONTEXT_READY'""",
                (attempt_id, owner_id, trace_id, owner_id, trace_id)).fetchone()
        if row is None:
            return None
        raw, digest = row
        if (not isinstance(raw, str) or not isinstance(digest, str)
                or not hmac.compare_digest(
                    hashlib.sha256(raw.encode("utf-8")).hexdigest(), digest)):
            raise PreflightDenied()
        try:
            receipt = json.loads(raw)
        except (ValueError, TypeError):
            raise PreflightDenied() from None
        if (not isinstance(receipt, dict)
                or receipt.get("contract_version") != SOURCES_CONTRACT
                or receipt.get("attempt_id") != attempt_id
                or receipt.get("attempt_trace_id") != trace_id):
            raise PreflightDenied()
        try:
            return validate_public_receipt(receipt)
        except EvidenceDenied:
            raise PreflightDenied() from None


class NoDispatchHandler:
    def __init__(self, layout: RunnerLayout, *, runner_sha256: str, ledger: NoDispatchLedger,
                 max_seconds: int = 180,
                 spawn_audit: LinuxRunnerSpawnAudit | None = None):
        if (not isinstance(layout, RunnerLayout)
                or not isinstance(ledger, NoDispatchLedger)
                or (spawn_audit is not None
                    and not isinstance(spawn_audit, LinuxRunnerSpawnAudit))):
            raise PreflightDenied()
        self.layout = layout
        self.profile = ApprovedNoDispatchCLI(runner_sha256, max_seconds)
        self.ledger = ledger
        self.spawn_audit = spawn_audit

    def reserve(self, owner: str, binding: AttemptBinding) -> bool:
        return self.ledger.reserve(owner, binding)

    def read(self, owner: str, attempt_id: str) -> dict:
        return self.ledger.read(owner, attempt_id)

    def read_sources(self, owner: str, attempt_id: str, trace_id: str) -> dict | None:
        return self.ledger.read_sources(owner, attempt_id, trace_id)

    def __call__(self, owner: str, binding: AttemptBinding, question: str):
        if not self.ledger.start(owner, binding):
            return  # no second execution, even after restarted worker
        try:
            raw = invoke_pinned_no_dispatch(
                layout=self.layout, profile=self.profile, binding=binding,
                question=question, environment=os.environ,
                spawn_audit=self.spawn_audit)
            parsed = validate_no_dispatch_context_ready(
                raw, question=question, binding=binding)
            if self.spawn_audit is not None:
                try:
                    witness = self.spawn_audit.receipt(binding)
                    if (witness["state"] != "EXITED_OK"
                            or witness["witnessed_exec_count"] != 1
                            or witness["runner_sha256"]
                               != self.profile.runner_file_sha256):
                        raise SpawnEvidenceUnknown()
                except SpawnEvidenceUnknown:
                    # An OS child may have run but audit is incomplete.
                    raise TimeoutError() from None
            try:
                sources = from_c018_stdout(
                    raw, binding=binding, question=question,
                    repo_root=self.layout.repo,
                    engine_sha256=self.profile.runner_file_sha256)
            except EvidenceDenied:
                # C018 execution is still CONTEXT_READY; source proof alone fails.
                # Withheld/invalid source evidence cannot become a clickable link.
                sources = unavailable_receipt(binding)
            if not self.ledger.succeed(owner, binding, parsed, sources):
                raise PreflightDenied()
        except (TimeoutError, OSError):
            self.ledger.fail(owner, binding, unknown=True)
        except (PreflightDenied, ValueError, sqlite3.Error):
            self.ledger.fail(owner, binding)
        # Neither success nor error invokes History.finalize_t3 or Gateway.
