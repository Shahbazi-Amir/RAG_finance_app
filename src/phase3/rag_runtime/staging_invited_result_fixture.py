"""STRICTLY synthetic, separate from product.v1: invited staging result CI fixture.

No real provider, paid Gateway, answer provenance, T3 or live deployment.
This exact fixture is the ONLY result this ledger accepts. Real staging needs
Foundation/DB/Security approval of separate encrypted storage, consent and TTL.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sqlite3
import stat
import time
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Mapping

from src.phase3.rag_runtime.dispatch_claim_test_stub import CountOnlyGatewayStub
from src.phase3.rag_runtime.staging_preflight import PreflightDenied

VERSION = "staging.invited_live_result.v1"
WARNING = "آزمایشی؛ این پاسخ و استناد تأییدشدهٔ محصول نیستند."
FIXTURE_ANSWER = {
    "text": "در این نمونهٔ آزمایشی، بودجه برنامه‌ای برای برآورد درآمدها و هزینه‌هاست.",
    "citations": [{
        "citation_id": "fixture-cite-budget-01",
        "source_id": "fixture:budget-example-001",
        "title": "سند ساختگی آزمون بودجه",
        "evidence_status": "SYNTHETIC_TEST_ONLY",
        "excerpt": None,
        "locator": None,
    }],
}
HEX32 = re.compile(r"^[0-9a-f]{32}$")
HEX64 = re.compile(r"^[0-9a-f]{64}$")
IDENTIFIER = re.compile(r"^[A-Za-z0-9_-]{1,128}$")


def _strict_ci():
    if os.getenv("CI") != "true" or os.getenv("GITHUB_ACTIONS") != "true":
        raise PreflightDenied()


@dataclass(frozen=True, repr=False)
class InvitedBinding:
    owner_user_id: str
    session_ref_sha256: str
    session_epoch: int
    session_generation: int
    requested_conversation_id: str | None
    resolved_conversation_id: str
    client_message_id: str
    idempotency_key: str
    attempt_id: str
    attempt_request_id: str
    attempt_trace_id: str

    def __post_init__(self):
        if (not isinstance(self.owner_user_id, str)
                or not 1 <= len(self.owner_user_id) <= 256
                or not isinstance(self.session_ref_sha256, str)
                or not HEX64.fullmatch(self.session_ref_sha256)
                or type(self.session_epoch) is not int or self.session_epoch < 0
                or type(self.session_generation) is not int
                or self.session_generation < 0
                or (self.requested_conversation_id is not None
                    and (not isinstance(self.requested_conversation_id, str)
                         or not IDENTIFIER.fullmatch(self.requested_conversation_id)))
                or not isinstance(self.resolved_conversation_id, str)
                or not IDENTIFIER.fullmatch(self.resolved_conversation_id)
                or not isinstance(self.client_message_id, str)
                or not IDENTIFIER.fullmatch(self.client_message_id)
                or not isinstance(self.idempotency_key, str)
                or len(self.idempotency_key) < 8
                or not IDENTIFIER.fullmatch(self.idempotency_key)
                or any(not isinstance(x, str) or not HEX32.fullmatch(x)
                       for x in (self.attempt_id, self.attempt_request_id,
                                 self.attempt_trace_id))):
            raise PreflightDenied()

    def digest(self) -> str:
        return hashlib.sha256(json.dumps(
            asdict(self), ensure_ascii=False, sort_keys=True,
            separators=(",", ":")).encode("utf-8")).hexdigest()

    def __repr__(self) -> str:
        return "InvitedBinding(<redacted>)"


def session_ref_digest(ref: str) -> str:
    if not isinstance(ref, str) or not 32 <= len(ref) <= 512:
        raise PreflightDenied()
    return hashlib.sha256(ref.encode("utf-8")).hexdigest()


class FixedInvitedGatewayStub(CountOnlyGatewayStub):
    """Only network-free, fixed synthetic producer; counted per Attempt."""

    def __call__(self, permit, question: str) -> dict:
        super().__call__(permit, question)  # increments once, or raises after count
        return json.loads(json.dumps(FIXTURE_ANSWER, ensure_ascii=False))


class PrivateFixtureResultLedger:
    """Single-host, durable synthetic receipt only, NOT approved for real answers.

    Data is synthetic constant; retains NO user question/secret/session token.
    Actual live responses require separately approved encrypted/result database.
    """

    def __init__(self, filepath: Path, *, ttl_seconds: int = 900):
        _strict_ci()
        if (not isinstance(filepath, Path) or not filepath.is_absolute()
                or type(ttl_seconds) is not int or not 60 <= ttl_seconds <= 1800):
            raise PreflightDenied()
        folder = filepath.parent
        try:
            folder_info = folder.stat()
            if (not stat.S_ISDIR(folder_info.st_mode)
                    or folder_info.st_uid != os.geteuid()
                    or stat.S_IMODE(folder_info.st_mode) != 0o700
                    or filepath.is_symlink()):
                raise PreflightDenied()
            if not filepath.exists():
                fd = os.open(str(filepath), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
                os.close(fd)
            file_info = filepath.stat()
            if (not stat.S_ISREG(file_info.st_mode)
                    or file_info.st_uid != os.geteuid()
                    or stat.S_IMODE(file_info.st_mode) != 0o600):
                raise PreflightDenied()
        except OSError:
            raise PreflightDenied() from None
        self.filepath = filepath
        self.ttl_seconds = ttl_seconds
        with self._connect() as conn:
            conn.execute("""CREATE TABLE IF NOT EXISTS staging_fixture_results(
                attempt_id TEXT PRIMARY KEY,
                binding_digest TEXT NOT NULL,
                expires_at INTEGER NOT NULL,
                state TEXT NOT NULL CHECK(state IN ('PENDING','READY','FAILED','UNKNOWN')),
                answer_json TEXT
            )""")

    @contextmanager
    def _connect(self):
        conn = sqlite3.connect(str(self.filepath), timeout=10)
        try:
            conn.execute("PRAGMA synchronous=FULL")
            conn.execute("PRAGMA busy_timeout=10000")
            conn.execute("PRAGMA secure_delete=ON")
            yield conn
            conn.commit()
        except BaseException:
            conn.rollback()
            raise
        finally:
            conn.close()

    def reserve(self, binding: InvitedBinding) -> bool:
        _strict_ci()
        if not isinstance(binding, InvitedBinding):
            raise PreflightDenied()
        with self._connect() as c:
            row = c.execute("""INSERT OR IGNORE INTO staging_fixture_results
                 (attempt_id,binding_digest,expires_at,state)
                 VALUES(?,?,?,'PENDING')""",
                 (binding.attempt_id, binding.digest(),
                  int(time.time()) + self.ttl_seconds))
            if row.rowcount == 1:
                return True
            existing = c.execute(
                "SELECT binding_digest FROM staging_fixture_results WHERE attempt_id=?",
                (binding.attempt_id,)).fetchone()
            if existing is None or existing[0] != binding.digest():
                raise PreflightDenied()
            return False  # replay, even after failed/unknown/restart

    def _change(self, binding: InvitedBinding, state: str,
                answer: Mapping | None = None) -> bool:
        _strict_ci()
        if not isinstance(binding, InvitedBinding) or state not in {
                "READY", "FAILED", "UNKNOWN"}:
            raise PreflightDenied()
        if (state == "READY" and answer != FIXTURE_ANSWER
                or state != "READY" and answer is not None):
            raise PreflightDenied()
        serialized = (json.dumps(answer, ensure_ascii=False, sort_keys=True)
                      if answer is not None else None)
        with self._connect() as c:
            cur = c.execute("""UPDATE staging_fixture_results
                SET state=?,answer_json=?
                WHERE attempt_id=? AND binding_digest=?
                  AND state='PENDING' AND expires_at>?""",
                (state, serialized, binding.attempt_id, binding.digest(),
                 int(time.time())))
            return cur.rowcount == 1

    def ready(self, binding: InvitedBinding, answer: Mapping) -> bool:
        return self._change(binding, "READY", answer)

    def unknown(self, binding: InvitedBinding) -> bool:
        return self._change(binding, "UNKNOWN")

    def read(self, binding: InvitedBinding) -> dict | None:
        """No DB writes, Gateway, Claim or Runner on poll/recovery."""
        _strict_ci()
        if not isinstance(binding, InvitedBinding):
            raise PreflightDenied()
        with self._connect() as c:
            row = c.execute("""SELECT binding_digest,expires_at,state,answer_json
               FROM staging_fixture_results WHERE attempt_id=?""",
               (binding.attempt_id,)).fetchone()
        if row is None:
            return None
        digest, expires_at, state, payload = row
        if digest != binding.digest():
            raise PreflightDenied()
        if int(time.time()) >= expires_at:
            return {"result_status": "UNKNOWN", "answer": None,
                    "retention_expires_at": expires_at}
        if state == "READY":
            try:
                answer = json.loads(payload)
            except (ValueError, TypeError):
                raise PreflightDenied() from None
            if answer != FIXTURE_ANSWER:
                raise PreflightDenied()
        else:
            if payload is not None:
                raise PreflightDenied()
            answer = None
        return {"result_status": state, "answer": answer,
                "retention_expires_at": expires_at}

    def purge_expired(self) -> int:
        """Separate explicit operator cleanup; never triggered by signed GET."""
        _strict_ci()
        with self._connect() as c:
            return c.execute(
                "DELETE FROM staging_fixture_results WHERE expires_at<=?",
                (int(time.time()),)).rowcount
