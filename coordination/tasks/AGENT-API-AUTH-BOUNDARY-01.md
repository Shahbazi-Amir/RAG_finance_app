# AGENT-API-AUTH-BOUNDARY-01 — cumulative documentation-only execution ledger

**Status:** READY_FOR_REVIEW — AUTH_SESSION_BOUNDARY proposed, **SUPERVISOR_PENDING**; IMPLEMENTED=DESIGN_DOCUMENT_ONLY, TESTED=STATIC_DOCUMENT_INVARIANT_CHECKS_ONLY, ACCEPTED=NONE. Product/Auth security and Integration tests ALL NOT_RUN.

## BND-01-A — real handoff/preflight, 2026-11-09

- Repository writable: Shahbazi-Amir/RAG_finance_app **only**. Source RAG_finance and parent AI-Agent-projects strictly read-only.
- Starting main and exact HEAD verified: **97293558bc80953bd88e98e81166a8da745a2207**. PR #13 Closed/Merged; Accepted head 975062681e8124e65f72cda3338cf4cfa4a3c782; merge SHA equals Starting main. No unmerged PR13 work should be redone. Proposed branch prep/auth-session-boundary did not exist and was created from exact Starting commit. docs/adr/0005-auth-session-boundary.md and this mission task did not exist; no same-name ADR collision.
- Read AGENTS.md, coordination/ownership.md, ADR 0004, coordination/open_decisions.md, cumulative coordination/tasks/AGENT-API-AUTH-IDP-01.md, canonical checklist and pinned references/phase2/roadmaps/RAG_finance_phase3_modular_execution_plan.md. Shared docs/checklist edit explicitly granted ONLY for this mission; permanent Foundation ownership unchanged.
- Target roadmap Module 05 L299-L316: P3M05-A03 session rotation, A04 cookie, A05 CSRF, A07 logout/revoke, A08 expiration/refresh, A09 secret-free events, A10 session theft/replay; A06 test-only behavioral lockout context. Module 03 L217-L253 error/schema/trace/contracts; Module 06 L324-L344 RLS/transaction owner/cross-user; Module 13 L503-L535 endpoint authorization. No Gate tick.
- PR13 bounded evidence: Keycloak 26.8.2 synthetic CI [Run 42617144329](https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/42617144329) success; tested source 835bd417ede49184caa93f36bbfcc8d7bac12a3a. After Reset old browser SSO+old refresh+old UserInfo still allowed (200), old JWT locally valid. Separate admin-initiated logout refresh=400, UserInfo=401 but local JWT signature valid before expiry. A/B/C real CI evidence does NOT test BFF session/CSRF/RLS/Production.
- Verified checklist **262 unique P3Mxx-Ayy**, **105 unique P3OPxx-Ryy**, **zero checked activity/Gate boxes** at baseline, 26 independent module gates (to be reverified after change). No unaccepted Gate updated.

## BND-01-B — official Keycloak 26.8.2 support, what is verified vs missing

Official checked 2026-11-09:
- [26.8.2 Server Administration Guide](https://www.keycloak.org/docs/26.8.2/server_admin/) names Update Credential (password/OTP), deprecated Update Password, Email Event Listener and Admin Events; does not itself demonstrate guaranteed Product delivery.
- [26.8.2 Server Developer Guide](https://www.keycloak.org/docs/26.8.2/server_development/) has Event Listener SPI and explicitly warns SPI is internal and may change after upgrades. Listener existence != atomic cross-DB Product revoke.
- [26.8.2 Admin REST](https://www.keycloak.org/docs-api/26.8.2/rest-api/index.html) documents POST /admin/realms/{realm}/users/{user-id}/logout (delete all user sessions and notify configured clients). This is an additional API action, not evidence that all reset methods invoke it.
- [Official OIDC endpoints](https://www.keycloak.org/securing-apps/oidc-layers) distinguish logout, revoke, UserInfo and JWT lifetime.
**NOT_VERIFIED:** persistent event capture with authenticated bounded delivery covering Admin REST, Account Console, required actions and user self-service; exact credential revision mapping; strong reconciliation under event loss; genuine post-reset reauthentication proof; immediate all-session cutoff. These require new separately authorized IdP integration tests and ops review. No production guarantee invented.

## BND-01-C — proposed design and ownership decisions, no runtime action

- [ADR 0005](../../docs/adr/0005-auth-session-boundary.md) specifies UI-owned Next BFF callback/session routes under apps/web/app/api/auth/**, FastAPI identity trust under apps/api/** + src/phase3/auth/**, DB-controlled owner/session/epoch under src/phase3/storage/postgres/** and infra/postgres/migrations/**, Foundation cross-component tests in tests/phase3/integration/cross_component/**. No parallel session-store directory or product schema fork created.
- Session: opaque HMAC-hash reference, durable server-side epoch+revoke, unique (issuer,subject) owner; CSRF/Origin/secure cookie/expiry/rotation; signed short-lived service assertion + private authenticated network; default-deny FastAPI and RLS non-BYPASS. Admin product role distinct from Keycloak realm management.
- Reset: product-initiated revocation BEFORE issuing link, per-user reset gate and mandatory fresh authentication; independent authoritative IdP credential change proof/epoch; callbacks and refresh CAS fenced. IdP event/outbox + reconciliation design is **conditional**, not a Keycloak 26.8.2 product capability claim. Under untrusted or missing events, fail-closed; outside-product reset **has no demonstrated finite guarantee**. The suggested 30-second delivery SLO is a future test target, not acceptance; old-session reuse from PR13 makes this a launch blocker.
- Future packages DB / IdP proof / API-BFF / UI / Integration have ordered dependencies, unique ownership and BND-T01..T10 NOT_RUN acceptance tests. No UI/API/DB/migration/code changes here.
- App/Provider selection, hosting, ops, SMTP, costs, Iran access, NB23 and Module00 unchanged/unapproved.

## BND-01-D — exact documentation checks, evidence and handoff

Changes permitted **only**:
1. docs/adr/0005-auth-session-boundary.md (NEW);
2. coordination/tasks/AGENT-API-AUTH-BOUNDARY-01.md (THIS cumulative file, NEW);
3. coordination/open_decisions.md (append-only scoped proposed decision section);
4. coordination/phase3_checklist.md (only Evidence column of selected existing activity rows plus one bounded PR13 evidence row under limited baselines).

Reproducible static checks on content before Push (no Code/Containers/API/Model):
- Compare all 262 unique activity IDs, all 105 operational requirement IDs, 26 independent Gate markers and total checked boxes pre/post; **must be unchanged**.
- For each touched activity row compare columns through Accepted byte-for-byte and preserve original evidence text; no activity/Gate State, Implemented, Tested, Accepted or checkmarks modified.
- Verify no altered path besides the four allowed, no newly created parallel Auth/Schema/Workflow/Migration.
- GitHub compare exact starting commit with mission head; Draft PR remains unmerged and source repos untouched. Future BND-T01..T10 tests explicitly NOT_RUN.
- Final commit/source SHA is obtained from Git history (not stored inside its own file); append future meaningful checkpoints to THIS SAME task file. No per-command reports.

**Review blockers:** supervisor design signoff; credible IdP credential epoch/atomic event coverage and bounded reset revocation **not proven**; real owner mapping/session store/BFF trust and integration not implemented; all full M05/M06/M13 Gates NOT_ACCEPTED. No deployment, SMTP, purchase, credentials, container, model or external service was executed.

**Delivery:** READY_FOR_REVIEW — AUTH_SESSION_BOUNDARY, documentation-only PR kept Draft; Merge only by supervisor.

## CONTROLLED-RESET-PLAN-01 / CRP-01-A — confirmed baseline and narrow authority (2026-11-11)

- **Starting main** `6d7ad5320267e4a10a0bf458f954023f89a25d8c` independently matched live main. PR #23 merged/closed, merged commit exactly same `6d7ad5320267e4a10a0bf458f954023f89a25d8c` with head `8546e4dcfcf7d2f38e02379a513f976923cd4caa`. Existing main ADRs numbered 0001..0005; no ADR 0006 collision. No existing `prep/controlled-reset` branch, matching open PR or `reset_operation`/credential_epoch implemented work found in checked branch/PR/default-branch code searches (not a claim about inaccessible external/private work).
- **Source-of-truth:** ADR 0005 (PROPOSED), `src/phase3/storage/postgres/AUTH_SESSION_INTERFACE.md`, `SERVICE_REPLAY_INTERFACE.md`, `src/phase3/auth/SERVICE_TRUST_INTERFACE.md`, `auth_session.py`, `service_replay.py`, `transactional_admission.py`, Migrations 003/004/005, `coordination/ownership.md`, checklist and PR23 cumulative IDP checkpoint.
- **Evidence:** [PR23 merged](https://github.com/Shahbazi-Amir/RAG_finance_app/pull/23), [PR CI 42923509560](https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/42923509560), [clean artifact](https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/42923509560/artifacts/13811749362), [red transition artifact](https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/42923509560/artifacts/13812198795). Clean PROVEN only synthetic new Realm; old flows NOT_PROVEN. Product Session/Gate untested/unaccepted.
- **Trace:** P3M05-A03/A04/A05/A07/A08/A09/A10; P3M06-A03/A05/A07; P3M13-A03/A07/A08/A09/A10, plus P3OP03 non-counting overlay. No canonical ID duplication, checkmarks or Gate modifications.
- **Decision:** A Reset design MUST use authorization-before-DB revoke-before-IdP mutation, two distinct recovery/session proof paths, strict unknown outcome gate, durable per-owner op/CAS, fresh credential proof before Gate open. `finish_simulated_reauth` only CI. Original product code does NOT implement this.
- **Implemented:** proposed [ADR 0006](../../docs/adr/0006-controlled-reset-execution-plan.md), this cumulative ledger append, open decision list, and evidence/dependency-only selected checklist rows. **No product code, Migration, public DTO, workflow, SPI/outbox, mail, deployment or merge.**
- **Static verification method:** compare GitHub base tree and branch diff; check only four authorized file paths; compare checklist checkbox count, canonical P3Mxx/P3OPxx IDs, 26 Gate markers, and per-row columns except Evidence byte-for-byte; search for changed status fields; inspect every new test ID CR-T01..T14 as `NOT_RUN`. Actual execution of schema/code/integration tests **NOT_RUN**.
- **Remaining blockers:** Supervisor acceptance CR-D01..CR-D06, fresh-auth guarantee and unknown-IdP outcome, validated per-user FGAP provisioner & admin emergency controls, DB/API/UI owner assignments and full Product integrated security tests. **Accepted NONE / SUPERVISOR_PENDING**.
- **Delivery:** READY_FOR_REVIEW — CONTROLLED_RESET_EXECUTION_PLAN. The final commit's own SHA is evidenced by GitHub PR/commit, not inserted into this document.


## CR-API-03A / C1D-A — independent scoped dispatch adapter and isolated harness (2026-11-11)

**Preflight:** exact live `main=93c323119e743ffb795a0da0c20ea44b7cd66257`, PR #25 CLOSED/MERGED with this exact merge SHA. Proposed new branch `agent/api-reset-c1-dispatch`, no prior matching branch, open PR or existing reset-dispatch adapter found in checked repository searches. Read merged [ADR 0006](../../docs/adr/0006-controlled-reset-execution-plan.md), [RESET_C1_INTERFACE](../../src/phase3/storage/postgres/RESET_C1_INTERFACE.md), immutable Migrations 003–006, role-specific `reset_c1.commit_c1`, existing 004 session fencing, FGAP v2 Clean Bootstrap source and [PR #23](https://github.com/Shahbazi-Amir/RAG_finance_app/pull/23). Version pins: Keycloak **26.8.2**, two independently disposable PostgreSQL **17.11** services (one Product + one Identity), Mailpit **1.32.0**, Playwright/Chromium **1.64.1**, isolated internal-only Docker network.

**Trace (non-counting):** CR-API-03A, roadmap Module 05 P3M05-A03/A07/A08/A09/A10, Module 06 P3M06-A07 and Module 13 P3M13-A07/A08; P3OP03 is only an operational overlay. No canonical checklist or Gate modification.

**Authorized exact file list announced before changes:**
1. `src/phase3/auth/reset_c1_dispatch.py` — new, **internal** transactional orchestration; no public API.
2. `tests/phase3/integration/api/reset_c1_fixture.py` — new, **independent CI-only** `auth_reset_issuer` role and disposable 003–006 migrations; Product/IdP synthetic fixtures.
3. `tests/phase3/integration/api/test_reset_c1_dispatch.py` — new, isolated real PostgreSQL and Chromium Keycloak tests.
4. `infra/auth-ci/compose.reset-c1.yml` — new, only additional Product PostgreSQL service (unchanged existing Identity DB and Keycloak compose).
5. `infra/auth-ci/Dockerfile.reset-c1-runner` — new, extends pinned existing IdP runner with pinned psycopg binary.
6. `.github/workflows/reset-c1-dispatch.yml` — new, separate Draft-PR/push CI, no published ports, outbound denial, explicit teardown, scrubbed artifacts.
7. `coordination/tasks/AGENT-API-AUTH-BOUNDARY-01.md` — this cumulative checkpoint append.

**Boundaries / design:** Fixture issues synthetic authorization *on a separately authenticated PostgreSQL issuer connection*. Runtime Adapter only uses `auth_reset_executor` with a real **outer** PostgreSQL transaction and accepted `commit_c1()` SQL; a successful SQL receipt before COMMIT is not permission to call IdP. `transport.send_reset()` invoked at most once ONLY after the entire transaction context exits successfully. Operation ID and consumed authorization cannot re-dispatch because current 006 CAS + single active owner operation deny a second C1. New password remains in short-lived Python RAM and the single outbound Keycloak JSON body; no queue, ledger payload, persistent retry or logging. The IdP client has only account-specific standard FGAP v2 `reset-password` (no broad manage-users). C1 always leaves the Product Gate `pending_reauth` with session epoch incremented; **never** attempts C2 or simulated gate open.

**Status classification:** a 204 is only `OBSERVED_REMOTE_SUCCESS` **in this process**, NOT durable `IDP_CONFIRMED`; HTTP definitive denial is `REMOTE_REJECTED`, timeout/lost response or other ambiguous status is `REMOTE_UNKNOWN`; none has persistent IdP Attempt/Outcome storage. A simulated stop after C1 commit (before network) leaves committed revocation and no dispatch. A real IdP write whose response is lost is still `REMOTE_UNKNOWN`; no automatic retry and no cross-PostgreSQL atomicity. Completion, reconciliation, durable retries and fresh reauth remain separate future authorized packages.

**Planned actual CI cases:** CR-A00..16 (CI-specific, noncanonical): role/migration boundary, fresh FGAP readback, real pre-login, no pre-COMMIT Reset, rollback/no Reset, real C1+IdP 204+old/new Chromium, both old Product Session admissions denied, consumed proof/op_id denied, two executor-connection race one dispatch, scoped non-target/profile 403, injected timeout/disconnect, post-COMMIT-before-PUT process stop, REAL write with lost response → UNKNOWN and no retry, no credential payload columns and every C1 Gate pending. **Before the first GitHub Run, all new CR-A tests are NOT_RUN.** All prior IdP test files/Regression behavior and migrations are left unchanged.

**Implemented:** bounded seven-file source/CI/checkpoint only; **Tested:** CI_PENDING for this first push; **Accepted:** NONE / SUPERVISOR_PENDING. C1's prior DB-only acceptance does NOT approve this Adapter or Product Auth. **No C2 / AUTH_PRODUCT_ACCEPTED / Module Gate PASS / Deployment / Merge.**

**Exact reproducible check:** GitHub Draft PR CI `reset-c1-dispatch.yml`, dedicated runner builds pinned image before internal-only networking, dynamically provisions non-BYPASSRLS issuer/executor roles and applies unmodified 003–006 on disposable Product PostgreSQL; performs real Chromium+FGAP calls against separately pinned disposable Keycloak/Identity PG, injects crash and connection failures, uploads only sanitized case outcomes; runner destroys both volumes. Final tested SHA/Run IDs and failures require a subsequent factual checkpoint after execution; no preemptive PASS claim.


### CR-API-03A / C1D-B — first real CI and narrow fixture repair (2026-11-11)

**Tested candidate:** source `00c53ea8c54a1bbfc6b49aca5f775871864770ff`, actual [GitHub Run 42934840014](https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/42934840014), job `130242219185` **COMPLETED FAILURE** at `CR-A00-product-database-versioned-migrations`, sanitized [artifact 13817098671](https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/42934840014/artifacts/13817098671). FOUR pinned container/image/internal network/zero port/real egress-denial tests passed, and unconditional Product+IdP container/volume teardown passed. Actual test exception type `UndefinedObject` during Product 003–006 schema bootstrap; no Keycloak Reset requests or successful C1 claimed.

**Root-cause from immutable Migration 003 SQL:** its final explicit `REVOKE ... FROM PUBLIC,history_app,...` requires the `history_app` role to exist. The brand-new reset-only fixture did not provision this pre-existing baseline role. **Fix** only in `tests/phase3/integration/api/reset_c1_fixture.py`: provision a **NOLOGIN, NOSUPERUSER, NOBYPASSRLS** `history_app` placeholder before applying the unchanged migrations. Neither migration nor protected DB repository, existing IdP harness, public API, workflow or ADR is edited. **Retest pending exact new SHA.** Implemented fixture repair; Tested prior failure, new CI not yet observed; Accepted NONE.
