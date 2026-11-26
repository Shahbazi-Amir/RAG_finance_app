"""Single-process, bounded staging dispatch with durable owner-scoped answers."""
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
import hashlib
import json
import os
from pathlib import Path
import socket
import sqlite3
import stat
import sys
from tempfile import TemporaryDirectory
from threading import BoundedSemaphore, Lock, Timer
from time import monotonic

from src.phase3.rag_runtime.dispatch_claim_bridge import (
    CommittedDispatchPermit, DispatchClaimDenied,
)

MAX_SOURCE_BYTES = 2 * 1024 * 1024
MAX_RESULTS = 128
TTL_SECONDS = 900


class LiveAnswerStore:
    """Durable results keyed by the authenticated owner and original question."""

    def __init__(self, folder):
        info = folder.lstat()
        if (not stat.S_ISDIR(info.st_mode) or info.st_uid != os.geteuid()
                or info.st_mode & 0o077):
            raise DispatchClaimDenied()
        self.path = folder / "answers.sqlite3"
        fd = os.open(self.path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW | os.O_NONBLOCK, 0o600)
        try:
            info = os.fstat(fd)
            if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.geteuid()
                    or info.st_mode & 0o777 != 0o600):
                raise DispatchClaimDenied()
        finally:
            os.close(fd)
        with closing(sqlite3.connect(self.path)) as conn:
            conn.execute("""CREATE TABLE IF NOT EXISTS answers (
                owner TEXT NOT NULL, conversation TEXT NOT NULL, message TEXT NOT NULL,
                attempt TEXT NOT NULL, result TEXT NOT NULL, metadata TEXT NOT NULL,
                PRIMARY KEY (owner, conversation, message)
            )""")
            conn.commit()

    def save(self, binding, message, result, producer):
        metadata = {key: producer[key] for key in
                    ("model", "usage", "semantic_support", "locator_openability")
                    if key in producer}
        with closing(sqlite3.connect(self.path)) as conn, conn:
            conn.execute("INSERT INTO answers VALUES (?, ?, ?, ?, ?, ?)",
                         (binding.owner_user_id, binding.resolved_conversation_id,
                          message, binding.attempt_id, json.dumps(result),
                          json.dumps(metadata)))

    def read(self, owner, conversation, messages):
        if not messages:
            return {}
        placeholders = ", ".join("?" for _ in messages)
        with closing(sqlite3.connect(self.path)) as conn:
            rows = conn.execute(
                "SELECT message, attempt, result FROM answers "
                f"WHERE owner = ? AND conversation = ? AND message IN ({placeholders})",
                (owner, conversation, *messages)).fetchall()
        return {message: (attempt, json.loads(result)) for message, attempt, result in rows}


class ArvanLiveDispatch:
    def __init__(self, worker_socket, generate, store=None):
        self.worker_socket = worker_socket
        self.generate = generate
        self.store = store
        self.slots = BoundedSemaphore(4)
        self.retrieval = ThreadPoolExecutor(max_workers=1)
        self.generation = ThreadPoolExecutor(max_workers=2)
        self.lock = Lock()
        self.results = {}
        self.expiry = None
        self.closed = False

    @classmethod
    def from_environment(cls, environ):
        root = Path(environ.get("ARVAN_INPUT_REPO", ""))
        engine_file = Path(environ.get("ARVAN_ENGINE_FILE", ""))
        diagnostic_root = Path(environ.get("ARVAN_DIAGNOSTIC_ROOT", ""))
        scratch = Path(environ.get("ARVAN_API_SCRATCH", ""))
        worker_socket = Path(environ.get("ARVAN_WORKER_SOCKET", ""))
        credentials = Path(environ.get("CREDENTIALS_DIRECTORY", ""))
        gateway_settings = credentials / "arvan-gateway"
        for path in (root, engine_file, diagnostic_root, scratch, worker_socket, gateway_settings):
            if not path.is_absolute():
                raise DispatchClaimDenied()
        for path, kind in ((gateway_settings, stat.S_ISREG), (scratch, stat.S_ISDIR),
                           (worker_socket, stat.S_ISSOCK)):
            info = path.lstat()
            if (not kind(info.st_mode) or info.st_uid not in {0, os.geteuid()}
                    or info.st_mode & 0o077):
                raise DispatchClaimDenied()
        if not os.access(gateway_settings, os.R_OK):
            raise DispatchClaimDenied()

        # Import only the reviewed deployment overlay and verify upstream bytes first.
        infra = Path(__file__).resolve().parents[3] / "infra/nb23-v4"
        sys.path.insert(0, str(infra))
        try:
            from arvan_gateway import metadata_issues, overlay_generation
            from worker import ENGINE_SHA
        finally:
            sys.path.remove(str(infra))
        source = engine_file.read_bytes()
        if hashlib.sha256(source).hexdigest() != ENGINE_SHA:
            raise DispatchClaimDenied()
        namespace = {"__name__": "arvan_pinned_engine", "metadata_issues": metadata_issues}
        exec(compile(overlay_generation(source.decode()), str(engine_file), "exec"), namespace)

        def generate(source, attempt_id):
            with TemporaryDirectory(dir=scratch) as outputs:
                return namespace["generate"](
                    root, Path(outputs), source, attempt_id,
                    diagnostic_root=diagnostic_root, gateway_settings=gateway_settings)

        state = Path(environ.get("STATE_DIRECTORY", ""))
        if not state.is_absolute():
            raise DispatchClaimDenied()
        service = cls(worker_socket, generate, LiveAnswerStore(state))
        if service._exchange({"probe": True}, 5) != {"ready": True}:
            raise DispatchClaimDenied()
        return service

    def _exchange(self, payload, timeout):
        with socket.socket(socket.AF_UNIX) as sock:
            sock.settimeout(timeout)
            sock.connect(str(self.worker_socket))
            sock.sendall(json.dumps(payload, ensure_ascii=False).encode() + b"\n")
            with sock.makefile("rb") as pipe:
                response = pipe.readline(MAX_SOURCE_BYTES + 1)
        if not response.endswith(b"\n") or len(response) > MAX_SOURCE_BYTES:
            raise DispatchClaimDenied()
        return json.loads(response)

    def enqueue(self, permit, binding, question, message_id=None):
        if (not isinstance(permit, CommittedDispatchPermit)
                or binding.attempt_id != permit.binding.engine_request_id
                or binding.attempt_request_id != permit.binding.product_request_id
                or binding.owner_user_id != permit.owner_id
                or binding.attempt_trace_id != permit.binding.trace_id):
            raise DispatchClaimDenied()
        key = binding.digest()
        with self.lock:
            if self.closed or key in self.results:
                raise DispatchClaimDenied()
            self.results[key] = (None, self._result("PENDING"))
        try:
            self.retrieval.submit(self._retrieve, key, binding, message_id, question)
        except RuntimeError:
            # Queue ownership stays with the sender until submit succeeds.
            self._finish(key, self._result("UNKNOWN"), release=False)
            raise DispatchClaimDenied() from None

    def _retrieve(self, key, binding, message_id, question):
        attempt_id = binding.attempt_id
        try:
            reply = self._exchange({"attempt_id": attempt_id, "question": question}, 120)
            if (reply["attempt_id"] != attempt_id
                    or reply["source"]["question"] != question.strip()):
                raise DispatchClaimDenied()
            self.generation.submit(self._generate, key, binding, message_id, reply["source"])
        except Exception:
            self._finish(key, self._result("UNKNOWN"))

    def _generate(self, key, binding, message_id, source):
        try:
            producer = self.generate(source, binding.attempt_id)
            result = public_result(producer)
            if self.store and result["state"] == "READY":
                self.store.save(binding, message_id, result, producer)
        except Exception:
            result = self._result("UNKNOWN")
        self._finish(key, result)

    @staticmethod
    def _result(state):
        return {"state": state, "outcome": None, "claims": []}

    def _schedule_expiry(self, now):
        deadlines = [deadline for deadline, _ in self.results.values() if deadline is not None]
        if not self.closed and self.expiry is None and deadlines:
            self.expiry = Timer(max(0, min(deadlines) - now), self._expire)
            self.expiry.daemon = True
            self.expiry.start()

    def _expire(self):
        with self.lock:
            self.expiry = None
            now = monotonic()
            self.results = {key: (deadline, result)
                            for key, (deadline, result) in self.results.items()
                            if deadline is None or deadline > now}
            self._schedule_expiry(now)

    def _finish(self, key, result, *, release=True):
        with self.lock:
            if not self.closed:
                if len(self.results) >= MAX_RESULTS:
                    oldest = next((k for k, (deadline, _) in self.results.items()
                                   if deadline is not None), None)
                    if oldest is not None:
                        del self.results[oldest]
                now = monotonic()
                self.results[key] = (now + TTL_SECONDS, result)
                self._schedule_expiry(now)
        if release:
            self.slots.release()

    def history(self, owner, conversation, messages):
        if not self.store:
            return {}
        return {message: result for message, (_, result) in
                self.store.read(owner, conversation, messages).items()}

    def read(self, binding, message_id=None):
        if self.store and message_id:
            saved = self.store.read(binding.owner_user_id, binding.resolved_conversation_id,
                                    (message_id,)).get(message_id)
            if saved and saved[0] == binding.attempt_id:
                return saved[1]
        with self.lock:
            deadline, result = self.results.get(binding.digest(), (0, None))
            if deadline is None or deadline > monotonic():
                return result
            return self._result("UNKNOWN")

    def close(self):
        with self.lock:
            self.closed = True
            self.results.clear()
            if self.expiry is not None:
                self.expiry.cancel()
        self.generation.shutdown(wait=False, cancel_futures=True)
        self.retrieval.shutdown(wait=False, cancel_futures=True)


def public_result(result):
    """Project producer-checked quotes only. Keep raw provider data private."""
    if result["issues"]:
        return ArvanLiveDispatch._result("REVIEW_REQUIRED")
    outcome, claims = result["outcome"], result["claims"]
    if outcome == "NO_ANSWER" and not claims:
        return {"state": "READY", "outcome": outcome, "claims": []}
    if outcome != "ANSWER" or not 1 <= len(claims) <= 5:
        raise DispatchClaimDenied()
    safe = []
    for claim in claims:
        citation = claim["citation"]
        text, quote, chunk = claim["text"], citation["quote"], citation["chunk_id"]
        if not all(isinstance(value, str) and 0 < len(value) <= limit
                   for value, limit in ((text, 2000), (quote, 2000), (chunk, 256))):
            raise DispatchClaimDenied()
        safe.append({"text": text, "quote": quote, "chunk_id": chunk})
    return {"state": "READY", "outcome": outcome, "claims": safe}
