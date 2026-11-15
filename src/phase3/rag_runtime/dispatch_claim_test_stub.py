"""DISPOSABLE CI-ONLY counting gateway boundary: ZERO network code.

The only permitted send-like action here is an in-memory count. Production
must supply a separately approved real transport (NOT part of this mission).
This stub is not a provider client and intentionally has no HTTP interface.
"""
from __future__ import annotations

from collections import Counter
from threading import Lock

from src.phase3.rag_runtime.dispatch_claim_bridge import CommittedDispatchPermit


class CountOnlyGatewayStub:
    def __init__(self):
        self._mutex = Lock()
        self._counts = Counter()
        self._failures = {}

    def inject_outcome(self, attempt_id: str, outcome: str) -> None:
        if outcome not in {"ACCEPTED", "TIMEOUT", "LOST_RESPONSE"}:
            raise ValueError("BAD_SYNTHETIC_GATEWAY_OUTCOME")
        with self._mutex:
            self._failures[attempt_id] = outcome

    def __call__(self, permit: CommittedDispatchPermit, question: str) -> None:
        if (not isinstance(permit, CommittedDispatchPermit)
                or not isinstance(question, str) or not question.strip()):
            raise ValueError("BAD_SYNTHETIC_DISPATCH_PERMIT")
        with self._mutex:
            self._counts[permit.binding.engine_request_id] += 1
            outcome = self._failures.get(permit.binding.engine_request_id, "ACCEPTED")
        if outcome == "TIMEOUT":
            raise TimeoutError("SYNTHETIC_TIMEOUT_AFTER_BOUNDARY")
        if outcome == "LOST_RESPONSE":
            raise ConnectionError("SYNTHETIC_LOST_RESPONSE_AFTER_BOUNDARY")
        # No result is an Answer, no Gateway or provider code is imported.

    def count(self, attempt_id: str | None = None) -> int:
        with self._mutex:
            return self._counts[attempt_id] if attempt_id else sum(self._counts.values())
