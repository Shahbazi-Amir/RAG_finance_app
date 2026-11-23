# RAG_finance_app — Phase3 API progress bars, accomplished work, remaining execution checklist (2026-11-23)

**Accounting is exact; NEVER reinterpret PARTIAL as DONE.**

## A. Primary API roadmap, by the original 91 IDs

Historical/source starts: **61 PARTIAL (67.03%)**, **30 NOT_VERIFIED (32.97%)**; accepted primary rows **0/91 (0%)**. The latest audit ledger captures **16/91 (17.58%) named directly tested *limited L1 subcases***, leaving **75/91** without *new individually bound* tests from the API turns, which does NOT erase earlier aggregate CI. These subsets overlap; never add 67.03% and 17.58% or treat 16 limited L1 subcases as completed rows.

```text
Partial implementation started       61 / 91  67.03%  █████████████░░░░░░░
Individually bound limited L1         16 / 91  17.58%  ████░░░░░░░░░░░░░░░░
Entire API row acceptance             0 / 91   0.00%  ░░░░░░░░░░░░░░░░░░░░
Module gate acceptance                0 / 26   0.00%  ░░░░░░░░░░░░░░░░░░░░
```

| API primary module | ID count | Starting PARTIAL | Starting NOT_VERIFIED | Direct *L1 subset* cases now | Fully accepted |
|---|---:|---:|---:|---:|---:|
| M05 Auth/Session | 10 | 10 | 0 | 2 | 0 |
| M07 Knowledge Release Loader | 10 | 10 | 0 | 1 | 0 |
| M08 Retrieval Runtime | 10 | 10 | 0 | 1 | 0 |
| M09 Model Gateway | 10 | 0 | 10 | 1 | 0 |
| M10 Answer Orchestration | 10 | 10 | 0 | 2 | 0 |
| M11 Citation & Attribution | 11 | 11 | 0 | 2 | 0 |
| M12 Safety/No-answer Policy | 10 | 0 | 10 | 1 | 0 |
| M13 Product API | 10 | 10 | 0 | 5 | 0 |
| M17 Cache/Rate/Cost | 10 | 0 | 10 | 1 | 0 |
| **TOTAL** | **91** | **61** | **30** | **16** | **0** |

Whole Phase 3 denominator **262 distinct P3M activities**, **26 independent Gates**; the user-delivered view includes **252** (151 PARTIAL, 58 NOT_VERIFIED, 43 NOT_RUN) and omits Module01's **10** tasks. The Foundation P3OP 105 IDs are crosswalk aliases, not extra tasks. Any unobserved other-owner acceptance must be checked at CENTRAL; source CI and API-only notes cannot sign off on it.

## B. Real source delivery by chronological PR (all Draft, no merge/deploy)

| PR | Exact source tested | Code effect | Unique CI suite |
|---|---|---|---|
| [#61](https://github.com/Shahbazi-Amir/RAG_finance_app/pull/61) | `c02ba7896edb78febd2042f7afb1243f2a6aca34` | Signed Send, 004/005 role+session fencing, T1/T2, History/status, no-dispatch, refresh/replay | [45081955496](https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/45081955496) **275 old combined** |
| [#63](https://github.com/Shahbazi-Amir/RAG_finance_app/pull/63) | `5d9df47c7ca52133ca8706bd748d535233bae050` | 262/91/26 audit-only, NO runtime addition | audit, not acceptance |
| [#66](https://github.com/Shahbazi-Amir/RAG_finance_app/pull/66) | `fb4255e5703defe67e2de235ce0c19fdf7e98ea3` | Revoke-one early trusted TLS peer requirement; 3 stub tests | [45210101448](https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/45210101448): 137 API +38 contract |
| [#68](https://github.com/Shahbazi-Amir/RAG_finance_app/pull/68) | `3ecbb53ce474a5e9250dacc34ffb5bca4fdfbeef` | Stream ordering, private no-store HTTP, provisional Feedback/Delete input validation | [45218211621](https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/45218211621): 159 API +54 contract |
| [#70](https://github.com/Shahbazi-Amir/RAG_finance_app/pull/70) | `cf8f1fb8af073cacfd2b0409cda64f345c247761` (post-test docs) | Send private TLS peer requirement BEFORE question parser, 4 mock tests | [45219612634](https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/45219612634): 163 API +54 contract |
| **[#71](https://github.com/Shahbazi-Amir/RAG_finance_app/pull/71)** | `33998afa7f2db374854eed03835178ab81b4f7ce` exact final tested HEAD | **Claim↔Citation graph reciprocal ID verification** before synthetic Product T3. Broken graph marks failed attempt, must never call finalize_t3. Structural only, source authenticity NOT_VERIFIED | [45221567236](https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/45221567236): 177 API +54 contract **PASS** |
| **[#72](https://github.com/Shahbazi-Amir/RAG_finance_app/pull/72)** | `633c515ed392c9e767771ab4620aef1292dfe307` first tested source | Reject duplicate ranked C018 chunk IDs on ingest/ledger replay and reconcile valid source receipt count with C018 summary. Preserve UNVERIFIED fallback with no rows. 10 new negative/positive tests | [45223379162](https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/45223379162): **187 API +54 contract =241 unique PASS** |

These stacked PRs have base chain **#61 ← #66 ← #68 ← #70 ← #71 ← #72**. #64 Foundation latest integrated source has NOT been shown to contain #70/#71/#72. Deployed Mac SHA **NOT_OBSERVED**. Any green GitHub Actions tests are offline **L1**, not signed real Mac **L2**. Do not claim CI "synthetic origin" to be genuine Phase2 producer provenance.

## C. Remaining checklist by executable paths and external hold

| Path | Completed executable groundwork | Remaining unclosed criterion and next owner |
|---|---|---|
| **M05/M06/M13 Auth+tenant** | Signed JWT/BFF, PostgreSQL 004/005 fixture, Revoke TLS check #66, Send TLS check #70; negative L1 | Real OIDC, HTTPS mTLS+RS256, two independent users, revoked/expiry, replay fence, role/RLS bypass and 404/401, signed Mac host trace; **Foundation/Ops+DB+UI** |
| **M13/M15 T1/T2 no-dispatch** | Send and owner-scoped History/status/retrieved-sources, GET no-dispatch, same Attempt, T1/T2 L1 | Actual Mac PG, one OS C018 child, top10=10, 202/200/404/401, zero generation/T3, no duplicate on GET/replay, UNKNOWN/crash; **Ops+ENGINE** |
| **M05/M13/M15 Privacy lifecycle** | Feedback/Delete strict Product v1 client-intent DTO validation and semantic digest only | Approved real Consent/withdrawal, Feedback linked to authorized Answer, source-report, Delete/retention/tombstone/restore, conditional Export, atomic DB side effects, A/B+409/UNKNOWN, signed UI; **CENTRAL+DB+UI** |
| **M07/M08 Release+retrieval** | Pinned C018 preflight and UNVERIFIED retrieved-sources; no production retrieval dispatch | Accepted Phase2 NB23 and Gate00, release manifest and hashes, genuine source-specific C019/Locator, Qdrant release parity, rollback/readiness and golden tests; **ENGINE+Foundation** |
| **M09/M10 Gateway+orchestration** | Synthetic 011 claim rehearsal, no-dispatch anti-double-send, client stream shape, Claim–Citation crosslink graph | Provider decision, explicit model/cost/security/retention permission, accepted C019 and 011 roles, real stream/T3 and timeout/reconcile, source-authenticated production Answer; **CENTRAL+ENGINE+DB** |
| **M11/M12 Citation/Safety** | Schema fields split author/editor/speaker; #71 structural graph verification, UNVERIFIED does not become citation truth | Real source records, Authority/Locator checks, no invented attribution or link, source-aware Claim evidence and red-team/no-answer calibration; **ENGINE+UI+Policy owner** |
| **M17 Abuse/cache/cost** | Private API no-store all HTTP statuses #68, early Send rejection #70 | Approved rate/quota/cost thresholds, release-bound cache keys, cross-user poisoning, backpressure and measured budget; **CENTRAL+Ops** |
| **Shared M03/04/14/16/19/20/21/22/23** | API source/contract L1 tests, UI source and DB isolated owner receipts from earlier refs | Integrated exact SHA, authentic Mac DB+IdP/browser, SBOM/security/secret scans, redacted trace/alert, backup+restore, load/SLO and UAT; **Foundation+UI+DB+Ops** |
| **M24/25 downstream, shared** | No launch claimed, Phase4 namespace remains design only | Signed Go/No-Go, Production controlled rollout, Hypercare/incident metrics, closure after all prior Gates; **CENTRAL+Ops/Employer** |

## D. Concrete next action gate and no-authority zone

1. **API owner independent now:** all missing per-ID negative+positive source tests (75 IDs currently without new individually attributable limited L1), no mutation to accepted schemas, maintain exact pinned CI.
2. **Foundation/Ops:** isolate current source sha with UI #65 and DB #59 on an approved candidate Mac namespace; capture sanitized runtime/OS/HTTP/DB evidence tied to image/source sha. No legacy stack impact.
3. **CENTRAL+DB+UI:** approve one versioned Consent/Feedback/Delete/Retention transaction; only then implement real endpoints and migrate/verify restore safely.
4. **ENGINE+Phase2:** release accepted NB23 and genuine C019/Locator; no `LIVE_VERIFIED` without this.
5. **CENTRAL cost/security:** separate explicit permission before Gateway/model generation or DB011/T3 production, then benchmark, security, stage and Go/No-Go.

**Current acceptance**: API **0/91**, Gates **0/26**. This turn: 14 → 16 direct-limited L1 row IDs (**+2/91, +2.20 percentage points**) and 231 → 241 unique passing tests (**+10**); **0/91 remains fully accepted**. **Full completion cannot be performed by the API-only Draft code lane without the external artifacts/approvals above.** All unchecked rows remain open and have owner/criteria/next action in the [live 91-row matrix](./API_F3_91_ROW_L1_SOURCE_MATRIX_20261123.csv).
