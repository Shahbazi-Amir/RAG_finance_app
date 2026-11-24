"""Run Q2, Q3 and WARM against one offline, isolated persistent worker."""

import argparse
import hashlib
import json
from pathlib import Path
import subprocess


def digest(path):
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def verify(args):
    contract = json.loads(args.contract.read_text())
    if digest(args.golden) != contract["input_pins"]["GOLDEN"]["file_bytes_sha256"]:
        raise ValueError("GOLDEN_PIN_MISMATCH")
    refs = contract["references"]
    ids = {ref["candidate_id"] for ref in refs.values()}
    questions = {}
    with args.golden.open() as golden:
        for line in golden:
            row = json.loads(line)
            if row["candidate_id"] in ids:
                questions[row["candidate_id"]] = row["evaluation_content"]["question"]
    requests = []
    for label in ("Q2", "Q3", "WARM"):
        ref = refs[label]
        question = questions[ref["candidate_id"]]
        if hashlib.sha256(question.encode()).hexdigest() != ref["question_sha256"]:
            raise ValueError("QUESTION_PIN_MISMATCH")
        requests.append(json.dumps({"attempt_id": label, "question": question}))
    completed = subprocess.run(args.command, input="\n".join(requests)+"\n",
                               text=True, stdout=subprocess.PIPE, timeout=900, check=False)
    if completed.returncode:
        print(json.dumps({"worker_exit": completed.returncode}))
        return completed.returncode
    events = [json.loads(line) for line in completed.stdout.splitlines()]
    if [e["event"] for e in events] != ["ready","result","result","result","closed"]:
        raise ValueError("INVALID_WORKER_LIFECYCLE")
    print(json.dumps(events[0]))
    passed = True
    for event, label in zip(events[1:-1], ("Q2", "Q3", "WARM")):
        result = event.pop("result")
        current = [(r["position"], r["chunk_id"], r["source_id"]) for r in result["top10"]]
        expected = [(r["position"], r["chunk_id"], r["source_id"]) for r in refs[label]["evidence"]]
        top = current == expected
        context = result["context_sha256"] == refs[label]["context_sha256"]
        passed &= top and context and event["attempt_id"] == label and result["generation_calls"] == 0
        print(json.dumps(dict(event, top10_parity=top, context_parity=context,
                              generation_calls=result["generation_calls"])))
    print(json.dumps(events[-1]))
    return 0 if passed else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("contract", type=Path)
    parser.add_argument("golden", type=Path)
    parser.add_argument("command", nargs=argparse.REMAINDER)
    raise SystemExit(verify(parser.parse_args()))
