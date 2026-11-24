"""Trace the existing engine at retrieval boundaries without changing scoring."""

import hashlib
import json
from pathlib import Path
import runpy
import sys

from worker import ENGINE_SHA

ENGINE = Path("/opt/nb23-v4/engine.py")
REFERENCE = Path("/trial/contract.json")
GOLDEN = Path("/trial/golden.jsonl")


def sha(data):
    return hashlib.sha256(data).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False,
                      separators=(",", ":"), allow_nan=False).encode()


def main():
    source = ENGINE.read_bytes()
    if sha(source) != ENGINE_SHA:
        raise ValueError("ENGINE_PIN_MISMATCH")
    contract = json.loads(REFERENCE.read_text())
    golden = GOLDEN.read_bytes()
    if sha(golden) != contract["input_pins"]["GOLDEN"]["file_bytes_sha256"]:
        raise ValueError("GOLDEN_PIN_MISMATCH")
    refs = contract["references"]
    ids = {r["candidate_id"] for r in refs.values()}
    questions = {}
    for line in golden.splitlines():
        entry = json.loads(line)
        if entry["candidate_id"] in ids:
            questions[entry["candidate_id"]] = entry["evaluation_content"]["question"]
    boundaries = {}
    prefixes = {
        "need(len(hybrid)": "hybrid",
        "local = sorted(hybrid": "onnx",
        "context_parts = []": "final",
    }
    for idx, line in enumerate(source.decode().splitlines(), 1):
        for prefix, label in prefixes.items():
            if line.strip().startswith(prefix):
                boundaries[idx] = label
    if len(boundaries) != len(prefixes):
        raise ValueError("TRACE_BOUNDARY_MISMATCH")
    engine = runpy.run_path(str(ENGINE))
    repo = Path("/tmp/repo")
    artifacts = Path("/inputs/artifacts")
    try:
        print(json.dumps({"ready": engine["d08_worker_initialize"](repo, artifacts)}), flush=True)
        for label in ("Q2", "Q3"):
            ref = refs[label]
            question = questions[ref["candidate_id"]]
            if sha(question.encode()) != ref["question_sha256"]:
                raise ValueError("QUESTION_PIN_MISMATCH")
            record = {"label": label}
            def at_line(frame, event, _):
                if event != "line":
                    return at_line
                step = boundaries.get(frame.f_lineno)
                if step == "hybrid":
                    local = frame.f_locals
                    dense = list(zip(local["dense_ids"], local["dense_scores"]))
                    sparse = [(local["doc_ids"][i], float(local["sparse_scores"][i]))
                              for i in local["chosen"]]
                    observed = local["hybrid"]
                    record.update(e5_sha=sha(local["vector"].astype("<f4").tobytes()),
                                  dense_sha=sha(canonical(dense)),
                                  sparse_sha=sha(canonical(sparse)),
                                  hybrid_sha=sha(canonical(observed)),
                                  hybrid_first_difference=next(
                                      (i for i,(a,b) in enumerate(zip(observed,ref["hybrid100"]),1) if a!=b),
                                      None),
                                  hybrid_common=len(set(observed)&set(ref["hybrid100"])))
                elif step == "onnx":
                    scores = frame.f_locals["scores"]
                    record.update(onnx_score_sha=sha(canonical(scores)), onnx_pairs=len(scores))
                elif step == "final":
                    record["final_top_sha"] = sha(canonical(frame.f_locals["top"]))
                return at_line
            def select(frame, event, _):
                if event == "call" and frame.f_code is engine["retrieve_context"].__code__:
                    return at_line
                return None
            sys.settrace(select)
            try:
                result = engine["answer_question"](question, repo_root=repo,
                                                   artifacts_root=artifacts,
                                                   request_id=label, dispatch=False)
            finally:
                sys.settrace(None)
            record.update(context_parity=result["context_sha256"]==ref["context_sha256"],
                          generation_calls=result["generation_calls"])
            print(json.dumps(record), flush=True)
    finally:
        engine["d08_worker_close"]()
        print('{"closed":true}', flush=True)


if __name__ == "__main__":
    main()
