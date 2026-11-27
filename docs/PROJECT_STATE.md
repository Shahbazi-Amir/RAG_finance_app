# RAG Finance — Master Project State & Coordination

- **Last Updated:** 2026-11-27
- **Live Staging URL:** `https://ragfinance.ir` (SSH alias: `rag-finance-arvan`)
- **App Repo (Codex-1):** `/Users/macbookpro/AMIR_DATA/00_WORKS/01_PROJECTS/AI-Agent-projects/RAG_finance_app`
  - Active Branch: `deploy/arvan-100users-candidate`
  - Control Notebook (untracked): `/Users/macbookpro/AMIR_DATA/00_WORKS/01_PROJECTS/AI-Agent-projects/RAG_finance_app/docs/codex_execution/ops_control.ipynb`
- **Engine Repo (Codex-2):** `/Users/macbookpro/AMIR_DATA/00_WORKS/01_PROJECTS/RAG-projects/RAG_finance`
  - Active Branch: `rag-phase2`
- **Detailed Arvan Handoff:** `infra/arvan-staging/ARVAN_STAGING_HANDOFF.md`
- **Phase 3 Checklist & Decisions:** `coordination/phase3_checklist.md`, `coordination/OWNER_DECISIONS_20261126.md`

## 1. Priority Tracks (Strict Order & File Ownership)

| Priority | Track | Owner Agent | Repo / Allowed Paths | Status |
| :---: | :--- | :--- | :--- | :--- |
| **1** | **100-User Candidate + Repeatable Arvan Deploy** | Codex-1 | `RAG_finance_app`: `apps/web/`, `infra/arvan-staging/`, `tests/phase3/ui/` | Next (6 backlog items in `ARVAN_STAGING_HANDOFF.md` + `deploy-arvan.sh`) |
| **2** | **Engine Latency Optimization (Zero Recall Drop)** | Codex-2 | `/Users/macbookpro/AMIR_DATA/00_WORKS/01_PROJECTS/RAG-projects/RAG_finance` (and later `RAG_finance_app/infra/nb23-v4/` via separate PR) | Next (Step 1: frozen baseline Latency + Recall benchmark) |
| **3** | **Complete Phase 3 Roadmap Gates** | Codex-1 | `RAG_finance_app`: `apps/`, `src/phase3/`, `tests/phase3/` (after Track 1 merge) | Pending Track 1 completion |
| **4** | **Engine Score & Recall Upgrade (Danesh-Bonyan)** | Codex-2 | `/Users/macbookpro/AMIR_DATA/00_WORKS/01_PROJECTS/RAG-projects/RAG_finance` (corpus fixes, index, retrieval, formal evaluation report) | Pending Track 2 baseline |
| **5** | **Phase 4: Admin Panel + Measurement & Learning Loop** | Codex-1 & 2 | New Phase 4 modules after Phase 3 sign-off (use `git worktree` if concurrent) | Locked until Track 3 complete |

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
