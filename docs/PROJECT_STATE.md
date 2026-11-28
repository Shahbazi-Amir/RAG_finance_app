# RAG Finance — Master Project State & Coordination

- **Last Updated:** 2026-11-28
- **Live Staging URL:** `https://ragfinance.ir` (SSH alias: `rag-finance-arvan`)
- **App Repo (Codex-1):** `/Users/macbookpro/AMIR_DATA/00_WORKS/01_PROJECTS/AI-Agent-projects/RAG_finance_app`
  - Active Phase 3 branch: `phase3/completion` (from `v0.1-arvan-100users-live`)
  - Live emergency hotfix branch: `deploy/arvan-100users-candidate`
  - Control Notebook (untracked): `/Users/macbookpro/AMIR_DATA/00_WORKS/01_PROJECTS/AI-Agent-projects/RAG_finance_app/docs/codex_execution/ops_control.ipynb`
- **Engine Repo (Codex-2):** `/Users/macbookpro/AMIR_DATA/00_WORKS/01_PROJECTS/RAG-projects/RAG_finance`
  - Active Branch: `rag-phase2`
- **Detailed Arvan Handoff:** `infra/arvan-staging/ARVAN_STAGING_HANDOFF.md`
- **Phase 3 Checklist & Decisions:** `coordination/phase3_checklist.md`, `coordination/OWNER_DECISIONS_20261126.md`

## 1. Priority Tracks (Strict Order & File Ownership)

| Priority | Track | Owner Agent | Repo / Allowed Paths | Status |
| :---: | :--- | :--- | :--- | :--- |
| **1** | **100-User Candidate + Repeatable Arvan Deploy** | Codex-1 | `RAG_finance_app`: `apps/web/`, `infra/arvan-staging/`, `tests/phase3/ui/` | Closed and frozen for the pilot (4 items delivered, 2 formally deferred, `deploy-arvan.sh` exercised, live #143 PASS) |
| **2** | **Engine Latency Optimization (Zero Recall Drop)** | Codex-2 | `/Users/macbookpro/AMIR_DATA/00_WORKS/01_PROJECTS/RAG-projects/RAG_finance` (and later `RAG_finance_app/infra/nb23-v4/` via separate PR) | Next (Step 1: frozen baseline Latency + Recall benchmark) |
| **3** | **Complete Phase 3 Roadmap Gates** | Codex-1 | `RAG_finance_app`: `apps/`, `src/phase3/`, `tests/phase3/` (after Track 1 merge) | App-only P3-00–P3-08 documented; P3-09 owner decisions recorded and isolated CI configured; Production: NO-GO |
| **4** | **Engine Score & Recall Upgrade (Danesh-Bonyan)** | Codex-2 | `/Users/macbookpro/AMIR_DATA/00_WORKS/01_PROJECTS/RAG-projects/RAG_finance` (corpus fixes, index, retrieval, formal evaluation report) | Pending Track 2 baseline |
| **5** | **Phase 4: Admin Panel + Measurement & Learning Loop** | Codex-1 & 2 | New Phase 4 modules after Phase 3 sign-off (use `git worktree` if concurrent) | Phase 4: LOCKED |

### Priority 1 freeze and Phase 3 transition

- **Frozen live candidate** — `v0.1-arvan-100users-live` → `4edadd3e784e1f9500dd9da8d4b6f6e40833cd13`. Annotated tag object `ebd0e6526b0d9578cf62167196577e7b5f2e81de`. Phase 3 starts directly from this tag. [Phase 3 audit](reports/SPEC-P3-00-phase3-audit.md)

- **Live #143 PASS on `ragfinance.ir`** — The updated `protected-profile-check.py` verified anonymous handshake rejection and an authenticated HTTP response on both private ports `18443` and `18444`. Live RS256, enforced PKCE S256, the exact callback and required 404 boundaries passed.
- **Delivered** — Keycloak logout cookie expiration, one-click CSRF-protected sidebar logout, the Keycloak theme fixes, and the chat/login palette and chart direction. The repeatable `deploy-arvan.sh` flow built and deployed the candidate from the offline cache. [Live verification report](reports/SPEC-01B-arvan-live-deploy.md)
- **DEFERRED — SMTP password reset** — After the pilot / Phase 4, once real user email addresses and SMTP settings are available. Authorized operators use manual Keycloak reset during the pilot.
- **DEFERRED — Corpus typo** — Correct `واریس` to `واریز` and rebuild the relevant index under Priority 4 in the engine repository, owned by Codex-2. [Arvan handoff](../infra/arvan-staging/ARVAN_STAGING_HANDOFF.md#3-remaining-backlog)
- Closing the pilot delivery scope does not certify a 100-user workload or accept a Phase 3 module gate.

### Phase 3 App-only handoff

- The original local audit sequence ended at SPEC-P3-08. The owner authorized SPEC-P3-09 separately for evidence collection on an isolated GitHub-hosted runner. Open checks remain prerequisites for acceptance. [Workflow](../.github/workflows/phase3-isolated-evidence.yml)
- The 26 independent Gate totals are **DONE 0 / PARTIAL 22 / PENDING 4**, with 16 producer-dependent labels overlapping those statuses. M24 and M25 remain PENDING. The frozen pilot's live #143 PASS remains scoped to that deployment.
- **SPEC-P3-10 CI reconciliation.** GitHub Actions run [46098376958](https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/46098376958) passed all four job definitions at `42b58e5e6f8a256d65dc11841737496d16b44b89`. The matrix remains **DONE 0 / PARTIAL 22 / PENDING 4**, including **16 EXTERNAL_DEP (Codex-2)**. **Production: NO-GO. Phase 4: LOCKED.** [Gate-by-Gate evidence](reports/SPEC-P3-10-ci-evidence-reconciliation.md)
- **SPEC-P3-11 App-only evidence and NB23-v4 pin.** The owner approved the App-only governance requirements and pinned the frozen NB23-v4 App-side integration. [Run 46102067648](https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/46102067648) at `aff653f8492f212aa602779a3c325e685b642f2f` finished 6/7 successful, including both PostgreSQL jobs. Trivy failed closed on HIGH/CRITICAL findings. **DONE 0 / PARTIAL 22 / PENDING 4 / WAIVED-TO-TRACK4 0**, including 16 producer-dependent Gates. **Production: NO-GO. Phase 4: LOCKED.** [Evidence and remaining criteria](reports/SPEC-P3-11-app-gates-closure-and-nb23-pin.md)
- Remaining local prerequisites include pinned Docker/PostgreSQL/Keycloak and Python/browser toolchains, same-SHA runtime/restore/load receipts, and owner decisions for SLO, UAT, risk and hypercare. Codex-2 owns the accepted engine Release and producer evidence. [App-only closeout matrix](reports/SPEC-P3-08-production-readiness-handoff.md) · [Production decision runbook](operations/phase3-production-readiness-handoff.md)

- **Owner decisions approved 2026-11-27.** امیر شهبازی آراللو (Primary Owner) covers Ops, Security, DBA, UAT, Release and Hypercare until the operations team is formed. **Production: NO-GO. Phase 4: LOCKED.** The frozen pilot tag remains in force.
- **Targets.** Monthly availability ≥99.5%, non-engine API p95 ≤500 ms, 5xx <1%, 100 invited users with at most 10 concurrent. PostgreSQL RPO ≤24 h with daily backup, then ≤15 min after PITR/WAL activation, and RTO ≤2 h.
- **Operating window.** Hypercare lasts 14 days after Go-Live, with P0/security initial response ≤30 min and P1 ≤4 h. Thursday/Friday 02:00–05:00 Tehran time. Immediate rollback on any #143 smoke failure or 5xx >2%. SMTP reset stays deferred to Phase 4 with manual pilot reset, and the corpus correction stays with Codex-2 under Priority 4. [Signed decisions](../coordination/OWNER_DECISIONS_20261127.md) · [P3-09 report](reports/SPEC-P3-09-owner-decisions-and-ci-runner.md)

## 2. Codex Account Isolation & Recovery

- **Codex-1 (Account 1):** Default profile `~/.codex`, working directory `/Users/macbookpro/AMIR_DATA/00_WORKS/01_PROJECTS/AI-Agent-projects/RAG_finance_app`.
- **Codex-2 (Account 2):** Isolated profile `CODEX_HOME=~/.codex-acc2`, working directory `/Users/macbookpro/AMIR_DATA/00_WORKS/01_PROJECTS/RAG-projects/RAG_finance`.
  - First-time login: `CODEX_HOME="$HOME/.codex-acc2" codex login`
  - Launch: `cd "/Users/macbookpro/AMIR_DATA/00_WORKS/01_PROJECTS/RAG-projects/RAG_finance" && CODEX_HOME="$HOME/.codex-acc2" codex`
- **Crash/Disconnect Recovery:** Run `git status` & `git diff --stat` in the repo's control notebook, reopen the same Codex profile in the same directory, and resume from the active `coordination/tasks/` spec.

## 3. Non-Negotiable Rules

1. **Zero Manual Server Drift:** Nginx, systemd units, Keycloak compose/theme, and realm-sync scripts must live in `infra/arvan-staging/` (zero secrets in git; secrets stay `0600` under `/etc/rag-arvan-candidate/`).
2. **Recall Guardrail for Speed Work:** No Track 2 latency change is accepted if frozen benchmark Recall regresses.
3. **Security #143 Lock:** Never relax mTLS, RS256, PKCE S256, `0600` permissions, or `404` blocks on `/internal/`, `/admin/`, `/realms/master/`, `/auth/`, and `idp-staging.ragfinance.ir`.
4. **Handoff Discipline:** Every finished task updates its spec and appends a 3-line summary here before pushing.

## 4. Gemini Chat Topology

- **00-Control-Room:** Cross-track priorities, branch merges, conflict checks, updating `docs/PROJECT_STATE.md`.
- **01-App-Arvan-Phase3:** Specs, reviews, and deploy commands for Codex-1 (Tracks 1 & 3).
- **02-Engine-Speed-DaneshBonyan:** Benchmark analysis, specs, and reviews for Codex-2 (Tracks 2 & 4).
- **03-Phase4-Panels-Learning:** Opens only after Track 3 is signed off.

## Next Arvan release performance queue

- **QUEUED — MANDATORY BEFORE NEXT ARVAN RELEASE** — Transfer the `Qdrant Snapshot Reuse` pattern to `infra/nb23-v4/` and finish UI polish before the next freeze tag, `v0.2-arvan-100users-fast`. Start immediately after the Phase 3 rail closes. The owner-supplied Codex-2 reference is `RAG_finance`, branch `bench/baseline-latency-recall` at `9d0c4471ed8dbcf15624d1402d9d601c01cb5b6d`, `SPEC-02C`, verdict `ADOPT_FOR_PRODUCTION_TRACK`, median reduction `9.57s`, `100/100` agreement and `0.0` Recall loss. SPEC-P3-12 leaves `infra/nb23-v4/` unchanged.
