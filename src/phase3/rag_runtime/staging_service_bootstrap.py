"""Fail-closed Ops startup constructor for private C018 no-dispatch staging.

This code DOES NOT install itself or deploy a service. An approved private
ASGI bootstrap must inject Auth/BFF trusted mTLS and the returned handler.
Engine version, Python, data paths and ledger are server-owned arguments.
No paid dispatch, external network, Gateway secrets or T3 in this module.
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

from src.phase3.auth.staging_service_profile import (
    PrivateStagingProfile, RUNNER_C018_SHA256,
)
from src.phase3.rag_runtime.no_dispatch_handler import (
    NoDispatchHandler, NoDispatchLedger,
)
from src.phase3.rag_runtime.runner_spawn_audit import LinuxRunnerSpawnAudit
from src.phase3.rag_runtime.staging_no_dispatch import _matches_exact_file_sha
from src.phase3.rag_runtime.staging_preflight import (
    PreflightDenied, RunnerLayout, inspect_no_dispatch,
)


@dataclass(frozen=True, repr=False)
class PrivateStagingEngineConfig:
    """Explicit Ops config; never create from a browser request or .env data."""

    layout: RunnerLayout
    engine_version: str
    ledger_file: Path
    max_seconds: int = 180

    def __post_init__(self):
        if (not isinstance(self.layout, RunnerLayout)
                or not isinstance(self.engine_version, str)
                or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}", self.engine_version)
                or not isinstance(self.ledger_file, Path)
                or not self.ledger_file.is_absolute()
                or type(self.max_seconds) is not int
                or not 1 <= self.max_seconds <= 300):
            raise PreflightDenied()


def build_private_no_dispatch_handler(
    *, profile: PrivateStagingProfile, config: PrivateStagingEngineConfig,
    environ: Mapping[str, str],
) -> NoDispatchHandler:
    """Require real file-digest, offline assets and private ledger BEFORE API enable.

    The *same* ledger filepath/volume and runtime UID must be used by Status
    and execution processes. This constructor cannot attest remote Ops/mTLS
    or make unapproved DB grants; those are separate hard deployment gates.
    """
    if (not isinstance(profile, PrivateStagingProfile)
            or not isinstance(config, PrivateStagingEngineConfig)
            or not isinstance(environ, Mapping)
            or profile.runner_sha256 != RUNNER_C018_SHA256):
        raise PreflightDenied()
    layout = config.layout
    report = inspect_no_dispatch(layout, environ)
    if not all(report["filesystem"].values()) or not all(
            report["offline_environment"].values()):
        raise PreflightDenied()
    try:
        runner = layout.runner().resolve(strict=True)
        if (not runner.is_file()
                or not _matches_exact_file_sha(runner, profile.runner_sha256)
                or not os.access(layout.repo, os.R_OK | os.X_OK)
                or not os.access(layout.artifacts, os.R_OK | os.X_OK)
                or not os.access(layout.cache, os.R_OK | os.X_OK)):
            raise PreflightDenied()
        ledger = NoDispatchLedger(config.ledger_file)
        # Separate 0600 private OS witness, same approved 0700 ledger directory.
        # No staging send is accepted unless this audit is writable at startup.
        audit_file = config.ledger_file.with_name(
            config.ledger_file.stem + ".spawn-audit.sqlite3")
        spawn_audit = LinuxRunnerSpawnAudit(audit_file)
    except (OSError, ValueError):
        raise PreflightDenied() from None
    return NoDispatchHandler(
        layout, runner_sha256=profile.runner_sha256,
        ledger=ledger, max_seconds=config.max_seconds,
        spawn_audit=spawn_audit,
    )
