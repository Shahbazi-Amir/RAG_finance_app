# Foundation F3 393-ID candidate registry

The existing project CSVs enumerate **262** canonical activities, **26** independent Gates and **105** non-counting operational crosswalks. `scripts/f3_candidate_registry.py` checks all IDs, denominator flags, owners/criteria and rejects fabricated acceptance in 11 mutation tests. It emits a versioned, SHA-bound **393-row** candidate table and JSON summary in `ci_receipts/f3_registry/` in CI.

**Important:** source row coverage is not evidence of a fully satisfied original criterion. The `owner` of operational crosswalks is derived provisionally from mapped primary IDs and still needs CENTRAL confirmation; target-specific witness, signed Ops decisions, engine and non-engine acceptance must remain open. The full frozen app-only denominator is not yet approved, and no new Gate or P3OP is counted as accepted.

This report is operational inventory and traceability only; do not label Phase3 done or increase accepted/262, accepted/26, witnessed/105.
