# FOUNDATION_F3 — DB59/API61/UI60 completion integration candidate (2026-11-23)
Parent integrated candidate: 0c0a942c893d13393e47d94ca0c0d260cce6067e. This is **a new isolated source candidate**, not a Mac acceptance or deployment.
## Immutable owner versions
- DATABASE_F3 #59: code-tested b6b79369006eca3a1e4c8e75a9ba4ab14d0fab74, HEAD da8d5b48af0c4fbecf8df633356939d6cc6cdd8c; later commits are docs/receipts only; **real isolated PG17.11+restore** witnessed in GitHub run 45082326382, not Mac runtime.
- API_F3 #61: exact tested/head c02ba7896edb78febd2042f7afb1243f2a6aca34; GitHub run 45081955496, full 134 API + 38 contracts + 103 Web/BFF = 275 isolated PASS. API wheel lock SHA256 `399a4e796403bd8fc5b8165c030ad4d4d8479fb946e363e29a5722ea88d35ff5`.
- UI_F3 #60: exact tested/head 21fe24913f85cb9cc013ce01b1d5dbb4bc97774f; GitHub run 45082202462, 112 Node, lint/typecheck/build and Chromium **fixture-only**, not Mac.
- UI branch diverged from API61 after API7c6 common ancestor. We preserve API61 final schema, API no-dispatch gate/receipt, signed GET and tests. UI60's `product-chat.tsx` supersedes API's older chat composition, but cannot replace API security modules, JSON schema or API tests. This decision is pinned in `integration/F3_COMPLETION_SOURCE_PINS.json`.
## Explicit hazards and gates
- This is NO_DISPATCH_ONLY. The signed sources DTO presents C018 observed chunk/source IDs with `UNVERIFIED` provenance, no fabricated URL/attribution, no product Answer generation.
- Only an actual Mac stack with approved PKI/DB/engine/C018 and separate central gate could attest UI -> real C018, same-Attempt source rows, Refresh GET only, user B 404 and generation_calls 0.
- No GitHub CI run constitutes Mac installation, host UID/HOME/mount admission, live login or external TLS attestation. No existing Mac demo, host database, secrets, Arvan or model Gateway touched.
- Existing Foundation Docker ZIP f0e53e... packages OLD source 0c0a... and must be repinned before Build.
- ENGINE lock/wheelhouse not attested here; never regenerate from guessed versions. Startup errors require actual redacted Ops log and code fix with clean-install retest. DB 011 excluded from first No-Dispatch install.
