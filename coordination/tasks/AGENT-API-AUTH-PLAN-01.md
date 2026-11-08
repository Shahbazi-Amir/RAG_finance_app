# AGENT-API-AUTH-PLAN-01 — cumulative checkpoint and controlled Auth decision proposal

**Current mission state: READY_FOR_DECISION — NOT AUTH_ACCEPTED; NOT IMPLEMENTED.**
**Date of baseline, official research and checklist reconciliation:** 2026-11-08. **Repository:** Shahbazi-Amir/RAG_finance_app.
**Starting Commit / confirmed actual main HEAD:** `9d5f2f9adc8e4522ec8cf4ffd397ba0a815e8fb7` (same exact PR #11 merge commit). **New branch:** `prep/auth-decision` created at this SHA, no pre-existing branch. **ADR numbering:** 0003 already exists as `docs/adr/0003-history-persistence-proposal.md`, PROPOSED/NEEDS_API_DB_REVIEW. `docs/adr/0004-auth-options.md` did not exist at Starting SHA; no parallel ADR/renumbering created.

## AUTH-PLAN-01-A — preflight and source ownership

Read-only verified before edit: `AGENTS.md`, `coordination/ownership.md`, the canonical `coordination/phase3_checklist.md`, `coordination/open_decisions.md`, ADR 0001, ADR 0003, five pinned source roadmaps and their roadmap activities, all three historical PR metadata/acceptance, and merged cumulative DB/API/UI task records. This task alone has **supervisor-authorized temporary permission** to write three Foundation-owned shared paths `docs/adr/0004-auth-options.md`, `coordination/open_decisions.md`, `coordination/phase3_checklist.md`. It does not confer permanent Foundation ownership or allow any other file/code change.

Module references **from real original roadmap, not guessed IDs**:

- Module 04 `P3M04-A02` (PK/FK/Index), `A06` (migration forward/rollback), `A07` (empty/populated migration testing), PostgreSQL subset;
- Module 05 `P3M05-A01` (employer choice), `A02` password hashing if password-based, `A03` session rotation, `A04` secure cookies, `A05` CSRF, `A06` lockout, `A07` logout/revoke, `A08` expiry/refresh, `A09` security events, `A10` session theft/replay (none implemented, tests NOT_RUN);
- Module 06 `P3M06-A01/A02/A03/A07` (RLS enablement/read-write policies/secure transaction context/Repository access checks);
- Module 13 `P3M13-A01/A02/A03/A04/A06/A07/A08/A09/A10` (versioned OpenAPI/size validation/error/pagination/idempotency/trace/endpoint Auth/contract/abuse); 
- Module 14 `P3M14-A01` Login Session UI **NOT_STARTED**, `P3M14-A02/A03/A09/A10/A11/A12` History list/responsive chat/retry/accessibility/mobile/no debug (only bounded fixture tests);
- Module 15 `P3M15-A01/A03/A07/A10` immutable History, pagination, cross-user protection and duplicate write, limited synthetic coverage.
- ADR 0003 and `H-DEC-01` **remain proposals**. `P3OPxx-Ryy` overlays are source cross-references only; **not new progress**. Module 00, NB23, engine, full L1/L2/DB01-02 and Auth Gate NOT ACCEPTED.

## AUTH-PLAN-01-B — verified limited prior acceptance, no inherited Production acceptance

| PR / checked merge | Actual supervisor accepted HEAD; exact tested code and CI | Implemented subset / tested / accepted scope |
|---|---|---|
| [#9 DB History](https://github.com/Shahbazi-Amir/RAG_finance_app/pull/9), merge `09f109da40a4eb06aeff96a7e5458895bef18fab` | accepted `022f223c795c65c9707ed77c9064eff40183731c`; tested `4b235e8d75ad485d9464f238c98804e28a4874b4` at [Run 42411664049](https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/42411664049) | **Implemented:** History SQL 001/002, RLS, owner-scoped idempotency and synthetic T1/T2/T3 fixture. **Tested:** 13/13 actual disposable PostgreSQL 17.11 tests. **Accepted:** only bounded synthetic storage/test evidence; not real Auth, Backup/Restore or DB01-02/M04/M06/M15 Gate. |
| [#10 API History](https://github.com/Shahbazi-Amir/RAG_finance_app/pull/10), merge `ee415c9209fbc423ca6299ebb2021c446d1b7217` | accepted `0a4d2615f2aa29e9c9ac4277e1d54b724d69b8dd`; tested `278b0714cb03ab3994558504ab548a30d731c47e` at [Run 42468083901](https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/42468083901) | **Implemented:** five versioned FastAPI History routes, T1-only Send, limit/error/pagination/status and default 401. **Tested:** 38 shared contract + 20 HTTP/ephemeral PostgreSQL tests, **58/58**. Identity **only by dependency override inside tests**; no real session/auth, public API, full M13 Gate. |
| [#11 UI History](https://github.com/Shahbazi-Amir/RAG_finance_app/pull/11), merge/Starting main `9d5f2f9adc8e4522ec8cf4ffd397ba0a815e8fb7` | accepted `87e1908ff3891120f24cb15480a89a6b2ebfc2b6`; tested `d638d493b066335109ba791906a7a1a79d99cc0d` at [Run 42483223918](https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/42483223918) | **Implemented:** separate Mock and UI History client, CI-only loopback proxy + browser harness with synthetic actors. **Tested:** 80 UI Node, 38 contract, 20 HTTP/PostgreSQL plus two Chromium browser paths and actual screenshots. **Accepted:** isolated integration and bounded reviewed visuals only; not production Auth, proxy, full browsers/accessibility/L1/L2 or Gate. |

**Do not add 13+58+138 into a new progress count.** Contract/API suites repeat in #10/#11. The accepted heads differ from their tested code SHAs by documentation-only commits. User/supervisor limited acceptance of three merged PRs **does not** transfer to complete activity/Gate acceptance. Real external login, user consent, live model and data privacy/availability still missing.

## AUTH-PLAN-01-C — limited canonical checklist edit (Foundation exception)

Original `coordination/phase3_checklist.md` before editing: **262 distinct numbered P3M activities, 262 activity rows, 26 explicitly NOT PASSED independent Module Gates, 0 checked Gates, 105 distinct P3OP-R overlay IDs and 2 existing source_manifest.json references** (counts are direct textual consistency checks, not new Gate metrics). The precise prior roadmap mapping, owners, output/check description, activity ordering, row count and Gate text must be byte-for-byte preserved except scoped evidence/status columns.

Reconciliation is **26 existing activity rows with bounded PR evidence + one P3M05-A01 evidence-only link**; no new numbered activity/Gate/operational requirement and no completed gate. Changed subsets and actual decision logic:

| Existing canonical rows touched | Field meaning |
|---|---|
| P3M04-A02/A06/A07, P3M06-A01/A02/A03/A07 | review; limited PostgreSQL 17.11 and synthetic owner/RLS/migration evidence from #9; no real identity, backup or full Module04/06 |
| P3M13-A01/A02/A03/A04/A06/A07/A08/A09/A10 | review; limited product.v1/HTTP validation, pagination, 401/owner-injected tests from #10; **A08 real Auth/valid session** NOT_RUN; no Module13 Gate |
| P3M14-A02/A03/A09/A10/A11/A12 | review; previously recognized Mock-only and newly limited History UI/Chromium #11; non-Chromium browsers/real Login→Chat→Citation NOT_RUN, no Module14 Gate |
| P3M15-A01/A03/A07/A10 | review; bounded DB/API/UI test evidence for message/answer, ordering, no duplicate and two fixture actors; real authenticated users/Production privacy NOT_RUN, no Module15 Gate |
| P3M05-A01 | evidence link to proposed ADR 0004 only; status and Implemented/Tested/Accepted all remain unselected/not-run. Other P3M05 activities unchanged. |

**Reconciliation field semantics:** `Implemented=LIMITED_SUBSET`, `Tested=PR9/10/11 exact successful synthetic-run reference`, `Accepted=ONLY_PR_SCOPED_EVIDENCE`; **FULL_ACTIVITY_GATE_NO**. This does not re-test or independently certify 262 activities. Recheck textual counts and modified paths before final handoff.

## AUTH-PLAN-01-D — options research, recommended decision and open items

**Sources actually looked up 2026-11-08 (official only, dated where available):**

- [OIDC Core §5.7](https://openid.net/specs/openid-connect-core-1_0.html#ClaimStability): stable identity requires `iss+sub`, not email/phone.
- [Keycloak OIDC](https://www.keycloak.org/securing-apps/oidc-layers), [server admin](https://www.keycloak.org/docs/latest/server_admin/), [production requirements](https://www.keycloak.org/server/configuration-production): standard OIDC, OTP/WebAuthn, recovery codes, production TLS/proxy/DB/HA and operator obligation.
- [Auth0 pricing](https://auth0.com/pricing): official **B2C** snapshot Free up to 25,000 MAU and Essentials/Professional STARTING price at chosen usage example; *not* firm budget, current plan availability at employer jurisdiction or a quote. [Auth0 database username flow](https://dev.auth0.com/docs/connections/database): username feature still needs email for that signup flow. [Auth0 public/private deployment regions](https://auth0.com/platform/cloud-deployment), [subregion restriction, updated 2025-09-10](https://support.auth0.com/center/s/article/Tenant-Creation-in-a-Specific-Sub-region) and [tenant relocation restriction](https://support.auth0.com/center/s/article/Change-the-Location-of-Existing-Tenant): region contract and legality **NOT_VERIFIED** for employer.
- [OWASP Session](https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html), [CSRF](https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html), [Password Storage](https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html), [MFA](https://cheatsheetseries.owasp.org/cheatsheets/Multifactor_Authentication_Cheat_Sheet.html).

**Full source-backed comparison and 16 NOT_RUN acceptance tests:** [ADR 0004](../../docs/adr/0004-auth-options.md). A = OIDC+server/BFF sessions, two **examined examples only**: Auth0 managed and Keycloak self-hosted. B = product-owned credentials+server sessions. No vendor contract/account/purchase/hosting or email/SMS requirement assumed. **Provisional recommendation: A architecture, provider not selected.** Scope separated: owner/account mapping and trusted FastAPI identity dependency, sessions, Cookie/CSRF/revocation, admin authorization, privacy/deletion-status, RLS tests independent of NB23. Actual RAG/streaming/full end-to-end blocked on NB23.

**Employer policy decisions remain OPEN** in [open_decisions](../open_decisions.md): provider/data transfer vs self-hosting; initial identifier + secure recovery without assuming email/SMS; organization cost/security/on-call approver. Product Auth provider, region, legal access, budget, actual activity and DB01-02 **not authorized**. Deletion status after session revocation cannot use the old session and needs separate approved independent verification mechanism; none built. Backend/BFF must fail closed and prevent forged owner across all paths. No change to historical specialist docs.

## AUTH-PLAN-01-E — actual checks and delivery constraints

- **Documentation-only work:** four explicitly authorized paths: new `coordination/tasks/AGENT-API-AUTH-PLAN-01.md`; new `docs/adr/0004-auth-options.md`; edited `coordination/open_decisions.md`; edited `coordination/phase3_checklist.md`. No other source/Repo/Workflow/schema/dependency/tests/database file.
- **Read-only GitHub inspection:** GET branch `main`, GET commit/tree at Starting SHA, GET branch `prep/auth-decision` before creation (404 / confirmed nonexistent), read docs and merged PR #9/#10/#11. Original ADR 0004 path 404; new version created. This is a review, not GitHub Actions validation.
- **Reproducible textual invariant check:** parse canonical checklist lines beginning `| **P3Mxx-Ayy**`, count unique IDs, count `Independent Module Gate — NOT PASSED`, checked Gates and unique `P3OPxx-Ryy` identifiers before/after; output must be 262/262/26/0/105 on both sides, and source_manifest references remain 2. All existing Gate lines, original source IDs and owner/output/check cells should be unchanged. Verify diff contains only four paths.
- **Real Auth tests:** every AUTH-P01..P16 = **NOT_RUN**; no local installation/execution/API/model/identity provisioning/CI, Migration, SQL, deploy, secrets, external payment or public service. Review of official web pages is external read-only research, not testing a vendor. Actual built modules and provisional costs have not been verified for employer policy or location.
- **PR handoff:** initial commit includes this cumulative checkpoint; Draft PR will be opened separately with the same four-path diff, then its verified number/status may be appended to this SAME file as a documentation-only checkpoint. **Do not merge**. Differentiate documented source check from actual runtime tests; this proposal is **READY_FOR_DECISION** only.

**Implemented (this mission): DOCUMENTATION_AND_CHECKLIST_RECONCILIATION_ONLY. Tested (this mission): TEXTUAL_INVARIANTS_AND_READ_ONLY_SOURCE_VERIFICATION; AUTH_RUNTIME_NOT_RUN. Accepted (this mission): NONE; employer/supervisor decision pending.**
