"""CI-only browser fixture for importing the accepted FastAPI history app.

Fixed identities are separate processes, selected ONLY by the CI orchestrator,
not by any public HTTP header, cookie, query, body or user-facing switch.
No seed routes or identity-selection endpoints are ever registered.
"""
from __future__ import annotations

import os
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
from apps.api.history_api import app, get_trusted_actor  # noqa: E402
from src.phase3.storage.postgres.repository import uid  # noqa: E402
import uvicorn  # noqa: E402

SLOTS = {
    "A": (8111, "synthetic_ui_history_actor_a"),
    "B": (8112, "synthetic_ui_history_actor_b"),
    "NONE": (8113, None),
}


def main() -> None:
    dsn = os.environ.get("API_HISTORY_DSN", "")
    slot = os.environ.get("UI_HISTORY_ACTOR_SLOT")
    if (
        os.environ.get("CI") != "true"
        or slot not in SLOTS
        or "dbname=history_ui_ci" not in dsn
        or "host=127.0.0.1" not in dsn
        or "user=history_app" not in dsn
    ):
        raise SystemExit("CI_ONLY: temporary loopback PostgreSQL required")
    port, owner = SLOTS[slot]
    if owner is not None:
        def synthetic_actor() -> dict:
            return {
                "kind": "trusted_actor_context",
                "contract_version": "product.v1",
                "owner_user_id": owner,
                "principal_source": "server_auth_context",
                "authenticated_at": datetime.now(timezone.utc).isoformat(),
                "request_id": uid(),
                "trace_id": uid(),
            }

        app.dependency_overrides[get_trusted_actor] = synthetic_actor
    # NONE runs with the original deny-by-default dependency. Never expose
    # this harness beyond loopback, even on a CI runner.
    uvicorn.run(app, host="127.0.0.1", port=port, access_log=False, log_level="warning")


if __name__ == "__main__":
    main()
