"""Private, single-flight subprocess transport for the pinned V4 worker."""
from __future__ import annotations

import json
import os
import selectors
import signal
import subprocess
from threading import Lock
import time

from .result_contract_gate import validate_no_dispatch_context_ready
from .staging_preflight import AttemptBinding

MAX_FRAME = 65536


class WorkerUnavailable(RuntimeError):
    pass


class PersistentV4Pipe:
    """The caller owns staging configuration and durable attempt admission."""

    def __init__(self, command: list[str], offline_environment: dict[str, str],
                 *, startup_timeout: float = 180, request_timeout: float = 180):
        if not 0 < startup_timeout <= 180 or not 0 < request_timeout <= 180:
            raise ValueError("INVALID_V4_TIMEOUT")
        required = {"HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1"}
        if any(offline_environment.get(key) != value for key, value in required.items()):
            raise ValueError("V4_OFFLINE_REQUIRED")
        env = {key: value for key, value in offline_environment.items()
               if key in {*required, "HF_HUB_CACHE", "LANG", "PATH"}}
        self._lock = Lock()
        self._buffer = bytearray()
        self._request_timeout = request_timeout
        self._process = subprocess.Popen(
            command, env=env, stdin=subprocess.PIPE, start_new_session=True,
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, bufsize=0,
        )
        try:
            os.set_blocking(self._process.stdin.fileno(), False)
            hello = self._read(time.monotonic() + startup_timeout)
            if (hello.get("event") != "ready"
                    or hello.get("constructions") != {"E5": 1, "TOKENIZER": 1, "ONNX_SESSION": 1}):
                raise WorkerUnavailable("V4_NOT_READY")
        except BaseException:
            self._shutdown()
            raise

    @staticmethod
    def _wait(fd: int, event: int, deadline: float) -> None:
        with selectors.DefaultSelector() as selector:
            selector.register(fd, event)
            remaining = deadline - time.monotonic()
            if remaining <= 0 or not selector.select(remaining):
                raise TimeoutError("V4_DEADLINE")

    def _read(self, deadline: float) -> dict:
        fd = self._process.stdout.fileno()
        while b"\n" not in self._buffer:
            self._wait(fd, selectors.EVENT_READ, deadline)
            part = os.read(fd, min(4096, MAX_FRAME + 1 - len(self._buffer)))
            if not part:
                raise WorkerUnavailable("V4_PIPE_CLOSED")
            self._buffer.extend(part)
            if len(self._buffer) > MAX_FRAME:
                raise WorkerUnavailable("V4_FRAME_TOO_LARGE")
        line, _, remaining = self._buffer.partition(b"\n")
        self._buffer = remaining
        frame = json.loads(line)
        if not isinstance(frame, dict):
            raise WorkerUnavailable("INVALID_V4_FRAME")
        return frame

    def request(self, binding: AttemptBinding, question: str) -> dict:
        if not self._lock.acquire(blocking=False):
            raise WorkerUnavailable("V4_BUSY")
        try:
            if self._process.poll() is not None:
                raise WorkerUnavailable("V4_NOT_RUNNING")
            request = json.dumps({"attempt_id": binding.engine_request_id, "question": question},
                                 ensure_ascii=False).encode() + b"\n"
            if len(request) > 16384:
                raise ValueError("V4_REQUEST_TOO_LARGE")
            deadline = time.monotonic() + self._request_timeout
            fd = self._process.stdin.fileno()
            while request:
                self._wait(fd, selectors.EVENT_WRITE, deadline)
                request = request[os.write(fd, request):]
            frame = self._read(deadline)
            if frame.get("event") != "result" or frame.get("attempt_id") != binding.engine_request_id:
                raise WorkerUnavailable("V4_RESULT_BINDING_MISMATCH")
            result = json.dumps(frame.get("result"), ensure_ascii=False, allow_nan=False).encode()
            return validate_no_dispatch_context_ready(result, question=question, binding=binding)
        except Exception:
            # Discard a potentially desynchronized stream. No restart or replay here.
            self._shutdown()
            raise
        finally:
            self._lock.release()

    def close(self) -> None:
        with self._lock:
            self._shutdown()

    def _shutdown(self) -> None:
        self._process.stdin.close()
        try:
            self._process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            try:
                os.killpg(self._process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            self._process.wait()
        finally:
            self._process.stdout.close()
