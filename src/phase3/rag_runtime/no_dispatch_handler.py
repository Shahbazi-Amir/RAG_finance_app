"""Persistent operational-only no-dispatch outcome; never a Product Answer.

SQLite ledger is an isolated, single-host private-service artifact, NOT
history_l1, and NOT a DB-owned paid dispatch CAS/outbox. The staging service
must explicitly install this handler after Ops config review. A service crash
never triggers auto-resend; stale queued/running states show UNKNOWN.
"""
from __future__ import annotations

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

    def succeed(self, owner, binding, summary):
        return self._transition(
            owner, binding, "RUNNING", "CONTEXT_READY",
            top10=summary["top10_count"], generation=0, matched=1)

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


class NoDispatchHandler:
    def __init__(self, layout: RunnerLayout, *, runner_sha256: str, ledger: NoDispatchLedger,
                 max_seconds: int = 180):
        if (not isinstance(layout, RunnerLayout)
                or not isinstance(ledger, NoDispatchLedger)):
            raise PreflightDenied()
        self.layout = layout
        self.profile = ApprovedNoDispatchCLI(runner_sha256, max_seconds)
        self.ledger = ledger

    def reserve(self, owner: str, binding: AttemptBinding) -> bool:
        return self.ledger.reserve(owner, binding)

    def read(self, owner: str, attempt_id: str) -> dict:
        return self.ledger.read(owner, attempt_id)

    def __call__(self, owner: str, binding: AttemptBinding, question: str):
        if not self.ledger.start(owner, binding):
            return  # no second execution, even after restarted worker
        try:
            raw = invoke_pinned_no_dispatch(
                layout=self.layout, profile=self.profile, binding=binding,
                question=question, environment=os.environ)
            parsed = validate_no_dispatch_context_ready(
                raw, question=question, binding=binding)
            if not self.ledger.succeed(owner, binding, parsed):
                raise PreflightDenied()
        except (TimeoutError, OSError):
            self.ledger.fail(owner, binding, unknown=True)
        except (PreflightDenied, ValueError, sqlite3.Error):
            self.ledger.fail(owner, binding)
        # Neither success nor error invokes History.finalize_t3 or Gateway.
