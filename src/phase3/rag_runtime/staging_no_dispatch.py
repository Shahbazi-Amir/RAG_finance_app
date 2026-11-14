"""API-owned no-dispatch Runner bridge for an already committed #52 T2 Attempt.

NOT a staging deployment or live adapter. Exact runner CLI/input is pending
inspection of NB23(2):C018/C019. Only a trusted approved server-side profile
may supply it. No T3, retry, auto-dispatch or raw engine-result logging.
"""
from __future__ import annotations

import hashlib
import os
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Mapping

from src.phase3.rag_runtime.staging_preflight import (
    AttemptBinding, PreflightDenied, RunnerLayout, OFFLINE_REQUIRED,
    bind_persisted_attempt,
)

HEX_SHA = re.compile(r"^[0-9a-f]{64}$")
MAX_OUTPUT_BYTES = 1_048_576


@dataclass(frozen=True)
class ApprovedNoDispatchCLI:
    """Server-side only, from vetted Runner source, NEVER browser-provided.

    C018 confirms --repo-root, --artifacts-root, --request-id, --question.
    The exact actual Runner file digest must still be pinned from Ops.
    """
    runner_file_sha256: str
    max_seconds: int = 180


@dataclass(frozen=True)
class PreDispatchReceipt:
    engine_request_id: str | None
    product_request_id: str | None
    trace_id: str | None
    enqueue_performed: bool
    is_replay: bool


def prepare_post_commit_no_dispatch(
    committed_operation: Callable[[], tuple[Mapping, Mapping | None]],
    enqueue_server_task: Callable[[AttemptBinding, str], None],
    question: str,
) -> tuple[Mapping, PreDispatchReceipt]:
    """Caller must supply existing signed/owner-scoped T1+T2 commit callback.

    Callback returns only AFTER successful PG COMMIT. No engine action is
    allowed in that transaction. Queue only a CREATED receipt; retry/Poll
    cannot queue a second attempt, nor can the function finalize an Answer.
    """
    if not isinstance(question, str) or not question.strip():
        raise PreflightDenied()
    receipt, attempt = committed_operation()
    if not isinstance(receipt, Mapping):
        raise PreflightDenied()
    disposition = receipt.get("disposition")
    if disposition == "replayed":
        if attempt is not None:
            raise PreflightDenied()
        return receipt, PreDispatchReceipt(None, None, None, False, True)
    if disposition != "created" or not isinstance(attempt, Mapping):
        raise PreflightDenied()
    binding = bind_persisted_attempt(attempt)
    # Must be a quick server-only enqueue, e.g. Starlette BackgroundTask.
    enqueue_server_task(binding, question)
    return receipt, PreDispatchReceipt(binding.engine_request_id,
                                       binding.product_request_id,
                                       binding.trace_id, True, False)


def _matches_exact_file_sha(path: Path, expected: str) -> bool:
    if not isinstance(expected, str) or HEX_SHA.fullmatch(expected) is None:
        return False
    digest = hashlib.sha256()
    try:
        with path.open("rb") as file:
            while True:
                chunk = file.read(1024 * 1024)
                if not chunk:
                    break
                digest.update(chunk)
    except OSError:
        return False
    return digest.hexdigest() == expected


def _safe_approved_argv(profile: ApprovedNoDispatchCLI,
                        binding: AttemptBinding, layout: RunnerLayout,
                        question: str) -> tuple[str, ...]:
    if (not isinstance(profile, ApprovedNoDispatchCLI)
            or not 1 <= profile.max_seconds <= 300
            or not isinstance(question, str) or not question.strip()
            or "\x00" in question or len(question.encode("utf-8")) > 8192):
        raise PreflightDenied()
    # NB23.C018: ONLY these four arguments, no stdin, no --dispatch.
    # Values are from the server's pinned layout and trusted T2 Attempt,
    # NEVER from user-supplied argv or browser-chosen request-id.
    return (
        "--repo-root", str(layout.repo),
        "--artifacts-root", str(layout.artifacts),
        "--request-id", binding.engine_request_id,
        "--question", question,
    )


def invoke_pinned_no_dispatch(
    *,
    layout: RunnerLayout,
    profile: ApprovedNoDispatchCLI,
    binding: AttemptBinding,
    question: str,
    environment: Mapping[str, str],
) -> bytes:
    """One bounded subprocess only, with no Gateway credentials in child env.

    Uses C018 --question CLI (stdin is unsupported). Raw stdout stays in memory,
    for later independently approved schema validation, never in History.
    """
    if (not isinstance(layout, RunnerLayout)
            or not isinstance(binding, AttemptBinding)
            or not isinstance(question, str)):
        raise PreflightDenied()
    argv = _safe_approved_argv(profile, binding, layout, question)
    try:
        root = layout.artifacts.resolve(strict=True)
        path = layout.runner().resolve(strict=True)
        if (not path.is_file() or not path.is_relative_to(root)
                or not layout.python.is_file()
                or not os.access(layout.python, os.X_OK)
                or not layout.repo.is_dir() or not layout.cache.is_dir()
                or not _matches_exact_file_sha(path, profile.runner_file_sha256)
                or environment.get("HF_HUB_CACHE") != str(layout.cache)
                or environment.get("HF_HUB_OFFLINE") != "1"
                or environment.get("TRANSFORMERS_OFFLINE") != "1"):
            raise PreflightDenied()
        allowed_env = {
            "PATH": "/usr/bin:/bin", "LANG": "C.UTF-8",
            "HF_HUB_CACHE": environment["HF_HUB_CACHE"],
            "HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1",
        }
        proc = subprocess.run(
            [str(layout.python), str(path), *argv],
            stdin=subprocess.DEVNULL, cwd=str(layout.repo), env=allowed_env,
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            timeout=profile.max_seconds, check=False,
        )
        if proc.returncode != 0 or not 0 < len(proc.stdout) <= MAX_OUTPUT_BYTES:
            raise PreflightDenied()
        return proc.stdout
    except subprocess.TimeoutExpired:
        # A launched process may have progressed despite timeout.
        # Preserve UNKNOWN and NEVER retry automatically.
        raise TimeoutError() from None
    except (OSError, ValueError, subprocess.SubprocessError):
        raise PreflightDenied() from None
