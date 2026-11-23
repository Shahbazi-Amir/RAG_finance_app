# UI_F3 Phase 3 — API #61 completion candidate, exact dependency ledger

**Document status:** DRAFT / L1 source tests only. **No Mac Docker access or signed live C018 evidence in this chat.**

- Current candidate branch: `agent/ui-f3-api61-completion-20261123`; base API #61 exact `c02ba7896edb78febd2042f7afb1243f2a6aca34`.
- Previous tested UI #60: `21fe24913f85cb9cc013ce01b1d5dbb4bc97774f`, [CI 45082202462](https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/45082202462) **112/112 Node**, desktop/mobile Chromium **L1**. The old CI result **does not validate this new branch**.
- Actual deployed Mac SHA: **NOT_OBSERVED**. Mac Docker, Keycloak, Product PostgreSQL, OIDC signed HTTP and genuine C018 Q2/spawn audit: **NOT_RUN**; no permissions or read-only Mac CLI/browser endpoint provided to this runtime.
- UI client.ts, proxy.ts and auth/server/product-session.ts blobs exactly **unchanged** between API #61 and tested UI #60; new API server adds closed public receipt validation. API #61 schema loosens `chunks_sha256` to a 64-hex pattern for test adaptability, **but runtime and UI client still pin exact production C011 hash**. UI deliberately rejects any alternate hash even if it matches generic Schema pattern.
- New UI source: Product retains same signed authenticated GET `api.retrieved_sources.v1` and existing original POST correlators, no owner input, no verified URL from retrieved rows; adds verified Answer display roles (author/editor/speaker separately), descriptive Confidence or explicit null, shared public-HTTPS gate, keyboard visible focus, hostile metadata tests. L1 Browser cannot prove real producer.
- Canonical registry: `coordination/phase3_checklist.md`, `coordination/tasks/AGENT-UI-01.md`. No canonical checkbox or 26 module Gate decisions modified here. Overlays `P3OP01/03/05/09` remain **crosswalk only**, not additional counted rows.

**Matrix semantics:** `yes L1` means UI behavior exists but lacks real L2; `partial` denotes bounded code only; `no` means not implemented/contract absent. `accepted=NO` until module Gate owner/central recorded actual approval. `SHAs UI@HEAD` refers to the changing candidate branch; **final frozen SHA and exact CI are recorded in PR, never inferred from preceding runs.**

## 14 specialized UI activities and 42 related canonical module rows

| ID | مالک | معیار | SHAs | محیط | implemented | tested | accepted | شاهد | مانع و ورودی دقیق |
|---|---|---|---|---|---|---|---|---|---|
| UI-01 | UI/Foundation | Journey و مرزهای Frontend | UI@HEAD / API@c02ba789 | Ubuntu CI L1; Mac L2=NOT_RUN | partial | L1 pending exact-SHA CI | NO | AGENT-UI-01.md; product-chat.tsx | تصمیم معماری و تأیید CENTRAL |
| UI-02 | UI/API | مصرف DTO مشترک و کنترل خطا | UI@HEAD / API@c02ba789 | Ubuntu CI L1; Mac L2=NOT_RUN | yes | L1 pending exact-SHA CI | NO | history/client.ts; retrieved-sources-client.test.mjs | signed HTTP A/B و نسخهٔ مستقر |
| UI-03 | UI/API/Ops | OIDC ورود/نشست/خروج/انقضا | UI@HEAD / API@c02ba789 | Ubuntu CI L1; Mac L2=NOT_RUN | partial | L1 pending exact-SHA CI | NO | app/login/route.ts; auth/*; product_chat_browser.py | Mac Keycloak واقعی، revoke و SSL |
| UI-04 | Product/API/DB/UI | Consent نسخه‌دار و withdrawal | UI@HEAD / API@c02ba789 | Ubuntu CI L1; Mac L2=NOT_RUN | no | NOT_RUN | NO | هیچ پذیرش ساختگی ثبت نشده | متن حقوقی+versioned signed DTO+سیاست gating |
| UI-05 | UI/API/DB | History خصوصی، pagination و Refresh | UI@HEAD / API@c02ba789 | Ubuntu CI L1; Mac L2=NOT_RUN | partial | L1 pending exact-SHA CI | NO | history/client.ts; history-client.test.mjs | PG owner isolation در L2 |
| UI-06 | UI | Composer فارسی و RTL بدون duplicate | UI@HEAD / API@c02ba789 | Ubuntu CI L1; Mac L2=NOT_RUN | yes | L1 pending exact-SHA CI | NO | product-chat.tsx; product_chat_browser.py | مرورگر Mac و درخواست حقیقی |
| UI-07 | UI/Producer | Outcome مجزا و Confidence واقعی | UI@HEAD / API@c02ba789 | Ubuntu CI L1; Mac L2=NOT_RUN | partial | L1 pending exact-SHA CI | NO | answer-visibility.ts; source-metadata.ts | producer verified و calibration |
| UI-08 | UI/API/Phase2 | Claim/Citation و نقش‌ها و Locator | UI@HEAD / API@c02ba789 | Ubuntu CI L1; Mac L2=NOT_RUN | partial | L1 pending exact-SHA CI | NO | source-metadata.ts; public-https.ts; preview Chromium | verified resolver و Q2 حقیقی |
| UI-09 | API/DB/UI | Feedback پاسخ معتبر با dedupe | UI@HEAD / API@c02ba789 | Ubuntu CI L1; Mac L2=NOT_RUN | no | NOT_RUN | NO | مسیر ساختگی ساخته نشده | Answer ID، endpoint، storage receipt |
| UI-10 | API/UI | stream/cancel/recovery و عدم POST تکراری | UI@HEAD / API@c02ba789 | Ubuntu CI L1; Mac L2=NOT_RUN | partial | L1 pending exact-SHA CI | NO | attempt-checkpoints.ts; product_chat_browser.py | قرارداد stream و server cancel |
| UI-11 | UI/Ops | Keyboard، focus، RTL، موبایل، contrast | UI@HEAD / API@c02ba789 | Ubuntu CI L1; Mac L2=NOT_RUN | partial | L1 pending exact-SHA CI | NO | history.css; browser desktop/mobile | دسترس‌پذیری کامل، Safari/Mac و WCAG audit |
| UI-12 | UI/Foundation | Typecheck/Lint/Node/Build/Browser L1/L2 | UI@HEAD / API@c02ba789 | Ubuntu CI L1; Mac L2=NOT_RUN | partial | L1 pending exact-SHA CI | NO | workflow ui-f3-api61-completion.yml | actual Mac L2 + Gate owner |
| UI-13 | Product/API/DB/UI | درخواست/وضعیت حذف و پایان نشست | UI@HEAD / API@c02ba789 | Ubuntu CI L1; Mac L2=NOT_RUN | no | NOT_RUN | NO | هیچ موفقیت حذف جعلی نیست | Retention، transaction، revoke، export decision |
| UI-14 | UI/Security | React escaped text، URL و redaction | UI@HEAD / API@c02ba789 | Ubuntu CI L1; Mac L2=NOT_RUN | partial | L1 pending exact-SHA CI | NO | public-https.ts; source-display.test.mjs; Chromium | prod security/abuse audit |
| P3M03-A01 | Foundation+API/UI/DB | مرز Domain | UI@HEAD / API@c02ba789 | Ubuntu CI L1; Mac L2=NOT_RUN | partial | L1 pending exact-SHA CI | NO | AGENT-UI-01.md | تصویب معماری |
| P3M03-A02 | Foundation+API/UI/DB | Error model مشترک | UI@HEAD / API@c02ba789 | Ubuntu CI L1; Mac L2=NOT_RUN | partial | L1 pending exact-SHA CI | NO | history/client.ts | DTO خطای نهایی |
| P3M03-A03 | Foundation+API/UI/DB | Request/Trace سروری | UI@HEAD / API@c02ba789 | Ubuntu CI L1; Mac L2=NOT_RUN | partial | L1 pending exact-SHA CI | NO | history/client.ts; BFF proxy | L2 signed correlation + redaction |
| P3M03-A04 | Foundation+API/UI/DB | نسخه‌بندی /v1 | UI@HEAD / API@c02ba789 | Ubuntu CI L1; Mac L2=NOT_RUN | yes | L1 pending exact-SHA CI | NO | history/proxy.ts | L2 signed API |
| P3M03-A05 | Foundation+API/UI/DB | Schema User/Conversation/Message/Answer/Citation | UI@HEAD / API@c02ba789 | Ubuntu CI L1; Mac L2=NOT_RUN | partial | L1 pending exact-SHA CI | NO | product.v1.schema.json; product-validation.ts | producer+DB L2 |
| P3M03-A06 | Foundation+API/UI/DB | Attribution fields | UI@HEAD / API@c02ba789 | Ubuntu CI L1; Mac L2=NOT_RUN | partial | L1 pending exact-SHA CI | NO | source-metadata.ts; product.v1 | verified resolver |
| P3M03-A07 | Foundation+API/UI/DB | Compatibility policy | UI@HEAD / API@c02ba789 | Ubuntu CI L1; Mac L2=NOT_RUN | partial | L1 pending exact-SHA CI | NO | api.retrieved_sources.v1.schema.json | تصمیم تغییرنسخه |
| P3M03-A08 | Foundation+API/UI/DB | Contract tests Backend/UI/Runner | UI@HEAD / API@c02ba789 | Ubuntu CI L1; Mac L2=NOT_RUN | partial | L1 pending exact-SHA CI | NO | retrieved-sources-client.test.mjs | L2 real Mac |
| P3M03-A09 | Foundation+API/UI/DB | Dependency architecture tests | UI@HEAD / API@c02ba789 | Ubuntu CI L1; Mac L2=NOT_RUN | partial | L1 pending exact-SHA CI | NO | bff-service.test.mjs | تصمیم Gate owner |
| P3M11-A01 | API+UI | Citation DTO مشترک | UI@HEAD / API@c02ba789 | Ubuntu CI L1; Mac L2=NOT_RUN | partial | L1 pending exact-SHA CI | NO | product.v1.schema.json | producer resolver L2 |
| P3M11-A02 | API+UI | URL/locator معتبر | UI@HEAD / API@c02ba789 | Ubuntu CI L1; Mac L2=NOT_RUN | partial | L1 pending exact-SHA CI | NO | public-https.ts; source-locator.ts | typed member_locators + permissions |
| P3M11-A03 | API+UI | credited_author_name | UI@HEAD / API@c02ba789 | Ubuntu CI L1; Mac L2=NOT_RUN | partial | L1 pending exact-SHA CI | NO | source-metadata.ts; source-display.test.mjs | verified catalog data |
| P3M11-A04 | API+UI | editorial_supervisor_name مستقل | UI@HEAD / API@c02ba789 | Ubuntu CI L1; Mac L2=NOT_RUN | partial | L1 pending exact-SHA CI | NO | source-metadata.ts; source-display.test.mjs | verified catalog data |
| P3M11-A05 | API+UI | speaker_name برای transcript | UI@HEAD / API@c02ba789 | Ubuntu CI L1; Mac L2=NOT_RUN | partial | L1 pending exact-SHA CI | NO | source-metadata.ts; source-display.test.mjs | verified transcript |
| P3M11-A06 | API+UI | content_authority_type/attribution_status | UI@HEAD / API@c02ba789 | Ubuntu CI L1; Mac L2=NOT_RUN | partial | L1 pending exact-SHA CI | NO | product.v1; source-metadata.ts | real resolver provenance |
| P3M11-A07 | API+UI | Citation کنار Claim | UI@HEAD / API@c02ba789 | Ubuntu CI L1; Mac L2=NOT_RUN | partial | L1 pending exact-SHA CI | NO | product-chat.tsx | REAL verified Answer claim/cite |
| P3M11-A08 | API+UI | چرا این منبع استفاده شد | UI@HEAD / API@c02ba789 | Ubuntu CI L1; Mac L2=NOT_RUN | no | NOT_RUN | NO | هیچ توضیحی جعل نشده | explanation DTO + approved rationale |
| P3M11-A09 | API+UI | Broken link/locator | UI@HEAD / API@c02ba789 | Ubuntu CI L1; Mac L2=NOT_RUN | partial | L1 pending exact-SHA CI | NO | source-locator.ts; source-display.test.mjs | real live destination 404/403 policy |
| P3M11-A10 | API+UI | چهار حالت نمایش منابع | UI@HEAD / API@c02ba789 | Ubuntu CI L1; Mac L2=NOT_RUN | yes L1 | L1 pending exact-SHA CI | NO | retrieval_evidence_preview_browser.py | real Q2 evidence not verified |
| P3M11-A11 | API+UI | ممنوعیت سردبیر→نویسنده | UI@HEAD / API@c02ba789 | Ubuntu CI L1; Mac L2=NOT_RUN | yes L1 | L1 pending exact-SHA CI | NO | source-metadata.ts; source-display.test.mjs | real source catalog |
| P3M14-A01 | UI | صفحه ورود/نشست | UI@HEAD / API@c02ba789 | Ubuntu CI L1; Mac L2=NOT_RUN | partial | L1 pending exact-SHA CI | NO | app/login/route.ts; auth tests | signed Mac OIDC |
| P3M14-A02 | UI | فهرست گفتگوهای کاربر | UI@HEAD / API@c02ba789 | Ubuntu CI L1; Mac L2=NOT_RUN | partial | L1 pending exact-SHA CI | NO | product-chat.tsx; history-client.test.mjs | A/B private PG |
| P3M14-A03 | UI | Chat واکنش‌گرا | UI@HEAD / API@c02ba789 | Ubuntu CI L1; Mac L2=NOT_RUN | yes L1 | L1 pending exact-SHA CI | NO | product-chat.tsx; Chromium | L2 device/browser |
| P3M14-A04 | UI | Streaming و لغو | UI@HEAD / API@c02ba789 | Ubuntu CI L1; Mac L2=NOT_RUN | no | NOT_RUN | NO | فقط GET recovery موجود | versioned server event/cancel |
| P3M14-A05 | UI | Claim Citation | UI@HEAD / API@c02ba789 | Ubuntu CI L1; Mac L2=NOT_RUN | partial | L1 pending exact-SHA CI | NO | CitationView in product-chat.tsx | producer verified claim |
| P3M14-A06 | UI | نویسنده/سردبیر جدا | UI@HEAD / API@c02ba789 | Ubuntu CI L1; Mac L2=NOT_RUN | yes L1 | L1 pending exact-SHA CI | NO | source-metadata.ts | real metadata |
| P3M14-A07 | UI | Confidence قابل فهم | UI@HEAD / API@c02ba789 | Ubuntu CI L1; Mac L2=NOT_RUN | partial | L1 pending exact-SHA CI | NO | confidenceLabel; source-display.test.mjs | calibrated valid producer |
| P3M14-A08 | UI | No-answer و clarification | UI@HEAD / API@c02ba789 | Ubuntu CI L1; Mac L2=NOT_RUN | partial | L1 pending exact-SHA CI | NO | answer-visibility.ts; Node fixtures | real producer outcome |
| P3M14-A09 | UI | Error/Retry بدون duplication | UI@HEAD / API@c02ba789 | Ubuntu CI L1; Mac L2=NOT_RUN | yes L1 | L1 pending exact-SHA CI | NO | attempt-checkpoints.ts; product_chat_browser.py | real C018 one spawn |
| P3M14-A10 | UI | Keyboard/focus/contrast/a11y | UI@HEAD / API@c02ba789 | Ubuntu CI L1; Mac L2=NOT_RUN | partial | L1 pending exact-SHA CI | NO | history.css; mobile Chromium | manual WCAG + screen reader |
| P3M14-A11 | UI | مرورگرها و موبایل | UI@HEAD / API@c02ba789 | Ubuntu CI L1; Mac L2=NOT_RUN | partial | L1 pending exact-SHA CI | NO | Chromium 1280/390 | Safari/Firefox targets approval |
| P3M14-A12 | UI | عدم نمایش Debug/Prompt | UI@HEAD / API@c02ba789 | Ubuntu CI L1; Mac L2=NOT_RUN | partial | L1 pending exact-SHA CI | NO | React escaped output; xss browser test | prod security audit |
| P3M15-A01 | DB+API+UI | immutable User Message/Answer | UI@HEAD / API@c02ba789 | Ubuntu CI L1; Mac L2=NOT_RUN | partial | L1 pending exact-SHA CI | NO | sendMessage; recoverStatus | Postgres+T3 real |
| P3M15-A02 | DB+API+UI | عنوان مکالمه بدون تغییر متن | UI@HEAD / API@c02ba789 | Ubuntu CI L1; Mac L2=NOT_RUN | partial | L1 pending exact-SHA CI | NO | history/client.ts | real update policy |
| P3M15-A03 | DB+API+UI | Pagination و sort | UI@HEAD / API@c02ba789 | Ubuntu CI L1; Mac L2=NOT_RUN | yes L1 | L1 pending exact-SHA CI | NO | history-client.test.mjs | PG concurrent L2 |
| P3M15-A04 | DB+API+UI | حذف طبق retention | UI@HEAD / API@c02ba789 | Ubuntu CI L1; Mac L2=NOT_RUN | no | NOT_RUN | NO | not implemented | retention policy+DELETE receipt |
| P3M15-A05 | DB+API+UI | Feedback مثبت/منفی و خطا | UI@HEAD / API@c02ba789 | Ubuntu CI L1; Mac L2=NOT_RUN | no | NOT_RUN | NO | not implemented | feedback DTO+storage |
| P3M15-A06 | DB+API+UI | گزارش Citation مشکل‌دار | UI@HEAD / API@c02ba789 | Ubuntu CI L1; Mac L2=NOT_RUN | no | NOT_RUN | NO | not implemented | citation+feedback contract |
| P3M15-A07 | DB+API+UI | جلوگیری cross-user | UI@HEAD / API@c02ba789 | Ubuntu CI L1; Mac L2=NOT_RUN | partial | L1 pending exact-SHA CI | NO | history-client.test.mjs; proxy | real signed A/B RLS |
| P3M15-A08 | DB+API+UI | Export شرطی | UI@HEAD / API@c02ba789 | Ubuntu CI L1; Mac L2=NOT_RUN | no | NOT_RUN | NO | not implemented | CENTRAL scope approval |
| P3M15-A09 | DB+API+UI | feedback dataset بدون PII | UI@HEAD / API@c02ba789 | Ubuntu CI L1; Mac L2=NOT_RUN | no | NOT_RUN | NO | not implemented | privacy policy + DB pipeline |
| P3M15-A10 | DB+API+UI | Race/duplicate write | UI@HEAD / API@c02ba789 | Ubuntu CI L1; Mac L2=NOT_RUN | partial | L1 pending exact-SHA CI | NO | once-only POST Node/Chromium | PG concurrency + OS C018 |

## Operational crosswalk (not extra activities)

- P3OP01-R01..R09 → M01/M03/M14 and UI-01/02 architecture, auth roles and threat model.
- P3OP03-R01..R06 → M05/M06/M21, UI-03/04, Consent and RLS.
- P3OP05-R01..R10 → M14/M15, UI-03..13, chat/history/privacy/feedback/citations/mobile.
- P3OP09-R01..R07 → M12/M21/02/16/17/19 and UI-08/14, access security/unsafe display. R06 cost gates remain separate.

**Gate statuses:** P3M03=NOT_ACCEPTED (real contract cross-system pending); P3M11=NOT_ACCEPTED (resolver/Citation provenance unavailable); P3M14=NOT_ACCEPTED (real OIDC→Chat→Citation→History browser route unproven); P3M15=NOT_ACCEPTED (retention/feedback/owner isolation L2 pending).

## One consolidated owner request each (exact inputs / acceptance)

### SERVER/Ops — Mac no-generation pilot (first live blocker)
Provide *read-only authenticated access or execute the signed sanitized run on the Mac yourself*, without touching frozen demo. Supply current deployed Web/API/Engine SHA, compose project/volume mapping, image digests, HTTPS IdP callback and PG preflight status; create **isolated** Compose project+volumes only after approval. Send one genuine UI question with valid invite and session. Capture its request client_message_id/idempotency_key/resolved_conversation_id, T2 attempt_id/attempt_trace_id, API status/engine-status/retrieved-sources signed GET, persisted C018 Q2 row rank/chunk/source, PostgreSQL T2 correlation, OS child spawn ledger exactly **one** C018, generation_calls=0, Gateway=0. Browser Refresh must issue no new POST and OS spawn count stays one. Provide sanitized desktop/mobile screenshots, server logs, timestamp, exit states and rollback. **DO NOT** infer from archived Q2 or Linux fixture. If unavailable state clear `MAC_C018=BLOCKED_OPS_ACCESS`, not PASS.

### API_F3 / Product architect — versioned contracts
Provide one design proposal/commit for five independently reviewed surfaces: (1) Consent `status/policy_version/accepted_at/withdrawn_at/gating`; (2) Feedback + report linked to trusted real `Answer ID`, idempotent receipt, duplicate/retry/409; (3) delete request/status with explicit confirmation, progress/terminal and revoke; (4) streaming/cancel event sequence, replay, cancellation confirmation and UNKNOWN; (5) verified Answer/Claim/Citation+locator+credited_author/editor/speaker and calibrated confidence producer. All must be signed owner-scoped, error versioned, never synthesize LiveVerified or activate paid Gateway. Reconcile with API #61, Product.v1 and CENTRAL decisions before UI switches endpoints.

### DATABASE_F3
Give signed/role-scoped PG17.11 SQL and transaction commitments for Consent version/withdraw, feedback with unique answer/owner/idempotency, erase/retention/export (export policy decision independent), history A/B & RLS and race test. Provide safe disposable DB replay/backup/restore evidence tied to real API SHA. No test migration 011 assumption in no-dispatch Mac pilot; never edit frozen demo database.

### Foundation
Reconcile API #61 + UI candidate + DB #59 on separate worktrees and isolated Mac Compose/volumes; hard-pin every image/lock/engine digest; verify BFF mTLS signatures, origin/CSRF, OIDC login/logout/rotation/revoke, A/B owner isolation, API 401, PG strict TLS and no paid dispatch. Run separate **L1** isolated CI and **L2** signed Mac Chromium with real same-Attempt Server/OS receipts. Deliver topology/startup error detail or successful sanitized log; do not declare deployed or Gate PASS without it.

### Phase 2 / Source resolver
Provide real authorized C018 typed `member_locators` contract, pinned chunk provenance, source credit roles and trusted resolution/permissions. `source_id` observation alone and old archived Q2 do not establish verified attribution. Provide actual Q2 row from same T2 and negative tests for denied/broken locator; only then may Product expose link/Citation.

### CENTRAL / Product decision
Approve/version Consent legal text and withdrawal effects, Feedback taxonomy and retention, deletion/restore/export policy, stream-cancel semantics, calibrated outcome/confidence gates, browser/a11y target list, and specific Gate owners. Decide merge/freeze/Arvan only after verified separate L2 signed receipts. No unapproved checkbox changed.

## Reproducible exact-source CI (L1 only)

On new isolated branch in approved runner (not production):
```bash
test "$(git rev-parse HEAD)" = "$GITHUB_SHA"
cd apps/web
npm ci --no-audit --no-fund
npm run typecheck
npm run lint
npm test
npm run build
cd ../..
python -m pip install 'playwright==1.64.1'
python -m playwright install --with-deps chromium
# launch CI-only production Next server on 127.0.0.1:3000 with
# CI=true GITHUB_ACTIONS=true AUTH_CI_PRODUCT_CHAT_MODE=INVITED_RESULT_STUB_CI_ONLY
python tests/phase3/integration/ui/retrieval_evidence_preview_browser.py
python tests/phase3/integration/ui/product_chat_browser.py
```
Actual workflow: `.github/workflows/ui-f3-api61-completion.yml`. No Mac service, remote staging, real C018, DB, Gate, Gateway or Arvan called. Synthetic screenshot artifacts are visibly labeled only.

## SHA handoff to next executor

Read: PR on `agent/ui-f3-api61-completion-20261123` plus `coordination/handoffs/UI_F3_API61_COMPLETION.md`, pinned API #61 `c02ba789...` (not historical 7c6), actual workflow exact HEAD and independent Foundation/Ops signed L2 receipt if any. Ignore old successful CI for source modifications. **First live step** is one signed Mac UI send/GET/Refresh with OS C018 one-spawn and no-generation; if permission lacking, continue the independently testable UI tasks without blocking and keep all external dependencies explicit.
