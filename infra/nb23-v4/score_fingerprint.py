"""Record private Q2 ONNX evidence in a fresh work file."""
import argparse
from contextlib import redirect_stdout
from importlib.metadata import version
import json
from pathlib import Path
import platform
import runpy
import sys

from trace_parity import ENGINE_SHA, sha


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("engine", "contract", "golden", "repo", "artifacts", "output"):
        parser.add_argument(name, type=Path)
    args = parser.parse_args()
    contract = json.loads(args.contract.read_text())
    engine_bytes, golden = args.engine.read_bytes(), args.golden.read_bytes()
    if (sha(engine_bytes) != ENGINE_SHA
            or sha(golden) != contract["input_pins"]["GOLDEN"]["file_bytes_sha256"]):
        raise ValueError("INPUT_PIN_MISMATCH")
    ref = contract["references"]["Q2"]
    question, = (row["evaluation_content"]["question"] for row in map(json.loads, golden.splitlines())
                 if row["candidate_id"] == ref["candidate_id"])
    if sha(question.encode()) != ref["question_sha256"]:
        raise ValueError("QUESTION_PIN_MISMATCH")
    calls = []
    engine = runpy.run_path(str(args.engine))
    state = engine["d08_worker_initialize"].__globals__["_d08_worker_state"]
    try:
        engine["d08_worker_initialize"](args.repo, args.artifacts)
        session = state["session"]
        original = session.run

        def observed(outputs, feed):
            result = original(outputs, feed)
            calls.append({
                "inputs": {key: {"shape": list(value.shape), "dtype": str(value.dtype),
                                 "sha256": sha(value.astype("<i8", copy=False).tobytes())}
                           for key, value in sorted(feed.items())},
                "scores": result[0].reshape(-1).tolist(),
            })
            return result

        session.run = observed
        try:
            with redirect_stdout(sys.stderr):
                result = engine["answer_question"](question, repo_root=args.repo,
                                                   artifacts_root=args.artifacts,
                                                   request_id="q2-batch-comparison", dispatch=False)
        finally:
            session.run = original
        if len(calls) != 25 or any(len(call["scores"]) != 4 for call in calls):
            raise ValueError("UNEXPECTED_BATCH_COUNT")
        if result["status"] != "CONTEXT_READY" or result["generation_calls"] != 0:
            raise ValueError("UNEXPECTED_RESULT")
        data = {"platform": platform.platform(), "python": platform.python_version(),
                "versions": {name: version(name) for name in ("onnxruntime", "torch", "numpy",
                             "sentence-transformers", "qdrant-client", "transformers", "tokenizers")},
                "batches": calls, "context_parity": result["context_sha256"] == ref["context_sha256"],
                "top10_parity": [row["chunk_id"] for row in result["top10"]] == ref["top10"]}
        if args.output == Path("-"):
            print(json.dumps(data, allow_nan=False))
        else:
            with args.output.open("x", encoding="utf-8") as output:
                json.dump(data, output, allow_nan=False)
            print(json.dumps({key: value for key, value in data.items() if key != "batches"}))
    finally:
        engine["d08_worker_close"]()


if __name__ == "__main__":
    main()
