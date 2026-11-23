# API_F3 — exact source audit + 262 activity coverage (2026-11-23)

**AUDIT ONLY / DRAFT / ZERO NEW ACCEPTANCES.** This file is a directly generated execution ledger from the immutable Phase3 modular roadmap. Per-row status is the initial inherited snapshot, NOT fresh code-level implementation verification. 252 listed rows in the supplied API handoff plus ten Module01 activities from the canonical map = **262 activities, 26 independent Gates**. 103 P3OP operational IDs cross-map, never double-count. 91 API-primary rows: **61 PARTIAL + 30 NOT_VERIFIED**, not an acceptance percentage.

## Evidence baseline

- API: [Draft #61](https://github.com/Shahbazi-Amir/RAG_finance_app/pull/61) source `c02ba7896edb78febd2042f7afb1243f2a6aca34`, open/unmerged; 21 commits beyond `5fe21e922b5e6570e319cf528fc481a96a4c8e9e`, 13 changed paths.
- API L1 only: [same-source CI 45081955496](https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/45081955496) 134 API + 38 contract/History + 103 BFF/Web = **275 PASS** as recorded in PR. NOT a real Mac proof.
- UI [#62](https://github.com/Shahbazi-Amir/RAG_finance_app/pull/62) `86bf2c2f1a0491d20496c704dbdfe3f9f1696d85`, based on API #61; DB [#59](https://github.com/Shahbazi-Amir/RAG_finance_app/pull/59) `8de9123634c0841fa61ba420978caee029350371`; Foundation [#55](https://github.com/Shahbazi-Amir/RAG_finance_app/pull/55) `c5e271d0fab8ab34c92a2da933ba6b194d1f1e9a`. **No accepted single integrated SHA** established by these independent PRs.
- Phase2 roadmap `Shahbazi-Amir/RAG_finance@7c74783c3dcda897b010ba9ea358d113f172ed1f`, modular map blob `53b44fbc9196bdd7c2d4a8f84a90676894bc210d`; operational map blob `8d7e9549f91369d9ca3bbfe107db8c62ca835f18`. Phase2/NB23 accepted Release still absent.
- API lock SHA-256 `399a4e796403bd8fc5b8165c030ad4d4d8479fb946e363e29a5722ea88d35ff5`, 28 CPython3.13 linux/amd64 pinned wheels.
- **Mac deployed SHA = NOT_OBSERVED; Mac signed HTTPS/OIDC/Product PG/C018 L2 = NOT_RUN; OS child count = NOT_OBSERVED; typed member_locators provenance = NOT_ATTESTED.** CI and synthetic fixture do not replace any of them.

## Exact API route/source inventory (#61)

| Method / Path | Trust / execution | Contract and side effects | L2 |
|---|---|---|---|
| GET `/v1/conversations` | signed BFF mTLS+RS256, PG role and same-session fence | `product.v1` history list, read | NOT_RUN |
| GET `/v1/conversations/{conversation_id}/messages` | same signed owner, coherent read | `product.v1` messages/answers, read | NOT_RUN |
| GET `/v1/message-requests/status` | signed owner and T2 tuple | `product.v1` status, read | NOT_RUN |
| POST `/v1/messages` | signed owner/session/epoch, PG T1+T2 commit prior to one-time reserve | 202 created/200 replay, no T3 in NO_DISPATCH_ONLY | NOT_RUN |
| GET `/v1/message-requests/engine-status` | same signed owner and PG T2 | `api.no_dispatch_status.v1`, no dispatch, answer null | NOT_RUN |
| GET `/v1/message-requests/retrieved-sources` | exact signed GET/query, same Attempt/Trace | `api.retrieved_sources.v1`, readonly private SQLite, UNVERIFIED IDs, verified_locators=[] | NOT_RUN |
| POST `/internal/auth/session/v1/revoke-one` | signed proof/restricted auth_revoker | DB commit then REVOKED_COMMITTED or fail closed | NOT_RUN |
| GET `/v1/message-requests/claim-test-status` | CI-only guarded stub | `api.claim_stub_diagnostic.v0`, NOT a real release DTO | N/A |
| GET `/v1/message-requests/invited-live-result` | CI-only fixture | UNVERIFIED_STAGING, NEVER LIVE_VERIFIED | N/A |

Read exact source: [API](https://github.com/Shahbazi-Amir/RAG_finance_app/blob/c02ba7896edb78febd2042f7afb1243f2a6aca34/apps/api/product_session_api.py), [History](https://github.com/Shahbazi-Amir/RAG_finance_app/blob/c02ba7896edb78febd2042f7afb1243f2a6aca34/apps/api/history_api.py), [NoDispatch](https://github.com/Shahbazi-Amir/RAG_finance_app/blob/c02ba7896edb78febd2042f7afb1243f2a6aca34/src/phase3/rag_runtime/no_dispatch_handler.py), [Retrieved Sources](https://github.com/Shahbazi-Amir/RAG_finance_app/blob/c02ba7896edb78febd2042f7afb1243f2a6aca34/src/phase3/rag_runtime/retrieved_sources.py), [RS256 BFF](https://github.com/Shahbazi-Amir/RAG_finance_app/blob/c02ba7896edb78febd2042f7afb1243f2a6aca34/apps/web/src/auth/server/product-session.ts), [schema](https://github.com/Shahbazi-Amir/RAG_finance_app/blob/c02ba7896edb78febd2042f7afb1243f2a6aca34/packages/contracts/api.retrieved_sources.v1.schema.json).

## Required real L2 matrix — all NOT_RUN in this audit

| Test | Positive / negative assertions | Owner |
|---|---|---|
| Ordinary login | Real OIDC Code+PKCE, issuer/sub→Owner, secure cookie/CSRF; deny invalid/unsigned | UI/Ops/API |
| Owner A/B | Signed History and sources A visible only to A; B=404; no RLS bypass | DB/API/Ops |
| Original POST | 202; same PG T1+T2, one authorized OS-attested C018 child, NO generation/T3 | Ops/API/DB/ENGINE |
| Refresh and replay | GET-only and no extra POST/OS child; 200 replay, same T2; conflict 409 | API/UI/DB/Ops |
| Revocation | 401 on expired/revoked session, deny old epoch/generation, redact output | API/Ops/DB |
| Crash/UNKNOWN | no automatic replay after commit ambiguity/timeouts; no second C018 | API/Ops |
| Tampered receipt | reject bad C011 hash, unknown chunk, extra schema key, forged locator or link | API/ENGINE |
| Producer/claim | C019 typed schema + Release/Locator/citation and DB011 authority before T3 | ENGINE/DB/CENTRAL |
| Safety/budget | no-answer/red-team, no cross-owner cache, approved quota/rate/cost cap | API/CENTRAL |
| Ops/privacy | trace/request correlation, scan and log PII/token/DSN redaction | Ops/Foundation |

## Owner requests and authority boundaries

- **Ops:** approved isolated Mac candidate SHA+image, Compose namespace/ports/volumes, valid TLS/IdP/PG proof, sanitized startup traceback and OS C018 exec count. Report one POST202, same-T2 GET-only, replay200, B404, revoked401, C018 top10=10 and generation_calls=0.
- **DB:** independently checked 001–010 PG17 roles `history_app`/`auth_revoker`, verify-full, RLS isolation, real migration/restore; approve 011 only for separately authorized Generation, 012+ only on accepted consent/feedback/retention/deletion contract.
- **ENGINE:** accepted Phase2 Release/NB23, hash-pinned C011/C018, independently typed C019/Locator/producer provenance and safety goldens.
- **CENTRAL:** formal security/consent/retention/export/streaming/cancellation/cost/SLO decisions and permissions. No paid calls, public launch, Arvan traffic change, existing-stack stop/restart/migrate/restore or original Qdrant RW.
- **Foundation/UI:** single integrated tested SHA, browser mTLS/OIDC/C018 and exact OS receipts, immutable DTO status, source display as nonclickable UNVERIFIED until independently validated, no fabricated `LIVE_VERIFIED`.

## API-primary 91-row activity trace

**Implemented** is the *inherited snapshot* (not verified per row). **Tested** and **Accepted** intentionally remain NOT_ATTESTED and NO respectively for each row until the same-SHA, domain-specific evidence exists.

| ID | Owner | Source map criterion | Commit/environment | Implemented | Tested | Accepted | Evidence | Blocker / precise next request |
|---|---|---|---|---|---|---|---|---|
| P3M05-A01 | API | انتخاب روش ورود طبق تصمیم کارفرما | #61 c02ba7896e, source L1; Mac NOT_RUN | PARTIAL snapshot | PER_ID_NOT_ATTESTED | NO | CI aggregate only | Real OIDC HTTPS signed A/B session; obtain owner artifact/SHAs, positive/negative tests |
| P3M05-A02 | API | Password hashing استاندارد در صورت ورود رمزدار | #61 c02ba7896e, source L1; Mac NOT_RUN | PARTIAL snapshot | PER_ID_NOT_ATTESTED | NO | CI aggregate only | Real OIDC HTTPS signed A/B session; obtain owner artifact/SHAs, positive/negative tests |
| P3M05-A03 | API | Session token امن و rotation | #61 c02ba7896e, source L1; Mac NOT_RUN | PARTIAL snapshot | PER_ID_NOT_ATTESTED | NO | CI aggregate only | Real OIDC HTTPS signed A/B session; obtain owner artifact/SHAs, positive/negative tests |
| P3M05-A04 | API | Cookie امن با `HttpOnly`، `Secure` و `SameSite` | #61 c02ba7896e, source L1; Mac NOT_RUN | PARTIAL snapshot | PER_ID_NOT_ATTESTED | NO | CI aggregate only | Real OIDC HTTPS signed A/B session; obtain owner artifact/SHAs, positive/negative tests |
| P3M05-A05 | API | CSRF policy | #61 c02ba7896e, source L1; Mac NOT_RUN | PARTIAL snapshot | PER_ID_NOT_ATTESTED | NO | CI aggregate only | Real OIDC HTTPS signed A/B session; obtain owner artifact/SHAs, positive/negative tests |
| P3M05-A06 | API | محدودیت تلاش ورود و lockout کنترل‌شده | #61 c02ba7896e, source L1; Mac NOT_RUN | PARTIAL snapshot | PER_ID_NOT_ATTESTED | NO | CI aggregate only | Real OIDC HTTPS signed A/B session; obtain owner artifact/SHAs, positive/negative tests |
| P3M05-A07 | API | Logout و revoke همه نشست‌ها | #61 c02ba7896e, source L1; Mac NOT_RUN | PARTIAL snapshot | PER_ID_NOT_ATTESTED | NO | CI aggregate only | Real OIDC HTTPS signed A/B session; obtain owner artifact/SHAs, positive/negative tests |
| P3M05-A08 | API | Expiration و refresh policy | #61 c02ba7896e, source L1; Mac NOT_RUN | PARTIAL snapshot | PER_ID_NOT_ATTESTED | NO | CI aggregate only | Real OIDC HTTPS signed A/B session; obtain owner artifact/SHAs, positive/negative tests |
| P3M05-A09 | API | ثبت Security event بدون ذخیره Secret | #61 c02ba7896e, source L1; Mac NOT_RUN | PARTIAL snapshot | PER_ID_NOT_ATTESTED | NO | CI aggregate only | Real OIDC HTTPS signed A/B session; obtain owner artifact/SHAs, positive/negative tests |
| P3M05-A10 | API | تست منفی Session theft و replay | #61 c02ba7896e, source L1; Mac NOT_RUN | PARTIAL snapshot | PER_ID_NOT_ATTESTED | NO | CI aggregate only | Real OIDC HTTPS signed A/B session; obtain owner artifact/SHAs, positive/negative tests |
| P3M07-A01 | API/ENGINE | خواندن `knowledge_release.lock` | #61 c02ba7896e, source L1; Mac NOT_RUN | PARTIAL snapshot | PER_ID_NOT_ATTESTED | NO | CI aggregate only | Accepted Release and Qdrant; obtain owner artifact/SHAs, positive/negative tests |
| P3M07-A02 | API/ENGINE | کنترل Hash و Schema پیش از Startup | #61 c02ba7896e, source L1; Mac NOT_RUN | PARTIAL snapshot | PER_ID_NOT_ATTESTED | NO | CI aggregate only | Accepted Release and Qdrant; obtain owner artifact/SHAs, positive/negative tests |
| P3M07-A03 | API/ENGINE | اتصال به Collection نسخه‌دار Qdrant | #61 c02ba7896e, source L1; Mac NOT_RUN | PARTIAL snapshot | PER_ID_NOT_ATTESTED | NO | CI aggregate only | Accepted Release and Qdrant; obtain owner artifact/SHAs, positive/negative tests |
| P3M07-A04 | API/ENGINE | اعتبارسنجی Point count و Payload schema | #61 c02ba7896e, source L1; Mac NOT_RUN | PARTIAL snapshot | PER_ID_NOT_ATTESTED | NO | CI aggregate only | Accepted Release and Qdrant; obtain owner artifact/SHAs, positive/negative tests |
| P3M07-A05 | API/ENGINE | کنترل فیلدهای Source locator و Attribution | #61 c02ba7896e, source L1; Mac NOT_RUN | PARTIAL snapshot | PER_ID_NOT_ATTESTED | NO | CI aggregate only | Accepted Release and Qdrant; obtain owner artifact/SHAs, positive/negative tests |
| P3M07-A06 | API/ENGINE | ممنوع‌کردن اتصال به Index بدون Release ID | #61 c02ba7896e, source L1; Mac NOT_RUN | PARTIAL snapshot | PER_ID_NOT_ATTESTED | NO | CI aggregate only | Accepted Release and Qdrant; obtain owner artifact/SHAs, positive/negative tests |
| P3M07-A07 | API/ENGINE | Health check مستقل دانش | #61 c02ba7896e, source L1; Mac NOT_RUN | PARTIAL snapshot | PER_ID_NOT_ATTESTED | NO | CI aggregate only | Accepted Release and Qdrant; obtain owner artifact/SHAs, positive/negative tests |
| P3M07-A08 | API/ENGINE | Warm-up محدود | #61 c02ba7896e, source L1; Mac NOT_RUN | PARTIAL snapshot | PER_ID_NOT_ATTESTED | NO | CI aggregate only | Accepted Release and Qdrant; obtain owner artifact/SHAs, positive/negative tests |
| P3M07-A09 | API/ENGINE | Rollback به Release قبلی | #61 c02ba7896e, source L1; Mac NOT_RUN | PARTIAL snapshot | PER_ID_NOT_ATTESTED | NO | CI aggregate only | Accepted Release and Qdrant; obtain owner artifact/SHAs, positive/negative tests |
| P3M07-A10 | API/ENGINE | تست خرابی Release و Fail-closed | #61 c02ba7896e, source L1; Mac NOT_RUN | PARTIAL snapshot | PER_ID_NOT_ATTESTED | NO | CI aggregate only | Accepted Release and Qdrant; obtain owner artifact/SHAs, positive/negative tests |
| P3M08-A01 | API/ENGINE | تبدیل Config برنده فاز ۲ به Runtime package | #61 c02ba7896e, source L1; Mac NOT_RUN | PARTIAL snapshot | PER_ID_NOT_ATTESTED | NO | CI aggregate only | Real C018/PG/Qdrant; obtain owner artifact/SHAs, positive/negative tests |
| P3M08-A02 | API/ENGINE | Dense/Sparse/Hybrid/Rerank pipeline | #61 c02ba7896e, source L1; Mac NOT_RUN | PARTIAL snapshot | PER_ID_NOT_ATTESTED | NO | CI aggregate only | Real C018/PG/Qdrant; obtain owner artifact/SHAs, positive/negative tests |
| P3M08-A03 | API/ENGINE | Metadata filter برای Source و Authority type | #61 c02ba7896e, source L1; Mac NOT_RUN | PARTIAL snapshot | PER_ID_NOT_ATTESTED | NO | CI aggregate only | Real C018/PG/Qdrant; obtain owner artifact/SHAs, positive/negative tests |
| P3M08-A04 | API/ENGINE | Intent-aware filter برای «نظر مستقیم مؤلف» | #61 c02ba7896e, source L1; Mac NOT_RUN | PARTIAL snapshot | PER_ID_NOT_ATTESTED | NO | CI aggregate only | Real C018/PG/Qdrant; obtain owner artifact/SHAs, positive/negative tests |
| P3M08-A05 | API/ENGINE | Timeout و retry محدود | #61 c02ba7896e, source L1; Mac NOT_RUN | PARTIAL snapshot | PER_ID_NOT_ATTESTED | NO | CI aggregate only | Real C018/PG/Qdrant; obtain owner artifact/SHAs, positive/negative tests |
| P3M08-A06 | API/ENGINE | Candidate و final-k ثابت و نسخه‌دار | #61 c02ba7896e, source L1; Mac NOT_RUN | PARTIAL snapshot | PER_ID_NOT_ATTESTED | NO | CI aggregate only | Real C018/PG/Qdrant; obtain owner artifact/SHAs, positive/negative tests |
| P3M08-A07 | API/ENGINE | عدم ثبت Query حساس به شکل Raw در log عمومی | #61 c02ba7896e, source L1; Mac NOT_RUN | PARTIAL snapshot | PER_ID_NOT_ATTESTED | NO | CI aggregate only | Real C018/PG/Qdrant; obtain owner artifact/SHAs, positive/negative tests |
| P3M08-A08 | API/ENGINE | ثبت Retrieval run و scoreها | #61 c02ba7896e, source L1; Mac NOT_RUN | PARTIAL snapshot | PER_ID_NOT_ATTESTED | NO | CI aggregate only | Real C018/PG/Qdrant; obtain owner artifact/SHAs, positive/negative tests |
| P3M08-A09 | API/ENGINE | Regression test با Golden set | #61 c02ba7896e, source L1; Mac NOT_RUN | PARTIAL snapshot | PER_ID_NOT_ATTESTED | NO | CI aggregate only | Real C018/PG/Qdrant; obtain owner artifact/SHAs, positive/negative tests |
| P3M08-A10 | API/ENGINE | Fallback کنترل‌شده در خرابی جزء غیرضروری | #61 c02ba7896e, source L1; Mac NOT_RUN | PARTIAL snapshot | PER_ID_NOT_ATTESTED | NO | CI aggregate only | Real C018/PG/Qdrant; obtain owner artifact/SHAs, positive/negative tests |
| P3M09-A01 | API | تعریف Interface مستقل از Provider | #61 c02ba7896e, source L1; Mac NOT_RUN | NOT_VERIFIED snapshot | PER_ID_NOT_ATTESTED | NO | CI aggregate only | C019 producer + cost approval; obtain owner artifact/SHAs, positive/negative tests |
| P3M09-A02 | API | Timeout، retry و circuit breaker | #61 c02ba7896e, source L1; Mac NOT_RUN | NOT_VERIFIED snapshot | PER_ID_NOT_ATTESTED | NO | CI aggregate only | C019 producer + cost approval; obtain owner artifact/SHAs, positive/negative tests |
| P3M09-A03 | API | محدودیت Token و هزینه | #61 c02ba7896e, source L1; Mac NOT_RUN | NOT_VERIFIED snapshot | PER_ID_NOT_ATTESTED | NO | CI aggregate only | C019 producer + cost approval; obtain owner artifact/SHAs, positive/negative tests |
| P3M09-A04 | API | ثبت مدل و نسخه در هر run | #61 c02ba7896e, source L1; Mac NOT_RUN | NOT_VERIFIED snapshot | PER_ID_NOT_ATTESTED | NO | CI aggregate only | C019 producer + cost approval; obtain owner artifact/SHAs, positive/negative tests |
| P3M09-A05 | API | حذف یا ماسک داده غیرضروری پیش از ارسال | #61 c02ba7896e, source L1; Mac NOT_RUN | NOT_VERIFIED snapshot | PER_ID_NOT_ATTESTED | NO | CI aggregate only | C019 producer + cost approval; obtain owner artifact/SHAs, positive/negative tests |
| P3M09-A06 | API | Streaming adapter | #61 c02ba7896e, source L1; Mac NOT_RUN | NOT_VERIFIED snapshot | PER_ID_NOT_ATTESTED | NO | CI aggregate only | C019 producer + cost approval; obtain owner artifact/SHAs, positive/negative tests |
| P3M09-A07 | API | خروجی ساخت‌یافته و Schema validation | #61 c02ba7896e, source L1; Mac NOT_RUN | NOT_VERIFIED snapshot | PER_ID_NOT_ATTESTED | NO | CI aggregate only | C019 producer + cost approval; obtain owner artifact/SHAs, positive/negative tests |
| P3M09-A08 | API | Fallback model طبق Policy | #61 c02ba7896e, source L1; Mac NOT_RUN | NOT_VERIFIED snapshot | PER_ID_NOT_ATTESTED | NO | CI aggregate only | C019 producer + cost approval; obtain owner artifact/SHAs, positive/negative tests |
| P3M09-A09 | API | تست خطا، کندی و پاسخ نامعتبر | #61 c02ba7896e, source L1; Mac NOT_RUN | NOT_VERIFIED snapshot | PER_ID_NOT_ATTESTED | NO | CI aggregate only | C019 producer + cost approval; obtain owner artifact/SHAs, positive/negative tests |
| P3M09-A10 | API | Benchmark کیفیت/هزینه/latency پیش از Freeze Provider | #61 c02ba7896e, source L1; Mac NOT_RUN | NOT_VERIFIED snapshot | PER_ID_NOT_ATTESTED | NO | CI aggregate only | C019 producer + cost approval; obtain owner artifact/SHAs, positive/negative tests |
| P3M10-A01 | API+DB | ساخت Query context از پیام جاری و تاریخچه محدود | #61 c02ba7896e, source L1; Mac NOT_RUN | PARTIAL snapshot | PER_ID_NOT_ATTESTED | NO | CI aggregate only | T3 proof/Claim/Answer; obtain owner artifact/SHAs, positive/negative tests |
| P3M10-A02 | API+DB | Intent و Answerability | #61 c02ba7896e, source L1; Mac NOT_RUN | PARTIAL snapshot | PER_ID_NOT_ATTESTED | NO | CI aggregate only | T3 proof/Claim/Answer; obtain owner artifact/SHAs, positive/negative tests |
| P3M10-A03 | API+DB | Retrieval و Context builder | #61 c02ba7896e, source L1; Mac NOT_RUN | PARTIAL snapshot | PER_ID_NOT_ATTESTED | NO | CI aggregate only | T3 proof/Claim/Answer; obtain owner artifact/SHAs, positive/negative tests |
| P3M10-A04 | API+DB | تولید پاسخ ساخت‌یافته | #61 c02ba7896e, source L1; Mac NOT_RUN | PARTIAL snapshot | PER_ID_NOT_ATTESTED | NO | CI aggregate only | T3 proof/Claim/Answer; obtain owner artifact/SHAs, positive/negative tests |
| P3M10-A05 | API+DB | Claim/Citation verification | #61 c02ba7896e, source L1; Mac NOT_RUN | PARTIAL snapshot | PER_ID_NOT_ATTESTED | NO | CI aggregate only | T3 proof/Claim/Answer; obtain owner artifact/SHAs, positive/negative tests |
| P3M10-A06 | API+DB | اعمال Safety و No-answer | #61 c02ba7896e, source L1; Mac NOT_RUN | PARTIAL snapshot | PER_ID_NOT_ATTESTED | NO | CI aggregate only | T3 proof/Claim/Answer; obtain owner artifact/SHAs, positive/negative tests |
| P3M10-A07 | API+DB | ساخت Confidence از اجزای قابل توضیح | #61 c02ba7896e, source L1; Mac NOT_RUN | PARTIAL snapshot | PER_ID_NOT_ATTESTED | NO | CI aggregate only | T3 proof/Claim/Answer; obtain owner artifact/SHAs, positive/negative tests |
| P3M10-A08 | API+DB | ذخیره Runها و Versionها در یک Transaction منطقی | #61 c02ba7896e, source L1; Mac NOT_RUN | PARTIAL snapshot | PER_ID_NOT_ATTESTED | NO | CI aggregate only | T3 proof/Claim/Answer; obtain owner artifact/SHAs, positive/negative tests |
| P3M10-A09 | API+DB | مدیریت cancellation و duplicate request | #61 c02ba7896e, source L1; Mac NOT_RUN | PARTIAL snapshot | PER_ID_NOT_ATTESTED | NO | CI aggregate only | T3 proof/Claim/Answer; obtain owner artifact/SHAs, positive/negative tests |
| P3M10-A10 | API+DB | Idempotency برای retry کلاینت | #61 c02ba7896e, source L1; Mac NOT_RUN | PARTIAL snapshot | PER_ID_NOT_ATTESTED | NO | CI aggregate only | T3 proof/Claim/Answer; obtain owner artifact/SHAs, positive/negative tests |
| P3M11-A01 | API+UI | تعریف Citation DTO مشترک Frontend/Backend | #61 c02ba7896e, source L1; Mac NOT_RUN | PARTIAL snapshot | PER_ID_NOT_ATTESTED | NO | CI aggregate only | Typed locator/attribution; obtain owner artifact/SHAs, positive/negative tests |
| P3M11-A02 | API+UI | ارسال URL و locator معتبر | #61 c02ba7896e, source L1; Mac NOT_RUN | PARTIAL snapshot | PER_ID_NOT_ATTESTED | NO | CI aggregate only | Typed locator/attribution; obtain owner artifact/SHAs, positive/negative tests |
| P3M11-A03 | API+UI | ارسال `credited_author_name` | #61 c02ba7896e, source L1; Mac NOT_RUN | PARTIAL snapshot | PER_ID_NOT_ATTESTED | NO | CI aggregate only | Typed locator/attribution; obtain owner artifact/SHAs, positive/negative tests |
| P3M11-A04 | API+UI | ارسال جداگانه `editorial_supervisor_name` | #61 c02ba7896e, source L1; Mac NOT_RUN | PARTIAL snapshot | PER_ID_NOT_ATTESTED | NO | CI aggregate only | Typed locator/attribution; obtain owner artifact/SHAs, positive/negative tests |
| P3M11-A05 | API+UI | ارسال `speaker_name` برای Transcript | #61 c02ba7896e, source L1; Mac NOT_RUN | PARTIAL snapshot | PER_ID_NOT_ATTESTED | NO | CI aggregate only | Typed locator/attribution; obtain owner artifact/SHAs, positive/negative tests |
| P3M11-A06 | API+UI | ارسال `content_authority_type` و `attribution_status` | #61 c02ba7896e, source L1; Mac NOT_RUN | PARTIAL snapshot | PER_ID_NOT_ATTESTED | NO | CI aggregate only | Typed locator/attribution; obtain owner artifact/SHAs, positive/negative tests |
| P3M11-A07 | API+UI | نمایش Citation کنار Claim و فهرست منابع | #61 c02ba7896e, source L1; Mac NOT_RUN | PARTIAL snapshot | PER_ID_NOT_ATTESTED | NO | CI aggregate only | Typed locator/attribution; obtain owner artifact/SHAs, positive/negative tests |
| P3M11-A08 | API+UI | Tooltip یا جزئیات «چرا این منبع استفاده شد» | #61 c02ba7896e, source L1; Mac NOT_RUN | PARTIAL snapshot | PER_ID_NOT_ATTESTED | NO | CI aggregate only | Typed locator/attribution; obtain owner artifact/SHAs, positive/negative tests |
| P3M11-A09 | API+UI | Broken link و Broken locator handling | #61 c02ba7896e, source L1; Mac NOT_RUN | PARTIAL snapshot | PER_ID_NOT_ATTESTED | NO | CI aggregate only | Typed locator/attribution; obtain owner artifact/SHAs, positive/negative tests |
| P3M11-A10 | API+UI | تست Snapshot برای چهار نوع نمایش منبع | #61 c02ba7896e, source L1; Mac NOT_RUN | PARTIAL snapshot | PER_ID_NOT_ATTESTED | NO | CI aggregate only | Typed locator/attribution; obtain owner artifact/SHAs, positive/negative tests |
| P3M11-A11 | API+UI | تست ممنوعیت تبدیل سردبیر به نویسنده | #61 c02ba7896e, source L1; Mac NOT_RUN | PARTIAL snapshot | PER_ID_NOT_ATTESTED | NO | CI aggregate only | Typed locator/attribution; obtain owner artifact/SHAs, positive/negative tests |
| P3M12-A01 | API | تفکیک آموزش مالی از توصیه سرمایه‌گذاری شخصی | #61 c02ba7896e, source L1; Mac NOT_RUN | NOT_VERIFIED snapshot | PER_ID_NOT_ATTESTED | NO | CI aggregate only | Approved Farsi red-team policy; obtain owner artifact/SHAs, positive/negative tests |
| P3M12-A02 | API | تشخیص سؤال خارج از منبع یا مبهم | #61 c02ba7896e, source L1; Mac NOT_RUN | NOT_VERIFIED snapshot | PER_ID_NOT_ATTESTED | NO | CI aggregate only | Approved Farsi red-team policy; obtain owner artifact/SHAs, positive/negative tests |
| P3M12-A03 | API | Clarification، Abstention و Safe completion | #61 c02ba7896e, source L1; Mac NOT_RUN | NOT_VERIFIED snapshot | PER_ID_NOT_ATTESTED | NO | CI aggregate only | Approved Farsi red-team policy; obtain owner artifact/SHAs, positive/negative tests |
| P3M12-A04 | API | ممنوعیت ادعای قطعی بدون Citation | #61 c02ba7896e, source L1; Mac NOT_RUN | NOT_VERIFIED snapshot | PER_ID_NOT_ATTESTED | NO | CI aggregate only | Approved Farsi red-team policy; obtain owner artifact/SHAs, positive/negative tests |
| P3M12-A05 | API | Prompt injection defense برای ورودی و محتوای بازیابی‌شده | #61 c02ba7896e, source L1; Mac NOT_RUN | NOT_VERIFIED snapshot | PER_ID_NOT_ATTESTED | NO | CI aggregate only | Approved Farsi red-team policy; obtain owner artifact/SHAs, positive/negative tests |
| P3M12-A06 | API | سیاست نمایش Disclaimer متناسب، نه ثابت و بی‌اثر | #61 c02ba7896e, source L1; Mac NOT_RUN | NOT_VERIFIED snapshot | PER_ID_NOT_ATTESTED | NO | CI aggregate only | Approved Farsi red-team policy; obtain owner artifact/SHAs, positive/negative tests |
| P3M12-A07 | API | ثبت Policy version | #61 c02ba7896e, source L1; Mac NOT_RUN | NOT_VERIFIED snapshot | PER_ID_NOT_ATTESTED | NO | CI aggregate only | Approved Farsi red-team policy; obtain owner artifact/SHAs, positive/negative tests |
| P3M12-A08 | API | ساخت Red-team corpus فارسی | #61 c02ba7896e, source L1; Mac NOT_RUN | NOT_VERIFIED snapshot | PER_ID_NOT_ATTESTED | NO | CI aggregate only | Approved Farsi red-team policy; obtain owner artifact/SHAs, positive/negative tests |
| P3M12-A09 | API | تست درخواست افشای داده کاربر دیگر | #61 c02ba7896e, source L1; Mac NOT_RUN | NOT_VERIFIED snapshot | PER_ID_NOT_ATTESTED | NO | CI aggregate only | Approved Farsi red-team policy; obtain owner artifact/SHAs, positive/negative tests |
| P3M12-A10 | API | تست توصیه خرید/فروش و پاسخ پرریسک | #61 c02ba7896e, source L1; Mac NOT_RUN | NOT_VERIFIED snapshot | PER_ID_NOT_ATTESTED | NO | CI aggregate only | Approved Farsi red-team policy; obtain owner artifact/SHAs, positive/negative tests |
| P3M13-A01 | API | OpenAPI نسخه‌دار | #61 c02ba7896e, source L1; Mac NOT_RUN | PARTIAL snapshot | PER_ID_NOT_ATTESTED | NO | CI aggregate only | Signed HTTP POST/GET L2; obtain owner artifact/SHAs, positive/negative tests |
| P3M13-A02 | API | Validation ورودی و محدودیت اندازه | #61 c02ba7896e, source L1; Mac NOT_RUN | PARTIAL snapshot | PER_ID_NOT_ATTESTED | NO | CI aggregate only | Signed HTTP POST/GET L2; obtain owner artifact/SHAs, positive/negative tests |
| P3M13-A03 | API | Error code پایدار | #61 c02ba7896e, source L1; Mac NOT_RUN | PARTIAL snapshot | PER_ID_NOT_ATTESTED | NO | CI aggregate only | Signed HTTP POST/GET L2; obtain owner artifact/SHAs, positive/negative tests |
| P3M13-A04 | API | Pagination تاریخچه | #61 c02ba7896e, source L1; Mac NOT_RUN | PARTIAL snapshot | PER_ID_NOT_ATTESTED | NO | CI aggregate only | Signed HTTP POST/GET L2; obtain owner artifact/SHAs, positive/negative tests |
| P3M13-A05 | API | Streaming پاسخ با stateهای مشخص | #61 c02ba7896e, source L1; Mac NOT_RUN | PARTIAL snapshot | PER_ID_NOT_ATTESTED | NO | CI aggregate only | Signed HTTP POST/GET L2; obtain owner artifact/SHAs, positive/negative tests |
| P3M13-A06 | API | Idempotency key | #61 c02ba7896e, source L1; Mac NOT_RUN | PARTIAL snapshot | PER_ID_NOT_ATTESTED | NO | CI aggregate only | Signed HTTP POST/GET L2; obtain owner artifact/SHAs, positive/negative tests |
| P3M13-A07 | API | Request/Trace ID | #61 c02ba7896e, source L1; Mac NOT_RUN | PARTIAL snapshot | PER_ID_NOT_ATTESTED | NO | CI aggregate only | Signed HTTP POST/GET L2; obtain owner artifact/SHAs, positive/negative tests |
| P3M13-A08 | API | Authorization در هر Endpoint | #61 c02ba7896e, source L1; Mac NOT_RUN | PARTIAL snapshot | PER_ID_NOT_ATTESTED | NO | CI aggregate only | Signed HTTP POST/GET L2; obtain owner artifact/SHAs, positive/negative tests |
| P3M13-A09 | API | Contract test و backward compatibility | #61 c02ba7896e, source L1; Mac NOT_RUN | PARTIAL snapshot | PER_ID_NOT_ATTESTED | NO | CI aggregate only | Signed HTTP POST/GET L2; obtain owner artifact/SHAs, positive/negative tests |
| P3M13-A10 | API | API abuse tests | #61 c02ba7896e, source L1; Mac NOT_RUN | PARTIAL snapshot | PER_ID_NOT_ATTESTED | NO | CI aggregate only | Signed HTTP POST/GET L2; obtain owner artifact/SHAs, positive/negative tests |
| P3M17-A01 | API | Rate limit بر اساس کاربر و IP | #61 c02ba7896e, source L1; Mac NOT_RUN | NOT_VERIFIED snapshot | PER_ID_NOT_ATTESTED | NO | CI aggregate only | Approved rate/budget/cache; obtain owner artifact/SHAs, positive/negative tests |
| P3M17-A02 | API | Daily quota و budget guard | #61 c02ba7896e, source L1; Mac NOT_RUN | NOT_VERIFIED snapshot | PER_ID_NOT_ATTESTED | NO | CI aggregate only | Approved rate/budget/cache; obtain owner artifact/SHAs, positive/negative tests |
| P3M17-A03 | API | Cache فقط برای خروجی‌های مجاز | #61 c02ba7896e, source L1; Mac NOT_RUN | NOT_VERIFIED snapshot | PER_ID_NOT_ATTESTED | NO | CI aggregate only | Approved rate/budget/cache; obtain owner artifact/SHAs, positive/negative tests |
| P3M17-A04 | API | Cache key شامل Release، Policy، Authority filter و Locale | #61 c02ba7896e, source L1; Mac NOT_RUN | NOT_VERIFIED snapshot | PER_ID_NOT_ATTESTED | NO | CI aggregate only | Approved rate/budget/cache; obtain owner artifact/SHAs, positive/negative tests |
| P3M17-A05 | API | ممنوعیت Cache مشترک برای پاسخ شخصی یا تاریخچه | #61 c02ba7896e, source L1; Mac NOT_RUN | NOT_VERIFIED snapshot | PER_ID_NOT_ATTESTED | NO | CI aggregate only | Approved rate/budget/cache; obtain owner artifact/SHAs, positive/negative tests |
| P3M17-A06 | API | TTL و invalidation هنگام Release جدید | #61 c02ba7896e, source L1; Mac NOT_RUN | NOT_VERIFIED snapshot | PER_ID_NOT_ATTESTED | NO | CI aggregate only | Approved rate/budget/cache; obtain owner artifact/SHAs, positive/negative tests |
| P3M17-A07 | API | Idempotency store | #61 c02ba7896e, source L1; Mac NOT_RUN | NOT_VERIFIED snapshot | PER_ID_NOT_ATTESTED | NO | CI aggregate only | Approved rate/budget/cache; obtain owner artifact/SHAs, positive/negative tests |
| P3M17-A08 | API | Queue/backpressure در پیک | #61 c02ba7896e, source L1; Mac NOT_RUN | NOT_VERIFIED snapshot | PER_ID_NOT_ATTESTED | NO | CI aggregate only | Approved rate/budget/cache; obtain owner artifact/SHAs, positive/negative tests |
| P3M17-A09 | API | تست bypass و cache poisoning | #61 c02ba7896e, source L1; Mac NOT_RUN | NOT_VERIFIED snapshot | PER_ID_NOT_ATTESTED | NO | CI aggregate only | Approved rate/budget/cache; obtain owner artifact/SHAs, positive/negative tests |
| P3M17-A10 | API | گزارش هزینه هر پاسخ موفق | #61 c02ba7896e, source L1; Mac NOT_RUN | NOT_VERIFIED snapshot | PER_ID_NOT_ATTESTED | NO | CI aggregate only | Approved rate/budget/cache; obtain owner artifact/SHAs, positive/negative tests |

## Full 262-row canonical activity and shared dependency index

| ID | Owner | Map criterion | Implemented source snapshot | Tested per ID | Accepted | Blocker and next action |
|---|---|---|---|---|---|---|
| P3M00-A01 | Foundation/ENGINE | دریافت `release_id` و Release Manifest فاز ۲ | NOT_VERIFIED | NOT_ATTESTED | NO | Accepted Phase2 Release/NB23; pin exact source, environment, test receipt and owner signoff |
| P3M00-A02 | Foundation/ENGINE | اعتبارسنجی `rag_request.schema.json` و `rag_response.schema.json` | NOT_VERIFIED | NOT_ATTESTED | NO | Accepted Phase2 Release/NB23; pin exact source, environment, test receipt and owner signoff |
| P3M00-A03 | Foundation/ENGINE | کنترل Hash داده، Chunk، Embedding، Index و Config | NOT_VERIFIED | NOT_ATTESTED | NO | Accepted Phase2 Release/NB23; pin exact source, environment, test receipt and owner signoff |
| P3M00-A04 | Foundation/ENGINE | اجرای Contract test روی نمونه درخواست‌ها | NOT_VERIFIED | NOT_ATTESTED | NO | Accepted Phase2 Release/NB23; pin exact source, environment, test receipt and owner signoff |
| P3M00-A05 | Foundation/ENGINE | کنترل Citation locator برای سایت، کتاب و Transcript | NOT_VERIFIED | NOT_ATTESTED | NO | Accepted Phase2 Release/NB23; pin exact source, environment, test receipt and owner signoff |
| P3M00-A06 | Foundation/ENGINE | کنترل وجود فیلدهای نویسنده، سردبیر، گوینده و نوع اختیار محتوایی | NOT_VERIFIED | NOT_ATTESTED | NO | Accepted Phase2 Release/NB23; pin exact source, environment, test receipt and owner signoff |
| P3M00-A07 | Foundation/ENGINE | اجرای Smoke benchmark فاز ۲ | NOT_VERIFIED | NOT_ATTESTED | NO | Accepted Phase2 Release/NB23; pin exact source, environment, test receipt and owner signoff |
| P3M00-A08 | Foundation/ENGINE | ثبت Compatibility matrix و نتیجه پذیرش | NOT_VERIFIED | NOT_ATTESTED | NO | Accepted Phase2 Release/NB23; pin exact source, environment, test receipt and owner signoff |
| P3M01-A01 | Foundation/CENTRAL | Freeze دامنه فاز ۳ و فهرست صریح موارد فاز ۴ | NOT_VERIFIED | NOT_ATTESTED | NO | Approved scope/SLO/cost/RPO/RTO; pin exact source, environment, test receipt and owner signoff |
| P3M01-A02 | Foundation/CENTRAL | ثبت Context diagram و Container diagram | NOT_VERIFIED | NOT_ATTESTED | NO | Approved scope/SLO/cost/RPO/RTO; pin exact source, environment, test receipt and owner signoff |
| P3M01-A03 | Foundation/CENTRAL | تثبیت Stack با ADR | NOT_VERIFIED | NOT_ATTESTED | NO | Approved scope/SLO/cost/RPO/RTO; pin exact source, environment, test receipt and owner signoff |
| P3M01-A04 | Foundation/CENTRAL | تعیین محیط‌های Local، Test، Staging و Production | NOT_VERIFIED | NOT_ATTESTED | NO | Approved scope/SLO/cost/RPO/RTO; pin exact source, environment, test receipt and owner signoff |
| P3M01-A05 | Foundation/CENTRAL | تعیین DAU، پیام روزانه، Concurrent request و بودجه مصرف | NOT_VERIFIED | NOT_ATTESTED | NO | Approved scope/SLO/cost/RPO/RTO; pin exact source, environment, test receipt and owner signoff |
| P3M01-A06 | Foundation/CENTRAL | تعیین SLO اولیه Availability، latency و error rate | NOT_VERIFIED | NOT_ATTESTED | NO | Approved scope/SLO/cost/RPO/RTO; pin exact source, environment, test receipt and owner signoff |
| P3M01-A07 | Foundation/CENTRAL | تعیین RPO و RTO Backup | NOT_VERIFIED | NOT_ATTESTED | NO | Approved scope/SLO/cost/RPO/RTO; pin exact source, environment, test receipt and owner signoff |
| P3M01-A08 | Foundation/CENTRAL | ثبت محل میزبانی، دامنه، TLS و محدودیت انتقال داده | NOT_VERIFIED | NOT_ATTESTED | NO | Approved scope/SLO/cost/RPO/RTO; pin exact source, environment, test receipt and owner signoff |
| P3M01-A09 | Foundation/CENTRAL | ساخت Risk register و Dependency register | NOT_VERIFIED | NOT_ATTESTED | NO | Approved scope/SLO/cost/RPO/RTO; pin exact source, environment, test receipt and owner signoff |
| P3M01-A10 | Foundation/CENTRAL | تعریف معیار Go/No-Go Launch | NOT_VERIFIED | NOT_ATTESTED | NO | Approved scope/SLO/cost/RPO/RTO; pin exact source, environment, test receipt and owner signoff |
| P3M02-A01 | Foundation | Freeze نسخه Python، Node، PostgreSQL، Qdrant، Redis و Docker | PARTIAL | NOT_ATTESTED | NO | Image/wheel lock security scan; pin exact source, environment, test receipt and owner signoff |
| P3M02-A02 | Foundation | ساخت lockfileهای وابستگی | PARTIAL | NOT_ATTESTED | NO | Image/wheel lock security scan; pin exact source, environment, test receipt and owner signoff |
| P3M02-A03 | Foundation | تعریف `.env.example` بدون Secret | PARTIAL | NOT_ATTESTED | NO | Image/wheel lock security scan; pin exact source, environment, test receipt and owner signoff |
| P3M02-A04 | Foundation | ممنوع‌کردن Secret در Repository | PARTIAL | NOT_ATTESTED | NO | Image/wheel lock security scan; pin exact source, environment, test receipt and owner signoff |
| P3M02-A05 | Foundation | فعال‌کردن Dependency و Secret scanning | PARTIAL | NOT_ATTESTED | NO | Image/wheel lock security scan; pin exact source, environment, test receipt and owner signoff |
| P3M02-A06 | Foundation | تنظیم Lint، Type check و Test command واحد | PARTIAL | NOT_ATTESTED | NO | Image/wheel lock security scan; pin exact source, environment, test receipt and owner signoff |
| P3M02-A07 | Foundation | ساخت SBOM و گزارش Dependency | PARTIAL | NOT_ATTESTED | NO | Image/wheel lock security scan; pin exact source, environment, test receipt and owner signoff |
| P3M02-A08 | Foundation | ثبت Timezone، Locale و Encoding | PARTIAL | NOT_ATTESTED | NO | Image/wheel lock security scan; pin exact source, environment, test receipt and owner signoff |
| P3M02-A09 | Foundation | تعیین Log redaction policy | PARTIAL | NOT_ATTESTED | NO | Image/wheel lock security scan; pin exact source, environment, test receipt and owner signoff |
| P3M02-A10 | Foundation | ساخت Environment manifest | PARTIAL | NOT_ATTESTED | NO | Image/wheel lock security scan; pin exact source, environment, test receipt and owner signoff |
| P3M03-A01 | Foundation+API/UI/DB | تعریف مرز Domain moduleها | PARTIAL | NOT_ATTESTED | NO | Cross-service contract L2; pin exact source, environment, test receipt and owner signoff |
| P3M03-A02 | Foundation+API/UI/DB | تعریف Error model مشترک | PARTIAL | NOT_ATTESTED | NO | Cross-service contract L2; pin exact source, environment, test receipt and owner signoff |
| P3M03-A03 | Foundation+API/UI/DB | تعریف Request ID و Trace ID | PARTIAL | NOT_ATTESTED | NO | Cross-service contract L2; pin exact source, environment, test receipt and owner signoff |
| P3M03-A04 | Foundation+API/UI/DB | نسخه‌بندی API از `/v1` | PARTIAL | NOT_ATTESTED | NO | Cross-service contract L2; pin exact source, environment, test receipt and owner signoff |
| P3M03-A05 | Foundation+API/UI/DB | ساخت Schemaهای User، Conversation، Message، Answer و Citation | PARTIAL | NOT_ATTESTED | NO | Cross-service contract L2; pin exact source, environment, test receipt and owner signoff |
| P3M03-A06 | Foundation+API/UI/DB | تعریف فیلدهای Attribution | PARTIAL | NOT_ATTESTED | NO | Cross-service contract L2; pin exact source, environment, test receipt and owner signoff |
| P3M03-A07 | Foundation+API/UI/DB | تعریف Compatibility policy | PARTIAL | NOT_ATTESTED | NO | Cross-service contract L2; pin exact source, environment, test receipt and owner signoff |
| P3M03-A08 | Foundation+API/UI/DB | ساخت Contract tests بین Backend، Frontend و RAG runtime | PARTIAL | NOT_ATTESTED | NO | Cross-service contract L2; pin exact source, environment, test receipt and owner signoff |
| P3M03-A09 | Foundation+API/UI/DB | ساخت Architecture dependency test برای جلوگیری از Import معکوس | PARTIAL | NOT_ATTESTED | NO | Cross-service contract L2; pin exact source, environment, test receipt and owner signoff |
| P3M04-A01 | DB | طراحی ERD و Data dictionary | PARTIAL | NOT_ATTESTED | NO | DB PG migration/retention; pin exact source, environment, test receipt and owner signoff |
| P3M04-A02 | DB | تعریف Primary/Foreign key و Index | PARTIAL | NOT_ATTESTED | NO | DB PG migration/retention; pin exact source, environment, test receipt and owner signoff |
| P3M04-A03 | DB | افزودن `user_id` به تمام داده‌های کاربر | PARTIAL | NOT_ATTESTED | NO | DB PG migration/retention; pin exact source, environment, test receipt and owner signoff |
| P3M04-A04 | DB | ذخیره Citation و Attribution به‌صورت ساخت‌یافته | PARTIAL | NOT_ATTESTED | NO | DB PG migration/retention; pin exact source, environment, test receipt and owner signoff |
| P3M04-A05 | DB | ذخیره Versionهای knowledge/retrieval/model/policy | PARTIAL | NOT_ATTESTED | NO | DB PG migration/retention; pin exact source, environment, test receipt and owner signoff |
| P3M04-A06 | DB | تعریف Migration forward و rollback | PARTIAL | NOT_ATTESTED | NO | DB PG migration/retention; pin exact source, environment, test receipt and owner signoff |
| P3M04-A07 | DB | تست Migration روی دیتابیس خالی و دیتابیس دارای داده | PARTIAL | NOT_ATTESTED | NO | DB PG migration/retention; pin exact source, environment, test receipt and owner signoff |
| P3M04-A08 | DB | تعریف Retention و soft/hard delete | PARTIAL | NOT_ATTESTED | NO | DB PG migration/retention; pin exact source, environment, test receipt and owner signoff |
| P3M04-A09 | DB | آماده‌سازی Namespace رزروشده برای موجودیت‌های فاز ۴ بدون فعال‌سازی آن‌ها | PARTIAL | NOT_ATTESTED | NO | DB PG migration/retention; pin exact source, environment, test receipt and owner signoff |
| P3M05-A01 | API | انتخاب روش ورود طبق تصمیم کارفرما | PARTIAL | NOT_ATTESTED | NO | Real OIDC HTTPS signed A/B session; pin exact source, environment, test receipt and owner signoff |
| P3M05-A02 | API | Password hashing استاندارد در صورت ورود رمزدار | PARTIAL | NOT_ATTESTED | NO | Real OIDC HTTPS signed A/B session; pin exact source, environment, test receipt and owner signoff |
| P3M05-A03 | API | Session token امن و rotation | PARTIAL | NOT_ATTESTED | NO | Real OIDC HTTPS signed A/B session; pin exact source, environment, test receipt and owner signoff |
| P3M05-A04 | API | Cookie امن با `HttpOnly`، `Secure` و `SameSite` | PARTIAL | NOT_ATTESTED | NO | Real OIDC HTTPS signed A/B session; pin exact source, environment, test receipt and owner signoff |
| P3M05-A05 | API | CSRF policy | PARTIAL | NOT_ATTESTED | NO | Real OIDC HTTPS signed A/B session; pin exact source, environment, test receipt and owner signoff |
| P3M05-A06 | API | محدودیت تلاش ورود و lockout کنترل‌شده | PARTIAL | NOT_ATTESTED | NO | Real OIDC HTTPS signed A/B session; pin exact source, environment, test receipt and owner signoff |
| P3M05-A07 | API | Logout و revoke همه نشست‌ها | PARTIAL | NOT_ATTESTED | NO | Real OIDC HTTPS signed A/B session; pin exact source, environment, test receipt and owner signoff |
| P3M05-A08 | API | Expiration و refresh policy | PARTIAL | NOT_ATTESTED | NO | Real OIDC HTTPS signed A/B session; pin exact source, environment, test receipt and owner signoff |
| P3M05-A09 | API | ثبت Security event بدون ذخیره Secret | PARTIAL | NOT_ATTESTED | NO | Real OIDC HTTPS signed A/B session; pin exact source, environment, test receipt and owner signoff |
| P3M05-A10 | API | تست منفی Session theft و replay | PARTIAL | NOT_ATTESTED | NO | Real OIDC HTTPS signed A/B session; pin exact source, environment, test receipt and owner signoff |
| P3M06-A01 | DB+API | فعال‌سازی Row-Level Security برای جداول کاربرمحور | PARTIAL | NOT_ATTESTED | NO | Real RLS A/B scope; pin exact source, environment, test receipt and owner signoff |
| P3M06-A02 | DB+API | تعریف Policy خواندن، نوشتن، ویرایش و حذف | PARTIAL | NOT_ATTESTED | NO | Real RLS A/B scope; pin exact source, environment, test receipt and owner signoff |
| P3M06-A03 | DB+API | تنظیم Context امن user/tenant در هر Transaction | PARTIAL | NOT_ATTESTED | NO | Real RLS A/B scope; pin exact source, environment, test receipt and owner signoff |
| P3M06-A04 | DB+API | جلوگیری از دسترسی Background job خارج از Scope | PARTIAL | NOT_ATTESTED | NO | Real RLS A/B scope; pin exact source, environment, test receipt and owner signoff |
| P3M06-A05 | DB+API | تست cross-user برای تمام Endpointها | PARTIAL | NOT_ATTESTED | NO | Real RLS A/B scope; pin exact source, environment, test receipt and owner signoff |
| P3M06-A06 | DB+API | تست ID enumeration | PARTIAL | NOT_ATTESTED | NO | Real RLS A/B scope; pin exact source, environment, test receipt and owner signoff |
| P3M06-A07 | DB+API | تست دسترسی مستقیم Repository layer | PARTIAL | NOT_ATTESTED | NO | Real RLS A/B scope; pin exact source, environment, test receipt and owner signoff |
| P3M06-A08 | DB+API | ثبت Audit برای عملیات حساس | PARTIAL | NOT_ATTESTED | NO | Real RLS A/B scope; pin exact source, environment, test receipt and owner signoff |
| P3M06-A09 | DB+API | ساخت Isolation matrix | PARTIAL | NOT_ATTESTED | NO | Real RLS A/B scope; pin exact source, environment, test receipt and owner signoff |
| P3M07-A01 | API/ENGINE | خواندن `knowledge_release.lock` | PARTIAL | NOT_ATTESTED | NO | Accepted Release and Qdrant; pin exact source, environment, test receipt and owner signoff |
| P3M07-A02 | API/ENGINE | کنترل Hash و Schema پیش از Startup | PARTIAL | NOT_ATTESTED | NO | Accepted Release and Qdrant; pin exact source, environment, test receipt and owner signoff |
| P3M07-A03 | API/ENGINE | اتصال به Collection نسخه‌دار Qdrant | PARTIAL | NOT_ATTESTED | NO | Accepted Release and Qdrant; pin exact source, environment, test receipt and owner signoff |
| P3M07-A04 | API/ENGINE | اعتبارسنجی Point count و Payload schema | PARTIAL | NOT_ATTESTED | NO | Accepted Release and Qdrant; pin exact source, environment, test receipt and owner signoff |
| P3M07-A05 | API/ENGINE | کنترل فیلدهای Source locator و Attribution | PARTIAL | NOT_ATTESTED | NO | Accepted Release and Qdrant; pin exact source, environment, test receipt and owner signoff |
| P3M07-A06 | API/ENGINE | ممنوع‌کردن اتصال به Index بدون Release ID | PARTIAL | NOT_ATTESTED | NO | Accepted Release and Qdrant; pin exact source, environment, test receipt and owner signoff |
| P3M07-A07 | API/ENGINE | Health check مستقل دانش | PARTIAL | NOT_ATTESTED | NO | Accepted Release and Qdrant; pin exact source, environment, test receipt and owner signoff |
| P3M07-A08 | API/ENGINE | Warm-up محدود | PARTIAL | NOT_ATTESTED | NO | Accepted Release and Qdrant; pin exact source, environment, test receipt and owner signoff |
| P3M07-A09 | API/ENGINE | Rollback به Release قبلی | PARTIAL | NOT_ATTESTED | NO | Accepted Release and Qdrant; pin exact source, environment, test receipt and owner signoff |
| P3M07-A10 | API/ENGINE | تست خرابی Release و Fail-closed | PARTIAL | NOT_ATTESTED | NO | Accepted Release and Qdrant; pin exact source, environment, test receipt and owner signoff |
| P3M08-A01 | API/ENGINE | تبدیل Config برنده فاز ۲ به Runtime package | PARTIAL | NOT_ATTESTED | NO | Real C018/PG/Qdrant; pin exact source, environment, test receipt and owner signoff |
| P3M08-A02 | API/ENGINE | Dense/Sparse/Hybrid/Rerank pipeline | PARTIAL | NOT_ATTESTED | NO | Real C018/PG/Qdrant; pin exact source, environment, test receipt and owner signoff |
| P3M08-A03 | API/ENGINE | Metadata filter برای Source و Authority type | PARTIAL | NOT_ATTESTED | NO | Real C018/PG/Qdrant; pin exact source, environment, test receipt and owner signoff |
| P3M08-A04 | API/ENGINE | Intent-aware filter برای «نظر مستقیم مؤلف» | PARTIAL | NOT_ATTESTED | NO | Real C018/PG/Qdrant; pin exact source, environment, test receipt and owner signoff |
| P3M08-A05 | API/ENGINE | Timeout و retry محدود | PARTIAL | NOT_ATTESTED | NO | Real C018/PG/Qdrant; pin exact source, environment, test receipt and owner signoff |
| P3M08-A06 | API/ENGINE | Candidate و final-k ثابت و نسخه‌دار | PARTIAL | NOT_ATTESTED | NO | Real C018/PG/Qdrant; pin exact source, environment, test receipt and owner signoff |
| P3M08-A07 | API/ENGINE | عدم ثبت Query حساس به شکل Raw در log عمومی | PARTIAL | NOT_ATTESTED | NO | Real C018/PG/Qdrant; pin exact source, environment, test receipt and owner signoff |
| P3M08-A08 | API/ENGINE | ثبت Retrieval run و scoreها | PARTIAL | NOT_ATTESTED | NO | Real C018/PG/Qdrant; pin exact source, environment, test receipt and owner signoff |
| P3M08-A09 | API/ENGINE | Regression test با Golden set | PARTIAL | NOT_ATTESTED | NO | Real C018/PG/Qdrant; pin exact source, environment, test receipt and owner signoff |
| P3M08-A10 | API/ENGINE | Fallback کنترل‌شده در خرابی جزء غیرضروری | PARTIAL | NOT_ATTESTED | NO | Real C018/PG/Qdrant; pin exact source, environment, test receipt and owner signoff |
| P3M09-A01 | API | تعریف Interface مستقل از Provider | NOT_VERIFIED | NOT_ATTESTED | NO | C019 producer + cost approval; pin exact source, environment, test receipt and owner signoff |
| P3M09-A02 | API | Timeout، retry و circuit breaker | NOT_VERIFIED | NOT_ATTESTED | NO | C019 producer + cost approval; pin exact source, environment, test receipt and owner signoff |
| P3M09-A03 | API | محدودیت Token و هزینه | NOT_VERIFIED | NOT_ATTESTED | NO | C019 producer + cost approval; pin exact source, environment, test receipt and owner signoff |
| P3M09-A04 | API | ثبت مدل و نسخه در هر run | NOT_VERIFIED | NOT_ATTESTED | NO | C019 producer + cost approval; pin exact source, environment, test receipt and owner signoff |
| P3M09-A05 | API | حذف یا ماسک داده غیرضروری پیش از ارسال | NOT_VERIFIED | NOT_ATTESTED | NO | C019 producer + cost approval; pin exact source, environment, test receipt and owner signoff |
| P3M09-A06 | API | Streaming adapter | NOT_VERIFIED | NOT_ATTESTED | NO | C019 producer + cost approval; pin exact source, environment, test receipt and owner signoff |
| P3M09-A07 | API | خروجی ساخت‌یافته و Schema validation | NOT_VERIFIED | NOT_ATTESTED | NO | C019 producer + cost approval; pin exact source, environment, test receipt and owner signoff |
| P3M09-A08 | API | Fallback model طبق Policy | NOT_VERIFIED | NOT_ATTESTED | NO | C019 producer + cost approval; pin exact source, environment, test receipt and owner signoff |
| P3M09-A09 | API | تست خطا، کندی و پاسخ نامعتبر | NOT_VERIFIED | NOT_ATTESTED | NO | C019 producer + cost approval; pin exact source, environment, test receipt and owner signoff |
| P3M09-A10 | API | Benchmark کیفیت/هزینه/latency پیش از Freeze Provider | NOT_VERIFIED | NOT_ATTESTED | NO | C019 producer + cost approval; pin exact source, environment, test receipt and owner signoff |
| P3M10-A01 | API+DB | ساخت Query context از پیام جاری و تاریخچه محدود | PARTIAL | NOT_ATTESTED | NO | T3 proof/Claim/Answer; pin exact source, environment, test receipt and owner signoff |
| P3M10-A02 | API+DB | Intent و Answerability | PARTIAL | NOT_ATTESTED | NO | T3 proof/Claim/Answer; pin exact source, environment, test receipt and owner signoff |
| P3M10-A03 | API+DB | Retrieval و Context builder | PARTIAL | NOT_ATTESTED | NO | T3 proof/Claim/Answer; pin exact source, environment, test receipt and owner signoff |
| P3M10-A04 | API+DB | تولید پاسخ ساخت‌یافته | PARTIAL | NOT_ATTESTED | NO | T3 proof/Claim/Answer; pin exact source, environment, test receipt and owner signoff |
| P3M10-A05 | API+DB | Claim/Citation verification | PARTIAL | NOT_ATTESTED | NO | T3 proof/Claim/Answer; pin exact source, environment, test receipt and owner signoff |
| P3M10-A06 | API+DB | اعمال Safety و No-answer | PARTIAL | NOT_ATTESTED | NO | T3 proof/Claim/Answer; pin exact source, environment, test receipt and owner signoff |
| P3M10-A07 | API+DB | ساخت Confidence از اجزای قابل توضیح | PARTIAL | NOT_ATTESTED | NO | T3 proof/Claim/Answer; pin exact source, environment, test receipt and owner signoff |
| P3M10-A08 | API+DB | ذخیره Runها و Versionها در یک Transaction منطقی | PARTIAL | NOT_ATTESTED | NO | T3 proof/Claim/Answer; pin exact source, environment, test receipt and owner signoff |
| P3M10-A09 | API+DB | مدیریت cancellation و duplicate request | PARTIAL | NOT_ATTESTED | NO | T3 proof/Claim/Answer; pin exact source, environment, test receipt and owner signoff |
| P3M10-A10 | API+DB | Idempotency برای retry کلاینت | PARTIAL | NOT_ATTESTED | NO | T3 proof/Claim/Answer; pin exact source, environment, test receipt and owner signoff |
| P3M11-A01 | API+UI | تعریف Citation DTO مشترک Frontend/Backend | PARTIAL | NOT_ATTESTED | NO | Typed locator/attribution; pin exact source, environment, test receipt and owner signoff |
| P3M11-A02 | API+UI | ارسال URL و locator معتبر | PARTIAL | NOT_ATTESTED | NO | Typed locator/attribution; pin exact source, environment, test receipt and owner signoff |
| P3M11-A03 | API+UI | ارسال `credited_author_name` | PARTIAL | NOT_ATTESTED | NO | Typed locator/attribution; pin exact source, environment, test receipt and owner signoff |
| P3M11-A04 | API+UI | ارسال جداگانه `editorial_supervisor_name` | PARTIAL | NOT_ATTESTED | NO | Typed locator/attribution; pin exact source, environment, test receipt and owner signoff |
| P3M11-A05 | API+UI | ارسال `speaker_name` برای Transcript | PARTIAL | NOT_ATTESTED | NO | Typed locator/attribution; pin exact source, environment, test receipt and owner signoff |
| P3M11-A06 | API+UI | ارسال `content_authority_type` و `attribution_status` | PARTIAL | NOT_ATTESTED | NO | Typed locator/attribution; pin exact source, environment, test receipt and owner signoff |
| P3M11-A07 | API+UI | نمایش Citation کنار Claim و فهرست منابع | PARTIAL | NOT_ATTESTED | NO | Typed locator/attribution; pin exact source, environment, test receipt and owner signoff |
| P3M11-A08 | API+UI | Tooltip یا جزئیات «چرا این منبع استفاده شد» | PARTIAL | NOT_ATTESTED | NO | Typed locator/attribution; pin exact source, environment, test receipt and owner signoff |
| P3M11-A09 | API+UI | Broken link و Broken locator handling | PARTIAL | NOT_ATTESTED | NO | Typed locator/attribution; pin exact source, environment, test receipt and owner signoff |
| P3M11-A10 | API+UI | تست Snapshot برای چهار نوع نمایش منبع | PARTIAL | NOT_ATTESTED | NO | Typed locator/attribution; pin exact source, environment, test receipt and owner signoff |
| P3M11-A11 | API+UI | تست ممنوعیت تبدیل سردبیر به نویسنده | PARTIAL | NOT_ATTESTED | NO | Typed locator/attribution; pin exact source, environment, test receipt and owner signoff |
| P3M12-A01 | API | تفکیک آموزش مالی از توصیه سرمایه‌گذاری شخصی | NOT_VERIFIED | NOT_ATTESTED | NO | Approved Farsi red-team policy; pin exact source, environment, test receipt and owner signoff |
| P3M12-A02 | API | تشخیص سؤال خارج از منبع یا مبهم | NOT_VERIFIED | NOT_ATTESTED | NO | Approved Farsi red-team policy; pin exact source, environment, test receipt and owner signoff |
| P3M12-A03 | API | Clarification، Abstention و Safe completion | NOT_VERIFIED | NOT_ATTESTED | NO | Approved Farsi red-team policy; pin exact source, environment, test receipt and owner signoff |
| P3M12-A04 | API | ممنوعیت ادعای قطعی بدون Citation | NOT_VERIFIED | NOT_ATTESTED | NO | Approved Farsi red-team policy; pin exact source, environment, test receipt and owner signoff |
| P3M12-A05 | API | Prompt injection defense برای ورودی و محتوای بازیابی‌شده | NOT_VERIFIED | NOT_ATTESTED | NO | Approved Farsi red-team policy; pin exact source, environment, test receipt and owner signoff |
| P3M12-A06 | API | سیاست نمایش Disclaimer متناسب، نه ثابت و بی‌اثر | NOT_VERIFIED | NOT_ATTESTED | NO | Approved Farsi red-team policy; pin exact source, environment, test receipt and owner signoff |
| P3M12-A07 | API | ثبت Policy version | NOT_VERIFIED | NOT_ATTESTED | NO | Approved Farsi red-team policy; pin exact source, environment, test receipt and owner signoff |
| P3M12-A08 | API | ساخت Red-team corpus فارسی | NOT_VERIFIED | NOT_ATTESTED | NO | Approved Farsi red-team policy; pin exact source, environment, test receipt and owner signoff |
| P3M12-A09 | API | تست درخواست افشای داده کاربر دیگر | NOT_VERIFIED | NOT_ATTESTED | NO | Approved Farsi red-team policy; pin exact source, environment, test receipt and owner signoff |
| P3M12-A10 | API | تست توصیه خرید/فروش و پاسخ پرریسک | NOT_VERIFIED | NOT_ATTESTED | NO | Approved Farsi red-team policy; pin exact source, environment, test receipt and owner signoff |
| P3M13-A01 | API | OpenAPI نسخه‌دار | PARTIAL | NOT_ATTESTED | NO | Signed HTTP POST/GET L2; pin exact source, environment, test receipt and owner signoff |
| P3M13-A02 | API | Validation ورودی و محدودیت اندازه | PARTIAL | NOT_ATTESTED | NO | Signed HTTP POST/GET L2; pin exact source, environment, test receipt and owner signoff |
| P3M13-A03 | API | Error code پایدار | PARTIAL | NOT_ATTESTED | NO | Signed HTTP POST/GET L2; pin exact source, environment, test receipt and owner signoff |
| P3M13-A04 | API | Pagination تاریخچه | PARTIAL | NOT_ATTESTED | NO | Signed HTTP POST/GET L2; pin exact source, environment, test receipt and owner signoff |
| P3M13-A05 | API | Streaming پاسخ با stateهای مشخص | PARTIAL | NOT_ATTESTED | NO | Signed HTTP POST/GET L2; pin exact source, environment, test receipt and owner signoff |
| P3M13-A06 | API | Idempotency key | PARTIAL | NOT_ATTESTED | NO | Signed HTTP POST/GET L2; pin exact source, environment, test receipt and owner signoff |
| P3M13-A07 | API | Request/Trace ID | PARTIAL | NOT_ATTESTED | NO | Signed HTTP POST/GET L2; pin exact source, environment, test receipt and owner signoff |
| P3M13-A08 | API | Authorization در هر Endpoint | PARTIAL | NOT_ATTESTED | NO | Signed HTTP POST/GET L2; pin exact source, environment, test receipt and owner signoff |
| P3M13-A09 | API | Contract test و backward compatibility | PARTIAL | NOT_ATTESTED | NO | Signed HTTP POST/GET L2; pin exact source, environment, test receipt and owner signoff |
| P3M13-A10 | API | API abuse tests | PARTIAL | NOT_ATTESTED | NO | Signed HTTP POST/GET L2; pin exact source, environment, test receipt and owner signoff |
| P3M14-A01 | UI | صفحه ورود و مدیریت Session | PARTIAL | NOT_ATTESTED | NO | Mac browser signed OIDC; pin exact source, environment, test receipt and owner signoff |
| P3M14-A02 | UI | فهرست گفت‌وگوهای خود کاربر | PARTIAL | NOT_ATTESTED | NO | Mac browser signed OIDC; pin exact source, environment, test receipt and owner signoff |
| P3M14-A03 | UI | صفحه Chat واکنش‌گرا | PARTIAL | NOT_ATTESTED | NO | Mac browser signed OIDC; pin exact source, environment, test receipt and owner signoff |
| P3M14-A04 | UI | Streaming پاسخ و امکان لغو | PARTIAL | NOT_ATTESTED | NO | Mac browser signed OIDC; pin exact source, environment, test receipt and owner signoff |
| P3M14-A05 | UI | نمایش Citation در سطح Claim | PARTIAL | NOT_ATTESTED | NO | Mac browser signed OIDC; pin exact source, environment, test receipt and owner signoff |
| P3M14-A06 | UI | نمایش صحیح نویسنده و سردبیر | PARTIAL | NOT_ATTESTED | NO | Mac browser signed OIDC; pin exact source, environment, test receipt and owner signoff |
| P3M14-A07 | UI | نمایش Confidence به زبان قابل فهم | PARTIAL | NOT_ATTESTED | NO | Mac browser signed OIDC; pin exact source, environment, test receipt and owner signoff |
| P3M14-A08 | UI | نمایش No-answer و سؤال روشن‌کننده | PARTIAL | NOT_ATTESTED | NO | Mac browser signed OIDC; pin exact source, environment, test receipt and owner signoff |
| P3M14-A09 | UI | Error/Retry state بدون تکرار پیام | PARTIAL | NOT_ATTESTED | NO | Mac browser signed OIDC; pin exact source, environment, test receipt and owner signoff |
| P3M14-A10 | UI | Accessibility پایه Keyboard، focus، contrast و screen-reader label | PARTIAL | NOT_ATTESTED | NO | Mac browser signed OIDC; pin exact source, environment, test receipt and owner signoff |
| P3M14-A11 | UI | تست موبایل و مرورگرهای هدف | PARTIAL | NOT_ATTESTED | NO | Mac browser signed OIDC; pin exact source, environment, test receipt and owner signoff |
| P3M14-A12 | UI | ممنوعیت نمایش اطلاعات Debug یا Prompt داخلی | PARTIAL | NOT_ATTESTED | NO | Mac browser signed OIDC; pin exact source, environment, test receipt and owner signoff |
| P3M15-A01 | DB+API+UI | ذخیره User message و Answer به‌صورت immutable event | PARTIAL | NOT_ATTESTED | NO | Consent/Feedback/Delete contract; pin exact source, environment, test receipt and owner signoff |
| P3M15-A02 | DB+API+UI | عنوان‌گذاری مکالمه بدون تغییر محتوای اصلی | PARTIAL | NOT_ATTESTED | NO | Consent/Feedback/Delete contract; pin exact source, environment, test receipt and owner signoff |
| P3M15-A03 | DB+API+UI | Pagination و مرتب‌سازی | PARTIAL | NOT_ATTESTED | NO | Consent/Feedback/Delete contract; pin exact source, environment, test receipt and owner signoff |
| P3M15-A04 | DB+API+UI | حذف مکالمه طبق Retention policy | PARTIAL | NOT_ATTESTED | NO | Consent/Feedback/Delete contract; pin exact source, environment, test receipt and owner signoff |
| P3M15-A05 | DB+API+UI | Feedback مثبت/منفی و دسته خطا | PARTIAL | NOT_ATTESTED | NO | Consent/Feedback/Delete contract; pin exact source, environment, test receipt and owner signoff |
| P3M15-A06 | DB+API+UI | ثبت Citation مشکل‌دار یا انتساب اشتباه | PARTIAL | NOT_ATTESTED | NO | Consent/Feedback/Delete contract; pin exact source, environment, test receipt and owner signoff |
| P3M15-A07 | DB+API+UI | جلوگیری از دسترسی کاربر دیگر | PARTIAL | NOT_ATTESTED | NO | Consent/Feedback/Delete contract; pin exact source, environment, test receipt and owner signoff |
| P3M15-A08 | DB+API+UI | Export ساخت‌یافته در صورت تصویب Scope | PARTIAL | NOT_ATTESTED | NO | Consent/Feedback/Delete contract; pin exact source, environment, test receipt and owner signoff |
| P3M15-A09 | DB+API+UI | Dataset بازخورد بدون PII برای ارزیابی بعدی | PARTIAL | NOT_ATTESTED | NO | Consent/Feedback/Delete contract; pin exact source, environment, test receipt and owner signoff |
| P3M15-A10 | DB+API+UI | تست Race condition و duplicate write | PARTIAL | NOT_ATTESTED | NO | Consent/Feedback/Delete contract; pin exact source, environment, test receipt and owner signoff |
| P3M16-A01 | Foundation | Structured log با Request/Trace ID | NOT_VERIFIED | NOT_ATTESTED | NO | Redacted tracing and alerts; pin exact source, environment, test receipt and owner signoff |
| P3M16-A02 | Foundation | Metricهای request، latency، error، retrieval و model | NOT_VERIFIED | NOT_ATTESTED | NO | Redacted tracing and alerts; pin exact source, environment, test receipt and owner signoff |
| P3M16-A03 | Foundation | Dashboard سلامت سرویس | NOT_VERIFIED | NOT_ATTESTED | NO | Redacted tracing and alerts; pin exact source, environment, test receipt and owner signoff |
| P3M16-A04 | Foundation | Alert برای Availability، error rate، DB pool و مصرف | NOT_VERIFIED | NOT_ATTESTED | NO | Redacted tracing and alerts; pin exact source, environment, test receipt and owner signoff |
| P3M16-A05 | Foundation | Audit event برای ورود و عملیات حساس | NOT_VERIFIED | NOT_ATTESTED | NO | Redacted tracing and alerts; pin exact source, environment, test receipt and owner signoff |
| P3M16-A06 | Foundation | Redaction داده مالی و Token | NOT_VERIFIED | NOT_ATTESTED | NO | Redacted tracing and alerts; pin exact source, environment, test receipt and owner signoff |
| P3M16-A07 | Foundation | ثبت نسخه Knowledge/Model/Policy | NOT_VERIFIED | NOT_ATTESTED | NO | Redacted tracing and alerts; pin exact source, environment, test receipt and owner signoff |
| P3M16-A08 | Foundation | Trace نمونه‌برداری‌شده برای مسیر پاسخ | NOT_VERIFIED | NOT_ATTESTED | NO | Redacted tracing and alerts; pin exact source, environment, test receipt and owner signoff |
| P3M16-A09 | Foundation | Runbook هشدارها | NOT_VERIFIED | NOT_ATTESTED | NO | Redacted tracing and alerts; pin exact source, environment, test receipt and owner signoff |
| P3M16-A10 | Foundation | تست اینکه PII و Secret در Log وجود ندارد | NOT_VERIFIED | NOT_ATTESTED | NO | Redacted tracing and alerts; pin exact source, environment, test receipt and owner signoff |
| P3M17-A01 | API | Rate limit بر اساس کاربر و IP | NOT_VERIFIED | NOT_ATTESTED | NO | Approved rate/budget/cache; pin exact source, environment, test receipt and owner signoff |
| P3M17-A02 | API | Daily quota و budget guard | NOT_VERIFIED | NOT_ATTESTED | NO | Approved rate/budget/cache; pin exact source, environment, test receipt and owner signoff |
| P3M17-A03 | API | Cache فقط برای خروجی‌های مجاز | NOT_VERIFIED | NOT_ATTESTED | NO | Approved rate/budget/cache; pin exact source, environment, test receipt and owner signoff |
| P3M17-A04 | API | Cache key شامل Release، Policy، Authority filter و Locale | NOT_VERIFIED | NOT_ATTESTED | NO | Approved rate/budget/cache; pin exact source, environment, test receipt and owner signoff |
| P3M17-A05 | API | ممنوعیت Cache مشترک برای پاسخ شخصی یا تاریخچه | NOT_VERIFIED | NOT_ATTESTED | NO | Approved rate/budget/cache; pin exact source, environment, test receipt and owner signoff |
| P3M17-A06 | API | TTL و invalidation هنگام Release جدید | NOT_VERIFIED | NOT_ATTESTED | NO | Approved rate/budget/cache; pin exact source, environment, test receipt and owner signoff |
| P3M17-A07 | API | Idempotency store | NOT_VERIFIED | NOT_ATTESTED | NO | Approved rate/budget/cache; pin exact source, environment, test receipt and owner signoff |
| P3M17-A08 | API | Queue/backpressure در پیک | NOT_VERIFIED | NOT_ATTESTED | NO | Approved rate/budget/cache; pin exact source, environment, test receipt and owner signoff |
| P3M17-A09 | API | تست bypass و cache poisoning | NOT_VERIFIED | NOT_ATTESTED | NO | Approved rate/budget/cache; pin exact source, environment, test receipt and owner signoff |
| P3M17-A10 | API | گزارش هزینه هر پاسخ موفق | NOT_VERIFIED | NOT_ATTESTED | NO | Approved rate/budget/cache; pin exact source, environment, test receipt and owner signoff |
| P3M18-A01 | Foundation | Dockerfile چندمرحله‌ای برای Web و API | PARTIAL | NOT_ATTESTED | NO | Isolated image scan/UID; pin exact source, environment, test receipt and owner signoff |
| P3M18-A02 | Foundation | اجرای process با کاربر غیر root | PARTIAL | NOT_ATTESTED | NO | Isolated image scan/UID; pin exact source, environment, test receipt and owner signoff |
| P3M18-A03 | Foundation | Healthcheck و startup dependency | PARTIAL | NOT_ATTESTED | NO | Isolated image scan/UID; pin exact source, environment, test receipt and owner signoff |
| P3M18-A04 | Foundation | Network segmentation | PARTIAL | NOT_ATTESTED | NO | Isolated image scan/UID; pin exact source, environment, test receipt and owner signoff |
| P3M18-A05 | Foundation | Volume و persistence policy | PARTIAL | NOT_ATTESTED | NO | Isolated image scan/UID; pin exact source, environment, test receipt and owner signoff |
| P3M18-A06 | Foundation | Secret injection در Runtime | PARTIAL | NOT_ATTESTED | NO | Isolated image scan/UID; pin exact source, environment, test receipt and owner signoff |
| P3M18-A07 | Foundation | محدودیت CPU/Memory | PARTIAL | NOT_ATTESTED | NO | Isolated image scan/UID; pin exact source, environment, test receipt and owner signoff |
| P3M18-A08 | Foundation | Image scanning و pin digest | PARTIAL | NOT_ATTESTED | NO | Isolated image scan/UID; pin exact source, environment, test receipt and owner signoff |
| P3M18-A09 | Foundation | Compose برای Local و Deployment | PARTIAL | NOT_ATTESTED | NO | Isolated image scan/UID; pin exact source, environment, test receipt and owner signoff |
| P3M18-A10 | Foundation | Cold-start و restart test | PARTIAL | NOT_ATTESTED | NO | Isolated image scan/UID; pin exact source, environment, test receipt and owner signoff |
| P3M19-A01 | Foundation | Lint، type check و unit tests | PARTIAL | NOT_ATTESTED | NO | Same-SHA integrated CI; pin exact source, environment, test receipt and owner signoff |
| P3M19-A02 | Foundation | Integration tests با سرویس‌های موقت | PARTIAL | NOT_ATTESTED | NO | Same-SHA integrated CI; pin exact source, environment, test receipt and owner signoff |
| P3M19-A03 | Foundation | Migration test | PARTIAL | NOT_ATTESTED | NO | Same-SHA integrated CI; pin exact source, environment, test receipt and owner signoff |
| P3M19-A04 | Foundation | Contract و security tests | PARTIAL | NOT_ATTESTED | NO | Same-SHA integrated CI; pin exact source, environment, test receipt and owner signoff |
| P3M19-A05 | Foundation | Build و scan Image | PARTIAL | NOT_ATTESTED | NO | Same-SHA integrated CI; pin exact source, environment, test receipt and owner signoff |
| P3M19-A06 | Foundation | تولید Release manifest و SBOM | PARTIAL | NOT_ATTESTED | NO | Same-SHA integrated CI; pin exact source, environment, test receipt and owner signoff |
| P3M19-A07 | Foundation | Deploy خودکار به Staging | PARTIAL | NOT_ATTESTED | NO | Same-SHA integrated CI; pin exact source, environment, test receipt and owner signoff |
| P3M19-A08 | Foundation | Approval دستی Production | PARTIAL | NOT_ATTESTED | NO | Same-SHA integrated CI; pin exact source, environment, test receipt and owner signoff |
| P3M19-A09 | Foundation | Rollback workflow | PARTIAL | NOT_ATTESTED | NO | Same-SHA integrated CI; pin exact source, environment, test receipt and owner signoff |
| P3M19-A10 | Foundation | نگهداری Artifact و Test report | PARTIAL | NOT_ATTESTED | NO | Same-SHA integrated CI; pin exact source, environment, test receipt and owner signoff |
| P3M19-A11 | Foundation | Branch protection و ممنوعیت Secret در log | PARTIAL | NOT_ATTESTED | NO | Same-SHA integrated CI; pin exact source, environment, test receipt and owner signoff |
| P3M20-A01 | Foundation | Provision محیط Staging نزدیک به Production | NOT_RUN | NOT_ATTESTED | NO | Mac 7-service L2 E2E; pin exact source, environment, test receipt and owner signoff |
| P3M20-A02 | Foundation | TLS و Domain آزمایشی | NOT_RUN | NOT_ATTESTED | NO | Mac 7-service L2 E2E; pin exact source, environment, test receipt and owner signoff |
| P3M20-A03 | Foundation | داده Test غیرشخصی | NOT_RUN | NOT_ATTESTED | NO | Mac 7-service L2 E2E; pin exact source, environment, test receipt and owner signoff |
| P3M20-A04 | Foundation | اجرای Migration | NOT_RUN | NOT_ATTESTED | NO | Mac 7-service L2 E2E; pin exact source, environment, test receipt and owner signoff |
| P3M20-A05 | Foundation | بارگذاری Release پذیرفته‌شده فاز ۲ | NOT_RUN | NOT_ATTESTED | NO | Mac 7-service L2 E2E; pin exact source, environment, test receipt and owner signoff |
| P3M20-A06 | Foundation | Smoke و E2E | NOT_RUN | NOT_ATTESTED | NO | Mac 7-service L2 E2E; pin exact source, environment, test receipt and owner signoff |
| P3M20-A07 | Foundation | تست سه منبع و چهار نوع Citation | NOT_RUN | NOT_ATTESTED | NO | Mac 7-service L2 E2E; pin exact source, environment, test receipt and owner signoff |
| P3M20-A08 | Foundation | تست نویسنده/سردبیر | NOT_RUN | NOT_ATTESTED | NO | Mac 7-service L2 E2E; pin exact source, environment, test receipt and owner signoff |
| P3M20-A09 | Foundation | تست No-answer و Safety | NOT_RUN | NOT_ATTESTED | NO | Mac 7-service L2 E2E; pin exact source, environment, test receipt and owner signoff |
| P3M20-A10 | Foundation | تست Restart و dependency outage | NOT_RUN | NOT_ATTESTED | NO | Mac 7-service L2 E2E; pin exact source, environment, test receipt and owner signoff |
| P3M20-A11 | Foundation | UAT کارفرما و ثبت Issue | NOT_RUN | NOT_ATTESTED | NO | Mac 7-service L2 E2E; pin exact source, environment, test receipt and owner signoff |
| P3M21-A01 | Foundation | Threat model برای Web، API، DB، Qdrant و Model gateway | NOT_VERIFIED | NOT_ATTESTED | NO | OWASP/PII scan; pin exact source, environment, test receipt and owner signoff |
| P3M21-A02 | Foundation | تست OWASP API/Web متناسب | NOT_VERIFIED | NOT_ATTESTED | NO | OWASP/PII scan; pin exact source, environment, test receipt and owner signoff |
| P3M21-A03 | Foundation | تست prompt injection و data exfiltration | NOT_VERIFIED | NOT_ATTESTED | NO | OWASP/PII scan; pin exact source, environment, test receipt and owner signoff |
| P3M21-A04 | Foundation | تست IDOR و RLS bypass | NOT_VERIFIED | NOT_ATTESTED | NO | OWASP/PII scan; pin exact source, environment, test receipt and owner signoff |
| P3M21-A05 | Foundation | TLS، headerهای امنیتی و CORS | NOT_VERIFIED | NOT_ATTESTED | NO | OWASP/PII scan; pin exact source, environment, test receipt and owner signoff |
| P3M21-A06 | Foundation | Dependency و image scan | NOT_VERIFIED | NOT_ATTESTED | NO | OWASP/PII scan; pin exact source, environment, test receipt and owner signoff |
| P3M21-A07 | Foundation | Consent و Retention validation | NOT_VERIFIED | NOT_ATTESTED | NO | OWASP/PII scan; pin exact source, environment, test receipt and owner signoff |
| P3M21-A08 | Foundation | Account/data deletion test | NOT_VERIFIED | NOT_ATTESTED | NO | OWASP/PII scan; pin exact source, environment, test receipt and owner signoff |
| P3M21-A09 | Foundation | Incident response tabletop | NOT_VERIFIED | NOT_ATTESTED | NO | OWASP/PII scan; pin exact source, environment, test receipt and owner signoff |
| P3M21-A10 | Foundation | ثبت Risk acceptanceهای باقی‌مانده | NOT_VERIFIED | NOT_ATTESTED | NO | OWASP/PII scan; pin exact source, environment, test receipt and owner signoff |
| P3M22-A01 | DB/Ops | Backup نسخه‌دار PostgreSQL | PARTIAL | NOT_ATTESTED | NO | Restore and RPO/RTO; pin exact source, environment, test receipt and owner signoff |
| P3M22-A02 | DB/Ops | Snapshot و Restore Qdrant | PARTIAL | NOT_ATTESTED | NO | Restore and RPO/RTO; pin exact source, environment, test receipt and owner signoff |
| P3M22-A03 | DB/Ops | Backup Config و Release pointer | PARTIAL | NOT_ATTESTED | NO | Restore and RPO/RTO; pin exact source, environment, test receipt and owner signoff |
| P3M22-A04 | DB/Ops | رمزگذاری و دسترسی محدود Backup | PARTIAL | NOT_ATTESTED | NO | Restore and RPO/RTO; pin exact source, environment, test receipt and owner signoff |
| P3M22-A05 | DB/Ops | Retention و rotation | PARTIAL | NOT_ATTESTED | NO | Restore and RPO/RTO; pin exact source, environment, test receipt and owner signoff |
| P3M22-A06 | DB/Ops | Restore در محیط خالی | PARTIAL | NOT_ATTESTED | NO | Restore and RPO/RTO; pin exact source, environment, test receipt and owner signoff |
| P3M22-A07 | DB/Ops | Point-in-time recovery در صورت امکان زیرساخت | PARTIAL | NOT_ATTESTED | NO | Restore and RPO/RTO; pin exact source, environment, test receipt and owner signoff |
| P3M22-A08 | DB/Ops | اندازه‌گیری RPO/RTO واقعی | PARTIAL | NOT_ATTESTED | NO | Restore and RPO/RTO; pin exact source, environment, test receipt and owner signoff |
| P3M22-A09 | DB/Ops | تست خرابی جزئی و کامل | PARTIAL | NOT_ATTESTED | NO | Restore and RPO/RTO; pin exact source, environment, test receipt and owner signoff |
| P3M22-A10 | DB/Ops | Runbook و گزارش Restore | PARTIAL | NOT_ATTESTED | NO | Restore and RPO/RTO; pin exact source, environment, test receipt and owner signoff |
| P3M23-A01 | Foundation | Freeze workload model با اعداد تأییدشده | NOT_RUN | NOT_ATTESTED | NO | Frozen load thresholds; pin exact source, environment, test receipt and owner signoff |
| P3M23-A02 | Foundation | Baseline p50/p95/p99 | NOT_RUN | NOT_ATTESTED | NO | Frozen load thresholds; pin exact source, environment, test receipt and owner signoff |
| P3M23-A03 | Foundation | Load، stress و soak test | NOT_RUN | NOT_ATTESTED | NO | Frozen load thresholds; pin exact source, environment, test receipt and owner signoff |
| P3M23-A04 | Foundation | اندازه‌گیری saturation | NOT_RUN | NOT_ATTESTED | NO | Frozen load thresholds; pin exact source, environment, test receipt and owner signoff |
| P3M23-A05 | Foundation | Failure injection کنترل‌شده | NOT_RUN | NOT_ATTESTED | NO | Frozen load thresholds; pin exact source, environment, test receipt and owner signoff |
| P3M23-A06 | Foundation | تحلیل Queue و timeout | NOT_RUN | NOT_ATTESTED | NO | Frozen load thresholds; pin exact source, environment, test receipt and owner signoff |
| P3M23-A07 | Foundation | بررسی DB pool و Index latency | NOT_RUN | NOT_ATTESTED | NO | Frozen load thresholds; pin exact source, environment, test receipt and owner signoff |
| P3M23-A08 | Foundation | اندازه‌گیری هزینه هر پاسخ | NOT_RUN | NOT_ATTESTED | NO | Frozen load thresholds; pin exact source, environment, test receipt and owner signoff |
| P3M23-A09 | Foundation | Capacity report و tuning | NOT_RUN | NOT_ATTESTED | NO | Frozen load thresholds; pin exact source, environment, test receipt and owner signoff |
| P3M23-A10 | Foundation | Regression threshold | NOT_RUN | NOT_ATTESTED | NO | Frozen load thresholds; pin exact source, environment, test receipt and owner signoff |
| P3M24-A01 | Foundation | Go/No-Go checklist | NOT_RUN | NOT_ATTESTED | NO | Go/No-Go + rollback approval; pin exact source, environment, test receipt and owner signoff |
| P3M24-A02 | Foundation | Freeze Image digest، DB migration و Knowledge release | NOT_RUN | NOT_ATTESTED | NO | Go/No-Go + rollback approval; pin exact source, environment, test receipt and owner signoff |
| P3M24-A03 | Foundation | Backup قبل از استقرار | NOT_RUN | NOT_ATTESTED | NO | Go/No-Go + rollback approval; pin exact source, environment, test receipt and owner signoff |
| P3M24-A04 | Foundation | اجرای Deployment کنترل‌شده | NOT_RUN | NOT_ATTESTED | NO | Go/No-Go + rollback approval; pin exact source, environment, test receipt and owner signoff |
| P3M24-A05 | Foundation | Migration و health verification | NOT_RUN | NOT_ATTESTED | NO | Go/No-Go + rollback approval; pin exact source, environment, test receipt and owner signoff |
| P3M24-A06 | Foundation | Smoke test با حساب آزمایشی | NOT_RUN | NOT_ATTESTED | NO | Go/No-Go + rollback approval; pin exact source, environment, test receipt and owner signoff |
| P3M24-A07 | Foundation | فعال‌سازی محدود کاربران اولیه | NOT_RUN | NOT_ATTESTED | NO | Go/No-Go + rollback approval; pin exact source, environment, test receipt and owner signoff |
| P3M24-A08 | Foundation | پایش Error، latency، cost و safety | NOT_RUN | NOT_ATTESTED | NO | Go/No-Go + rollback approval; pin exact source, environment, test receipt and owner signoff |
| P3M24-A09 | Foundation | Rollback در عبور از Threshold | NOT_RUN | NOT_ATTESTED | NO | Go/No-Go + rollback approval; pin exact source, environment, test receipt and owner signoff |
| P3M24-A10 | Foundation | ثبت زمان، نسخه‌ها و مسئول تصمیم | NOT_RUN | NOT_ATTESTED | NO | Go/No-Go + rollback approval; pin exact source, environment, test receipt and owner signoff |
| P3M24-A11 | Foundation | Production acceptance report | NOT_RUN | NOT_ATTESTED | NO | Go/No-Go + rollback approval; pin exact source, environment, test receipt and owner signoff |
| P3M25-A01 | Foundation | بازه Hypercare با مالک مشخص | NOT_RUN | NOT_ATTESTED | NO | Actual launch+hypercare; pin exact source, environment, test receipt and owner signoff |
| P3M25-A02 | Foundation | دسته‌بندی Incident و SLA پاسخ داخلی | NOT_RUN | NOT_ATTESTED | NO | Actual launch+hypercare; pin exact source, environment, test receipt and owner signoff |
| P3M25-A03 | Foundation | مرور روزانه Error، latency، Citation و Safety | NOT_RUN | NOT_ATTESTED | NO | Actual launch+hypercare; pin exact source, environment, test receipt and owner signoff |
| P3M25-A04 | Foundation | تحلیل Feedback کاربران اولیه | NOT_RUN | NOT_ATTESTED | NO | Actual launch+hypercare; pin exact source, environment, test receipt and owner signoff |
| P3M25-A05 | Foundation | اصلاح فقط Bugهای فاز ۳ و جلوگیری از Scope creep | NOT_RUN | NOT_ATTESTED | NO | Actual launch+hypercare; pin exact source, environment, test receipt and owner signoff |
| P3M25-A06 | Foundation | Freeze Baseline عملیاتی پس از پایداری | NOT_RUN | NOT_ATTESTED | NO | Actual launch+hypercare; pin exact source, environment, test receipt and owner signoff |
| P3M25-A07 | Foundation | ساخت Runbook بهره‌برداری | NOT_RUN | NOT_ATTESTED | NO | Actual launch+hypercare; pin exact source, environment, test receipt and owner signoff |
| P3M25-A08 | Foundation | انتقال دانش به تیم نگهداری | NOT_RUN | NOT_ATTESTED | NO | Actual launch+hypercare; pin exact source, environment, test receipt and owner signoff |
| P3M25-A09 | Foundation | تعریف Contract فاز ۴ برای Profile، Assessment، Goals و Action Plan | NOT_RUN | NOT_ATTESTED | NO | Actual launch+hypercare; pin exact source, environment, test receipt and owner signoff |
| P3M25-A10 | Foundation | ثبت Tech debt و Deferred decisions | NOT_RUN | NOT_ATTESTED | NO | Actual launch+hypercare; pin exact source, environment, test receipt and owner signoff |
| P3M25-A11 | Foundation | Phase 3 closure report | NOT_RUN | NOT_ATTESTED | NO | Actual launch+hypercare; pin exact source, environment, test receipt and owner signoff |

## 26 independent module Gates

| Gate | Module | Starting state | This audit decision | Evidence needed |
|---|---|---|---|---|
| P3M00 | phase2_handoff_acceptance | NOT_VERIFIED snapshot | NOT_ACCEPTED | Accepted Phase2 Release/NB23 |
| P3M01 | architecture_slo_and_scope_freeze | NOT_VERIFIED snapshot | NOT_ACCEPTED | Approved scope/SLO/cost/RPO/RTO |
| P3M02 | environment_and_security_baseline | PARTIAL snapshot | NOT_ACCEPTED | Image/wheel lock security scan |
| P3M03 | project_structure_and_contracts | PARTIAL snapshot | NOT_ACCEPTED | Cross-service contract L2 |
| P3M04 | database_schema_and_migrations | PARTIAL snapshot | NOT_ACCEPTED | DB PG migration/retention |
| P3M05 | authentication_and_sessions | PARTIAL snapshot | NOT_ACCEPTED | Real OIDC HTTPS signed A/B session |
| P3M06 | tenant_isolation_and_rls | PARTIAL snapshot | NOT_ACCEPTED | Real RLS A/B scope |
| P3M07 | knowledge_release_loader | PARTIAL snapshot | NOT_ACCEPTED | Accepted Release and Qdrant |
| P3M08 | retrieval_runtime | PARTIAL snapshot | NOT_ACCEPTED | Real C018/PG/Qdrant |
| P3M09 | model_gateway | NOT_VERIFIED snapshot | NOT_ACCEPTED | C019 producer + cost approval |
| P3M10 | answer_orchestration | PARTIAL snapshot | NOT_ACCEPTED | T3 proof/Claim/Answer |
| P3M11 | citation_and_attribution_delivery | PARTIAL snapshot | NOT_ACCEPTED | Typed locator/attribution |
| P3M12 | safety_no_answer_and_policy | NOT_VERIFIED snapshot | NOT_ACCEPTED | Approved Farsi red-team policy |
| P3M13 | product_api | PARTIAL snapshot | NOT_ACCEPTED | Signed HTTP POST/GET L2 |
| P3M14 | web_chat_interface | PARTIAL snapshot | NOT_ACCEPTED | Mac browser signed OIDC |
| P3M15 | conversation_history_and_feedback | PARTIAL snapshot | NOT_ACCEPTED | Consent/Feedback/Delete contract |
| P3M16 | observability_and_audit | NOT_VERIFIED snapshot | NOT_ACCEPTED | Redacted tracing and alerts |
| P3M17 | cache_rate_limit_and_cost_control | NOT_VERIFIED snapshot | NOT_ACCEPTED | Approved rate/budget/cache |
| P3M18 | containerization_and_networking | PARTIAL snapshot | NOT_ACCEPTED | Isolated image scan/UID |
| P3M19 | ci_cd_and_release_pipeline | PARTIAL snapshot | NOT_ACCEPTED | Same-SHA integrated CI |
| P3M20 | staging_deployment_and_e2e | NOT_RUN snapshot | NOT_ACCEPTED | Mac 7-service L2 E2E |
| P3M21 | security_privacy_and_threat_validation | NOT_VERIFIED snapshot | NOT_ACCEPTED | OWASP/PII scan |
| P3M22 | backup_restore_and_disaster_recovery | PARTIAL snapshot | NOT_ACCEPTED | Restore and RPO/RTO |
| P3M23 | performance_load_and_failure_testing | NOT_RUN snapshot | NOT_ACCEPTED | Frozen load thresholds |
| P3M24 | production_launch | NOT_RUN snapshot | NOT_ACCEPTED | Go/No-Go + rollback approval |
| P3M25 | hypercare_and_phase4_handoff | NOT_RUN snapshot | NOT_ACCEPTED | Actual launch+hypercare |

## Completion and reproducibility

The operational roadmap contains **103 P3OP overlays** (non-counting); the submitted complete audit attachment indexes all of them. This GitHub note indexes all 262 canonical rows and every Gate, but does not silently mark any full gate as passed based on the 275 L1 tests. Exact final HEAD, tested SHA, integrated SHA and Mac deployed SHA must be independently recorded after any downstream patch; the currently observed #55 cannot be promoted to the API #61 / UI #62 / DB #59 combination without proof.

Run actual unit/integration/contract checks on the final integrated commit; do signed Mac L2 with appropriate permission; obtain no-generation single-C018 OS audit; only then consider C019/DB011 and real T3 under separate scope; finish security/backup/load/UAT/Go-NoGo/hypercare independently. **New accepted row count in this audit: 0; full phase3 percentage: NOT_DETERMINABLE** without direct same-SHA per-ID evidence. This documentation-only handoff has not executed or authorized a Mac operation or an external paid model call.
