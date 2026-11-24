"""Check frozen chunk membership and matching retrieval receipts offline."""

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path


MANIFEST_SHA256 = "a3ffce372eab24e210bedae9b2b6087dc2493e45805c4c27836d223a6578fe80"


def checked_bytes(path, expected):
    data = path.read_bytes()
    if hashlib.sha256(data).hexdigest() != expected:
        raise ValueError("Frozen input hash mismatch")
    return data


def load_chunks(repo, manifest):
    contract = json.loads(checked_bytes(manifest, MANIFEST_SHA256))["execution_contract"]
    pin = contract["input_pins"]["CHUNKS"]
    data = checked_bytes(repo / pin["path"], pin["file_bytes_sha256"])
    chunks = {}
    for line in data.splitlines():
        chunk = json.loads(line)
        chunk_id = chunk["chunk_id"]
        if not chunk_id or chunk_id in chunks or not chunk["source_id"]:
            raise ValueError("Invalid chunk or source identity")
        members = chunk["member_document_ids"]
        locators = chunk["member_locators"]
        if not members or Counter(members) != Counter(item["document_id"] for item in locators):
            raise ValueError("Document membership mismatch")
        chunks[chunk_id] = chunk
    if len(chunks) != 3488:
        raise ValueError("Unexpected C018 chunk count")
    return chunks


def check_top10(result, chunks):
    if result["status"] != "CONTEXT_READY" or result["generation_calls"] != 0:
        raise ValueError("Expected no-generation retrieval receipt")
    rows = result["top10"]
    if len(rows) != 10 or len({row["chunk_id"] for row in rows}) != 10:
        raise ValueError("Expected ten distinct chunks")
    for position, row in enumerate(rows, 1):
        chunk = chunks[row["chunk_id"]]
        if (row["position"] != position or row["source_id"] != chunk["source_id"]
                or row["member_locators"] != chunk["member_locators"]):
            raise ValueError("Retrieval source evidence mismatch")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("repo", type=Path)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--result", type=Path)
    args = parser.parse_args()
    chunks = load_chunks(args.repo, args.manifest)
    if args.result:
        check_top10(json.loads(args.result.read_text()), chunks)
    print(json.dumps({"chunks": len(chunks),
                      "source_types": Counter(row["source_type"] for row in chunks.values()),
                      "top10_membership": "matched" if args.result else "not_checked",
                      "locator_resolution": "unresolved"}))


if __name__ == "__main__":
    main()
