"""Q2 first-batch diagnostic, using exact historical ordering and pinned inputs."""
import hashlib
import json
from pathlib import Path
import sys

from huggingface_hub import snapshot_download
import numpy as np
import onnxruntime as ort
from transformers import AutoTokenizer

from trace_parity import GOLDEN, REFERENCE, sha


def main():
    trial = json.loads(REFERENCE.read_text())
    golden = GOLDEN.read_bytes()
    assert sha(golden) == trial["input_pins"]["GOLDEN"]["file_bytes_sha256"]
    ref = trial["references"]["Q2"]
    question, = (row["evaluation_content"]["question"] for row in map(json.loads, golden.splitlines())
                 if row["candidate_id"] == ref["candidate_id"])
    assert sha(question.encode()) == ref["question_sha256"]
    chunk_pin = trial["input_pins"]["CHUNKS"]
    content = (Path("/tmp/repo") / chunk_pin["path"]).read_bytes()
    assert sha(content) == chunk_pin["file_bytes_sha256"]
    batch = ref["hybrid100"][:4]
    by_id = {row["chunk_id"]: row["content"] for row in map(json.loads, content.splitlines())
             if row["chunk_id"] in batch}
    pin = trial["model_pins"]["onnx"]
    snapshot = Path(snapshot_download(pin["model_id"], revision=pin["revision"], local_files_only=True))
    for name, info in pin["tokenizer_files"].items():
        assert sha((snapshot / name).read_bytes()) == info["sha256"]
    manifest_path = next(Path("/inputs/artifacts").glob("C011.population_boundary.*.json"))
    data = manifest_path.read_bytes()
    assert sha(data) == trial["frozen_files"]["C011"]
    alias = json.loads(data)["execution_contract"]["onnx"]["model_alias_relative_inside_snapshot"]
    model = snapshot / alias
    with model.open("rb") as handle:
        assert hashlib.file_digest(handle, "sha256").hexdigest() == pin["model_sha256"]
    tokenizer = AutoTokenizer.from_pretrained(str(snapshot), local_files_only=True, trust_remote_code=False)
    encoded = tokenizer([question]*4, [by_id[cid] for cid in batch], padding=True,
                        truncation=True, max_length=512, return_tensors="np")
    native, docker = json.load(sys.stdin)
    print(json.dumps({"ort_version": ort.__version__, "ort_build": ort.get_build_info(),
                      "available_providers": ort.get_available_providers(),
                      "model_sha256": pin["model_sha256"]}), flush=True)
    for label, level in [("x64_quant_precision", None),
                         ("x64_quant_precision_no_optimizer", ort.GraphOptimizationLevel.ORT_DISABLE_ALL)]:
        options = ort.SessionOptions()
        options.intra_op_num_threads = 4
        options.inter_op_num_threads = 1
        options.execution_mode = ort.ExecutionMode.ORT_SEQUENTIAL
        options.add_session_config_entry("session.x64quantprecision", "1")
        if level is not None:
            options.graph_optimization_level = level
        session = ort.InferenceSession(str(model), sess_options=options, providers=["CPUExecutionProvider"])
        feed = {node.name: np.asarray(encoded[node.name], dtype=np.int64) for node in session.get_inputs()}
        fingerprints = {key: {"shape": list(value.shape), "dtype": str(value.dtype),
                              "sha256": sha(value.astype("<i8", copy=False).tobytes())}
                        for key, value in feed.items()}
        assert fingerprints == native["inputs"] == docker["inputs"]
        scores = session.run(None, feed)[0].reshape(-1).tolist()
        outputs = [{"name": node.name, "shape": node.shape, "type": node.type}
                   for node in session.get_outputs()]
        del session
        print(json.dumps({"option": label, "matches_native": scores == native["scores"],
                          "matches_docker": scores == docker["scores"],
                          "outputs": outputs,
                          "max_abs_delta_from_native": max(abs(x-y) for x,y in zip(scores,native["scores"]))}),
              flush=True)


if __name__ == "__main__":
    main()
