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
