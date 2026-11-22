"""Fail-closed Gate3 C018 retrieval evidence, not a product.v1 Answer.

Never interprets member_locators without the approved typed ENGINE contract.
Only immutable, sanitized observations may enter the API receipt. Any real
locator or source attribution remains unverified, even when chunk identity
matches a SHA-pinned JSONL file.
"""
from __future__ import annotations

import hashlib
import hmac
import json
from pathlib import Path
from typing import Mapping

CHUNKS_RELATIVE = Path("data/phase2/chunks/nb11_benchmark_v1/baseline_phase1_char_safe_v1.jsonl")
CHUNKS_SHA256 = "3891c4ecad9332ba753cd605bbccd99da9d063f64934a30ee39e495349cffb50"
ENGINE_SHA256 = "93233bfdf25e40684fd9120b82ec19c217695fdb632ed4a1f7d2bb2a3abcb17d"
CONTRACT = "api.retrieved_sources.v1"
MAX_CHUNKS_BYTES = 100_000_000
MAX_ROWS = 10


class EvidenceDenied(Exception):
    """No raw filename, chunk, locator or question in public exceptions."""


def _json_object(pairs):
    out = {}
    for name, val in pairs:
        if name in out:
            raise EvidenceDenied()
        out[name] = val
    return out


def _decode_json(raw: bytes) -> dict:
    try:
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=_json_object,
                           parse_constant=lambda _: (_ for _ in ()).throw(EvidenceDenied()))
    except (UnicodeError, ValueError, TypeError):
        raise EvidenceDenied() from None
    if not isinstance(value, dict):
        raise EvidenceDenied()
    return value


def pinned_chunk_ids(repo_root: Path, expected_sha256: str = CHUNKS_SHA256) -> frozenset[str]:
    """Read-only, byte-exact lookup. Missing/ambiguous C011 schema fails closed."""
    if not isinstance(repo_root, Path) or not isinstance(expected_sha256, str):
        raise EvidenceDenied()
    try:
        root = repo_root.resolve(strict=True)
        candidate = root / CHUNKS_RELATIVE
        if candidate.is_symlink():
            raise EvidenceDenied()
        path = candidate.resolve(strict=True)
        if not path.is_relative_to(root) or not path.is_file() or path.stat().st_size > MAX_CHUNKS_BYTES:
            raise EvidenceDenied()
        raw = path.read_bytes()
        if not hmac.compare_digest(hashlib.sha256(raw).hexdigest(), expected_sha256):
            raise EvidenceDenied()
        ids = set()
        for line in raw.splitlines():
            if not line.strip():
                raise EvidenceDenied()
            item = _decode_json(line)
            chunk_id = item.get("chunk_id")
            if not isinstance(chunk_id, str) or not chunk_id or chunk_id in ids:
                raise EvidenceDenied()
            ids.add(chunk_id)
        if not ids:
            raise EvidenceDenied()
        return frozenset(ids)
    except (OSError, RuntimeError):
        raise EvidenceDenied() from None


def from_c018_stdout(raw: bytes, *, binding, question: str,
                      repo_root: Path, chunks_sha256: str = CHUNKS_SHA256,
                      engine_sha256: str = ENGINE_SHA256) -> dict:
    """Require a valid C018 receipt + pinned chunk existence, no trusted links.

    Binding must be from committed T2 (not from stdout). Engine C018 itself has
    no request_id. member_locators is only checked for key presence; its typed
    structure has NOT been attested, so no member data or URL is persisted.
    """
    from src.phase3.rag_runtime.result_contract_gate import validate_no_dispatch_context_ready

    try:
        summary = validate_no_dispatch_context_ready(raw, question=question, binding=binding)
    except Exception:
        raise EvidenceDenied() from None
    result = _decode_json(raw)
    top10 = result.get("top10")
    if not isinstance(top10, list) or not 0 <= len(top10) <= MAX_ROWS:
        raise EvidenceDenied()
    allowed_ids = pinned_chunk_ids(repo_root, chunks_sha256)
    rows = []
    for offset, record in enumerate(top10, 1):
        if not isinstance(record, Mapping):
            raise EvidenceDenied()
        # Do not infer source or locator fields from arbitrary nested metadata.
        if not {"position", "chunk_id", "source_id", "member_locators"}.issubset(record):
            raise EvidenceDenied()
        position, chunk_id, source_id = (record[k] for k in ("position", "chunk_id", "source_id"))
        if (type(position) is not int or position != offset or
                not isinstance(chunk_id, str) or not 1 <= len(chunk_id) <= 256 or
                chunk_id not in allowed_ids or
                (source_id is not None and (
                    not isinstance(source_id, str) or not 1 <= len(source_id) <= 256))):
            raise EvidenceDenied()
        rows.append({"position": position, "chunk_id": chunk_id,
                     "chunk_match": "PASS", "source_id": source_id,
                     "source_validation": "UNVERIFIED",
                     "locator_validation": "PENDING_STRUCTURE",
                     "verified_locators": []})
    return {
        "kind": "retrieved_sources",
        "contract_version": CONTRACT,
        "attempt_id": binding.engine_request_id,
        "attempt_trace_id": binding.trace_id,
        "retrieval_state": "PARTIAL_UNVERIFIED",
        "engine_sha256": engine_sha256,
        "chunks_sha256": chunks_sha256,
        "generation_calls": summary["generation_calls"],
        "rows": rows,
    }


def unavailable_receipt(binding, reason: str = "EVIDENCE_INVALID") -> dict:
    """Sanitized missing evidence never creates a pseudo-citation."""
    if reason not in {"EVIDENCE_INVALID", "EVIDENCE_NOT_AVAILABLE"}:
        raise EvidenceDenied()
    return {"kind": "retrieved_sources", "contract_version": CONTRACT,
            "attempt_id": binding.engine_request_id,
            "attempt_trace_id": binding.trace_id,
            "retrieval_state": reason,
            "engine_sha256": ENGINE_SHA256,
            "chunks_sha256": CHUNKS_SHA256,
            "generation_calls": 0, "rows": []}
