"""Docker liveness: verify the actual app-only TCP listener exists.

This is deliberately NOT a BFF/DB/IdP readiness claim: only the pinned
mTLS BFF can call HTTPS /internal/ready for real DB-backed readiness.
"""
from __future__ import annotations

import argparse
import socket
from pathlib import Path
from apps.api.private_app_only_asgi import load_app_only_config
from src.phase3.auth.staging_service_profile import StagingConfigDenied


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        cfg = load_app_only_config(args.config)
        with socket.create_connection(("127.0.0.1", cfg.port), timeout=2):
            pass
        return 0
    except (OSError, ValueError, RuntimeError, StagingConfigDenied):
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
