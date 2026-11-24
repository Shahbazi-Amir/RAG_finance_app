"""Offline timing probe for the pinned C018 reranker. Never print retrieval data."""

import argparse
import hashlib
import json
from pathlib import Path
import resource
import runpy
import sys
import time

DIAGNOSTICS = sys.stdout
RUNNER_SHA256 = "93233bfdf25e40684fd9120b82ec19c217695fdb632ed4a1f7d2bb2a3abcb17d"


def emit(event, start=None, cpu=None, **details):
    fields = {"event": event, **details}
    if start is not None:
        fields.update(wall_seconds=round(time.monotonic() - start, 3),
                      cpu_seconds=round(time.process_time() - cpu, 3),
                      peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    print(json.dumps(fields), file=DIAGNOSTICS, flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("runner", type=Path)
    parser.add_argument("repo", type=Path)
    parser.add_argument("artifacts", type=Path)
    parser.add_argument("--disable-intra-op-spinning", action="store_true")
    parser.add_argument("--audit-sources", action="store_true")
    args = parser.parse_args()
    with args.runner.open("rb") as file:
        if hashlib.file_digest(file, "sha256").hexdigest() != RUNNER_SHA256:
            raise ValueError("Runner pin mismatch")

    import onnxruntime

    original = onnxruntime.InferenceSession

    def timed_session(*pos, **kw):
        wall, cpu = time.monotonic(), time.process_time()
        emit("onnx_load_started")
        if args.disable_intra_op_spinning:
            kw["sess_options"].add_session_config_entry("session.intra_op.allow_spinning", "0")
        session = original(*pos, **kw)
        emit("onnx_load_finished", wall, cpu)
        run = session.run
        index = 0

        def timed_run(output_names, input_feed):
            nonlocal index
            index += 1
            started, started_cpu = time.monotonic(), time.process_time()
            emit("onnx_batch_started", batch=index, shape=list(input_feed["input_ids"].shape))
            output = run(output_names, input_feed)
            emit("onnx_batch_finished", started, started_cpu, batch=index)
            return output

        session.run = timed_run
        return session

    onnxruntime.InferenceSession = timed_session
    try:
        runner = runpy.run_path(str(args.runner))
        wall, cpu = time.monotonic(), time.process_time()
        result = runner["answer_question"](
            "سنجش مستقل بازیابی اسناد بودجه",
            repo_root=args.repo,
            artifacts_root=args.artifacts,
            request_id="isolated-onnx-profile",
            dispatch=False,
        )
        state = result.get("status")
        count = len(result["top10"]) if isinstance(result.get("top10"), list) else None
        generation = result.get("generation_calls")
        top10 = [row["chunk_id"] for row in result.get("top10", [])]
        top10_sha256 = hashlib.sha256(json.dumps(top10).encode()).hexdigest()
        emit("retrieval_finished", wall, cpu, context_ready=state == "CONTEXT_READY",
             generation_zero=generation == 0, top10_count=count, top10_sha256=top10_sha256)
        if args.audit_sources:
            from audit_c018_sources import MANIFEST_SHA256, check_top10, load_chunks

            manifest = args.artifacts / f"C011.population_boundary.{MANIFEST_SHA256}.json"
            check_top10(result, load_chunks(args.repo, manifest))
            emit("source_membership_matched")
        return 0 if state == "CONTEXT_READY" and generation == 0 and count == 10 else 1
    finally:
        onnxruntime.InferenceSession = original


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as error:
        emit("probe_failed", error_type=type(error).__name__)
        sys.exit(1)
