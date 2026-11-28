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
| **3** | **Complete Phase 3 Roadmap Gates** | Codex-1 | `RAG_finance_app`: `apps/`, `src/phase3/`, `tests/phase3/` (after Track 1 merge) | Audit complete; proposed next SPEC-P3-01, subject to assignment |
| **4** | **Engine Score & Recall Upgrade (Danesh-Bonyan)** | Codex-2 | `/Users/macbookpro/AMIR_DATA/00_WORKS/01_PROJECTS/RAG-projects/RAG_finance` (corpus fixes, index, retrieval, formal evaluation report) | Pending Track 2 baseline |
| **5** | **Phase 4: Admin Panel + Measurement & Learning Loop** | Codex-1 & 2 | New Phase 4 modules after Phase 3 sign-off (use `git worktree` if concurrent) | Locked until Track 3 complete |

### Priority 1 freeze and Phase 3 transition

- **Frozen live candidate** — `v0.1-arvan-100users-live` → `4edadd3e784e1f9500dd9da8d4b6f6e40833cd13`. Annotated tag object `ebd0e6526b0d9578cf62167196577e7b5f2e81de`. Phase 3 starts directly from this tag. [Phase 3 audit](reports/SPEC-P3-00-phase3-audit.md)

- **Live #143 PASS on `ragfinance.ir`** — The updated `protected-profile-check.py` verified anonymous handshake rejection and an authenticated HTTP response on both private ports `18443` and `18444`. Live RS256, enforced PKCE S256, the exact callback and required 404 boundaries passed.
- **Delivered** — Keycloak logout cookie expiration, one-click CSRF-protected sidebar logout, the Keycloak theme fixes, and the chat/login palette and chart direction. The repeatable `deploy-arvan.sh` flow built and deployed the candidate from the offline cache. [Live verification report](reports/SPEC-01B-arvan-live-deploy.md)
- **DEFERRED — SMTP password reset** — After the pilot / Phase 4, once real user email addresses and SMTP settings are available. Authorized operators use manual Keycloak reset during the pilot.
- **DEFERRED — Corpus typo** — Correct `واریس` to `واریز` and rebuild the relevant index under Priority 4 in the engine repository, owned by Codex-2. [Arvan handoff](../infra/arvan-staging/ARVAN_STAGING_HANDOFF.md#3-remaining-backlog)
- Closing the pilot delivery scope does not certify a 100-user workload or accept a Phase 3 module gate.

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
