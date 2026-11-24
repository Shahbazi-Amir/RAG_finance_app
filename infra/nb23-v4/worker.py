"""Offline persistent V4 worker over inherited pipes; no public socket."""

import argparse
from contextlib import redirect_stdout
import hashlib
import json
from pathlib import Path
import resource
import runpy
import signal
import sys
import time

ENGINE_SHA = "91a1a34628f221f7f8bc892a0fb6a917328817dae1328856d84aad7f880f406e"
MAX_LINE = 16384


def emit(**data):
    print(json.dumps(data, ensure_ascii=False), flush=True)


def terminate(*_):
    raise SystemExit(143)


def run(args):
    with args.engine.open("rb") as source:
        if hashlib.file_digest(source, "sha256").hexdigest() != ENGINE_SHA:
            raise ValueError("ENGINE_PIN_MISMATCH")
    started = time.monotonic()
    with redirect_stdout(sys.stderr):
        engine = runpy.run_path(str(args.engine))
    try:
        with redirect_stdout(sys.stderr):
            counts = engine["d08_worker_initialize"](args.repo, args.artifacts)
        if counts != {"E5": 1, "ONNX_SESSION": 1, "TOKENIZER": 1}:
            raise RuntimeError("INVALID_CONSTRUCTION_COUNTS")
        emit(event="ready", seconds=time.monotonic()-started, constructions=counts,
             rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
        while line := sys.stdin.buffer.readline(MAX_LINE + 1):
            if len(line) > MAX_LINE:
                raise ValueError("REQUEST_TOO_LARGE")
            request = json.loads(line)
            if not isinstance(request, dict) or set(request) != {"attempt_id", "question"}:
                raise ValueError("INVALID_REQUEST")
            entered, cpu = time.monotonic(), time.process_time()
            with redirect_stdout(sys.stderr):
                result = engine["answer_question"](
                    request["question"], repo_root=args.repo,
                    artifacts_root=args.artifacts, request_id=request["attempt_id"],
                    dispatch=False,
                )
            if result["status"] != "CONTEXT_READY" or result["generation_calls"] != 0:
                raise RuntimeError("INVALID_RESULT")
            emit(event="result", attempt_id=request["attempt_id"],
                 seconds=time.monotonic()-entered, cpu_seconds=time.process_time()-cpu,
                 rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss, result=result)
    finally:
        engine["d08_worker_close"]()
        emit(event="closed")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("engine", "repo", "artifacts"):
        parser.add_argument(name, type=Path)
    signal.signal(signal.SIGTERM, terminate)
    try:
        run(parser.parse_args())
    except Exception as exc:
        emit(event="failed", error_type=type(exc).__name__)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
