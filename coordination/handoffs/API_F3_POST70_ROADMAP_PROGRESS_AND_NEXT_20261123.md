# API_F3 — Progress, done/remaining checklist, source receipts (2026-11-23)

> **Read this correctly:** The project is NOT 67% done. Historical API primary status was **61/91 PARTIAL** (started), **30/91 NOT_VERIFIED**. Neither counts as accepted. The directly tested subcase count increased from **10 to 11** with Draft #70; it does not represent fully completed rows.

## 1. Three distinct progress bars

| Measure | Completed-or-witnessed | Remaining to full criterion | Visual |
|---|---:|---:|---|
| API primary rows with at least PARTIAL implementation (historical snapshot) | 61/91 = **67.03%** | 30/91 NOT_VERIFIED = 32.97% | `█████████████░░░░░░░` |
| API primary rows with a *direct named limited L1 subcase receipt* | 11/91 = **12.09%** | 80/91 without new individually bound L1 cases = 87.91% | `██░░░░░░░░░░░░░░░░░░` |
| API primary fully accepted under whole row criterion | **0/91 = 0%** | **91/91 = 100%** | `░░░░░░░░░░░░░░░░░░░░` |
| Phase3 module Gates accepted in recorded evidence | **0/26 = 0%** | **26/26 = 100%** | `░░░░░░░░░░░░░░░░░░░░` |

The **262-activity whole-project** denominator includes **10 Module01 rows omitted from the user's 252-row visible table**. Snapshot for those 252 rows: **151 PARTIAL, 58 NOT_VERIFIED, 43 NOT_RUN**, fully checked **0 in that snapshot**. None of these counts should be extrapolated into other owners' current accepted work without a direct canonical registrar/decision receipt. P3OP 105 is a crosswalk/alias ledger, not 105 additional activities.

## 2. Real executable changes and their exact refs

| PR | Tested source SHA | Scope | Exact CI evidence | Accepted? |
|---|---|---|---|---|
| [#61](https://github.com/Shahbazi-Amir/RAG_finance_app/pull/61) | `c02ba7896edb78febd2042f7afb1243f2a6aca34` | Signed Send/History/Status/Get T1/T2, replay, no-dispatch; earlier 275 aggregate CI | [45081955496](https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/45081955496) | NO |
| [#63](https://github.com/Shahbazi-Amir/RAG_finance_app/pull/63) | `5d9df47c7ca52133ca8706bd748d535233bae050` audit | 262 activity / 91 API / 26 Gate audit ONLY | Markdown-only; no runtime CI evidence | NO |
| [#66](https://github.com/Shahbazi-Amir/RAG_finance_app/pull/66) | `fb4255e5703defe67e2de235ce0c19fdf7e98ea3` | Revoke-one route trusted TLS peer check before credential/DB, 3 targeted mock tests | [45210101448](https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/45210101448): 137 API +38 contract PASS | NO |
| [#68](https://github.com/Shahbazi-Amir/RAG_finance_app/pull/68) | `3ecbb53ce474a5e9250dacc34ffb5bca4fdfbeef` | Stream schema/FSM 15, private HTTP no-store 7, provisional Feedback/Delete request structural guards 16 | [45218211621](https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/45218211621): 159 API +54 contract PASS | NO |
| **[#70](https://github.com/Shahbazi-Amir/RAG_finance_app/pull/70)** | `0bdaf1b301ac38fb9428e645198556fac5c02394` | **New:** Send private TLS peer guard **before parsing question** + 4 tests, no real DB/IdP/Runner | [45219612634](https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/45219612634): **163 API +54 contract =217 unique PASS** | NO |

Source #70 is **stacked** over #68 → #66 → #61. The real Mac staging deployed SHA remains `NOT_OBSERVED`. Do not mistake CI source SHA for an integrated or deployed SHA. No part of this delivery performs network model calls, paid Generation, real PG migration, original Mac Docker restarts or Product T3.

### #70 defect precisely

Prior source `apps/api/product_session_api.py::session_send_message` invoked `history._read_body` before entering `_signed_history`, where private `allowed_peer(scope)` was already checked. Route-level *pre-parse* defense-in-depth was missing; this does **not** demonstrate missing outer ASGI mTLS transport. Now fail-closed with HTTP 401 and `Cache-Control: no-store` before reading private question; forged forwarded client-cert headers cannot pass. Four mock TestClient tests include positive trusted-entry-to-validation and negative spoof, overlong/invalid body, no-DB/no-auth-path case. Real signed mTLS+OIDC/PG still untested by API.

New individually tested limited subcase: `P3M05-A10`. Prior `P3M13-A08` and `P3M13-A10` gained Send asserts but were already counted in 10. Updated matrix now has **11/91** direct-limited rows, not 13/91.

## 3. Grouped checklist by API responsibility, acceptance remains OPEN

| Scope | Already implemented / source-level evidence | Still to implement or demonstrate before **acceptance** |
|---|---|---|
| **M03/05/06/13 — Auth, API and tenant** | OIDC/BFF signed assertion, restricted PG 004/005 synthetic logic; Revoke #66; Send pre-peer #70; exact-path, replay/idempotency code | Real OIDC HTTPS/BFF mTLS RS256 + two accounts, revoke-one/all and expired, RLS A/B/IDOR, approved auth method/cookie/CSRF, real Mac signed L2; each route full negative receipt |
| **M13/15 — History, no-dispatch** | T1/T2/202/replay, History and status/source GET L1; same Attempt and no-generation code | Real PostgreSQL + C018 one OS child, 200 replay, B=404, revoked=401, refresh GET-only, UNKNOWN/crash and no extra child, original Source metadata; NO_DISPATCH_ONLY |
| **M05/13/15/21 — Privacy lifecycle** | Feedback/Delete *provisional input validation*, no endpoints/side effects, canonical payload fingerprint L1 | CENTRAL versioned Consent+withdrawal, Feedback on accepted Answer, Source report, tombstones, retention/restore, DB/UI write contract and transaction/replay/400/401/404/409/UNKNOWN A/B tests; Export only upon approval |
| **M07/08/11 — Knowledge/Retrieval/Citation** | no-dispatch source receipt with UNVERIFIED locators and structural pinning | Accepted NB23 release hashes, source-specific C019/Locator/authority metadata, actual parity/retrieval/claim-level citation; verified attribution from original site/book/transcript |
| **M09/10/12 — Gateway/Answer/Safety** | Isolated Claim/test stub, source validation design, stream FSM (#68), no real T3 | Separate approved Provider/C019/DB011/cost/retention; real model Error/stream/cancel/UNKNOWN/Claim; Safety/no-answer/gold tests; no made-up citations and policy acceptance |
| **M17 — Abuse/cache/rate/cost** | Private HTTP no-store (#68), owner-bound stream invariants | Approved quota/rate/cost thresholds, cache release/policy/authority keying, cross-user cache/poisoning tests, load and cost measurements |
| **M16/19/20/21/23 — CI, Obs, Security, Staging, Load** | Reproducible source tests #61/#66/#68/#70, locked dependency CI | Real clean build/SBOM/image scan, redacted trace/alerts, full Mac service E2E, independent rollback/restore, approved SLO/load & security checks |

No owner should close a whole activity on a mock-L1 assert alone.

## 4. External owner handoff needed for complete Phase3 acceptance

1. **FOUNDATION/Ops (P0):** publish exact integrated candidate SHA and Docker image digest, private Mac resource/name/port/volume isolation, original signed client identities, real IdP, PG role and TLS proof; run exact 202/T1/T2/C018 single-OS-spawn/GET refresh/replay/Owner B/revoke/UNKNOWN/T3=absent with sanitized timestamp and linked outcome. Do not modify legacy Docker.
2. **CENTRAL + Product Privacy (P0):** make a dated approval for consent version/withdrawal, real feedback, source reports, deletion/retention/restore and conditional export; authorize/deny generation separately with cost and security ceilings. API cannot invent decisions.
3. **DB owner (P0):** approve 004/005 auth admission + PG grants, account deletion transaction, idempotency and replay states; separately decide whether 011 external Claim is installed and provide isolated PostgreSQL A/B/restore proof.
4. **UI owner (P0):** match v1 DTOs, stream cancellation vs backend cancellation, forwarded signed headers, error cache no-store, real two-user browser Refresh tests.
5. **ENGINE/Phase2 (P0):** accepted NB23 manifest+hashes, genuine C018 one-child proof, independently verified C019 producer/citation locator + source-authority mapping; no premature `LIVE_VERIFIED`.
6. **CENTRAL/Release/Ops (P1):** threshold freeze, accepted security/scan/SBOM, restore, load/SLO, UAT, signed Go/No-Go; production and Hypercare only after preceding accepted Gates.

## 5. Next independent development and verification order

- Expand line-by-line [91-row source matrix](./API_F3_91_ROW_L1_SOURCE_MATRIX_20261123.csv), record all missing per-ID executable asserts while existing evidence remains live. **Currently 11 directly attested limited L1 subcases, 80 not newly individually attested**. Each row's `accepted` remains NO.
- Execute real isolated integration once Foundation publishes exact pinned CI candidate; route-level no-store and Send/Revoke peer guards must stay on; no network-Gateway until separate approval.
- Implement real Consent/Feedback/Delete only after exact DB/UI/CENTRAL contract version is accepted; don't use mock fixture as real user Answer.
- Next deliverable must be a source file, a reproducible CI result or a real host receipt—not percentage changed by prose.

## 6. Completion definition

**API done** only when **91/91** primary criteria are met with owner-specific reproducible and environment-scoped evidence and CENTRAL accepts them; **whole phase3 done** only when canonical **262** activities and **26 Gates** are accepted after release, staging, security, performance, production Go/No-Go and Hypercare. This cannot be claimed on current evidence or completed by API-only source edits.
