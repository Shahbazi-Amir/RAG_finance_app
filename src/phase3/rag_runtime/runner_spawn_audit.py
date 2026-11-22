"""Restricted, durable C018 spawn witness; never stores argv, question or stdout.

An intent is NOT proof of execution. On Linux, Popen's completed exec handshake
plus a kernel pidfd, /proc start ticks and executable identity provide positive
OS process evidence. An ambiguous child remains UNKNOWN and is never retried.
This observation is collected by the API, not a separately approved eBPF/auditd
monitor; external independent confirmation remains an Ops gate.
"""
from __future__ import annotations

import os
import re
import secrets
import sqlite3
import stat
import sys
import time
from dataclasses import dataclass
from pathlib import Path

from src.phase3.rag_runtime.staging_preflight import AttemptBinding, PreflightDenied

_IDENTIFIER = re.compile(r"^[0-9a-f]{32}$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


class SpawnEvidenceUnknown(TimeoutError):
    """An OS child might have executed, but its count cannot be proven."""


@dataclass(frozen=True)
class ProcessIdentity:
    pid: int
    proc_start_ticks: int
    observed_at_ns: int


def observe_linux_exec(pid: int, python_path: Path) -> ProcessIdentity:
    """Positive kernel observation: pidfd + /proc start identity + executable.

    Never inspect /proc/PID/cmdline or environ (they can contain --question).
    A short-lived child may be gone: fail UNKNOWN rather than invent a count.
    """
    if (not sys.platform.startswith("linux") or not hasattr(os, "pidfd_open")
            or type(pid) is not int or pid <= 0 or not isinstance(python_path, Path)):
        raise SpawnEvidenceUnknown()
    handle = None
    try:
        handle = os.pidfd_open(pid, 0)
        raw = Path(f"/proc/{pid}/stat").read_text(encoding="ascii")
        delimiter = raw.rfind(") ")
        if delimiter < 0 or int(raw.split(" (", 1)[0]) != pid:
            raise SpawnEvidenceUnknown()
        fields = raw[delimiter + 2:].split()
        # /proc/<pid>/stat field 22: indexing from state, field 3 => [19].
        ticks = int(fields[19])
        if ticks <= 0:
            raise SpawnEvidenceUnknown()
        executable = Path(os.readlink(f"/proc/{pid}/exe")).resolve(strict=True)
        if executable != python_path.resolve(strict=True):
            raise SpawnEvidenceUnknown()
        return ProcessIdentity(pid, ticks, time.time_ns())
    except (OSError, ValueError, IndexError, UnicodeError):
        raise SpawnEvidenceUnknown() from None
    finally:
        if handle is not None:
            os.close(handle)


class LinuxRunnerSpawnAudit:
    """Per-Attempt, private SQLite audit, separate from NoDispatch outcomes.

    Only an actual verified OS child increments witnessed_exec_count. Never
    expose the table through browser/API. Reboot/crash gaps are UNKNOWN.
    """
    def __init__(self, filepath: Path):
        if not isinstance(filepath, Path) or not filepath.is_absolute():
            raise PreflightDenied()
        directory = filepath.parent
        try:
            info = directory.stat()
            if (not stat.S_ISDIR(info.st_mode) or info.st_uid != os.geteuid()
                    or stat.S_IMODE(info.st_mode) & 0o077 or filepath.is_symlink()):
                raise PreflightDenied()
            if not filepath.exists():
                fd = os.open(str(filepath), os.O_CREAT | os.O_EXCL | os.O_WRONLY |
                             getattr(os, "O_NOFOLLOW", 0), 0o600)
                os.close(fd)
            entry = filepath.stat()
            if (not stat.S_ISREG(entry.st_mode) or entry.st_uid != os.geteuid()
                    or stat.S_IMODE(entry.st_mode) != 0o600):
                raise PreflightDenied()
        except OSError:
            raise PreflightDenied() from None
        self.filepath = filepath
        with self._connect() as db:
            db.execute("""CREATE TABLE IF NOT EXISTS spawn_witnesses (
                attempt_id TEXT PRIMARY KEY,
                product_request_id TEXT NOT NULL,
                trace_id TEXT NOT NULL,
                runner_sha256 TEXT NOT NULL,
                event_id TEXT NOT NULL UNIQUE,
                state TEXT NOT NULL CHECK (state IN
                    ('INTENT','OS_OBSERVED','EXITED_OK','EXITED_FAILED',
                     'FAILED_BEFORE_SPAWN','UNKNOWN')),
                intent_at_ns INTEGER NOT NULL,
                observed_at_ns INTEGER,
                pid INTEGER,
                proc_start_ticks INTEGER,
                witnessed_exec_count INTEGER NOT NULL DEFAULT 0
                    CHECK(witnessed_exec_count IN (0,1)),
                exit_code INTEGER
            )""")

    def _connect(self):
        db = sqlite3.connect(str(self.filepath), timeout=10)
        db.execute("PRAGMA synchronous=FULL")
        db.execute("PRAGMA busy_timeout=10000")
        return _AuditConnection(db)

    @staticmethod
    def _check(binding: AttemptBinding):
        if (not isinstance(binding, AttemptBinding) or not all(
                isinstance(v, str) and _IDENTIFIER.fullmatch(v)
                for v in (binding.engine_request_id, binding.product_request_id,
                          binding.trace_id))):
            raise PreflightDenied()

    def intent(self, binding: AttemptBinding, runner_sha256: str) -> None:
        self._check(binding)
        if not isinstance(runner_sha256, str) or not _SHA256.fullmatch(runner_sha256):
            raise PreflightDenied()
        try:
            with self._connect() as db:
                db.execute("""INSERT INTO spawn_witnesses
                    (attempt_id,product_request_id,trace_id,runner_sha256,
                     event_id,state,intent_at_ns)
                    VALUES (?,?,?,?,?,'INTENT',?)""",
                    (binding.engine_request_id, binding.product_request_id,
                     binding.trace_id, runner_sha256, secrets.token_hex(16),
                     time.time_ns()))
        except sqlite3.Error:
            raise PreflightDenied() from None

    def _update(self, binding: AttemptBinding, from_states: tuple[str, ...],
                new_state: str, *, identity: ProcessIdentity | None = None,
                exit_code: int | None = None) -> None:
        self._check(binding)
        if len(from_states) == 0:
            raise PreflightDenied()
        placeholders = ",".join("?" for _ in from_states)
        if identity is None:
            updated = (new_state, exit_code)
            statement = ("UPDATE spawn_witnesses SET state=?,exit_code=? "
                         "WHERE attempt_id=? AND product_request_id=? "
                         "AND trace_id=? AND state IN (" + placeholders + ")")
        else:
            if (not isinstance(identity, ProcessIdentity) or identity.pid <= 0
                    or identity.proc_start_ticks <= 0):
                raise SpawnEvidenceUnknown()
            updated = (new_state, identity.observed_at_ns, identity.pid,
                       identity.proc_start_ticks)
            statement = ("UPDATE spawn_witnesses SET state=?,observed_at_ns=?,"
                         "pid=?,proc_start_ticks=?,witnessed_exec_count=1 "
                         "WHERE attempt_id=? AND product_request_id=? "
                         "AND trace_id=? AND state IN (" + placeholders + ")")
        params = (*updated, binding.engine_request_id,
                  binding.product_request_id, binding.trace_id, *from_states)
        try:
            with self._connect() as db:
                count = db.execute(statement, params).rowcount
                if count != 1:
                    raise SpawnEvidenceUnknown()
        except sqlite3.Error:
            raise SpawnEvidenceUnknown() from None

    def observed(self, binding: AttemptBinding, identity: ProcessIdentity) -> None:
        self._update(binding, ("INTENT",), "OS_OBSERVED", identity=identity)

    def finished(self, binding: AttemptBinding, returncode: int) -> None:
        if type(returncode) is not int:
            raise SpawnEvidenceUnknown()
        self._update(binding, ("OS_OBSERVED",),
                     "EXITED_OK" if returncode == 0 else "EXITED_FAILED",
                     exit_code=returncode)

    def failed_before_spawn(self, binding: AttemptBinding) -> None:
        self._update(binding, ("INTENT",), "FAILED_BEFORE_SPAWN")

    def unknown(self, binding: AttemptBinding) -> None:
        # Best effort: failure to persist UNKNOWN MUST NOT enable a retry.
        try:
            self._update(binding, ("INTENT", "OS_OBSERVED"), "UNKNOWN")
        except (SpawnEvidenceUnknown, PreflightDenied):
            pass

    def receipt(self, binding: AttemptBinding) -> dict:
        self._check(binding)
        try:
            with self._connect() as db:
                row = db.execute("""SELECT state,witnessed_exec_count,pid,
                    proc_start_ticks,runner_sha256,event_id,exit_code
                    FROM spawn_witnesses WHERE attempt_id=?
                    AND product_request_id=? AND trace_id=?""",
                    (binding.engine_request_id, binding.product_request_id,
                     binding.trace_id)).fetchone()
        except sqlite3.Error:
            raise SpawnEvidenceUnknown() from None
        if row is None:
            raise SpawnEvidenceUnknown()
        state, count, pid, ticks, sha, event, code = row
        return {"state": state,
                "witnessed_exec_count": count if count == 1 else None,
                "pid": pid, "proc_start_ticks": ticks,
                "runner_sha256": sha, "event_id": event, "exit_code": code}


class _AuditConnection:
    def __init__(self, connection: sqlite3.Connection):
        self.db = connection

    def __enter__(self) -> sqlite3.Connection:
        return self.db

    def __exit__(self, typ, value, tb):
        try:
            if typ is None:
                self.db.commit()
            else:
                self.db.rollback()
        finally:
            self.db.close()
        return False
