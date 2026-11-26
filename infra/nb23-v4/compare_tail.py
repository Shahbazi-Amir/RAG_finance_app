"""Compare DEMO08 and V4 post-processing using one shared real score vector."""
import ast
import json
from pathlib import Path
import runpy
import sys

from trace_parity import ENGINE, GOLDEN, REFERENCE, ENGINE_SHA, sha

BASELINE = Path("/trial/demo08.py")


def ranking_tail(source):
    tree = ast.parse(source)
    fn = next(node for node in tree.body if isinstance(node, ast.FunctionDef)
              and node.name == "retrieve_context")
    start = next(i for i, node in enumerate(fn.body) if isinstance(node, ast.Assign)
                 and isinstance(node.targets[0], ast.Name)
                 and node.targets[0].id == "local")
    assert isinstance(fn.body[-1], ast.Return)
    return compile(ast.Module(body=fn.body[start:-1], type_ignores=[]),
                   "<verified-demo08-tail>", "exec")


def main():
    contract = json.loads(REFERENCE.read_text())
    golden, baseline = GOLDEN.read_bytes(), BASELINE.read_bytes()
    if (sha(ENGINE.read_bytes()) != ENGINE_SHA
            or sha(baseline) != contract["frozen_files"]["A_worker"]
            or sha(golden) != contract["input_pins"]["GOLDEN"]["file_bytes_sha256"]):
        raise ValueError("INPUT_PIN_MISMATCH")
    reference = contract["references"]["Q2"]
    question, = (row["evaluation_content"]["question"] for row in map(json.loads, golden.splitlines())
                 if row["candidate_id"] == reference["candidate_id"])
    if sha(question.encode()) != reference["question_sha256"]:
        raise ValueError("QUESTION_PIN_MISMATCH")
    tail = ranking_tail(baseline)
    engine = runpy.run_path(str(ENGINE))
    repo, artifacts = Path("/tmp/repo"), Path("/inputs/artifacts")
    comparison = {}

    def observe(frame, event, receipt):
        if event == "return" and isinstance(receipt, dict):
            scope = {**frame.f_globals, **frame.f_locals}
            exec(tail, scope)
            control = scope["receipt"]
            comparison.update(
                hybrid_parity=receipt["hybrid100"] == reference["hybrid100"],
                shared_score_count=len(scope["scores"]),
                local_onnx_order_equal=control["local100"] == receipt["local100"],
                local_top10_equal=control["final_top10"] == receipt["final_top10"],
                local_context_equal=control["context_sha256"] == receipt["context_sha256"],
                demo08_tail_matches_historical=control["context_sha256"] == reference["context_sha256"],
                v4_matches_historical=receipt["context_sha256"] == reference["context_sha256"],
                generation_calls=receipt["generation_calls"],
            )
        return observe

    def select(frame, event, _):
        if event == "call" and frame.f_code is engine["retrieve_context"].__code__:
            frame.f_trace_lines = False
            return observe
        return None

    try:
        engine["d08_worker_initialize"](repo, artifacts)
        sys.settrace(select)
        try:
            engine["answer_question"](question, repo_root=repo, artifacts_root=artifacts,
                                      request_id="q2-shared-scores", dispatch=False)
        finally:
            sys.settrace(None)
        if not comparison:
            raise RuntimeError("NO_COMPARISON")
        print(json.dumps(comparison), flush=True)
    finally:
        engine["d08_worker_close"]()
        print('{"closed":true}', flush=True)


if __name__ == "__main__":
    main()
