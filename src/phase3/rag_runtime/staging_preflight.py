"""Read-only Phase 3 pinned-engine staging preflight; NO model/paid dispatch.

This is NOT an engine integration, production readiness, or a grant.
The actual rag_engine.py CLI and rag_finance.mvp_engine_result.v1 schema
must be independently inspected by Ops before any --dispatch is enabled.
Do not read, source, print or export the staging .env file here.
"""
from __future__ import annotations

import argparse
import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

CONTRACT_EXPECTED = "rag_finance.mvp_engine_result.v1"
OFFLINE_CACHE = "/opt/rag-finance-staging/hf/hub"
PYTHON_PATH = "/opt/rag-finance-staging/.venv-onnx-probe/bin/python"
REPO_ROOT = "/opt/rag-finance-staging/RAG_finance"
ARTIFACTS_ROOT = "/opt/rag-finance-staging/_RAG_finance_NB22E_v4_outputs"
RUNNER_RELATIVE = (
    "MVP_engine_bundles/"
    "93233bfdf25e40684fd9120b82ec19c217695fdb632ed4a1f7d2bb2a3abcb17d/"
    "rag_engine.py"
)
OFFLINE_REQUIRED = {
    "HF_HUB_CACHE": OFFLINE_CACHE,
    "HF_HUB_OFFLINE": "1",
    "TRANSFORMERS_OFFLINE": "1",
}
# These names are grounded in the repo's prior read-only gateway interface.
# Presence here does NOT prove Secret Store provisioning or paid-call consent.
GATEWAY_SETTING_NAMES = ("ARVAN_GATEWAY_URL", "ARVAN_GATEWAY_API_KEY")
IDENTIFIER = re.compile(r"^[0-9a-f]{32}$")


class PreflightDenied(Exception):
    """Non-sensitive fixed pre-dispatch refusal; never format runtime details."""

    def __str__(self) -> str:
        return "STAGING_PREFLIGHT_DENIED"


@dataclass(frozen=True)
class RunnerLayout:
    python: Path
    repo: Path
    artifacts: Path
    runner_relative: str
    cache: Path

    @classmethod
    def pinned(cls) -> RunnerLayout:
        return cls(
            python=Path(PYTHON_PATH),
            repo=Path(REPO_ROOT),
            artifacts=Path(ARTIFACTS_ROOT),
            runner_relative=RUNNER_RELATIVE,
            cache=Path(OFFLINE_CACHE),
        )

    def runner(self) -> Path:
        # Never accept user-controlled paths, absolute or parent traversal.
        relative = Path(self.runner_relative)
        if relative.is_absolute() or ".." in relative.parts:
            raise PreflightDenied()
        return self.artifacts / relative


@dataclass(frozen=True)
class AttemptBinding:
    """Stable engine request-id is the DB attempt primary key, NOT the JTI.

    Product attempt_request_id is a distinct existing product correlation ID;
    preserving both avoids silently changing #52 product.v1/T3 identity checks.
    The runner only receives a question in a separately approved dispatch path.
    """

    engine_request_id: str
    product_request_id: str
    trace_id: str


def bind_persisted_attempt(attempt: Mapping[str, object]) -> AttemptBinding:
    """Called on trusted T2 row AFTER outer transaction COMMIT, never browser data."""
    if not isinstance(attempt, Mapping) or attempt.get("state") != "attempt_pending":
        raise PreflightDenied()
    ids = (attempt.get("id"), attempt.get("attempt_request_id"),
           attempt.get("attempt_trace_id"))
    if any(not isinstance(x, str) or not IDENTIFIER.fullmatch(x) for x in ids):
        raise PreflightDenied()
    return AttemptBinding(
        engine_request_id=ids[0],
        product_request_id=ids[1],
        trace_id=ids[2],
    )


def inspect_no_dispatch(layout: RunnerLayout, environ: Mapping[str, str]) -> dict:
    """Zero subprocess, zero Runner import, zero Gateway HTTP, zero DB writes.

    Produces ONLY booleans and static contract identifiers; never file bytes,
    environment values, question, IdP token, Owner, model output or password.
    """
    runner = layout.runner()
    try:
        artifact_root = layout.artifacts.resolve(strict=True)
        resolved_runner = runner.resolve(strict=True)
        runner_confined = resolved_runner.is_relative_to(artifact_root)
    except (OSError, RuntimeError):
        runner_confined = False
    filesystem = {
        "python_present_executable":
            layout.python.is_file() and os.access(layout.python, os.X_OK),
        "repo_root_present": layout.repo.is_dir(),
        "artifacts_root_present": layout.artifacts.is_dir(),
        "runner_present_confined": runner.is_file() and runner_confined,
        "hf_cache_present": layout.cache.is_dir(),
    }
    offline_environment = {
        key: environ.get(key) == required
        for key, required in OFFLINE_REQUIRED.items()
    }
    settings_present = {
        name: bool(environ.get(name))
        for name in GATEWAY_SETTING_NAMES
    }
    return {
        "kind": "pinned_runner_preflight",
        "contract_version": "api.staging_runner_preflight.v1",
        "engine_result_contract_requested": CONTRACT_EXPECTED,
        "dispatch_performed": False,
        "gateway_call_performed": False,
        "secrets_read_from_dotenv": False,
        "filesystem": filesystem,
        "offline_environment": offline_environment,
        "gateway_settings_present_only": settings_present,
        "ops_secret_store_verified": False,
        "db_grants_verified": False,
        "runner_cli_and_result_schema_verified": False,
        "model_identity_verified": False,
        "ui_invited_session_smoke_verified": False,
        "ready_for_dispatch": False,
        "reason": "OPS_DB_RUNNER_CONTRACT_AND_UI_GATES_PENDING",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Read-only staging runner preflight")
    parser.add_argument("--no-dispatch", action="store_true", required=True,
                        help="Required safety guard; forbids any Runner invocation.")
    args = parser.parse_args(argv)
    if not args.no_dispatch:
        raise PreflightDenied()
    result = inspect_no_dispatch(RunnerLayout.pinned(), os.environ)
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    return 0 if all(result["filesystem"].values()) and all(
        result["offline_environment"].values()) else 2


if __name__ == "__main__":
    raise SystemExit(main())
