# پایگاه‌داده | نقشه، چک‌لیست و وضعیت اجرای فاز سه

**مبنای گزارش:** آخرین تحویل بررسی‌شدهٔ ۲۳ نوامبر ۲۰۲۶. **پیشرفت تخصصی:** ۷٪ DONE محدود (۴/۵۷)؛ ۲۹ OPEN و ۲۴ BLOCKED؛ پذیرش محصول هنوز ثبت نشده.

## ۱. سهم این چت از نقشهٔ اصلی

- ماژول‌های اصلی این مأموریت: M04، M06، M22.
- ماژول‌های مشترک: M03، M05، M10، M13، M15.
- سایر ماژول‌های دارای وابستگی و شاهد مصرفی: M02، M16، M18، M19، M20، M21، M23، M24، M25.
- مالک هر ردیف از رجیستر خوانده می‌شود. گروه‌بندی ماژول‌ها جایگزین مالکیت رسمی ردیف نیست. ردیف‌های مشترک فقط یک بار در پیشرفت کل شمارش می‌شوند.
- [نقشهٔ ماژولار اصلی](https://github.com/Shahbazi-Amir/RAG_finance/blob/7c74783c3dcda897b010ba9ea358d113f172ed1f/data/Road_Maps/RAG_finance_phase3_modular_execution_plan.md) · [نقشهٔ عملیاتی اصلی](https://github.com/Shahbazi-Amir/RAG_finance/blob/7c74783c3dcda897b010ba9ea358d113f172ed1f/data/Road_Maps/RAG_finance_phase3_operational_roadmap.md)

## ۲. کارهای انجام‌شده و شاهد هر تحویل

| تحویل | کار انجام‌شده و دامنهٔ شاهد | شاهد |
|---|---|---|
| بستهٔ پایه PostgreSQL 17.11 | 001–010 پین‌شده، DB55 no-dispatch، TLS، نقش‌ها، RLS، Restore مستقل و rollback محدود در CI. | [شاهد GitHub](https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/45109023781) |
| ارتقای داده‌دار | 009–010 روی دو کلاستر با Backup پیش از ارتقا، حفظ داده و نشست دو مالک و RLS؛ M04-A07. | [شاهد GitHub](https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/45199834089) |
| تحویل جدید 996dfc9 | کنترل Ledger نیمه‌تمام و مغایرت، Query Plan با ۲۴۰۰ مکالمه و ۴۸۰۰ پیام مصنوعی، Blob جدید نصب‌کنندهٔ 03. CI پایه سبز و 011 اختیاری SKIPPED. | [شاهد GitHub](https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/45202743968) |

این بخش پیشرفت اجرایی و مستنداتی را نشان می‌دهد. آزمون GitHub ایزوله و شاهد مقصد در رجیستر جدا ثبت می‌شوند.

## ۳. کارهای باقی‌مانده و ترتیب اجرا

- [ ] **M04/M06** — ERD و migration/privilege/RLS را روی SHA ادغام‌شده و نقش‌های واقعی تأیید کن. Foundation نسخه installer 03 و اسکریپت‌های 15–17 را پین کند.
- [ ] **M05/M13/M15** — Product/Bootstrap و signed HTTP در مقصد، fence و idempotency و قراردادهای Consent/Feedback/Deletion را با API/UI ببند.
- [ ] **M22/M23** — Backup رمزگذاری‌شده، Restore مستقل، حذف بدون بازگشت، RPO/RTO و بار/Query Plan نماینده را با سیاست مصوب تحویل بده. 011 فقط در مسیر مستقل.

## ۴. چک‌لیست تمام فعالیت‌های مرتبط در رجیستر

این نمای اجرا 171 شناسه دارد. هر شناسه یک‌بار در این بخش آمده و شامل فعالیت‌های مستقیم و وابسته است. ستون وضعیت، snapshot مشترک Foundation است و شواهد تازه‌تر در بخش ۲ و پیوست آمده‌اند. برای هر ردیف، شاهد موجود را کنترل کن و مانده را تا معیار پذیرش همان ردیف اجرا کن. تیک نهایی پس از تأیید مقصد و مالک پذیرش ثبت شود.

### P3M02 · environment_and_security_baseline

| چک | فعالیت و معیار | مالک | شاهد ثبت‌شده در ماتریس | ورودی یا اقدام باقی‌مانده |
|---|---|---|---|---|
| ☐ P3M02-A01 | **Output:** Freeze نسخه Python، Node، PostgreSQL، Qdrant، Redis و Docker; **Check:** clean build and security scan in a separately authorized environment | Foundation; environment owner pending; M01 | PARTIAL · API61 exact lock present; engine lock/wheelhouse unresolved; Docker scan not run | ENGINE+SERVER/Ops: original engine lock/wheelhouse/ABI, image digest/SBOM/scan, isolated Mac snapshot & Build receipts; verify per target SHA and mode |
| ☐ P3M02-A02 | **Output:** ساخت lockfileهای وابستگی; **Check:** versioned artifact plus reproducible source-specific acceptance check and evidence | Foundation; environment owner pending; M01 | PARTIAL · API61 exact lock present; engine lock/wheelhouse unresolved; Docker scan not run | ENGINE+SERVER/Ops: original engine lock/wheelhouse/ABI, image digest/SBOM/scan, isolated Mac snapshot & Build receipts; verify per target SHA and mode |
| ☐ P3M02-A03 | **Output:** تعریف `.env.example` بدون Secret; **Check:** policy-controlled privacy and leakage negative checks, no assumed success | Foundation; environment owner pending; M01 | PARTIAL · API61 exact lock present; engine lock/wheelhouse unresolved; Docker scan not run | ENGINE+SERVER/Ops: original engine lock/wheelhouse/ABI, image digest/SBOM/scan, isolated Mac snapshot & Build receipts; verify per target SHA and mode |
| ☐ P3M02-A04 | **Output:** ممنوع‌کردن Secret در Repository; **Check:** policy-controlled privacy and leakage negative checks, no assumed success | Foundation; environment owner pending; M01 | PARTIAL · API61 exact lock present; engine lock/wheelhouse unresolved; Docker scan not run | ENGINE+SERVER/Ops: original engine lock/wheelhouse/ABI, image digest/SBOM/scan, isolated Mac snapshot & Build receipts; verify per target SHA and mode |
| ☐ P3M02-A05 | **Output:** فعال‌کردن Dependency و Secret scanning; **Check:** policy-controlled privacy and leakage negative checks, no assumed success | Foundation; environment owner pending; M01 | PARTIAL · API61 exact lock present; engine lock/wheelhouse unresolved; Docker scan not run | ENGINE+SERVER/Ops: original engine lock/wheelhouse/ABI, image digest/SBOM/scan, isolated Mac snapshot & Build receipts; verify per target SHA and mode |
| ☐ P3M02-A06 | **Output:** تنظیم Lint، Type check و Test command واحد; **Check:** clean build and security scan in a separately authorized environment | Foundation; environment owner pending; M01 | PARTIAL · API61 exact lock present; engine lock/wheelhouse unresolved; Docker scan not run | ENGINE+SERVER/Ops: original engine lock/wheelhouse/ABI, image digest/SBOM/scan, isolated Mac snapshot & Build receipts; verify per target SHA and mode |
| ☐ P3M02-A07 | **Output:** ساخت SBOM و گزارش Dependency; **Check:** clean build and security scan in a separately authorized environment | Foundation; environment owner pending; M01 | PARTIAL · API61 exact lock present; engine lock/wheelhouse unresolved; Docker scan not run | ENGINE+SERVER/Ops: original engine lock/wheelhouse/ABI, image digest/SBOM/scan, isolated Mac snapshot & Build receipts; verify per target SHA and mode |
| ☐ P3M02-A08 | **Output:** ثبت Timezone، Locale و Encoding; **Check:** versioned artifact plus reproducible source-specific acceptance check and evidence | Foundation; environment owner pending; M01 | PARTIAL · API61 exact lock present; engine lock/wheelhouse unresolved; Docker scan not run | ENGINE+SERVER/Ops: original engine lock/wheelhouse/ABI, image digest/SBOM/scan, isolated Mac snapshot & Build receipts; verify per target SHA and mode |
| ☐ P3M02-A09 | **Output:** تعیین Log redaction policy; **Check:** policy-controlled privacy and leakage negative checks, no assumed success | Foundation; environment owner pending; M01 | PARTIAL · API61 exact lock present; engine lock/wheelhouse unresolved; Docker scan not run | ENGINE+SERVER/Ops: original engine lock/wheelhouse/ABI, image digest/SBOM/scan, isolated Mac snapshot & Build receipts; verify per target SHA and mode |
| ☐ P3M02-A10 | **Output:** ساخت Environment manifest.; **Check:** compare actual hashes and versioned manifests; zero mismatches | Foundation; environment owner pending; M01 | PARTIAL · API61 exact lock present; engine lock/wheelhouse unresolved; Docker scan not run | ENGINE+SERVER/Ops: original engine lock/wheelhouse/ABI, image digest/SBOM/scan, isolated Mac snapshot & Build receipts; verify per target SHA and mode |

### P3M03 · project_structure_and_contracts

| چک | فعالیت و معیار | مالک | شاهد ثبت‌شده در ماتریس | ورودی یا اقدام باقی‌مانده |
|---|---|---|---|---|
| ☐ P3M03-A01 | **Output:** تعریف مرز Domain moduleها; **Check:** versioned artifact plus reproducible source-specific acceptance check and evidence | Foundation + API/UI/DB; M01-M02 | PARTIAL · API source/schema code present; same-SHA cross-service CI does not imply Mac; OWNER_L1_SOURCE_CI: https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/45081955496 (API61 L1 275 tests; not Mac); OWNER_L1_SOURCE_CI: https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/45108323298 (UI62 L1 Node115/Chromium synthetic) | Owner must provide exact artifact SHA, environment and positive/negative acceptance witness; supervisor approval remains separate; REAL_CROSS_SERVICE_CONTRACT_ACCEPTANCE; original row criterion: تعریف مرز Domain moduleها; owner must deliver versioned artifact, SHA and ta |
| ☐ P3M03-A02 | **Output:** تعریف Error model مشترک; **Check:** versioned artifact plus reproducible source-specific acceptance check and evidence | Foundation + API/UI/DB; M01-M02 | PARTIAL · API source/schema code present; same-SHA cross-service CI does not imply Mac; OWNER_L1_SOURCE_CI: https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/45081955496 (API61 L1 275 tests; not Mac); OWNER_L1_SOURCE_CI: https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/45108323298 (UI62 L1 Node115/Chromium synthetic) | Owner must provide exact artifact SHA, environment and positive/negative acceptance witness; supervisor approval remains separate; REAL_CROSS_SERVICE_CONTRACT_ACCEPTANCE; original row criterion: تعریف Error model مشترک; owner must deliver versioned artifact, SHA and targ |
| ☐ P3M03-A03 | **Output:** تعریف Request ID و Trace ID; **Check:** server-issued trace correlation, redaction and alert test evidence | Foundation + API/UI/DB; M01-M02 | PARTIAL · API source/schema code present; same-SHA cross-service CI does not imply Mac; OWNER_L1_SOURCE_CI: https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/45081955496 (API61 L1 275 tests; not Mac); OWNER_L1_SOURCE_CI: https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/45108323298 (UI62 L1 Node115/Chromium synthetic) | Owner must provide exact artifact SHA, environment and positive/negative acceptance witness; supervisor approval remains separate; REAL_CROSS_SERVICE_CONTRACT_ACCEPTANCE; original row criterion: تعریف Request ID و Trace ID; owner must deliver versioned artifact, SHA and  |
| ☐ P3M03-A04 | **Output:** نسخه‌بندی API از `/v1`; **Check:** versioned artifact plus reproducible source-specific acceptance check and evidence | Foundation + API/UI/DB; M01-M02 | PARTIAL · API source/schema code present; same-SHA cross-service CI does not imply Mac; OWNER_L1_SOURCE_CI: https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/45081955496 (API61 L1 275 tests; not Mac); OWNER_L1_SOURCE_CI: https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/45108323298 (UI62 L1 Node115/Chromium synthetic) | Owner must provide exact artifact SHA, environment and positive/negative acceptance witness; supervisor approval remains separate; REAL_CROSS_SERVICE_CONTRACT_ACCEPTANCE; original row criterion: نسخه‌بندی API از `/v1`; owner must deliver versioned artifact, SHA and targe |
| ☐ P3M03-A05 | **Output:** ساخت Schemaهای User، Conversation، Message، Answer و Citation; **Check:** run positive/negative Schema and version compatibility checks | Foundation + API/UI/DB; M01-M02 | PARTIAL · API source/schema code present; same-SHA cross-service CI does not imply Mac; OWNER_L1_SOURCE_CI: https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/45081955496 (API61 L1 275 tests; not Mac); OWNER_L1_SOURCE_CI: https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/45108323298 (UI62 L1 Node115/Chromium synthetic) | Owner must provide exact artifact SHA, environment and positive/negative acceptance witness; supervisor approval remains separate; REAL_CROSS_SERVICE_CONTRACT_ACCEPTANCE; original row criterion: ساخت Schemaهای User، Conversation، Message، Answer و Citation; owner must de |
| ☐ P3M03-A06 | **Output:** تعریف فیلدهای Attribution; **Check:** source-aware provenance and permission checks; no invented locator or attribution | Foundation + API/UI/DB; M01-M02 | PARTIAL · API source/schema code present; same-SHA cross-service CI does not imply Mac; OWNER_L1_SOURCE_CI: https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/45081955496 (API61 L1 275 tests; not Mac); OWNER_L1_SOURCE_CI: https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/45108323298 (UI62 L1 Node115/Chromium synthetic) | Owner must provide exact artifact SHA, environment and positive/negative acceptance witness; supervisor approval remains separate; REAL_CROSS_SERVICE_CONTRACT_ACCEPTANCE; original row criterion: تعریف فیلدهای Attribution; owner must deliver versioned artifact, SHA and ta |
| ☐ P3M03-A07 | **Output:** تعریف Compatibility policy; **Check:** versioned artifact plus reproducible source-specific acceptance check and evidence | Foundation + API/UI/DB; M01-M02 | PARTIAL · API source/schema code present; same-SHA cross-service CI does not imply Mac; OWNER_L1_SOURCE_CI: https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/45081955496 (API61 L1 275 tests; not Mac); OWNER_L1_SOURCE_CI: https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/45108323298 (UI62 L1 Node115/Chromium synthetic) | Owner must provide exact artifact SHA, environment and positive/negative acceptance witness; supervisor approval remains separate; REAL_CROSS_SERVICE_CONTRACT_ACCEPTANCE; original row criterion: تعریف Compatibility policy; owner must deliver versioned artifact, SHA and t |
| ☐ P3M03-A08 | **Output:** ساخت Contract tests بین Backend، Frontend و RAG runtime; **Check:** separate synthetic L1 and real L2; L2 remains NOT_RUN | Foundation + API/UI/DB; M01-M02 | PARTIAL · API source/schema code present; same-SHA cross-service CI does not imply Mac; OWNER_L1_SOURCE_CI: https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/45081955496 (API61 L1 275 tests; not Mac); OWNER_L1_SOURCE_CI: https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/45108323298 (UI62 L1 Node115/Chromium synthetic) | Owner must provide exact artifact SHA, environment and positive/negative acceptance witness; supervisor approval remains separate; REAL_CROSS_SERVICE_CONTRACT_ACCEPTANCE; original row criterion: ساخت Contract tests بین Backend، Frontend و RAG runtime; owner must deliver  |
| ☐ P3M03-A09 | **Output:** ساخت Architecture dependency test برای جلوگیری از Import معکوس.; **Check:** dated approved decision, diagrams/risk register and explicit Gate owner | Foundation + API/UI/DB; M01-M02 | PARTIAL · API source/schema code present; same-SHA cross-service CI does not imply Mac; OWNER_L1_SOURCE_CI: https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/45081955496 (API61 L1 275 tests; not Mac); OWNER_L1_SOURCE_CI: https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/45108323298 (UI62 L1 Node115/Chromium synthetic) | Owner must provide exact artifact SHA, environment and positive/negative acceptance witness; supervisor approval remains separate; REAL_CROSS_SERVICE_CONTRACT_ACCEPTANCE; original row criterion: ساخت Architecture dependency test برای جلوگیری از Import معکوس.; owner must  |

### P3M04 · database_schema_and_migrations

| چک | فعالیت و معیار | مالک | شاهد ثبت‌شده در ماتریس | ورودی یا اقدام باقی‌مانده |
|---|---|---|---|---|
| ☐ P3M04-A01 | **Output:** طراحی ERD و Data dictionary; **Check:** ERD/Data Dictionary reviewed by API/DB, DB01-02 still DRAFT | DB; M03; retention policy | PARTIAL · Isolated PG17.11 DB59 lab + independent restore evidence run 45082326382; Mac pending; OWNER_ISOLATED_DB_CI: https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/45109023781 (DB0e PG17 main PASS; optional 011 SKIPPED) | DBA+SERVER/Ops: approved isolated PG17.11 001-010 migration ledger, role/TLS, actual backup/restore and A/B results; avoid 011 without separate authorization |
| ☐ P3M04-A02 | **Output:** تعریف Primary/Foreign key و Index; **Check:** test database constraints and query plans, including negative cases | DB; M03; retention policy | PARTIAL · Isolated PG17.11 DB59 lab + independent restore evidence run 45082326382; Mac pending; OWNER_ISOLATED_DB_CI: https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/45109023781 (DB0e PG17 main PASS; optional 011 SKIPPED) | DBA+SERVER/Ops: approved isolated PG17.11 001-010 migration ledger, role/TLS, actual backup/restore and A/B results; avoid 011 without separate authorization |
| ☐ P3M04-A03 | **Output:** افزودن `user_id` به تمام داده‌های کاربر; **Check:** versioned artifact plus reproducible source-specific acceptance check and evidence | DB; M03; retention policy | PARTIAL · Isolated PG17.11 DB59 lab + independent restore evidence run 45082326382; Mac pending; OWNER_ISOLATED_DB_CI: https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/45109023781 (DB0e PG17 main PASS; optional 011 SKIPPED) | DBA+SERVER/Ops: approved isolated PG17.11 001-010 migration ledger, role/TLS, actual backup/restore and A/B results; avoid 011 without separate authorization |
| ☐ P3M04-A04 | **Output:** ذخیره Citation و Attribution به‌صورت ساخت‌یافته; **Check:** source-aware provenance and permission checks; no invented locator or attribution | DB; M03; retention policy | PARTIAL · Isolated PG17.11 DB59 lab + independent restore evidence run 45082326382; Mac pending; OWNER_ISOLATED_DB_CI: https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/45109023781 (DB0e PG17 main PASS; optional 011 SKIPPED) | DBA+SERVER/Ops: approved isolated PG17.11 001-010 migration ledger, role/TLS, actual backup/restore and A/B results; avoid 011 without separate authorization |
| ☐ P3M04-A05 | **Output:** ذخیره Versionهای knowledge/retrieval/model/policy; **Check:** versioned artifact plus reproducible source-specific acceptance check and evidence | DB; M03; retention policy | PARTIAL · Isolated PG17.11 DB59 lab + independent restore evidence run 45082326382; Mac pending; OWNER_ISOLATED_DB_CI: https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/45109023781 (DB0e PG17 main PASS; optional 011 SKIPPED) | DBA+SERVER/Ops: approved isolated PG17.11 001-010 migration ledger, role/TLS, actual backup/restore and A/B results; avoid 011 without separate authorization |
| ☐ P3M04-A06 | **Output:** تعریف Migration forward و rollback; **Check:** reproducible migration/restore rollback plus consistency report in isolated test environment | DB; M03; retention policy | PARTIAL · Isolated PG17.11 DB59 lab + independent restore evidence run 45082326382; Mac pending; OWNER_ISOLATED_DB_CI: https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/45109023781 (DB0e PG17 main PASS; optional 011 SKIPPED) | DBA+SERVER/Ops: approved isolated PG17.11 001-010 migration ledger, role/TLS, actual backup/restore and A/B results; avoid 011 without separate authorization |
| ☐ P3M04-A07 | **Output:** تست Migration روی دیتابیس خالی و دیتابیس دارای داده; **Check:** reproducible migration/restore rollback plus consistency report in isolated test environment | DB; M03; retention policy | PARTIAL · Isolated PG17.11 DB59 lab + independent restore evidence run 45082326382; Mac pending; OWNER_ISOLATED_DB_CI: https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/45109023781 (DB0e PG17 main PASS; optional 011 SKIPPED) | DBA+SERVER/Ops: approved isolated PG17.11 001-010 migration ledger, role/TLS, actual backup/restore and A/B results; avoid 011 without separate authorization |
| ☐ P3M04-A08 | **Output:** تعریف Retention و soft/hard delete; **Check:** policy-controlled privacy and leakage negative checks, no assumed success | DB; M03; retention policy | PARTIAL · Isolated PG17.11 DB59 lab + independent restore evidence run 45082326382; Mac pending; OWNER_ISOLATED_DB_CI: https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/45109023781 (DB0e PG17 main PASS; optional 011 SKIPPED) | DBA+SERVER/Ops: approved isolated PG17.11 001-010 migration ledger, role/TLS, actual backup/restore and A/B results; avoid 011 without separate authorization |
| ☐ P3M04-A09 | **Output:** آماده‌سازی Namespace رزروشده برای موجودیت‌های فاز ۴ بدون فعال‌سازی آن‌ها.; **Check:** Phase4 namespace is design-only, no active tables | DB; M03; retention policy | PARTIAL · Isolated PG17.11 DB59 lab + independent restore evidence run 45082326382; Mac pending; OWNER_ISOLATED_DB_CI: https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/45109023781 (DB0e PG17 main PASS; optional 011 SKIPPED) | DBA+SERVER/Ops: approved isolated PG17.11 001-010 migration ledger, role/TLS, actual backup/restore and A/B results; avoid 011 without separate authorization |

### P3M05 · authentication_and_sessions

| چک | فعالیت و معیار | مالک | شاهد ثبت‌شده در ماتریس | ورودی یا اقدام باقی‌مانده |
|---|---|---|---|---|
| ☐ P3M05-A01 | **Output:** انتخاب روش ورود طبق تصمیم کارفرما; **Check:** versioned artifact plus reproducible source-specific acceptance check and evidence | API; Auth policy pending; M03-M04; auth policy | PARTIAL · OIDC/mTLS source and isolated tests; real Mac IdP not observed; OWNER_L1_SOURCE_CI: https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/45081955496 (API61 L1 275 tests; not Mac) | API/UI/DB/Ops: separate real HTTPS/IdP + BFF signed mTLS + original T2 tests, C018 one OS spawn if authorized, two account Refresh/A-B/401 proof; sanitized receipt on exact SHA |
| ☐ P3M05-A02 | **Output:** Password hashing استاندارد در صورت ورود رمزدار; **Check:** compare actual hashes and versioned manifests; zero mismatches | API; Auth policy pending; M03-M04; auth policy | PARTIAL · OIDC/mTLS source and isolated tests; real Mac IdP not observed; OWNER_L1_SOURCE_CI: https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/45081955496 (API61 L1 275 tests; not Mac) | API/UI/DB/Ops: separate real HTTPS/IdP + BFF signed mTLS + original T2 tests, C018 one OS spawn if authorized, two account Refresh/A-B/401 proof; sanitized receipt on exact SHA |
| ☐ P3M05-A03 | **Output:** Session token امن و rotation; **Check:** validate real Auth/session, revoke and invalid-user cases after policy approval | API; Auth policy pending; M03-M04; auth policy | PARTIAL · OIDC/mTLS source and isolated tests; real Mac IdP not observed; OWNER_L1_SOURCE_CI: https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/45081955496 (API61 L1 275 tests; not Mac) | API/UI/DB/Ops: separate real HTTPS/IdP + BFF signed mTLS + original T2 tests, C018 one OS spawn if authorized, two account Refresh/A-B/401 proof; sanitized receipt on exact SHA |
| ☐ P3M05-A04 | **Output:** Cookie امن با `HttpOnly`، `Secure` و `SameSite`; **Check:** validate real Auth/session, revoke and invalid-user cases after policy approval | API; Auth policy pending; M03-M04; auth policy | PARTIAL · OIDC/mTLS source and isolated tests; real Mac IdP not observed; OWNER_L1_SOURCE_CI: https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/45081955496 (API61 L1 275 tests; not Mac) | API/UI/DB/Ops: separate real HTTPS/IdP + BFF signed mTLS + original T2 tests, C018 one OS spawn if authorized, two account Refresh/A-B/401 proof; sanitized receipt on exact SHA |
| ☐ P3M05-A05 | **Output:** CSRF policy; **Check:** validate real Auth/session, revoke and invalid-user cases after policy approval | API; Auth policy pending; M03-M04; auth policy | PARTIAL · OIDC/mTLS source and isolated tests; real Mac IdP not observed; OWNER_L1_SOURCE_CI: https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/45081955496 (API61 L1 275 tests; not Mac) | API/UI/DB/Ops: separate real HTTPS/IdP + BFF signed mTLS + original T2 tests, C018 one OS spawn if authorized, two account Refresh/A-B/401 proof; sanitized receipt on exact SHA |
| ☐ P3M05-A06 | **Output:** محدودیت تلاش ورود و lockout کنترل‌شده; **Check:** versioned artifact plus reproducible source-specific acceptance check and evidence | API; Auth policy pending; M03-M04; auth policy | PARTIAL · OIDC/mTLS source and isolated tests; real Mac IdP not observed; OWNER_L1_SOURCE_CI: https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/45081955496 (API61 L1 275 tests; not Mac) | API/UI/DB/Ops: separate real HTTPS/IdP + BFF signed mTLS + original T2 tests, C018 one OS spawn if authorized, two account Refresh/A-B/401 proof; sanitized receipt on exact SHA |
| ☐ P3M05-A07 | **Output:** Logout و revoke همه نشست‌ها; **Check:** validate real Auth/session, revoke and invalid-user cases after policy approval | API; Auth policy pending; M03-M04; auth policy | PARTIAL · OIDC/mTLS source and isolated tests; real Mac IdP not observed; OWNER_L1_SOURCE_CI: https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/45081955496 (API61 L1 275 tests; not Mac) | API/UI/DB/Ops: separate real HTTPS/IdP + BFF signed mTLS + original T2 tests, C018 one OS spawn if authorized, two account Refresh/A-B/401 proof; sanitized receipt on exact SHA |
| ☐ P3M05-A08 | **Output:** Expiration و refresh policy; **Check:** versioned artifact plus reproducible source-specific acceptance check and evidence | API; Auth policy pending; M03-M04; auth policy | PARTIAL · OIDC/mTLS source and isolated tests; real Mac IdP not observed; OWNER_L1_SOURCE_CI: https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/45081955496 (API61 L1 275 tests; not Mac) | API/UI/DB/Ops: separate real HTTPS/IdP + BFF signed mTLS + original T2 tests, C018 one OS spawn if authorized, two account Refresh/A-B/401 proof; sanitized receipt on exact SHA |
| ☐ P3M05-A09 | **Output:** ثبت Security event بدون ذخیره Secret; **Check:** policy-controlled privacy and leakage negative checks, no assumed success | API; Auth policy pending; M03-M04; auth policy | PARTIAL · OIDC/mTLS source and isolated tests; real Mac IdP not observed; OWNER_L1_SOURCE_CI: https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/45081955496 (API61 L1 275 tests; not Mac) | API/UI/DB/Ops: separate real HTTPS/IdP + BFF signed mTLS + original T2 tests, C018 one OS spawn if authorized, two account Refresh/A-B/401 proof; sanitized receipt on exact SHA |
| ☐ P3M05-A10 | **Output:** تست منفی Session theft و replay.; **Check:** validate real Auth/session, revoke and invalid-user cases after policy approval | API; Auth policy pending; M03-M04; auth policy | PARTIAL · OIDC/mTLS source and isolated tests; real Mac IdP not observed; OWNER_L1_SOURCE_CI: https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/45081955496 (API61 L1 275 tests; not Mac) | API/UI/DB/Ops: separate real HTTPS/IdP + BFF signed mTLS + original T2 tests, C018 one OS spawn if authorized, two account Refresh/A-B/401 proof; sanitized receipt on exact SHA |

### P3M06 · tenant_isolation_and_rls

| چک | فعالیت و معیار | مالک | شاهد ثبت‌شده در ماتریس | ورودی یا اقدام باقی‌مانده |
|---|---|---|---|---|
| ☐ P3M06-A01 | **Output:** فعال‌سازی Row-Level Security برای جداول کاربرمحور; **Check:** versioned artifact plus reproducible source-specific acceptance check and evidence | DB + API; M04-M05 | PARTIAL · DB59 independent role/RLS preflight synthetic; real client A/B not observed; OWNER_ISOLATED_DB_CI: https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/45109023781 (DB0e PG17 main PASS; optional 011 SKIPPED) | DBA+SERVER/Ops: approved isolated PG17.11 001-010 migration ledger, role/TLS, actual backup/restore and A/B results; avoid 011 without separate authorization |
| ☐ P3M06-A02 | **Output:** تعریف Policy خواندن، نوشتن، ویرایش و حذف; **Check:** versioned artifact plus reproducible source-specific acceptance check and evidence | DB + API; M04-M05 | PARTIAL · DB59 independent role/RLS preflight synthetic; real client A/B not observed; OWNER_ISOLATED_DB_CI: https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/45109023781 (DB0e PG17 main PASS; optional 011 SKIPPED) | DBA+SERVER/Ops: approved isolated PG17.11 001-010 migration ledger, role/TLS, actual backup/restore and A/B results; avoid 011 without separate authorization |
| ☐ P3M06-A03 | **Output:** تنظیم Context امن user/tenant در هر Transaction; **Check:** test cross-user/role bypass with valid server identity; zero leaks | DB + API; M04-M05 | PARTIAL · DB59 independent role/RLS preflight synthetic; real client A/B not observed; OWNER_ISOLATED_DB_CI: https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/45109023781 (DB0e PG17 main PASS; optional 011 SKIPPED) | DBA+SERVER/Ops: approved isolated PG17.11 001-010 migration ledger, role/TLS, actual backup/restore and A/B results; avoid 011 without separate authorization |
| ☐ P3M06-A04 | **Output:** جلوگیری از دسترسی Background job خارج از Scope; **Check:** dated approved decision, diagrams/risk register and explicit Gate owner | DB + API; M04-M05 | PARTIAL · DB59 independent role/RLS preflight synthetic; real client A/B not observed; OWNER_ISOLATED_DB_CI: https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/45109023781 (DB0e PG17 main PASS; optional 011 SKIPPED) | DBA+SERVER/Ops: approved isolated PG17.11 001-010 migration ledger, role/TLS, actual backup/restore and A/B results; avoid 011 without separate authorization |
| ☐ P3M06-A05 | **Output:** تست cross-user برای تمام Endpointها; **Check:** test cross-user/role bypass with valid server identity; zero leaks | DB + API; M04-M05 | PARTIAL · DB59 independent role/RLS preflight synthetic; real client A/B not observed; OWNER_ISOLATED_DB_CI: https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/45109023781 (DB0e PG17 main PASS; optional 011 SKIPPED) | DBA+SERVER/Ops: approved isolated PG17.11 001-010 migration ledger, role/TLS, actual backup/restore and A/B results; avoid 011 without separate authorization |
| ☐ P3M06-A06 | **Output:** تست ID enumeration; **Check:** test cross-user/role bypass with valid server identity; zero leaks | DB + API; M04-M05 | PARTIAL · DB59 independent role/RLS preflight synthetic; real client A/B not observed; OWNER_ISOLATED_DB_CI: https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/45109023781 (DB0e PG17 main PASS; optional 011 SKIPPED) | DBA+SERVER/Ops: approved isolated PG17.11 001-010 migration ledger, role/TLS, actual backup/restore and A/B results; avoid 011 without separate authorization |
| ☐ P3M06-A07 | **Output:** تست دسترسی مستقیم Repository layer; **Check:** versioned artifact plus reproducible source-specific acceptance check and evidence | DB + API; M04-M05 | PARTIAL · DB59 independent role/RLS preflight synthetic; real client A/B not observed; OWNER_ISOLATED_DB_CI: https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/45109023781 (DB0e PG17 main PASS; optional 011 SKIPPED) | DBA+SERVER/Ops: approved isolated PG17.11 001-010 migration ledger, role/TLS, actual backup/restore and A/B results; avoid 011 without separate authorization |
| ☐ P3M06-A08 | **Output:** ثبت Audit برای عملیات حساس; **Check:** server-issued trace correlation, redaction and alert test evidence | DB + API; M04-M05 | PARTIAL · DB59 independent role/RLS preflight synthetic; real client A/B not observed; OWNER_ISOLATED_DB_CI: https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/45109023781 (DB0e PG17 main PASS; optional 011 SKIPPED) | DBA+SERVER/Ops: approved isolated PG17.11 001-010 migration ledger, role/TLS, actual backup/restore and A/B results; avoid 011 without separate authorization |
| ☐ P3M06-A09 | **Output:** ساخت Isolation matrix.; **Check:** test cross-user/role bypass with valid server identity; zero leaks | DB + API; M04-M05 | PARTIAL · DB59 independent role/RLS preflight synthetic; real client A/B not observed; OWNER_ISOLATED_DB_CI: https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/45109023781 (DB0e PG17 main PASS; optional 011 SKIPPED) | DBA+SERVER/Ops: approved isolated PG17.11 001-010 migration ledger, role/TLS, actual backup/restore and A/B results; avoid 011 without separate authorization |

### P3M10 · answer_orchestration

| چک | فعالیت و معیار | مالک | شاهد ثبت‌شده در ماتریس | ورودی یا اقدام باقی‌مانده |
|---|---|---|---|---|
| ☐ P3M10-A01 | **Output:** ساخت Query context از پیام جاری و تاریخچه محدود; **Check:** versioned artifact plus reproducible source-specific acceptance check and evidence | API + DB; M08-M09; NB23 | PARTIAL · T1/T2 synthetic tests; live Answer T3 remains blocked; OWNER_L1_SOURCE_CI: https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/45081955496 (API61 L1 275 tests; not Mac) | API+CENTRAL: provider/model/LLM-Gateway generation and C019/claims/policy contract must be separately approved; never run paid dispatch from this candidate |
| ☐ P3M10-A02 | **Output:** Intent و Answerability; **Check:** distinct outcome/policy negative tests and measured calibration where required | API + DB; M08-M09; NB23 | PARTIAL · T1/T2 synthetic tests; live Answer T3 remains blocked; OWNER_L1_SOURCE_CI: https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/45081955496 (API61 L1 275 tests; not Mac) | API+CENTRAL: provider/model/LLM-Gateway generation and C019/claims/policy contract must be separately approved; never run paid dispatch from this candidate |
| ☐ P3M10-A03 | **Output:** Retrieval و Context builder; **Check:** clean build and security scan in a separately authorized environment | API + DB; M08-M09; NB23 | PARTIAL · T1/T2 synthetic tests; live Answer T3 remains blocked; OWNER_L1_SOURCE_CI: https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/45081955496 (API61 L1 275 tests; not Mac) | API+CENTRAL: provider/model/LLM-Gateway generation and C019/claims/policy contract must be separately approved; never run paid dispatch from this candidate |
| ☐ P3M10-A04 | **Output:** تولید پاسخ ساخت‌یافته; **Check:** versioned artifact plus reproducible source-specific acceptance check and evidence | API + DB; M08-M09; NB23 | PARTIAL · T1/T2 synthetic tests; live Answer T3 remains blocked; OWNER_L1_SOURCE_CI: https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/45081955496 (API61 L1 275 tests; not Mac) | API+CENTRAL: provider/model/LLM-Gateway generation and C019/claims/policy contract must be separately approved; never run paid dispatch from this candidate |
| ☐ P3M10-A05 | **Output:** Claim/Citation verification; **Check:** source-aware provenance and permission checks; no invented locator or attribution | API + DB; M08-M09; NB23 | PARTIAL · T1/T2 synthetic tests; live Answer T3 remains blocked; OWNER_L1_SOURCE_CI: https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/45081955496 (API61 L1 275 tests; not Mac) | API+CENTRAL: provider/model/LLM-Gateway generation and C019/claims/policy contract must be separately approved; never run paid dispatch from this candidate |
| ☐ P3M10-A06 | **Output:** اعمال Safety و No-answer; **Check:** distinct outcome/policy negative tests and measured calibration where required | API + DB; M08-M09; NB23 | PARTIAL · T1/T2 synthetic tests; live Answer T3 remains blocked; OWNER_L1_SOURCE_CI: https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/45081955496 (API61 L1 275 tests; not Mac) | API+CENTRAL: provider/model/LLM-Gateway generation and C019/claims/policy contract must be separately approved; never run paid dispatch from this candidate |
| ☐ P3M10-A07 | **Output:** ساخت Confidence از اجزای قابل توضیح; **Check:** distinct outcome/policy negative tests and measured calibration where required | API + DB; M08-M09; NB23 | PARTIAL · T1/T2 synthetic tests; live Answer T3 remains blocked; OWNER_L1_SOURCE_CI: https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/45081955496 (API61 L1 275 tests; not Mac) | API+CENTRAL: provider/model/LLM-Gateway generation and C019/claims/policy contract must be separately approved; never run paid dispatch from this candidate |
| ☐ P3M10-A08 | **Output:** ذخیره Runها و Versionها در یک Transaction منطقی; **Check:** transaction T1/T2/T3 + crash window review, NEEDS_API_DB_REVIEW | API + DB; M08-M09; NB23 | PARTIAL · T1/T2 synthetic tests; live Answer T3 remains blocked; OWNER_L1_SOURCE_CI: https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/45081955496 (API61 L1 275 tests; not Mac) | API+CENTRAL: provider/model/LLM-Gateway generation and C019/claims/policy contract must be separately approved; never run paid dispatch from this candidate |
| ☐ P3M10-A09 | **Output:** مدیریت cancellation و duplicate request; **Check:** replay/cancel/unknown/ordering tests, no claim of exactly-once provider execution | API + DB; M08-M09; NB23 | PARTIAL · T1/T2 synthetic tests; live Answer T3 remains blocked; OWNER_L1_SOURCE_CI: https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/45081955496 (API61 L1 275 tests; not Mac) | API+CENTRAL: provider/model/LLM-Gateway generation and C019/claims/policy contract must be separately approved; never run paid dispatch from this candidate |
| ☐ P3M10-A10 | **Output:** Idempotency برای retry کلاینت.; **Check:** replay/cancel/unknown/ordering tests, no claim of exactly-once provider execution | API + DB; M08-M09; NB23 | PARTIAL · T1/T2 synthetic tests; live Answer T3 remains blocked; OWNER_L1_SOURCE_CI: https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/45081955496 (API61 L1 275 tests; not Mac) | API+CENTRAL: provider/model/LLM-Gateway generation and C019/claims/policy contract must be separately approved; never run paid dispatch from this candidate |

### P3M13 · product_api

| چک | فعالیت و معیار | مالک | شاهد ثبت‌شده در ماتریس | ورودی یا اقدام باقی‌مانده |
|---|---|---|---|---|
| ☐ P3M13-A01 | **Output:** OpenAPI نسخه‌دار; **Check:** run positive/negative Schema and version compatibility checks | API; M03; M05-M12 | PARTIAL · API61 same-source offline 134/134 prior owner CI; new integrated CI to verify separately; OWNER_L1_SOURCE_CI: https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/45081955496 (API61 L1 275 tests; not Mac) | API/UI/DB/Ops: separate real HTTPS/IdP + BFF signed mTLS + original T2 tests, C018 one OS spawn if authorized, two account Refresh/A-B/401 proof; sanitized receipt on exact SHA |
| ☐ P3M13-A02 | **Output:** Validation ورودی و محدودیت اندازه; **Check:** run positive/negative Schema and version compatibility checks | API; M03; M05-M12 | PARTIAL · API61 same-source offline 134/134 prior owner CI; new integrated CI to verify separately; OWNER_L1_SOURCE_CI: https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/45081955496 (API61 L1 275 tests; not Mac) | API/UI/DB/Ops: separate real HTTPS/IdP + BFF signed mTLS + original T2 tests, C018 one OS spawn if authorized, two account Refresh/A-B/401 proof; sanitized receipt on exact SHA |
| ☐ P3M13-A03 | **Output:** Error code پایدار; **Check:** versioned artifact plus reproducible source-specific acceptance check and evidence | API; M03; M05-M12 | PARTIAL · API61 same-source offline 134/134 prior owner CI; new integrated CI to verify separately; OWNER_L1_SOURCE_CI: https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/45081955496 (API61 L1 275 tests; not Mac) | API/UI/DB/Ops: separate real HTTPS/IdP + BFF signed mTLS + original T2 tests, C018 one OS spawn if authorized, two account Refresh/A-B/401 proof; sanitized receipt on exact SHA |
| ☐ P3M13-A04 | **Output:** Pagination تاریخچه; **Check:** stable user ownership, linked records and concurrency/retry checks | API; M03; M05-M12 | PARTIAL · API61 same-source offline 134/134 prior owner CI; new integrated CI to verify separately; OWNER_L1_SOURCE_CI: https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/45081955496 (API61 L1 275 tests; not Mac) | API/UI/DB/Ops: separate real HTTPS/IdP + BFF signed mTLS + original T2 tests, C018 one OS spawn if authorized, two account Refresh/A-B/401 proof; sanitized receipt on exact SHA |
| ☐ P3M13-A05 | **Output:** Streaming پاسخ با stateهای مشخص; **Check:** replay/cancel/unknown/ordering tests, no claim of exactly-once provider execution | API; M03; M05-M12 | PARTIAL · API61 same-source offline 134/134 prior owner CI; new integrated CI to verify separately; OWNER_L1_SOURCE_CI: https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/45081955496 (API61 L1 275 tests; not Mac) | API/UI/DB/Ops: separate real HTTPS/IdP + BFF signed mTLS + original T2 tests, C018 one OS spawn if authorized, two account Refresh/A-B/401 proof; sanitized receipt on exact SHA |
| ☐ P3M13-A06 | **Output:** Idempotency key; **Check:** replay/cancel/unknown/ordering tests, no claim of exactly-once provider execution | API; M03; M05-M12 | PARTIAL · API61 same-source offline 134/134 prior owner CI; new integrated CI to verify separately; OWNER_L1_SOURCE_CI: https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/45081955496 (API61 L1 275 tests; not Mac) | API/UI/DB/Ops: separate real HTTPS/IdP + BFF signed mTLS + original T2 tests, C018 one OS spawn if authorized, two account Refresh/A-B/401 proof; sanitized receipt on exact SHA |
| ☐ P3M13-A07 | **Output:** Request/Trace ID; **Check:** server-issued trace correlation, redaction and alert test evidence | API; M03; M05-M12 | PARTIAL · API61 same-source offline 134/134 prior owner CI; new integrated CI to verify separately; OWNER_L1_SOURCE_CI: https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/45081955496 (API61 L1 275 tests; not Mac) | API/UI/DB/Ops: separate real HTTPS/IdP + BFF signed mTLS + original T2 tests, C018 one OS spawn if authorized, two account Refresh/A-B/401 proof; sanitized receipt on exact SHA |
| ☐ P3M13-A08 | **Output:** Authorization در هر Endpoint; **Check:** test cross-user/role bypass with valid server identity; zero leaks | API; M03; M05-M12 | PARTIAL · API61 same-source offline 134/134 prior owner CI; new integrated CI to verify separately; OWNER_L1_SOURCE_CI: https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/45081955496 (API61 L1 275 tests; not Mac) | API/UI/DB/Ops: separate real HTTPS/IdP + BFF signed mTLS + original T2 tests, C018 one OS spawn if authorized, two account Refresh/A-B/401 proof; sanitized receipt on exact SHA |
| ☐ P3M13-A09 | **Output:** Contract test و backward compatibility; **Check:** run positive/negative Schema and version compatibility checks | API; M03; M05-M12 | PARTIAL · API61 same-source offline 134/134 prior owner CI; new integrated CI to verify separately; OWNER_L1_SOURCE_CI: https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/45081955496 (API61 L1 275 tests; not Mac) | API/UI/DB/Ops: separate real HTTPS/IdP + BFF signed mTLS + original T2 tests, C018 one OS spawn if authorized, two account Refresh/A-B/401 proof; sanitized receipt on exact SHA |
| ☐ P3M13-A10 | **Output:** API abuse tests.; **Check:** positive/negative executable tests with reproducible result | API; M03; M05-M12 | PARTIAL · API61 same-source offline 134/134 prior owner CI; new integrated CI to verify separately; OWNER_L1_SOURCE_CI: https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/45081955496 (API61 L1 275 tests; not Mac) | API/UI/DB/Ops: separate real HTTPS/IdP + BFF signed mTLS + original T2 tests, C018 one OS spawn if authorized, two account Refresh/A-B/401 proof; sanitized receipt on exact SHA |

### P3M15 · conversation_history_and_feedback

| چک | فعالیت و معیار | مالک | شاهد ثبت‌شده در ماتریس | ورودی یا اقدام باقی‌مانده |
|---|---|---|---|---|
| ☐ P3M15-A01 | **Output:** ذخیره User message و Answer به‌صورت immutable event; **Check:** stable user ownership, linked records and concurrency/retry checks | DB + API + UI; M04; M06; M13-M14 | PARTIAL · History source present; consent/privacy/genuine UI->DB not proven; OWNER_L1_SOURCE_CI: https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/45108323298 (UI62 L1 Node115/Chromium synthetic); OWNER_ISOLATED_DB_CI: https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/45109023781 (DB0e PG17 main PASS; optional 011 SKIPPED) | API/UI/DB/Ops: separate real HTTPS/IdP + BFF signed mTLS + original T2 tests, C018 one OS spawn if authorized, two account Refresh/A-B/401 proof; sanitized receipt on exact SHA |
| ☐ P3M15-A02 | **Output:** عنوان‌گذاری مکالمه بدون تغییر محتوای اصلی; **Check:** versioned artifact plus reproducible source-specific acceptance check and evidence | DB + API + UI; M04; M06; M13-M14 | PARTIAL · History source present; consent/privacy/genuine UI->DB not proven; OWNER_L1_SOURCE_CI: https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/45108323298 (UI62 L1 Node115/Chromium synthetic); OWNER_ISOLATED_DB_CI: https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/45109023781 (DB0e PG17 main PASS; optional 011 SKIPPED) | API/UI/DB/Ops: separate real HTTPS/IdP + BFF signed mTLS + original T2 tests, C018 one OS spawn if authorized, two account Refresh/A-B/401 proof; sanitized receipt on exact SHA |
| ☐ P3M15-A03 | **Output:** Pagination و مرتب‌سازی; **Check:** stable user ownership, linked records and concurrency/retry checks | DB + API + UI; M04; M06; M13-M14 | PARTIAL · History source present; consent/privacy/genuine UI->DB not proven; OWNER_L1_SOURCE_CI: https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/45108323298 (UI62 L1 Node115/Chromium synthetic); OWNER_ISOLATED_DB_CI: https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/45109023781 (DB0e PG17 main PASS; optional 011 SKIPPED) | API/UI/DB/Ops: separate real HTTPS/IdP + BFF signed mTLS + original T2 tests, C018 one OS spawn if authorized, two account Refresh/A-B/401 proof; sanitized receipt on exact SHA |
| ☐ P3M15-A04 | **Output:** حذف مکالمه طبق Retention policy; **Check:** policy-controlled privacy and leakage negative checks, no assumed success | DB + API + UI; M04; M06; M13-M14 | PARTIAL · History source present; consent/privacy/genuine UI->DB not proven; OWNER_L1_SOURCE_CI: https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/45108323298 (UI62 L1 Node115/Chromium synthetic); OWNER_ISOLATED_DB_CI: https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/45109023781 (DB0e PG17 main PASS; optional 011 SKIPPED) | API/UI/DB/Ops: separate real HTTPS/IdP + BFF signed mTLS + original T2 tests, C018 one OS spawn if authorized, two account Refresh/A-B/401 proof; sanitized receipt on exact SHA |
| ☐ P3M15-A05 | **Output:** Feedback مثبت/منفی و دسته خطا; **Check:** stable user ownership, linked records and concurrency/retry checks | DB + API + UI; M04; M06; M13-M14 | PARTIAL · History source present; consent/privacy/genuine UI->DB not proven; OWNER_L1_SOURCE_CI: https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/45108323298 (UI62 L1 Node115/Chromium synthetic); OWNER_ISOLATED_DB_CI: https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/45109023781 (DB0e PG17 main PASS; optional 011 SKIPPED) | API/UI/DB/Ops: separate real HTTPS/IdP + BFF signed mTLS + original T2 tests, C018 one OS spawn if authorized, two account Refresh/A-B/401 proof; sanitized receipt on exact SHA |
| ☐ P3M15-A06 | **Output:** ثبت Citation مشکل‌دار یا انتساب اشتباه; **Check:** source-aware provenance and permission checks; no invented locator or attribution | DB + API + UI; M04; M06; M13-M14 | PARTIAL · History source present; consent/privacy/genuine UI->DB not proven; OWNER_L1_SOURCE_CI: https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/45108323298 (UI62 L1 Node115/Chromium synthetic); OWNER_ISOLATED_DB_CI: https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/45109023781 (DB0e PG17 main PASS; optional 011 SKIPPED) | API/UI/DB/Ops: separate real HTTPS/IdP + BFF signed mTLS + original T2 tests, C018 one OS spawn if authorized, two account Refresh/A-B/401 proof; sanitized receipt on exact SHA |
| ☐ P3M15-A07 | **Output:** جلوگیری از دسترسی کاربر دیگر; **Check:** versioned artifact plus reproducible source-specific acceptance check and evidence | DB + API + UI; M04; M06; M13-M14 | PARTIAL · History source present; consent/privacy/genuine UI->DB not proven; OWNER_L1_SOURCE_CI: https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/45108323298 (UI62 L1 Node115/Chromium synthetic); OWNER_ISOLATED_DB_CI: https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/45109023781 (DB0e PG17 main PASS; optional 011 SKIPPED) | API/UI/DB/Ops: separate real HTTPS/IdP + BFF signed mTLS + original T2 tests, C018 one OS spawn if authorized, two account Refresh/A-B/401 proof; sanitized receipt on exact SHA |
| ☐ P3M15-A08 | **Output:** Export ساخت‌یافته در صورت تصویب Scope; **Check:** Export only after Scope approval; deletion independent | DB + API + UI; M04; M06; M13-M14 | PARTIAL · History source present; consent/privacy/genuine UI->DB not proven; OWNER_L1_SOURCE_CI: https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/45108323298 (UI62 L1 Node115/Chromium synthetic); OWNER_ISOLATED_DB_CI: https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/45109023781 (DB0e PG17 main PASS; optional 011 SKIPPED) | API/UI/DB/Ops: separate real HTTPS/IdP + BFF signed mTLS + original T2 tests, C018 one OS spawn if authorized, two account Refresh/A-B/401 proof; sanitized receipt on exact SHA |
| ☐ P3M15-A09 | **Output:** Dataset بازخورد بدون PII برای ارزیابی بعدی; **Check:** policy-controlled privacy and leakage negative checks, no assumed success | DB + API + UI; M04; M06; M13-M14 | PARTIAL · History source present; consent/privacy/genuine UI->DB not proven; OWNER_L1_SOURCE_CI: https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/45108323298 (UI62 L1 Node115/Chromium synthetic); OWNER_ISOLATED_DB_CI: https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/45109023781 (DB0e PG17 main PASS; optional 011 SKIPPED) | API/UI/DB/Ops: separate real HTTPS/IdP + BFF signed mTLS + original T2 tests, C018 one OS spawn if authorized, two account Refresh/A-B/401 proof; sanitized receipt on exact SHA |
| ☐ P3M15-A10 | **Output:** تست Race condition و duplicate write.; **Check:** replay/cancel/unknown/ordering tests, no claim of exactly-once provider execution | DB + API + UI; M04; M06; M13-M14 | PARTIAL · History source present; consent/privacy/genuine UI->DB not proven; OWNER_L1_SOURCE_CI: https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/45108323298 (UI62 L1 Node115/Chromium synthetic); OWNER_ISOLATED_DB_CI: https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/45109023781 (DB0e PG17 main PASS; optional 011 SKIPPED) | API/UI/DB/Ops: separate real HTTPS/IdP + BFF signed mTLS + original T2 tests, C018 one OS spawn if authorized, two account Refresh/A-B/401 proof; sanitized receipt on exact SHA |

### P3M16 · observability_and_audit

| چک | فعالیت و معیار | مالک | شاهد ثبت‌شده در ماتریس | ورودی یا اقدام باقی‌مانده |
|---|---|---|---|---|
| ☐ P3M16-A01 | **Output:** Structured log با Request/Trace ID; **Check:** server-issued trace correlation, redaction and alert test evidence | Foundation; ops owner pending; M13-M15; log policy | NOT_VERIFIED · Structured tracing/on-call receipts absent | Ops/Security: run scoped redacted trace, alert/incident tabletop, credential/PII leakage and dependency/container scans; attach real negative receipts |
| ☐ P3M16-A02 | **Output:** Metricهای request، latency، error، retrieval و model; **Check:** measured baseline and stress tests vs approved, non-invented thresholds | Foundation; ops owner pending; M13-M15; log policy | NOT_VERIFIED · Structured tracing/on-call receipts absent | Ops/Security: run scoped redacted trace, alert/incident tabletop, credential/PII leakage and dependency/container scans; attach real negative receipts |
| ☐ P3M16-A03 | **Output:** Dashboard سلامت سرویس; **Check:** versioned artifact plus reproducible source-specific acceptance check and evidence | Foundation; ops owner pending; M13-M15; log policy | NOT_VERIFIED · Structured tracing/on-call receipts absent | Ops/Security: run scoped redacted trace, alert/incident tabletop, credential/PII leakage and dependency/container scans; attach real negative receipts |
| ☐ P3M16-A04 | **Output:** Alert برای Availability، error rate، DB pool و مصرف; **Check:** resource/abuse and cross-user-cache negative tests, with approved bounds | Foundation; ops owner pending; M13-M15; log policy | NOT_VERIFIED · Structured tracing/on-call receipts absent | Ops/Security: run scoped redacted trace, alert/incident tabletop, credential/PII leakage and dependency/container scans; attach real negative receipts |
| ☐ P3M16-A05 | **Output:** Audit event برای ورود و عملیات حساس; **Check:** server-issued trace correlation, redaction and alert test evidence | Foundation; ops owner pending; M13-M15; log policy | NOT_VERIFIED · Structured tracing/on-call receipts absent | Ops/Security: run scoped redacted trace, alert/incident tabletop, credential/PII leakage and dependency/container scans; attach real negative receipts |
| ☐ P3M16-A06 | **Output:** Redaction داده مالی و Token; **Check:** validate real Auth/session, revoke and invalid-user cases after policy approval | Foundation; ops owner pending; M13-M15; log policy | NOT_VERIFIED · Structured tracing/on-call receipts absent | Ops/Security: run scoped redacted trace, alert/incident tabletop, credential/PII leakage and dependency/container scans; attach real negative receipts |
| ☐ P3M16-A07 | **Output:** ثبت نسخه Knowledge/Model/Policy; **Check:** versioned artifact plus reproducible source-specific acceptance check and evidence | Foundation; ops owner pending; M13-M15; log policy | NOT_VERIFIED · Structured tracing/on-call receipts absent | Ops/Security: run scoped redacted trace, alert/incident tabletop, credential/PII leakage and dependency/container scans; attach real negative receipts |
| ☐ P3M16-A08 | **Output:** Trace نمونه‌برداری‌شده برای مسیر پاسخ; **Check:** server-issued trace correlation, redaction and alert test evidence | Foundation; ops owner pending; M13-M15; log policy | NOT_VERIFIED · Structured tracing/on-call receipts absent | Ops/Security: run scoped redacted trace, alert/incident tabletop, credential/PII leakage and dependency/container scans; attach real negative receipts |
| ☐ P3M16-A09 | **Output:** Runbook هشدارها; **Check:** versioned artifact plus reproducible source-specific acceptance check and evidence | Foundation; ops owner pending; M13-M15; log policy | NOT_VERIFIED · Structured tracing/on-call receipts absent | Ops/Security: run scoped redacted trace, alert/incident tabletop, credential/PII leakage and dependency/container scans; attach real negative receipts |
| ☐ P3M16-A10 | **Output:** تست اینکه PII و Secret در Log وجود ندارد.; **Check:** policy-controlled privacy and leakage negative checks, no assumed success | Foundation; ops owner pending; M13-M15; log policy | NOT_VERIFIED · Structured tracing/on-call receipts absent | Ops/Security: run scoped redacted trace, alert/incident tabletop, credential/PII leakage and dependency/container scans; attach real negative receipts |

### P3M18 · containerization_and_networking

| چک | فعالیت و معیار | مالک | شاهد ثبت‌شده در ماتریس | ورودی یا اقدام باقی‌مانده |
|---|---|---|---|---|
| ☐ P3M18-A01 | **Output:** Dockerfile چندمرحله‌ای برای Web و API; **Check:** clean build and security scan in a separately authorized environment | Foundation; infrastructure owner pending; M02-M17; hosting | PARTIAL · Docker package source static; clean build and image scan NOT_RUN | ENGINE+SERVER/Ops: original engine lock/wheelhouse/ABI, image digest/SBOM/scan, isolated Mac snapshot & Build receipts; verify per target SHA and mode |
| ☐ P3M18-A02 | **Output:** اجرای process با کاربر غیر root; **Check:** versioned artifact plus reproducible source-specific acceptance check and evidence | Foundation; infrastructure owner pending; M02-M17; hosting | PARTIAL · Docker package source static; clean build and image scan NOT_RUN | ENGINE+SERVER/Ops: original engine lock/wheelhouse/ABI, image digest/SBOM/scan, isolated Mac snapshot & Build receipts; verify per target SHA and mode |
| ☐ P3M18-A03 | **Output:** Healthcheck و startup dependency; **Check:** accepted version/readiness, smoke and rollback evidence | Foundation; infrastructure owner pending; M02-M17; hosting | PARTIAL · Docker package source static; clean build and image scan NOT_RUN | ENGINE+SERVER/Ops: original engine lock/wheelhouse/ABI, image digest/SBOM/scan, isolated Mac snapshot & Build receipts; verify per target SHA and mode |
| ☐ P3M18-A04 | **Output:** Network segmentation; **Check:** versioned artifact plus reproducible source-specific acceptance check and evidence | Foundation; infrastructure owner pending; M02-M17; hosting | PARTIAL · Docker package source static; clean build and image scan NOT_RUN | ENGINE+SERVER/Ops: original engine lock/wheelhouse/ABI, image digest/SBOM/scan, isolated Mac snapshot & Build receipts; verify per target SHA and mode |
| ☐ P3M18-A05 | **Output:** Volume و persistence policy; **Check:** versioned artifact plus reproducible source-specific acceptance check and evidence | Foundation; infrastructure owner pending; M02-M17; hosting | PARTIAL · Docker package source static; clean build and image scan NOT_RUN | ENGINE+SERVER/Ops: original engine lock/wheelhouse/ABI, image digest/SBOM/scan, isolated Mac snapshot & Build receipts; verify per target SHA and mode |
| ☐ P3M18-A06 | **Output:** Secret injection در Runtime; **Check:** policy-controlled privacy and leakage negative checks, no assumed success | Foundation; infrastructure owner pending; M02-M17; hosting | PARTIAL · Docker package source static; clean build and image scan NOT_RUN | ENGINE+SERVER/Ops: original engine lock/wheelhouse/ABI, image digest/SBOM/scan, isolated Mac snapshot & Build receipts; verify per target SHA and mode |
| ☐ P3M18-A07 | **Output:** محدودیت CPU/Memory; **Check:** versioned artifact plus reproducible source-specific acceptance check and evidence | Foundation; infrastructure owner pending; M02-M17; hosting | PARTIAL · Docker package source static; clean build and image scan NOT_RUN | ENGINE+SERVER/Ops: original engine lock/wheelhouse/ABI, image digest/SBOM/scan, isolated Mac snapshot & Build receipts; verify per target SHA and mode |
| ☐ P3M18-A08 | **Output:** Image scanning و pin digest; **Check:** clean build and security scan in a separately authorized environment | Foundation; infrastructure owner pending; M02-M17; hosting | PARTIAL · Docker package source static; clean build and image scan NOT_RUN | ENGINE+SERVER/Ops: original engine lock/wheelhouse/ABI, image digest/SBOM/scan, isolated Mac snapshot & Build receipts; verify per target SHA and mode |
| ☐ P3M18-A09 | **Output:** Compose برای Local و Deployment; **Check:** Compose only chosen for a later mission; run/build NOT_RUN | Foundation; infrastructure owner pending; M02-M17; hosting | PARTIAL · Docker package source static; clean build and image scan NOT_RUN | ENGINE+SERVER/Ops: original engine lock/wheelhouse/ABI, image digest/SBOM/scan, isolated Mac snapshot & Build receipts; verify per target SHA and mode |
| ☐ P3M18-A10 | **Output:** Cold-start و restart test.; **Check:** positive/negative executable tests with reproducible result | Foundation; infrastructure owner pending; M02-M17; hosting | PARTIAL · Docker package source static; clean build and image scan NOT_RUN | ENGINE+SERVER/Ops: original engine lock/wheelhouse/ABI, image digest/SBOM/scan, isolated Mac snapshot & Build receipts; verify per target SHA and mode |

### P3M19 · ci_cd_and_release_pipeline

| چک | فعالیت و معیار | مالک | شاهد ثبت‌شده در ماتریس | ورودی یا اقدام باقی‌مانده |
|---|---|---|---|---|
| ☐ P3M19-A01 | **Output:** Lint، type check و unit tests; **Check:** clean build and security scan in a separately authorized environment | Foundation; CI owner pending; M02-M18 | PARTIAL · Same-SHA source workflow tracked separately; release scan/approval absent | ENGINE+SERVER/Ops: original engine lock/wheelhouse/ABI, image digest/SBOM/scan, isolated Mac snapshot & Build receipts; verify per target SHA and mode |
| ☐ P3M19-A02 | **Output:** Integration tests با سرویس‌های موقت; **Check:** positive/negative executable tests with reproducible result | Foundation; CI owner pending; M02-M18 | PARTIAL · Same-SHA source workflow tracked separately; release scan/approval absent | ENGINE+SERVER/Ops: original engine lock/wheelhouse/ABI, image digest/SBOM/scan, isolated Mac snapshot & Build receipts; verify per target SHA and mode |
| ☐ P3M19-A03 | **Output:** Migration test; **Check:** reproducible migration/restore rollback plus consistency report in isolated test environment | Foundation; CI owner pending; M02-M18 | PARTIAL · Same-SHA source workflow tracked separately; release scan/approval absent | ENGINE+SERVER/Ops: original engine lock/wheelhouse/ABI, image digest/SBOM/scan, isolated Mac snapshot & Build receipts; verify per target SHA and mode |
| ☐ P3M19-A04 | **Output:** Contract و security tests; **Check:** run positive/negative Schema and version compatibility checks | Foundation; CI owner pending; M02-M18 | PARTIAL · Same-SHA source workflow tracked separately; release scan/approval absent | ENGINE+SERVER/Ops: original engine lock/wheelhouse/ABI, image digest/SBOM/scan, isolated Mac snapshot & Build receipts; verify per target SHA and mode |
| ☐ P3M19-A05 | **Output:** Build و scan Image; **Check:** clean build and security scan in a separately authorized environment | Foundation; CI owner pending; M02-M18 | PARTIAL · Same-SHA source workflow tracked separately; release scan/approval absent | ENGINE+SERVER/Ops: original engine lock/wheelhouse/ABI, image digest/SBOM/scan, isolated Mac snapshot & Build receipts; verify per target SHA and mode |
| ☐ P3M19-A06 | **Output:** تولید Release manifest و SBOM; **Check:** compare actual hashes and versioned manifests; zero mismatches | Foundation; CI owner pending; M02-M18 | PARTIAL · Same-SHA source workflow tracked separately; release scan/approval absent | ENGINE+SERVER/Ops: original engine lock/wheelhouse/ABI, image digest/SBOM/scan, isolated Mac snapshot & Build receipts; verify per target SHA and mode |
| ☐ P3M19-A07 | **Output:** Deploy خودکار به Staging; **Check:** accepted version/readiness, smoke and rollback evidence | Foundation; CI owner pending; M02-M18 | PARTIAL · Same-SHA source workflow tracked separately; release scan/approval absent | ENGINE+SERVER/Ops: original engine lock/wheelhouse/ABI, image digest/SBOM/scan, isolated Mac snapshot & Build receipts; verify per target SHA and mode |
| ☐ P3M19-A08 | **Output:** Approval دستی Production; **Check:** accepted version/readiness, smoke and rollback evidence | Foundation; CI owner pending; M02-M18 | PARTIAL · Same-SHA source workflow tracked separately; release scan/approval absent | ENGINE+SERVER/Ops: original engine lock/wheelhouse/ABI, image digest/SBOM/scan, isolated Mac snapshot & Build receipts; verify per target SHA and mode |
| ☐ P3M19-A09 | **Output:** Rollback workflow; **Check:** reproducible migration/restore rollback plus consistency report in isolated test environment | Foundation; CI owner pending; M02-M18 | PARTIAL · Same-SHA source workflow tracked separately; release scan/approval absent | ENGINE+SERVER/Ops: original engine lock/wheelhouse/ABI, image digest/SBOM/scan, isolated Mac snapshot & Build receipts; verify per target SHA and mode |
| ☐ P3M19-A10 | **Output:** نگهداری Artifact و Test report; **Check:** positive/negative executable tests with reproducible result | Foundation; CI owner pending; M02-M18 | PARTIAL · Same-SHA source workflow tracked separately; release scan/approval absent | ENGINE+SERVER/Ops: original engine lock/wheelhouse/ABI, image digest/SBOM/scan, isolated Mac snapshot & Build receipts; verify per target SHA and mode |
| ☐ P3M19-A11 | **Output:** Branch protection و ممنوعیت Secret در log.; **Check:** policy-controlled privacy and leakage negative checks, no assumed success | Foundation; CI owner pending; M02-M18 | PARTIAL · Same-SHA source workflow tracked separately; release scan/approval absent | ENGINE+SERVER/Ops: original engine lock/wheelhouse/ABI, image digest/SBOM/scan, isolated Mac snapshot & Build receipts; verify per target SHA and mode |

### P3M20 · staging_deployment_and_e2e

| چک | فعالیت و معیار | مالک | شاهد ثبت‌شده در ماتریس | ورودی یا اقدام باقی‌مانده |
|---|---|---|---|---|
| ☐ P3M20-A01 | **Output:** Provision محیط Staging نزدیک به Production; **Check:** accepted version/readiness, smoke and rollback evidence | Foundation; staging owner pending; M00; M03-M19 | NOT_RUN · No Mac 7-service E2E evidence | API/UI/DB/Ops: separate real HTTPS/IdP + BFF signed mTLS + original T2 tests, C018 one OS spawn if authorized, two account Refresh/A-B/401 proof; sanitized receipt on exact SHA |
| ☐ P3M20-A02 | **Output:** TLS و Domain آزمایشی; **Check:** versioned artifact plus reproducible source-specific acceptance check and evidence | Foundation; staging owner pending; M00; M03-M19 | NOT_RUN · No Mac 7-service E2E evidence | API/UI/DB/Ops: separate real HTTPS/IdP + BFF signed mTLS + original T2 tests, C018 one OS spawn if authorized, two account Refresh/A-B/401 proof; sanitized receipt on exact SHA |
| ☐ P3M20-A03 | **Output:** داده Test غیرشخصی; **Check:** positive/negative executable tests with reproducible result | Foundation; staging owner pending; M00; M03-M19 | NOT_RUN · No Mac 7-service E2E evidence | API/UI/DB/Ops: separate real HTTPS/IdP + BFF signed mTLS + original T2 tests, C018 one OS spawn if authorized, two account Refresh/A-B/401 proof; sanitized receipt on exact SHA |
| ☐ P3M20-A04 | **Output:** اجرای Migration; **Check:** reproducible migration/restore rollback plus consistency report in isolated test environment | Foundation; staging owner pending; M00; M03-M19 | NOT_RUN · No Mac 7-service E2E evidence | API/UI/DB/Ops: separate real HTTPS/IdP + BFF signed mTLS + original T2 tests, C018 one OS spawn if authorized, two account Refresh/A-B/401 proof; sanitized receipt on exact SHA |
| ☐ P3M20-A05 | **Output:** بارگذاری Release پذیرفته‌شده فاز ۲; **Check:** accepted version/readiness, smoke and rollback evidence | Foundation; staging owner pending; M00; M03-M19 | NOT_RUN · No Mac 7-service E2E evidence | API/UI/DB/Ops: separate real HTTPS/IdP + BFF signed mTLS + original T2 tests, C018 one OS spawn if authorized, two account Refresh/A-B/401 proof; sanitized receipt on exact SHA |
| ☐ P3M20-A06 | **Output:** Smoke و E2E; **Check:** positive/negative executable tests with reproducible result | Foundation; staging owner pending; M00; M03-M19 | NOT_RUN · No Mac 7-service E2E evidence | API/UI/DB/Ops: separate real HTTPS/IdP + BFF signed mTLS + original T2 tests, C018 one OS spawn if authorized, two account Refresh/A-B/401 proof; sanitized receipt on exact SHA |
| ☐ P3M20-A07 | **Output:** تست سه منبع و چهار نوع Citation; **Check:** source-aware provenance and permission checks; no invented locator or attribution | Foundation; staging owner pending; M00; M03-M19 | NOT_RUN · No Mac 7-service E2E evidence | API/UI/DB/Ops: separate real HTTPS/IdP + BFF signed mTLS + original T2 tests, C018 one OS spawn if authorized, two account Refresh/A-B/401 proof; sanitized receipt on exact SHA |
| ☐ P3M20-A08 | **Output:** تست نویسنده/سردبیر; **Check:** versioned artifact plus reproducible source-specific acceptance check and evidence | Foundation; staging owner pending; M00; M03-M19 | NOT_RUN · No Mac 7-service E2E evidence | API/UI/DB/Ops: separate real HTTPS/IdP + BFF signed mTLS + original T2 tests, C018 one OS spawn if authorized, two account Refresh/A-B/401 proof; sanitized receipt on exact SHA |
| ☐ P3M20-A09 | **Output:** تست No-answer و Safety; **Check:** distinct outcome/policy negative tests and measured calibration where required | Foundation; staging owner pending; M00; M03-M19 | NOT_RUN · No Mac 7-service E2E evidence | API/UI/DB/Ops: separate real HTTPS/IdP + BFF signed mTLS + original T2 tests, C018 one OS spawn if authorized, two account Refresh/A-B/401 proof; sanitized receipt on exact SHA |
| ☐ P3M20-A10 | **Output:** تست Restart و dependency outage; **Check:** versioned artifact plus reproducible source-specific acceptance check and evidence | Foundation; staging owner pending; M00; M03-M19 | NOT_RUN · No Mac 7-service E2E evidence | API/UI/DB/Ops: separate real HTTPS/IdP + BFF signed mTLS + original T2 tests, C018 one OS spawn if authorized, two account Refresh/A-B/401 proof; sanitized receipt on exact SHA |
| ☐ P3M20-A11 | **Output:** UAT کارفرما و ثبت Issue.; **Check:** positive/negative executable tests with reproducible result | Foundation; staging owner pending; M00; M03-M19 | NOT_RUN · No Mac 7-service E2E evidence | API/UI/DB/Ops: separate real HTTPS/IdP + BFF signed mTLS + original T2 tests, C018 one OS spawn if authorized, two account Refresh/A-B/401 proof; sanitized receipt on exact SHA |

### P3M21 · security_privacy_and_threat_validation

| چک | فعالیت و معیار | مالک | شاهد ثبت‌شده در ماتریس | ورودی یا اقدام باقی‌مانده |
|---|---|---|---|---|
| ☐ P3M21-A01 | **Output:** Threat model برای Web، API، DB، Qdrant و Model gateway; **Check:** versioned artifact plus reproducible source-specific acceptance check and evidence | Foundation; security owner pending; M05-M06; M20; privacy | NOT_VERIFIED · No verified complete high/critical scan/incident rehearsal | Ops/Security: run scoped redacted trace, alert/incident tabletop, credential/PII leakage and dependency/container scans; attach real negative receipts |
| ☐ P3M21-A02 | **Output:** تست OWASP API/Web متناسب; **Check:** versioned artifact plus reproducible source-specific acceptance check and evidence | Foundation; security owner pending; M05-M06; M20; privacy | NOT_VERIFIED · No verified complete high/critical scan/incident rehearsal | Ops/Security: run scoped redacted trace, alert/incident tabletop, credential/PII leakage and dependency/container scans; attach real negative receipts |
| ☐ P3M21-A03 | **Output:** تست prompt injection و data exfiltration; **Check:** distinct outcome/policy negative tests and measured calibration where required | Foundation; security owner pending; M05-M06; M20; privacy | NOT_VERIFIED · No verified complete high/critical scan/incident rehearsal | Ops/Security: run scoped redacted trace, alert/incident tabletop, credential/PII leakage and dependency/container scans; attach real negative receipts |
| ☐ P3M21-A04 | **Output:** تست IDOR و RLS bypass; **Check:** test cross-user/role bypass with valid server identity; zero leaks | Foundation; security owner pending; M05-M06; M20; privacy | NOT_VERIFIED · No verified complete high/critical scan/incident rehearsal | Ops/Security: run scoped redacted trace, alert/incident tabletop, credential/PII leakage and dependency/container scans; attach real negative receipts |
| ☐ P3M21-A05 | **Output:** TLS، headerهای امنیتی و CORS; **Check:** versioned artifact plus reproducible source-specific acceptance check and evidence | Foundation; security owner pending; M05-M06; M20; privacy | NOT_VERIFIED · No verified complete high/critical scan/incident rehearsal | Ops/Security: run scoped redacted trace, alert/incident tabletop, credential/PII leakage and dependency/container scans; attach real negative receipts |
| ☐ P3M21-A06 | **Output:** Dependency و image scan; **Check:** clean build and security scan in a separately authorized environment | Foundation; security owner pending; M05-M06; M20; privacy | NOT_VERIFIED · No verified complete high/critical scan/incident rehearsal | Ops/Security: run scoped redacted trace, alert/incident tabletop, credential/PII leakage and dependency/container scans; attach real negative receipts |
| ☐ P3M21-A07 | **Output:** Consent و Retention validation; **Check:** run positive/negative Schema and version compatibility checks | Foundation; security owner pending; M05-M06; M20; privacy | NOT_VERIFIED · No verified complete high/critical scan/incident rehearsal | Ops/Security: run scoped redacted trace, alert/incident tabletop, credential/PII leakage and dependency/container scans; attach real negative receipts |
| ☐ P3M21-A08 | **Output:** Account/data deletion test; **Check:** positive/negative executable tests with reproducible result | Foundation; security owner pending; M05-M06; M20; privacy | NOT_VERIFIED · No verified complete high/critical scan/incident rehearsal | Ops/Security: run scoped redacted trace, alert/incident tabletop, credential/PII leakage and dependency/container scans; attach real negative receipts |
| ☐ P3M21-A09 | **Output:** Incident response tabletop; **Check:** versioned artifact plus reproducible source-specific acceptance check and evidence | Foundation; security owner pending; M05-M06; M20; privacy | NOT_VERIFIED · No verified complete high/critical scan/incident rehearsal | Ops/Security: run scoped redacted trace, alert/incident tabletop, credential/PII leakage and dependency/container scans; attach real negative receipts |
| ☐ P3M21-A10 | **Output:** ثبت Risk acceptanceهای باقی‌مانده.; **Check:** dated approved decision, diagrams/risk register and explicit Gate owner | Foundation; security owner pending; M05-M06; M20; privacy | NOT_VERIFIED · No verified complete high/critical scan/incident rehearsal | Ops/Security: run scoped redacted trace, alert/incident tabletop, credential/PII leakage and dependency/container scans; attach real negative receipts |

### P3M22 · backup_restore_and_disaster_recovery

| چک | فعالیت و معیار | مالک | شاهد ثبت‌شده در ماتریس | ورودی یا اقدام باقی‌مانده |
|---|---|---|---|---|
| ☐ P3M22-A01 | **Output:** Backup نسخه‌دار PostgreSQL; **Check:** reproducible migration/restore rollback plus consistency report in isolated test environment | DB for PostgreSQL; Qdrant ops pending; M04; M07; M18; RPO/RTO | PARTIAL · DB59 isolated restore PASS; real Mac backup/independent restore and RPO/RTO NOT_RUN; OWNER_ISOLATED_DB_CI: https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/45109023781 (DB0e PG17 main PASS; optional 011 SKIPPED) | DBA+SERVER/Ops: approved isolated PG17.11 001-010 migration ledger, role/TLS, actual backup/restore and A/B results; avoid 011 without separate authorization |
| ☐ P3M22-A02 | **Output:** Snapshot و Restore Qdrant; **Check:** reproducible migration/restore rollback plus consistency report in isolated test environment | DB for PostgreSQL; Qdrant ops pending; M04; M07; M18; RPO/RTO | PARTIAL · DB59 isolated restore PASS; real Mac backup/independent restore and RPO/RTO NOT_RUN; OWNER_ISOLATED_DB_CI: https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/45109023781 (DB0e PG17 main PASS; optional 011 SKIPPED) | DBA+SERVER/Ops: approved isolated PG17.11 001-010 migration ledger, role/TLS, actual backup/restore and A/B results; avoid 011 without separate authorization |
| ☐ P3M22-A03 | **Output:** Backup Config و Release pointer; **Check:** reproducible migration/restore rollback plus consistency report in isolated test environment | DB for PostgreSQL; Qdrant ops pending; M04; M07; M18; RPO/RTO | PARTIAL · DB59 isolated restore PASS; real Mac backup/independent restore and RPO/RTO NOT_RUN; OWNER_ISOLATED_DB_CI: https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/45109023781 (DB0e PG17 main PASS; optional 011 SKIPPED) | DBA+SERVER/Ops: approved isolated PG17.11 001-010 migration ledger, role/TLS, actual backup/restore and A/B results; avoid 011 without separate authorization |
| ☐ P3M22-A04 | **Output:** رمزگذاری و دسترسی محدود Backup; **Check:** reproducible migration/restore rollback plus consistency report in isolated test environment | DB for PostgreSQL; Qdrant ops pending; M04; M07; M18; RPO/RTO | PARTIAL · DB59 isolated restore PASS; real Mac backup/independent restore and RPO/RTO NOT_RUN; OWNER_ISOLATED_DB_CI: https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/45109023781 (DB0e PG17 main PASS; optional 011 SKIPPED) | DBA+SERVER/Ops: approved isolated PG17.11 001-010 migration ledger, role/TLS, actual backup/restore and A/B results; avoid 011 without separate authorization |
| ☐ P3M22-A05 | **Output:** Retention و rotation; **Check:** policy-controlled privacy and leakage negative checks, no assumed success | DB for PostgreSQL; Qdrant ops pending; M04; M07; M18; RPO/RTO | PARTIAL · DB59 isolated restore PASS; real Mac backup/independent restore and RPO/RTO NOT_RUN; OWNER_ISOLATED_DB_CI: https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/45109023781 (DB0e PG17 main PASS; optional 011 SKIPPED) | DBA+SERVER/Ops: approved isolated PG17.11 001-010 migration ledger, role/TLS, actual backup/restore and A/B results; avoid 011 without separate authorization |
| ☐ P3M22-A06 | **Output:** Restore در محیط خالی; **Check:** reproducible migration/restore rollback plus consistency report in isolated test environment | DB for PostgreSQL; Qdrant ops pending; M04; M07; M18; RPO/RTO | PARTIAL · DB59 isolated restore PASS; real Mac backup/independent restore and RPO/RTO NOT_RUN; OWNER_ISOLATED_DB_CI: https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/45109023781 (DB0e PG17 main PASS; optional 011 SKIPPED) | DBA+SERVER/Ops: approved isolated PG17.11 001-010 migration ledger, role/TLS, actual backup/restore and A/B results; avoid 011 without separate authorization |
| ☐ P3M22-A07 | **Output:** Point-in-time recovery در صورت امکان زیرساخت; **Check:** versioned artifact plus reproducible source-specific acceptance check and evidence | DB for PostgreSQL; Qdrant ops pending; M04; M07; M18; RPO/RTO | PARTIAL · DB59 isolated restore PASS; real Mac backup/independent restore and RPO/RTO NOT_RUN; OWNER_ISOLATED_DB_CI: https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/45109023781 (DB0e PG17 main PASS; optional 011 SKIPPED) | DBA+SERVER/Ops: approved isolated PG17.11 001-010 migration ledger, role/TLS, actual backup/restore and A/B results; avoid 011 without separate authorization |
| ☐ P3M22-A08 | **Output:** اندازه‌گیری RPO/RTO واقعی; **Check:** dated approved decision, diagrams/risk register and explicit Gate owner | DB for PostgreSQL; Qdrant ops pending; M04; M07; M18; RPO/RTO | PARTIAL · DB59 isolated restore PASS; real Mac backup/independent restore and RPO/RTO NOT_RUN; OWNER_ISOLATED_DB_CI: https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/45109023781 (DB0e PG17 main PASS; optional 011 SKIPPED) | DBA+SERVER/Ops: approved isolated PG17.11 001-010 migration ledger, role/TLS, actual backup/restore and A/B results; avoid 011 without separate authorization |
| ☐ P3M22-A09 | **Output:** تست خرابی جزئی و کامل; **Check:** versioned artifact plus reproducible source-specific acceptance check and evidence | DB for PostgreSQL; Qdrant ops pending; M04; M07; M18; RPO/RTO | PARTIAL · DB59 isolated restore PASS; real Mac backup/independent restore and RPO/RTO NOT_RUN; OWNER_ISOLATED_DB_CI: https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/45109023781 (DB0e PG17 main PASS; optional 011 SKIPPED) | DBA+SERVER/Ops: approved isolated PG17.11 001-010 migration ledger, role/TLS, actual backup/restore and A/B results; avoid 011 without separate authorization |
| ☐ P3M22-A10 | **Output:** Runbook و گزارش Restore.; **Check:** reproducible migration/restore rollback plus consistency report in isolated test environment | DB for PostgreSQL; Qdrant ops pending; M04; M07; M18; RPO/RTO | PARTIAL · DB59 isolated restore PASS; real Mac backup/independent restore and RPO/RTO NOT_RUN; OWNER_ISOLATED_DB_CI: https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/45109023781 (DB0e PG17 main PASS; optional 011 SKIPPED) | DBA+SERVER/Ops: approved isolated PG17.11 001-010 migration ledger, role/TLS, actual backup/restore and A/B results; avoid 011 without separate authorization |

### P3M23 · performance_load_and_failure_testing

| چک | فعالیت و معیار | مالک | شاهد ثبت‌شده در ماتریس | ورودی یا اقدام باقی‌مانده |
|---|---|---|---|---|
| ☐ P3M23-A01 | **Output:** Freeze workload model با اعداد تأییدشده; **Check:** real approved workload; sample SLO values are NONBINDING | Foundation; performance owner pending; M20-M22; real workload | NOT_RUN · Workload thresholds not frozen or measured | CENTRAL/employer and Ops: approve exact workload/cost/privacy/retention/SLO/RPO/RTO numbers or keep proposals nonbinding; then targeted positive and negative tests |
| ☐ P3M23-A02 | **Output:** Baseline p50/p95/p99; **Check:** measured baseline and stress tests vs approved, non-invented thresholds | Foundation; performance owner pending; M20-M22; real workload | NOT_RUN · Workload thresholds not frozen or measured | CENTRAL/employer and Ops: approve exact workload/cost/privacy/retention/SLO/RPO/RTO numbers or keep proposals nonbinding; then targeted positive and negative tests |
| ☐ P3M23-A03 | **Output:** Load، stress و soak test; **Check:** measured baseline and stress tests vs approved, non-invented thresholds | Foundation; performance owner pending; M20-M22; real workload | NOT_RUN · Workload thresholds not frozen or measured | CENTRAL/employer and Ops: approve exact workload/cost/privacy/retention/SLO/RPO/RTO numbers or keep proposals nonbinding; then targeted positive and negative tests |
| ☐ P3M23-A04 | **Output:** اندازه‌گیری saturation; **Check:** versioned artifact plus reproducible source-specific acceptance check and evidence | Foundation; performance owner pending; M20-M22; real workload | NOT_RUN · Workload thresholds not frozen or measured | CENTRAL/employer and Ops: approve exact workload/cost/privacy/retention/SLO/RPO/RTO numbers or keep proposals nonbinding; then targeted positive and negative tests |
| ☐ P3M23-A05 | **Output:** Failure injection کنترل‌شده; **Check:** versioned artifact plus reproducible source-specific acceptance check and evidence | Foundation; performance owner pending; M20-M22; real workload | NOT_RUN · Workload thresholds not frozen or measured | CENTRAL/employer and Ops: approve exact workload/cost/privacy/retention/SLO/RPO/RTO numbers or keep proposals nonbinding; then targeted positive and negative tests |
| ☐ P3M23-A06 | **Output:** تحلیل Queue و timeout; **Check:** replay/cancel/unknown/ordering tests, no claim of exactly-once provider execution | Foundation; performance owner pending; M20-M22; real workload | NOT_RUN · Workload thresholds not frozen or measured | CENTRAL/employer and Ops: approve exact workload/cost/privacy/retention/SLO/RPO/RTO numbers or keep proposals nonbinding; then targeted positive and negative tests |
| ☐ P3M23-A07 | **Output:** بررسی DB pool و Index latency; **Check:** test database constraints and query plans, including negative cases | Foundation; performance owner pending; M20-M22; real workload | NOT_RUN · Workload thresholds not frozen or measured | CENTRAL/employer and Ops: approve exact workload/cost/privacy/retention/SLO/RPO/RTO numbers or keep proposals nonbinding; then targeted positive and negative tests |
| ☐ P3M23-A08 | **Output:** اندازه‌گیری هزینه هر پاسخ; **Check:** versioned artifact plus reproducible source-specific acceptance check and evidence | Foundation; performance owner pending; M20-M22; real workload | NOT_RUN · Workload thresholds not frozen or measured | CENTRAL/employer and Ops: approve exact workload/cost/privacy/retention/SLO/RPO/RTO numbers or keep proposals nonbinding; then targeted positive and negative tests |
| ☐ P3M23-A09 | **Output:** Capacity report و tuning; **Check:** resource/abuse and cross-user-cache negative tests, with approved bounds | Foundation; performance owner pending; M20-M22; real workload | NOT_RUN · Workload thresholds not frozen or measured | CENTRAL/employer and Ops: approve exact workload/cost/privacy/retention/SLO/RPO/RTO numbers or keep proposals nonbinding; then targeted positive and negative tests |
| ☐ P3M23-A10 | **Output:** Regression threshold.; **Check:** positive/negative executable tests with reproducible result | Foundation; performance owner pending; M20-M22; real workload | NOT_RUN · Workload thresholds not frozen or measured | CENTRAL/employer and Ops: approve exact workload/cost/privacy/retention/SLO/RPO/RTO numbers or keep proposals nonbinding; then targeted positive and negative tests |

### P3M24 · production_launch

| چک | فعالیت و معیار | مالک | شاهد ثبت‌شده در ماتریس | ورودی یا اقدام باقی‌مانده |
|---|---|---|---|---|
| ☐ P3M24-A01 | **Output:** Go/No-Go checklist; **Check:** versioned artifact plus reproducible source-specific acceptance check and evidence | Foundation; launch approver pending; M00-M23; Go/No-Go | NOT_RUN · Public launch forbidden until Go decision | CENTRAL+Ops/employer: all prior Gate evidence, alpha/beta/UAT, rollback/restore/SLO security and signed Go/No-Go before any deployment or Hypercare |
| ☐ P3M24-A02 | **Output:** Freeze Image digest، DB migration و Knowledge release; **Check:** reproducible migration/restore rollback plus consistency report in isolated test environment | Foundation; launch approver pending; M00-M23; Go/No-Go | NOT_RUN · Public launch forbidden until Go decision | CENTRAL+Ops/employer: all prior Gate evidence, alpha/beta/UAT, rollback/restore/SLO security and signed Go/No-Go before any deployment or Hypercare |
| ☐ P3M24-A03 | **Output:** Backup قبل از استقرار; **Check:** reproducible migration/restore rollback plus consistency report in isolated test environment | Foundation; launch approver pending; M00-M23; Go/No-Go | NOT_RUN · Public launch forbidden until Go decision | CENTRAL+Ops/employer: all prior Gate evidence, alpha/beta/UAT, rollback/restore/SLO security and signed Go/No-Go before any deployment or Hypercare |
| ☐ P3M24-A04 | **Output:** اجرای Deployment کنترل‌شده; **Check:** accepted version/readiness, smoke and rollback evidence | Foundation; launch approver pending; M00-M23; Go/No-Go | NOT_RUN · Public launch forbidden until Go decision | CENTRAL+Ops/employer: all prior Gate evidence, alpha/beta/UAT, rollback/restore/SLO security and signed Go/No-Go before any deployment or Hypercare |
| ☐ P3M24-A05 | **Output:** Migration و health verification; **Check:** reproducible migration/restore rollback plus consistency report in isolated test environment | Foundation; launch approver pending; M00-M23; Go/No-Go | NOT_RUN · Public launch forbidden until Go decision | CENTRAL+Ops/employer: all prior Gate evidence, alpha/beta/UAT, rollback/restore/SLO security and signed Go/No-Go before any deployment or Hypercare |
| ☐ P3M24-A06 | **Output:** Smoke test با حساب آزمایشی; **Check:** positive/negative executable tests with reproducible result | Foundation; launch approver pending; M00-M23; Go/No-Go | NOT_RUN · Public launch forbidden until Go decision | CENTRAL+Ops/employer: all prior Gate evidence, alpha/beta/UAT, rollback/restore/SLO security and signed Go/No-Go before any deployment or Hypercare |
| ☐ P3M24-A07 | **Output:** فعال‌سازی محدود کاربران اولیه; **Check:** versioned artifact plus reproducible source-specific acceptance check and evidence | Foundation; launch approver pending; M00-M23; Go/No-Go | NOT_RUN · Public launch forbidden until Go decision | CENTRAL+Ops/employer: all prior Gate evidence, alpha/beta/UAT, rollback/restore/SLO security and signed Go/No-Go before any deployment or Hypercare |
| ☐ P3M24-A08 | **Output:** پایش Error، latency، cost و safety; **Check:** distinct outcome/policy negative tests and measured calibration where required | Foundation; launch approver pending; M00-M23; Go/No-Go | NOT_RUN · Public launch forbidden until Go decision | CENTRAL+Ops/employer: all prior Gate evidence, alpha/beta/UAT, rollback/restore/SLO security and signed Go/No-Go before any deployment or Hypercare |
| ☐ P3M24-A09 | **Output:** Rollback در عبور از Threshold; **Check:** reproducible migration/restore rollback plus consistency report in isolated test environment | Foundation; launch approver pending; M00-M23; Go/No-Go | NOT_RUN · Public launch forbidden until Go decision | CENTRAL+Ops/employer: all prior Gate evidence, alpha/beta/UAT, rollback/restore/SLO security and signed Go/No-Go before any deployment or Hypercare |
| ☐ P3M24-A10 | **Output:** ثبت زمان، نسخه‌ها و مسئول تصمیم; **Check:** versioned artifact plus reproducible source-specific acceptance check and evidence | Foundation; launch approver pending; M00-M23; Go/No-Go | NOT_RUN · Public launch forbidden until Go decision | CENTRAL+Ops/employer: all prior Gate evidence, alpha/beta/UAT, rollback/restore/SLO security and signed Go/No-Go before any deployment or Hypercare |
| ☐ P3M24-A11 | **Output:** Production acceptance report.; **Check:** accepted version/readiness, smoke and rollback evidence | Foundation; launch approver pending; M00-M23; Go/No-Go | NOT_RUN · Public launch forbidden until Go decision | CENTRAL+Ops/employer: all prior Gate evidence, alpha/beta/UAT, rollback/restore/SLO security and signed Go/No-Go before any deployment or Hypercare |

### P3M25 · hypercare_and_phase4_handoff

| چک | فعالیت و معیار | مالک | شاهد ثبت‌شده در ماتریس | ورودی یا اقدام باقی‌مانده |
|---|---|---|---|---|
| ☐ P3M25-A01 | **Output:** بازه Hypercare با مالک مشخص; **Check:** versioned artifact plus reproducible source-specific acceptance check and evidence | Foundation; hypercare owner pending; M24; operations owner | NOT_RUN · No launch; hypercare is not started | CENTRAL+Ops/employer: all prior Gate evidence, alpha/beta/UAT, rollback/restore/SLO security and signed Go/No-Go before any deployment or Hypercare |
| ☐ P3M25-A02 | **Output:** دسته‌بندی Incident و SLA پاسخ داخلی; **Check:** versioned artifact plus reproducible source-specific acceptance check and evidence | Foundation; hypercare owner pending; M24; operations owner | NOT_RUN · No launch; hypercare is not started | CENTRAL+Ops/employer: all prior Gate evidence, alpha/beta/UAT, rollback/restore/SLO security and signed Go/No-Go before any deployment or Hypercare |
| ☐ P3M25-A03 | **Output:** مرور روزانه Error، latency، Citation و Safety; **Check:** source-aware provenance and permission checks; no invented locator or attribution | Foundation; hypercare owner pending; M24; operations owner | NOT_RUN · No launch; hypercare is not started | CENTRAL+Ops/employer: all prior Gate evidence, alpha/beta/UAT, rollback/restore/SLO security and signed Go/No-Go before any deployment or Hypercare |
| ☐ P3M25-A04 | **Output:** تحلیل Feedback کاربران اولیه; **Check:** stable user ownership, linked records and concurrency/retry checks | Foundation; hypercare owner pending; M24; operations owner | NOT_RUN · No launch; hypercare is not started | CENTRAL+Ops/employer: all prior Gate evidence, alpha/beta/UAT, rollback/restore/SLO security and signed Go/No-Go before any deployment or Hypercare |
| ☐ P3M25-A05 | **Output:** اصلاح فقط Bugهای فاز ۳ و جلوگیری از Scope creep; **Check:** dated approved decision, diagrams/risk register and explicit Gate owner | Foundation; hypercare owner pending; M24; operations owner | NOT_RUN · No launch; hypercare is not started | CENTRAL+Ops/employer: all prior Gate evidence, alpha/beta/UAT, rollback/restore/SLO security and signed Go/No-Go before any deployment or Hypercare |
| ☐ P3M25-A06 | **Output:** Freeze Baseline عملیاتی پس از پایداری; **Check:** dated approved decision, diagrams/risk register and explicit Gate owner | Foundation; hypercare owner pending; M24; operations owner | NOT_RUN · No launch; hypercare is not started | CENTRAL+Ops/employer: all prior Gate evidence, alpha/beta/UAT, rollback/restore/SLO security and signed Go/No-Go before any deployment or Hypercare |
| ☐ P3M25-A07 | **Output:** ساخت Runbook بهره‌برداری; **Check:** versioned artifact plus reproducible source-specific acceptance check and evidence | Foundation; hypercare owner pending; M24; operations owner | NOT_RUN · No launch; hypercare is not started | CENTRAL+Ops/employer: all prior Gate evidence, alpha/beta/UAT, rollback/restore/SLO security and signed Go/No-Go before any deployment or Hypercare |
| ☐ P3M25-A08 | **Output:** انتقال دانش به تیم نگهداری; **Check:** versioned artifact plus reproducible source-specific acceptance check and evidence | Foundation; hypercare owner pending; M24; operations owner | NOT_RUN · No launch; hypercare is not started | CENTRAL+Ops/employer: all prior Gate evidence, alpha/beta/UAT, rollback/restore/SLO security and signed Go/No-Go before any deployment or Hypercare |
| ☐ P3M25-A09 | **Output:** تعریف Contract فاز ۴ برای Profile، Assessment، Goals و Action Plan; **Check:** run positive/negative Schema and version compatibility checks | Foundation; hypercare owner pending; M24; operations owner | NOT_RUN · No launch; hypercare is not started | CENTRAL+Ops/employer: all prior Gate evidence, alpha/beta/UAT, rollback/restore/SLO security and signed Go/No-Go before any deployment or Hypercare |
| ☐ P3M25-A10 | **Output:** ثبت Tech debt و Deferred decisions; **Check:** versioned artifact plus reproducible source-specific acceptance check and evidence | Foundation; hypercare owner pending; M24; operations owner | NOT_RUN · No launch; hypercare is not started | CENTRAL+Ops/employer: all prior Gate evidence, alpha/beta/UAT, rollback/restore/SLO security and signed Go/No-Go before any deployment or Hypercare |
| ☐ P3M25-A11 | **Output:** Phase 3 closure report.; **Check:** versioned artifact plus reproducible source-specific acceptance check and evidence | Foundation; hypercare owner pending; M24; operations owner | NOT_RUN · No launch; hypercare is not started | CENTRAL+Ops/employer: all prior Gate evidence, alpha/beta/UAT, rollback/restore/SLO security and signed Go/No-Go before any deployment or Hypercare |

## ۵. متن اصلی ماژول‌ها و بسته‌های عملیاتی مرتبط

متن ماژول‌ها و بسته‌ها با دامنهٔ کامل منبع آمده است. معیارها، Gateها و خروجی‌های منبع در زمان تحویل کنترل شوند. جدول بخش ۴ مالک اقدام را مشخص می‌کند.

## Module 02 — `environment_and_security_baseline`

### فعالیت‌ها

1. Freeze نسخه Python، Node، PostgreSQL، Qdrant، Redis و Docker؛
2. ساخت lockfileهای وابستگی؛
3. تعریف `.env.example` بدون Secret؛
4. ممنوع‌کردن Secret در Repository؛
5. فعال‌کردن Dependency و Secret scanning؛
6. تنظیم Lint، Type check و Test command واحد؛
7. ساخت SBOM و گزارش Dependency؛
8. ثبت Timezone، Locale و Encoding؛
9. تعیین Log redaction policy؛
10. ساخت Environment manifest.

### Gate و شواهد

Build پاک روی محیط جدید، Secret leakage صفر، Dependency بحرانی حل‌نشده صفر و فرمان واحد تست موفق باشد. شواهد: SBOM، Environment manifest و Security baseline report.

---

## Module 03 — `project_structure_and_contracts`

### ساختار پیشنهادی

```text
apps/
  api/
  web/
src/phase3/
  auth/
  conversations/
  rag_runtime/
  citations/
  safety/
  telemetry/
  storage/
schemas/phase3/
infra/
tests/phase3/
docs/phase3/
```

### فعالیت‌ها

1. تعریف مرز Domain moduleها؛
2. تعریف Error model مشترک؛
3. تعریف Request ID و Trace ID؛
4. نسخه‌بندی API از `/v1`؛
5. ساخت Schemaهای User، Conversation، Message، Answer و Citation؛
6. تعریف فیلدهای Attribution؛
7. تعریف Compatibility policy؛
8. ساخت Contract tests بین Backend، Frontend و RAG runtime؛
9. ساخت Architecture dependency test برای جلوگیری از Import معکوس.

### Gate

Schema validation و Contract test صددرصد PASS و Circular dependency صفر باشد.

### شاهد دانش فنی

Separation of concerns، Versioned contracts و Dependency governance.

---

## Module 04 — `database_schema_and_migrations`

### توضیح برای کارفرما

دیتابیس فقط محل ذخیره پیام نیست؛ باید نشان دهد چه کسی، چه زمانی، با کدام نسخه دانش و کدام منبع پاسخ گرفته است.

### موجودیت‌های فعال فاز ۳

```text
users, identities, sessions, consents
conversations, messages, answers, citations
retrieval_runs, model_runs, feedback
audit_events, security_events
knowledge_releases
```

### فعالیت‌ها

1. طراحی ERD و Data dictionary؛
2. تعریف Primary/Foreign key و Index؛
3. افزودن `user_id` به تمام داده‌های کاربر؛
4. ذخیره Citation و Attribution به‌صورت ساخت‌یافته؛
5. ذخیره Versionهای knowledge/retrieval/model/policy؛
6. تعریف Migration forward و rollback؛
7. تست Migration روی دیتابیس خالی و دیتابیس دارای داده؛
8. تعریف Retention و soft/hard delete؛
9. آماده‌سازی Namespace رزروشده برای موجودیت‌های فاز ۴ بدون فعال‌سازی آن‌ها.

### Gate

Migration clean، rollback test، FK violation صفر و Query plan قابل قبول برای مسیرهای اصلی.

### شاهد دانش فنی

Data modeling، Migration discipline، Version trace و Query optimization.

---

## Module 05 — `authentication_and_sessions`

### فعالیت‌ها

1. انتخاب روش ورود طبق تصمیم کارفرما؛
2. Password hashing استاندارد در صورت ورود رمزدار؛
3. Session token امن و rotation؛
4. Cookie امن با `HttpOnly`، `Secure` و `SameSite`؛
5. CSRF policy؛
6. محدودیت تلاش ورود و lockout کنترل‌شده؛
7. Logout و revoke همه نشست‌ها؛
8. Expiration و refresh policy؛
9. ثبت Security event بدون ذخیره Secret؛
10. تست منفی Session theft و replay.

### Gate

دسترسی بدون هویت به Endpoint محافظت‌شده صفر، Session پس از revoke نامعتبر و Secret در log صفر باشد.

### شاهد دانش فنی

Identity architecture، Session lifecycle و Negative security testing.

---

## Module 06 — `tenant_isolation_and_rls`

### توضیح برای کارفرما

مهم‌ترین ریسک چندکاربره این است که یک کاربر تاریخچه یا داده کاربر دیگر را ببیند. کنترل فقط در کد کافی نیست و باید در دیتابیس نیز اعمال شود.

### فعالیت‌ها

1. فعال‌سازی Row-Level Security برای جداول کاربرمحور؛
2. تعریف Policy خواندن، نوشتن، ویرایش و حذف؛
3. تنظیم Context امن user/tenant در هر Transaction؛
4. جلوگیری از دسترسی Background job خارج از Scope؛
5. تست cross-user برای تمام Endpointها؛
6. تست ID enumeration؛
7. تست دسترسی مستقیم Repository layer؛
8. ثبت Audit برای عملیات حساس؛
9. ساخت Isolation matrix.

### Gate

Cross-user data exposure و RLS bypass در تست‌ها باید صفر باشد.

### شاهد دانش فنی

Defense in depth، Database-enforced isolation و Adversarial authorization tests.

---

## Module 10 — `answer_orchestration`

### فعالیت‌ها

1. ساخت Query context از پیام جاری و تاریخچه محدود؛
2. Intent و Answerability؛
3. Retrieval و Context builder؛
4. تولید پاسخ ساخت‌یافته؛
5. Claim/Citation verification؛
6. اعمال Safety و No-answer؛
7. ساخت Confidence از اجزای قابل توضیح؛
8. ذخیره Runها و Versionها در یک Transaction منطقی؛
9. مدیریت cancellation و duplicate request؛
10. Idempotency برای retry کلاینت.

### Gate

هر Answer باید `request_id`، نسخه دانش، Runها، Citation و وضعیت Safety داشته باشد. پاسخ ناقص نباید به‌عنوان موفق ثبت شود.

### شاهد دانش فنی

Traceable orchestration، Idempotency، Failure-state design و Explainable confidence.

---

## Module 13 — `product_api`

### Endpointهای حداقل

```text
POST /v1/auth/login
POST /v1/auth/logout
GET  /v1/me
POST /v1/conversations
GET  /v1/conversations
GET  /v1/conversations/{id}
POST /v1/conversations/{id}/messages
POST /v1/answers/{id}/feedback
GET  /health/live
GET  /health/ready
```

### فعالیت‌ها

1. OpenAPI نسخه‌دار؛
2. Validation ورودی و محدودیت اندازه؛
3. Error code پایدار؛
4. Pagination تاریخچه؛
5. Streaming پاسخ با stateهای مشخص؛
6. Idempotency key؛
7. Request/Trace ID؛
8. Authorization در هر Endpoint؛
9. Contract test و backward compatibility؛
10. API abuse tests.

### Gate

OpenAPI validation، Contract suite، Authorization suite و Error contract صددرصد PASS.

### شاهد دانش فنی

API engineering، versioning، streaming contract و abuse resistance.

---

## Module 15 — `conversation_history_and_feedback`

### فعالیت‌ها

1. ذخیره User message و Answer به‌صورت immutable event؛
2. عنوان‌گذاری مکالمه بدون تغییر محتوای اصلی؛
3. Pagination و مرتب‌سازی؛
4. حذف مکالمه طبق Retention policy؛
5. Feedback مثبت/منفی و دسته خطا؛
6. ثبت Citation مشکل‌دار یا انتساب اشتباه؛
7. جلوگیری از دسترسی کاربر دیگر؛
8. Export ساخت‌یافته در صورت تصویب Scope؛
9. Dataset بازخورد بدون PII برای ارزیابی بعدی؛
10. تست Race condition و duplicate write.

### Gate

History consistency، حذف مطابق Policy، cross-user exposure صفر و Feedback trace کامل.

### شاهد دانش فنی

Event traceability، feedback engineering و privacy-preserving evaluation data.

---

## Module 16 — `observability_and_audit`

### فعالیت‌ها

1. Structured log با Request/Trace ID؛
2. Metricهای request، latency، error، retrieval و model؛
3. Dashboard سلامت سرویس؛
4. Alert برای Availability، error rate، DB pool و مصرف؛
5. Audit event برای ورود و عملیات حساس؛
6. Redaction داده مالی و Token؛
7. ثبت نسخه Knowledge/Model/Policy؛
8. Trace نمونه‌برداری‌شده برای مسیر پاسخ؛
9. Runbook هشدارها؛
10. تست اینکه PII و Secret در Log وجود ندارد.

### Gate

هر درخواست قابل ردیابی، Alertهای بحرانی آزمایش‌شده و Secret/PII leakage در log صفر.

### شاهد دانش فنی

End-to-end traceability، privacy-aware telemetry و operational runbooks.

---

## Module 18 — `containerization_and_networking`

### سرویس‌های مرجع

```text
web, api, postgres, qdrant, redis, reverse-proxy
```

### فعالیت‌ها

1. Dockerfile چندمرحله‌ای برای Web و API؛
2. اجرای process با کاربر غیر root؛
3. Healthcheck و startup dependency؛
4. Network segmentation؛
5. Volume و persistence policy؛
6. Secret injection در Runtime؛
7. محدودیت CPU/Memory؛
8. Image scanning و pin digest؛
9. Compose برای Local و Deployment؛
10. Cold-start و restart test.

### Gate

Build تکرارپذیر، Critical image vulnerability حل‌نشده صفر و restart بدون از دست‌رفتن داده.

### شاهد دانش فنی

Reproducible packaging، container hardening و stateful-service design.

---

## Module 19 — `ci_cd_and_release_pipeline`

### فعالیت‌ها

1. Lint، type check و unit tests؛
2. Integration tests با سرویس‌های موقت؛
3. Migration test؛
4. Contract و security tests؛
5. Build و scan Image؛
6. تولید Release manifest و SBOM؛
7. Deploy خودکار به Staging؛
8. Approval دستی Production؛
9. Rollback workflow؛
10. نگهداری Artifact و Test report؛
11. Branch protection و ممنوعیت Secret در log.

### Gate

هیچ Deployment تولیدی بدون Test report، Image digest، Migration check و Approval انجام نشود.

### شاهد دانش فنی

Quality gates، supply-chain evidence و controlled deployment.

---

## Module 20 — `staging_deployment_and_e2e`

### فعالیت‌ها

1. Provision محیط Staging نزدیک به Production؛
2. TLS و Domain آزمایشی؛
3. داده Test غیرشخصی؛
4. اجرای Migration؛
5. بارگذاری Release پذیرفته‌شده فاز ۲؛
6. Smoke و E2E؛
7. تست سه منبع و چهار نوع Citation؛
8. تست نویسنده/سردبیر؛
9. تست No-answer و Safety؛
10. تست Restart و dependency outage؛
11. UAT کارفرما و ثبت Issue.

### Gate

مسیرهای بحرانی E2E و UAT PASS، Issue بحرانی باز صفر و Staging قابل بازسازی باشد.

### شاهد دانش فنی

Production-like validation، E2E evidence و stakeholder acceptance.

---

## Module 21 — `security_privacy_and_threat_validation`

### فعالیت‌ها

1. Threat model برای Web، API، DB، Qdrant و Model gateway؛
2. تست OWASP API/Web متناسب؛
3. تست prompt injection و data exfiltration؛
4. تست IDOR و RLS bypass؛
5. TLS، headerهای امنیتی و CORS؛
6. Dependency و image scan؛
7. Consent و Retention validation؛
8. Account/data deletion test؛
9. Incident response tabletop؛
10. ثبت Risk acceptanceهای باقی‌مانده.

### Gate

Critical/High vulnerability حل‌نشده صفر، Data isolation failure صفر و Incident runbook تأییدشده.

### شاهد دانش فنی

Threat modeling، privacy engineering، adversarial validation و incident readiness.

---

## Module 22 — `backup_restore_and_disaster_recovery`

### فعالیت‌ها

1. Backup نسخه‌دار PostgreSQL؛
2. Snapshot و Restore Qdrant؛
3. Backup Config و Release pointer؛
4. رمزگذاری و دسترسی محدود Backup؛
5. Retention و rotation؛
6. Restore در محیط خالی؛
7. Point-in-time recovery در صورت امکان زیرساخت؛
8. اندازه‌گیری RPO/RTO واقعی؛
9. تست خرابی جزئی و کامل؛
10. Runbook و گزارش Restore.

### Gate

Backup بدون Restore موفق ارزشی ندارد. Restore کامل باید در محدوده RPO/RTO مصوب PASS شود.

### شاهد دانش فنی

Recoverability evidence، DR testing و state restoration.

---

## Module 23 — `performance_load_and_failure_testing`

### سناریوها

- Login و History بدون مدل؛
- Chat کوتاه و بلند؛
- Query بدون پاسخ؛
- Citation چندمنبعی؛
- پیک Concurrent؛
- کندی یا قطع Model provider؛
- قطع Redis؛
- کندی PostgreSQL یا Qdrant؛
- Restart یک سرویس؛
- محدودیت Rate و Budget.

### فعالیت‌ها

1. Freeze workload model با اعداد تأییدشده؛
2. Baseline p50/p95/p99؛
3. Load، stress و soak test؛
4. اندازه‌گیری saturation؛
5. Failure injection کنترل‌شده؛
6. تحلیل Queue و timeout؛
7. بررسی DB pool و Index latency؛
8. اندازه‌گیری هزینه هر پاسخ؛
9. Capacity report و tuning؛
10. Regression threshold.

### Gate

SLOهای Freeze‌شده، Error budget و ظرفیت Peak باید PASS شوند. اعداد نمونه یادداشت تصمیم، تا زمان Freeze تعهد قطعی نیستند.

### شاهد دانش فنی

Load model، capacity engineering، failure analysis و cost-performance tuning.

---

## Module 24 — `production_launch`

### فعالیت‌ها

1. Go/No-Go checklist؛
2. Freeze Image digest، DB migration و Knowledge release؛
3. Backup قبل از استقرار؛
4. اجرای Deployment کنترل‌شده؛
5. Migration و health verification؛
6. Smoke test با حساب آزمایشی؛
7. فعال‌سازی محدود کاربران اولیه؛
8. پایش Error، latency، cost و safety؛
9. Rollback در عبور از Threshold؛
10. ثبت زمان، نسخه‌ها و مسئول تصمیم؛
11. Production acceptance report.

### Gate

تمام P0ها بسته، Rollback آماده، Backup معتبر، UAT تأییدشده و مانیتورینگ فعال باشد.

### شاهد دانش فنی

Controlled release، change traceability، rollback readiness و launch evidence.

---

## Module 25 — `hypercare_and_phase4_handoff`

### فعالیت‌ها

1. بازه Hypercare با مالک مشخص؛
2. دسته‌بندی Incident و SLA پاسخ داخلی؛
3. مرور روزانه Error، latency، Citation و Safety؛
4. تحلیل Feedback کاربران اولیه؛
5. اصلاح فقط Bugهای فاز ۳ و جلوگیری از Scope creep؛
6. Freeze Baseline عملیاتی پس از پایداری؛
7. ساخت Runbook بهره‌برداری؛
8. انتقال دانش به تیم نگهداری؛
9. تعریف Contract فاز ۴ برای Profile، Assessment، Goals و Action Plan؛
10. ثبت Tech debt و Deferred decisions؛
11. Phase 3 closure report.

### Gate

Incident بحرانی باز صفر، Runbook و آموزش تحویل‌شده، Metrics پایدار و قرارداد ورودی فاز ۴ تأییدشده باشد.

### شاهد دانش فنی

Operational learning، incident taxonomy، maintainability و controlled handoff.

---

## ۴. بسته P3-02 - مدل داده PostgreSQL

### موجودیت‌های فعال

- users، identities، sessions و consents.
- conversations، messages و citations.
- retrieval_runs، model_runs و feedback.
- audit_events، security_events و deletion_requests.

### موجودیت‌های رزروشده برای فاز ۴

- financial_profiles و financial_snapshots.
- assessments، scores، goals و action_plans.
- risk_flags و human_referrals.

### قواعد

- همه داده‌های کاربر user_id یا tenant_id داشته باشند.
- Migrationها نسخه‌دار و rollback plan داشته باشند.
- PII از log و model payload تا حد ممکن حذف شود.
- Foreign key، uniqueness و retention job تست شود.

### Gate

Migration از DB خالی موفق و تست cross-user access برای تمام جداول حساس پاس شود.

## ۵. بسته P3-03 - Auth، Consent و Isolation

### کارها

- ثبت‌نام، ورود، logout، session rotation و password reset.
- password hashing استاندارد، cookie امن و CSRF/CORS policy.
- consent version، تاریخ پذیرش و امکان پس‌گرفتن.
- Row-Level Security و FORCE RLS در جداول کاربر.
- تست‌های منفی افقی و عمودی دسترسی.
- rate limit برای login، chat و feedback.

PostgreSQL امکان اعمال Policy در سطح سطر را فراهم می‌کند؛ نبود Policy پس از فعال‌سازی RLS حالت default-deny ایجاد می‌کند، اما owner و نقش‌های BYPASSRLS باید در طراحی و تست کنترل شوند. مرجع: <span dir="ltr">https://www.postgresql.org/docs/current/ddl-rowsecurity.html</span>

### Gate

هیچ User A نتواند با API، شناسه یا Query تغییریافته، داده User B را بخواند یا تغییر دهد.

## ۸. بسته P3-06 - زیرساخت و Deployment

### اجزا

- Docker images نسخه‌دار برای Web، API و Worker.
- PostgreSQL، Qdrant، Redis و Object Storage مدیریت‌شده یا self-host بر اساس تصمیم.
- Reverse proxy، TLS، domain و secure headers.
- environment separation برای local/staging/production.
- secrets management و rotation.
- migrations و seedهای کنترل‌شده.

### Release

- CI: lint، unit، integration، security و build.
- CD با approval، migration gate، smoke test و rollback.
- Infrastructure/Deployment runbook.
- Release manifest شامل app و RAG artifact versions.

### Gate

Staging و Production از روی دستور مستند ساخته شوند و rollback یک Release آزمایشی اجرا شود.

## ۹. بسته P3-07 - Backup، Restore و Data Lifecycle

- backup رمزگذاری‌شده PostgreSQL و Qdrant snapshot.
- retention و lifecycle برای object/log.
- restore drill و گزارش RPO/RTO واقعی.
- export و deletion workflow.
- tombstone/audit برای حذف و عدم بازگشت ناخواسته از backup.

### Gate

Restore روی محیط جدا انجام و consistency مکالمه، Citation و Release IDs بررسی شود.

## ۱۱. بسته P3-09 - Security و GenAI Hardening

- prompt injection tests برای Query و Retrieved content.
- output validation و safe rendering.
- access control روی Sourceهای غیرعمومی.
- dependency/container scanning و SBOM.
- secret scanning، audit log و admin access review.
- abuse، rate/cost limit و denial-of-wallet controls.
- test برای sensitive information disclosure.

OWASP در نسخه جاری GenAI، Prompt Injection، افشای اطلاعات حساس، handling ناامن خروجی و agency بیش از حد را از ریسک‌های اصلی می‌داند. مرجع: <span dir="ltr">https://owasp.org/www-project-top-10-for-large-language-model-applications/</span>

### Gate

هیچ finding بحرانی باز در تست امنیت، cross-user و LLM red-team وجود نداشته باشد.

## ۱۲. بسته P3-10 - Performance و Capacity

### سناریوهای تست

- chat cached و uncached.
- پاسخ کوتاه/بلند و چند Citation.
- provider کند یا unavailable.
- spike، sustained load و concurrent conversations.
- DB و Qdrant degradation.

### Targetهای اولیه غیرقراردادی

- Availability پایلوت: 99.5٪.
- p95 مسیر غیر AI: کمتر از 500ms.
- p95 پاسخ AI: ترجیحاً کمتر از 15s، وابسته به مدل.
- error budget، concurrent limit و daily cost cap پس از Load test فریز شوند.

### Gate

Capacity report بر مبنای بار واقعی و Cost model وجود داشته باشد؛ عدد ۱۵۰۰ تا ۲۰۰۰ کاربر ثبت‌شده به‌تنهایی sizing محسوب نشود.

## ۶. دستور کامل اجرا، Gateها، Crosswalk و پیوست تخصصی

# پایگاه‌داده DATABASE_F3 | دستور مستقل

## مبنای فعلی و ترتیب اجرای این نسخه

این فایل به‌تنهایی دستور کامل این چت است. مبنای شروع فعلی: **source آزموده 996dfc9b66cf8cbd4b37b7a267d08cc5acd5deba و HEAD مستندات 5b0f14d06bf37b8b20926a3db491344b22daac05؛ 0e301a نسخهٔ پیشین است.** شواهد قبلی و نسخه‌های ذکرشده در متن و پیوست برای مقایسه تاریخی‌اند. هر جا دستور قدیمی دربارهٔ نسخه یا تقدم کار با این بخش تفاوت دارد، همین بخش ملاک اجراست. تطبیق ۹۲→۱۰۵ Crosswalk در Foundation انجام شده و کار دوباره برای شمارش لازم نیست. شواهد جدید هر ردیف را به رجیستر اضافه کن.

از source آزموده `996dfc9b66cf8cbd4b37b7a267d08cc5acd5deba` ادامه بده و HEAD مستندات را جدا گزارش کن. SQL، image و role pins موجود را برای مقایسه حفظ کن. Git Blob نصب‌کنندهٔ 03 و workflow/اسکریپت‌های 15–17 را برای repin بده. پیش‌نیازهای ترتیب اجرا و شواهد موردنیاز 11 را صریح ثبت کن.

1. شواهد populated upgrade/Restore، Ledger failure و Query Plan را به M04-A07 و M22-A09 و ردیف‌های مرتبط با معیار دقیق وصل کن. PG17.11، دو Owner، حجم دادهٔ آزمایشی و محدودیت RPO/RTO را ثبت کن. نسخه‌های `0e301a` و `996dfc9` را در یک محیط ایزوله با DB55، 001–010 و Restore هدف تأیید کن. اجرای دستورات روی DB قدیمی فقط با مسیر Ops.
2. Data Dictionary و ERD را با دامنهٔ فعال و سیاست Owner، Consent/withdrawal، Feedback روی Answer معتبر، حذف و عدم بازگشت داده در Restore تکمیل کن. مشترکاً قرارداد را به API بده. اندازه و بار واقعی، SLO، PITR/retention و نسخه/رمزگذاری backup را به تصمیم مالک وصل کن. 011 در مسیر جدا و بدون فعال‌سازی در no-dispatch.
3. روی SHA یکپارچه، Product/Bootstrap و نقش‌های واقعی را با Foundation/Ops attest کن. هر ردیف ۵۷گانه را با وضعیت تازه به‌روز کن و دلیل تداوم ۲۹ OPEN/۲۴ BLOCKED را ردیف‌به‌ردیف بسنج. از ثبت دوبارهٔ صرف CSV عبور کن.

## قالب ثابت برای گزارش بعدی

برای هر تیم `baseline SHA → tested SHA → PR HEAD → integrated/deployed SHA`، diff اجرایی، CI و محیط، IDهایی که شواهد/پذیرششان عوض شده، تعداد انجام‌شده و باقی‌مانده با همان مخرج، مانع و درخواست بعدی. گزارش تازه با آخرین وضعیت مقایسه می‌شود. از یک تست سبز یا یک فایل ممیزی افزایش خودکار پذیرش ثبت نکن.

## دستور کامل و معیارهای نقشه

این متن را به‌صورت کامل به چت اجرایی بده. معیارهای نهایی و مسیر ادامه پس از رفع وابستگی در خود فایل آمده‌اند.

## سری آزمون و رسید الزامی Database

از نصب خالی شروع کن، سپس همان workflow را با دادهٔ نماینده، دو owner و دادهٔ قدیمی تکرار کن. هویت و manifest ورودی کلاستر اصلی آزمایش و مقصد Restore باید متفاوت باشند. برای ہر migration شماره، digest، timestamp، state و نتیجه ثبت شود. روال partially applied/duplicate/rollback باید وضعیت سازگار باقی بگذارد. SQL و رفتار API را با sessionهای معتبر، لغوشده و owner متفاوت کنار هم بسنج. سیاست retention/deletion و هویت نقش‌ها را در backup index و restore test لحاظ کن. سنجش عملیاتی RTO/RPO با اندازه/بار و معیار امضاشده گزارش شود.

تحویل به API و Foundation شامل ERD/data dictionary، mapping Owner و transaction fence، ماتریس schema/function/grant/RLS، replay/concurrency، policy consent/delete/export/feedback، DB55 profiles، مسیر 011 جدا، restore/rollback manifest و shas. ۴/۵۷ فقط DONE محدود، ۲۹ OPEN، ۲۴ BLOCKED. شواهد مقصد مستقل از CI هستند.

تو مجری DB فاز ۳ هستی. از Draft [#59](https://github.com/Shahbazi-Amir/RAG_finance_app/pull/59) و آزمایشگاه `infra/postgres/dev_f3_isolated/` ادامه بده. تحویل نهایی DB: SHA آزموده `0e301a26096cb9f8c2b8e3fde3e20e9a1add48a5`، CI `45109023781`. آزمون جدا DB011 در `45108041850` attempt 2. Foundation در c2edbbf قبلاً DB `b6b79369006eca3a1e4c8e75a9ba4ab14d0fab74` را ثبت کرده؛ تفاوت را با blob/diff و CI حل کن و به Foundation بگو کدام تغییر runtime باید repin شود. دنبالهٔ DB #56/#57 را فقط به‌عنوان مرجع Claim و عملیات بخوان. ۵۷ ردیف `docs/PHASE3_57_ROW_DATABASE_AUDIT_20261123.md` و `coordination/tasks/AGENT-DB-01.md` را مبنا قرار بده. اکنون ۴ DONE محدود CI، ۲۹ OPEN و ۲۴ BLOCKED در گزارش DB ثبت شده‌اند.

- [ ] M03/04: ERD و data dictionary نسخه‌دار، شناسه و مالکیت هر جدول کاربرمحور، کلید مرکب و cross-owner FK، indexes و EXPLAIN در دادهٔ نماینده. طرح persistence برای Citation/Attribution و نسخهٔ knowledge/retrieval/model/policy را بعد از قرارداد producer تثبیت کن. جدول‌های فاز ۴ در محدودهٔ طراحی بمانند.
- [ ] M04/06: 001–010 pin شده با migration ledger و DB55 در profile no-dispatch، نصب fresh و داده‌دار، backup پیش از مهاجرت؛ آزمون rollback مجاز در clone و بازیابی امن شکست/نیمه‌تمام با شواهد. TLS verify-full، حداقل grantهای Product/Bootstrap، FORCE RLS و transaction-scoped owner، بدون port عمومی. نام DB، system ID، نقش‌ها، نسخه، migration SHAs و خروجی DB55 مشترک را به API/Foundation بده.
- [ ] M05/06/13/15: Signed Owner/session fence همان تراکنش، A/B، revoke، pagination، immutable messages/answers، عنوان mutable، idempotency هم‌زمان و پس از crash، FK و عدم duplicate. تست اتصال **ماژول واقعی** Product/Bootstrap در کلاستر تازه و restore؛ L2 همراه API/Ops. Consent و withdrawal، Feedback با Answer ID، citation report، حذف حساب/داده و عدم reappearance در Restore را با قرارداد، سیاست Retention و مالکیت آزمایش کن؛ Export و dataset بدون PII به تصمیم مصوب وابسته‌اند.
- [ ] DB011 مسیر جدا: یک Claim دائمی بعد از T1/T2 و تأیید commit، race و UNKNOWN/reconciliation بدون reclaim خودکار؛ Gateway calls=0 در آزمون DB. فقط پس از اختیار مستقل برای مسیر dispatch واقعی. Migration 012+ فقط برای نیاز مدل‌شدهٔ مصوب.
- [ ] M21/22/23 و P3OP02/03/07: نسخه‌گذاری dump، checksum، رمزگذاری و custody مصوب، بازیابی در کلاستر دوم و اثبات عدم بازگشت دادهٔ حذف‌شده، rollback و سناریوی خرابی، retention/rotation، PITR اگر مصوب، RPO/RTO واقعی. برای Qdrant، config و release pointer رسید از Engine/Ops بخواه. دستورات، معیارهای DB55 و نتیجهٔ روی مقصد را تحویل بده.

### قواعد اجرا و تحویل

- مرجع اصلی فقط‌خواندنی: `Shahbazi-Amir/RAG_finance` شاخه `rag-phase2`، دو فایل `data/Road_Maps/RAG_finance_phase3_modular_execution_plan.md` و `data/Road_Maps/RAG_finance_phase3_operational_roadmap.md`. مرجع ثابت `7c74783c3dcda897b010ba9ea358d113f172ed1f`. تغییرات کد فقط در `Shahbazi-Amir/RAG_finance_app`، worktree/شاخهٔ مستقل و Draft PR تخصصی. رجیستر `coordination/phase3_checklist.md` فقط با Foundation و تصمیم پذیرش با CENTRAL. `coordination/open_decisions.md` و `references/phase2/source_manifest.json` را بخوان.
- ابتدا HEAD، SHA آزموده، SHA integrated و SHA مستقر را جدا ثبت کن. روی مبنای قدیمی از صفر بازسازی نکن. اختلاف executable blobs، وضعیت CI و کارهای باز را از Git و رسید به دست بیاور. کار را در همان نوبت از اولین ردیف قابل اجرا شروع کن و همهٔ کارهای مستقل را تا رسید قابل بازتولید پیش ببر.
- تمام ردیف‌های مالکیتی و رابط‌های مشترک نقشه را به جدول `ID | مالک مسئول | معیار قبولی | مسیر و SHA | محیط | پیاده‌سازی | تست | پذیرش | رسید | مانع و ورودی دقیق` تبدیل کن. ۲۶۲ فعالیت و ۲۶ Gate مستقل‌اند. شناسه‌های P3OP روی P3M نگاشت می‌شوند. رجیستر ۱۰۵ شناسهٔ P3OP دارد. CSV تحویل ۹۲ دارد. الزامات و GAP/CONFLICT موجود را ردیف‌به‌ردیف reconcile کن. کار تکمیل‌شده را با شاهد معتبر همان دامنه ثبت کن. برای هر کار بیرونی یک درخواست دقیق با فایل/نسخه/مالک و آزمون پس از دریافت آماده کن. حالت فاقد شاهد را باز بگذار و کارهای مستقل را ادامه بده.
- عملیات عادی داخل محدوده را خودت اجرا کن. پشتهٔ قدیمی Docker در اختیار SERVER/Ops است. کاندیدا را با نام پروژه، شبکه، مسیر، پورت و Volume مستقل بساز. هیچ stop/restart/migrate/restore روی پشتهٔ موجود، بازکردن ایندکس اصلی در حالت RW، ادغام نهایی، جابه‌جایی ترافیک آروان یا هزینهٔ مدل از این مأموریت مجوز نمی‌گیرد. برای اقدام واقعی روی مک، از Ops receipt مربوط به همان scope و همان SHA بگیر. اگر دسترسی نداری، آزمایش مستقل، runbook واقعی و ورودی دقیق برای Ops را تحویل بده.
- مسیر هماهنگ: تکمیل کد/API/UI/DB و قراردادها هم‌زمان با آماده‌سازی نصب؛ نصب تمیز و L2 ورود/History روی کاندیدای مک؛ در صورت مجوز جداگانه فقط یک Smoke با C018 موجود در حالت NO_DISPATCH_ONLY؛ فعالیت‌های دیگر نقشه موازی ادامه دارند. اتصال موتور محصول پس از Release/NB23 پذیرفته‌شده و Gate00 و تصمیم‌های قرارداد/C019/Locator/هزینه. بعد از E2E واقعی و Gateهای انتشار، Freeze و Restore/Rollback و تصمیم آروان. Smoke بازیابی شاهد محدود است.
- معیار L2 مشترک: HTTPS و OIDC واقعی، BFF امضاشده mTLS/RS256، Product PG و دو کاربر مستقل. یک Send حقیقی با 202 و T1/T2 پایدار؛ فقط یک فرزند C018 با شاهد OS در محیط مجاز؛ همان Attempt/Trace، CONTEXT_READY، top10=10، generation_calls=0، dispatch=false و answer=null. Refresh فقط GET، بدون POST/فرزند اضافه؛ replay=200 با همان T2؛ Owner B=404، نشست منقضی یا لغوشده=401؛ FAILED/UNKNOWN بدون اجرای مجدد خودکار. شواهد sanitize شده و هم‌بسته با SHA، زمان، شناسه‌های مستعار و Assert. در آزمون بدون موتور، بخش C018 را صریحاً NOT_RUN ثبت کن.
- پایان: Draft PR، SHA ثابت، Diff نسبت به مبنا، فرمان‌های واقعی تست و نتیجهٔ مثبت/منفی، لینک CI و رسیدهای بدون secret، جدول همهٔ ردیف‌ها و تحویل دقیق به مالکان. اگر ردیف باز است، مانع خارجی و آزمون بعدی را مشخص کن. از عدد PASS تست به درصد پایان نقشه یا تأیید Gate نرس.
## از آغاز تا تحویل کامل

این فایل دستور اجرای کامل است. ظرف همین مأموریت کد، تست، رسید و handoff را انجام بده. در اولین پیام به ساخت برنامه اکتفا نکن. ابتدا refs، شاخه‌ها، وضعیت Git و ابزار دسترس را بخوان. بعد روی اولین ردیف مستقل اجرا کن. تا بسته‌شدن همهٔ ردیف‌های قابل اجرا، مانع یک ردیف نباید ردیف‌های مستقل را متوقف کند. برای تصمیم‌های عادی و قابل برگشت از خط‌مشی موجود و شواهد همان مخزن استفاده کن.

مبنای تعیین دامنه دو نقشهٔ زیر و رجیستر نسخه‌دار اپ است. اگر نسخهٔ تازه‌تری از سند پیدا کردی، Diff و مالک تغییر را ثبت کن و ردیفی را بی‌صدا حذف نکن. اولویت‌بندی P0/P1/P2 فقط برای ترتیب اجراست. شرطی بودن یک قابلیت را با تصمیم مالک ثبت کن و تا آن زمان وضعیت را باز نگه دار.

- [نقشهٔ ماژولار](https://github.com/Shahbazi-Amir/RAG_finance/blob/7c74783c3dcda897b010ba9ea358d113f172ed1f/data/Road_Maps/RAG_finance_phase3_modular_execution_plan.md)
- [نقشهٔ عملیاتی](https://github.com/Shahbazi-Amir/RAG_finance/blob/7c74783c3dcda897b010ba9ea358d113f172ed1f/data/Road_Maps/RAG_finance_phase3_operational_roadmap.md)
- [رجیستر و Gateهای اپ](https://github.com/Shahbazi-Amir/RAG_finance_app/blob/c2edbbf87f02ff2cfb8ba12a0a9594533324fd28/coordination/phase3_checklist.md)
- [دفتر تصمیم‌های باز](https://github.com/Shahbazi-Amir/RAG_finance_app/blob/c2edbbf87f02ff2cfb8ba12a0a9594533324fd28/coordination/open_decisions.md)
- [Provenance نقشه‌ها](https://github.com/Shahbazi-Amir/RAG_finance_app/blob/c2edbbf87f02ff2cfb8ba12a0a9594533324fd28/references/phase2/source_manifest.json)

### برنامهٔ اجرایی و معیار پایان

1. baseline را برای هر ID ثبت کن. بین تغییر لازم، شاهد معتبر موجود و وابستگی بیرونی تمایز بگذار. ستون‌های اجباری دفتر اجرا `ID, owner, criterion, commit/blob, environment, implemented, tested, accepted, witness, blocker, next-action`. مستند قبلی فقط برای همان SHA یا subtree اثبات‌شده و همان محیط معتبر است. اختلاف تغییرات را از Git تعیین کن.
2. قراردادهای مشترک را پیش از تغییر ناسازگار با هر مصرف‌کننده reconcile کن. تصمیم حل‌نشده را با گزینه‌ها، پیشنهاد و آزمون بستن یک‌بار به مالک بده و کارهای مستقل را ادامه بده. Mock و synthetic با برچسب محیط و محدودیت ثبت شوند. Gate مستقل از درصد فعالیت‌هاست.
3. کد، fixtures و تست را در شاخهٔ تخصصی اجرا کن. یک Draft PR نسخه‌دار با baseline، changed paths، exact SHA، run log و دستور بازتولید بساز. در صورت CI قرمز علت را رفع کن و روی SHA نهایی تست کن. بازبینی روی محیط ایزوله و درخواست بازبینی برای مصرف‌کنندگان را در handoff ثبت کن.
4. با Foundation روی یک SHA یکپارچه، pin ورودی‌ها، pass/fail و اختلاف‌ها را دوباره بسنج. برای دسترسی بیرونی، یک درخواست مشخص با scope، artifact/نسخه، مالک، روش verify و نتیجهٔ مورد انتظار تحویل بده. وقتی ورودی و اختیار معتبر رسید، همین دستور را ادامه بده و گزارش‌های موقت را به رسید نهایی تبدیل کن.
5. هر تحویل باید کد/آرتیفکت، اجرای موفق و منفیِ مرتبط، لینک CI/رسید مقصد، مرز ریسک، runbook مختصر فارسی و قابلیت استفادهٔ تیم بعدی از قرارداد ثابت را داشته باشد. پیشرفت را از ردیف‌ها به‌روز کن. `ACCEPTED` فقط با معیار همان ردیف، شاهد محیط لازم و تأیید صاحب پذیرش. اگر تمام دامنه بسته شد نشانگر `100% ACCEPTED` بده. در غیر این صورت تعداد باز، مالک و ورودی واقعی را ثبت کن. همین فایل دستور ادامه پس از رفع مانع است.

### ترتیب مشترک تا پذیرش

کارهای مستقل اپ و شواهد آفلاین را موازی تکمیل کن. SERVER/Ops روی سرویس قدیمی در حال کار است. برای کاندیدا worktree و Compose مستقل و در صورت نیاز port/path/volume مستقل بساز. بعد از تثبیت inputs و Build/Start مجاز، ورود/History و جداسازی کاربران را روی مقصد بگیر. سپس فقط در scope مجاز Smoke بازیابی C018 بدون dispatch. اتصال کامل موتور محصول با Gate00، Release/NB23 پذیرفته، قرارداد provenance/Locator/C019 و تصمیم‌های DB011/هزینه/امنیت/Retention. پس از اتصال، روی candidate واقعی E2E، quality/safety، Restore/Rollback و Gateهای Launch را بگیر. برای عملیات جاری مک/آروان یا هزینهٔ مدل از رسید اختیار همان scope استفاده کن.

این همکاری باید بدون انتظار سریالی روی مراحل قابل ساخت پیش برود. UI قرارداد نسخه‌دار را مصرف می‌کند، API قرارداد و invariant تراکنش را می‌دهد، DB رول و migration و بازیابی را attest می‌کند، Foundation اختلاف نسخه‌ها و پذیرش مقصد را می‌بندد. کار موتور و شواهد upstream را ENGINE تحویل می‌دهد. کار روی پشتهٔ موجود فقط از مسیر SERVER/Ops انجام می‌شود.

## رجیستر ردیف‌به‌ردیف اجرا

این پیوست 171 فعالیت مسئولیتی یا وابستگی مرتبط دارد. ستون مالک از رجیستر است. ردیف‌های مشترک برای تطبیق قرارداد و شواهد درج شده‌اند. مسئولیت اجرای کد طبق مالکیت تخصصی است. وضعیت شروع snapshot است. برای بسته‌شدن هر ردیف، شاهد مستقیم و تازه لازم را در دفتر اجرا درج کن.

### P3M02 — environment_and_security_baseline

- [ ] **Independent Module Gate — NOT PASSED:** deliver module-level outcome. **Source:** modular plan Module 02 (line 195). **Owner:** foundation (human operational role pending where applicable). **Dependencies:** M01. **Output:** module deliverables as specified below. **Acceptance Gate:** Build پاک روی محیط جدید، Secret leakage صفر، Dependency بحرانی حل‌نشده صفر و فرمان واحد تست موفق باشد. شواهد: SBOM، Environment manifest و Security baseline report.. **Status:** `planned`. **Implemented:** not verified. **Tested:** not run. **Supervisor approval:** pending. **Evidence:** `coordination/evidence/P3M02/` (future evidence only).

| ID | خروجی و معیار قبولی | مالک و وابستگی | وضعیت شروع / ورودی باقی‌مانده |
|---|---|---|---|
| P3M02-A01 | **Output:** Freeze نسخه Python، Node، PostgreSQL، Qdrant، Redis و Docker; **Check:** clean build and security scan in a separately authorized environment | Foundation; environment owner pending; M01 | PARTIAL / ENGINE_LOCK_WHEELHOUSE_AND_IMAGE_SCAN; original row criterion: Freeze نسخه Python، Node، PostgreSQL، Qdrant، Redis و Docker; owner must deliver versioned artifact, SHA and target acceptance witness |
| P3M02-A02 | **Output:** ساخت lockfileهای وابستگی; **Check:** versioned artifact plus reproducible source-specific acceptance check and evidence | Foundation; environment owner pending; M01 | PARTIAL / ENGINE_LOCK_WHEELHOUSE_AND_IMAGE_SCAN; original row criterion: ساخت lockfileهای وابستگی; owner must deliver versioned artifact, SHA and target acceptance witness |
| P3M02-A03 | **Output:** تعریف `.env.example` بدون Secret; **Check:** policy-controlled privacy and leakage negative checks, no assumed success | Foundation; environment owner pending; M01 | PARTIAL / ENGINE_LOCK_WHEELHOUSE_AND_IMAGE_SCAN; original row criterion: تعریف `.env.example` بدون Secret; owner must deliver versioned artifact, SHA and target acceptance witness |
| P3M02-A04 | **Output:** ممنوع‌کردن Secret در Repository; **Check:** policy-controlled privacy and leakage negative checks, no assumed success | Foundation; environment owner pending; M01 | PARTIAL / ENGINE_LOCK_WHEELHOUSE_AND_IMAGE_SCAN; original row criterion: ممنوع‌کردن Secret در Repository; owner must deliver versioned artifact, SHA and target acceptance witness |
| P3M02-A05 | **Output:** فعال‌کردن Dependency و Secret scanning; **Check:** policy-controlled privacy and leakage negative checks, no assumed success | Foundation; environment owner pending; M01 | PARTIAL / ENGINE_LOCK_WHEELHOUSE_AND_IMAGE_SCAN; original row criterion: فعال‌کردن Dependency و Secret scanning; owner must deliver versioned artifact, SHA and target acceptance witness |
| P3M02-A06 | **Output:** تنظیم Lint، Type check و Test command واحد; **Check:** clean build and security scan in a separately authorized environment | Foundation; environment owner pending; M01 | PARTIAL / ENGINE_LOCK_WHEELHOUSE_AND_IMAGE_SCAN; original row criterion: تنظیم Lint، Type check و Test command واحد; owner must deliver versioned artifact, SHA and target acceptance witness |
| P3M02-A07 | **Output:** ساخت SBOM و گزارش Dependency; **Check:** clean build and security scan in a separately authorized environment | Foundation; environment owner pending; M01 | PARTIAL / ENGINE_LOCK_WHEELHOUSE_AND_IMAGE_SCAN; original row criterion: ساخت SBOM و گزارش Dependency; owner must deliver versioned artifact, SHA and target acceptance witness |
| P3M02-A08 | **Output:** ثبت Timezone، Locale و Encoding; **Check:** versioned artifact plus reproducible source-specific acceptance check and evidence | Foundation; environment owner pending; M01 | PARTIAL / ENGINE_LOCK_WHEELHOUSE_AND_IMAGE_SCAN; original row criterion: ثبت Timezone، Locale و Encoding; owner must deliver versioned artifact, SHA and target acceptance witness |
| P3M02-A09 | **Output:** تعیین Log redaction policy; **Check:** policy-controlled privacy and leakage negative checks, no assumed success | Foundation; environment owner pending; M01 | PARTIAL / ENGINE_LOCK_WHEELHOUSE_AND_IMAGE_SCAN; original row criterion: تعیین Log redaction policy; owner must deliver versioned artifact, SHA and target acceptance witness |
| P3M02-A10 | **Output:** ساخت Environment manifest.; **Check:** compare actual hashes and versioned manifests; zero mismatches | Foundation; environment owner pending; M01 | PARTIAL / ENGINE_LOCK_WHEELHOUSE_AND_IMAGE_SCAN; original row criterion: ساخت Environment manifest.; owner must deliver versioned artifact, SHA and target acceptance witness |

### P3M03 — project_structure_and_contracts

- [ ] **Independent Module Gate — NOT PASSED:** deliver module-level outcome. **Source:** modular plan Module 03 (line 216). **Owner:** foundation (human operational role pending where applicable). **Dependencies:** M01-M02. **Output:** module deliverables as specified below. **Acceptance Gate:** Schema validation و Contract test صددرصد PASS و Circular dependency صفر باشد.. **Status:** `planned`. **Implemented:** not verified. **Tested:** not run. **Supervisor approval:** pending. **Evidence:** `coordination/evidence/P3M03/` (future evidence only).

| ID | خروجی و معیار قبولی | مالک و وابستگی | وضعیت شروع / ورودی باقی‌مانده |
|---|---|---|---|
| P3M03-A01 | **Output:** تعریف مرز Domain moduleها; **Check:** versioned artifact plus reproducible source-specific acceptance check and evidence | Foundation + API/UI/DB; M01-M02 | PARTIAL / REAL_CROSS_SERVICE_CONTRACT_ACCEPTANCE; original row criterion: تعریف مرز Domain moduleها; owner must deliver versioned artifact, SHA and target acceptance witness |
| P3M03-A02 | **Output:** تعریف Error model مشترک; **Check:** versioned artifact plus reproducible source-specific acceptance check and evidence | Foundation + API/UI/DB; M01-M02 | PARTIAL / REAL_CROSS_SERVICE_CONTRACT_ACCEPTANCE; original row criterion: تعریف Error model مشترک; owner must deliver versioned artifact, SHA and target acceptance witness |
| P3M03-A03 | **Output:** تعریف Request ID و Trace ID; **Check:** server-issued trace correlation, redaction and alert test evidence | Foundation + API/UI/DB; M01-M02 | PARTIAL / REAL_CROSS_SERVICE_CONTRACT_ACCEPTANCE; original row criterion: تعریف Request ID و Trace ID; owner must deliver versioned artifact, SHA and target acceptance witness |
| P3M03-A04 | **Output:** نسخه‌بندی API از `/v1`; **Check:** versioned artifact plus reproducible source-specific acceptance check and evidence | Foundation + API/UI/DB; M01-M02 | PARTIAL / REAL_CROSS_SERVICE_CONTRACT_ACCEPTANCE; original row criterion: نسخه‌بندی API از `/v1`; owner must deliver versioned artifact, SHA and target acceptance witness |
| P3M03-A05 | **Output:** ساخت Schemaهای User، Conversation، Message، Answer و Citation; **Check:** run positive/negative Schema and version compatibility checks | Foundation + API/UI/DB; M01-M02 | PARTIAL / REAL_CROSS_SERVICE_CONTRACT_ACCEPTANCE; original row criterion: ساخت Schemaهای User، Conversation، Message، Answer و Citation; owner must deliver versioned artifact, SHA and target acceptance witness |
| P3M03-A06 | **Output:** تعریف فیلدهای Attribution; **Check:** source-aware provenance and permission checks; no invented locator or attribution | Foundation + API/UI/DB; M01-M02 | PARTIAL / REAL_CROSS_SERVICE_CONTRACT_ACCEPTANCE; original row criterion: تعریف فیلدهای Attribution; owner must deliver versioned artifact, SHA and target acceptance witness |
| P3M03-A07 | **Output:** تعریف Compatibility policy; **Check:** versioned artifact plus reproducible source-specific acceptance check and evidence | Foundation + API/UI/DB; M01-M02 | PARTIAL / REAL_CROSS_SERVICE_CONTRACT_ACCEPTANCE; original row criterion: تعریف Compatibility policy; owner must deliver versioned artifact, SHA and target acceptance witness |
| P3M03-A08 | **Output:** ساخت Contract tests بین Backend، Frontend و RAG runtime; **Check:** separate synthetic L1 and real L2; L2 remains NOT_RUN | Foundation + API/UI/DB; M01-M02 | PARTIAL / REAL_CROSS_SERVICE_CONTRACT_ACCEPTANCE; original row criterion: ساخت Contract tests بین Backend، Frontend و RAG runtime; owner must deliver versioned artifact, SHA and target acceptance witness |
| P3M03-A09 | **Output:** ساخت Architecture dependency test برای جلوگیری از Import معکوس.; **Check:** dated approved decision, diagrams/risk register and explicit Gate owner | Foundation + API/UI/DB; M01-M02 | PARTIAL / REAL_CROSS_SERVICE_CONTRACT_ACCEPTANCE; original row criterion: ساخت Architecture dependency test برای جلوگیری از Import معکوس.; owner must deliver versioned artifact, SHA and target acceptance witness |

### P3M04 — database_schema_and_migrations

- [ ] **Independent Module Gate — NOT PASSED:** deliver module-level outcome. **Source:** modular plan Module 04 (line 260). **Owner:** database. **Dependencies:** M03; retention policy. **Output:** module deliverables as specified below. **Acceptance Gate:** Migration clean، rollback test، FK violation صفر و Query plan قابل قبول برای مسیرهای اصلی.. **Status:** `planned`. **Implemented:** not verified. **Tested:** not run. **Supervisor approval:** pending. **Evidence:** `coordination/evidence/P3M04/` (future evidence only).

| ID | خروجی و معیار قبولی | مالک و وابستگی | وضعیت شروع / ورودی باقی‌مانده |
|---|---|---|---|
| P3M04-A01 | **Output:** طراحی ERD و Data dictionary; **Check:** ERD/Data Dictionary reviewed by API/DB, DB01-02 still DRAFT | DB; M03; retention policy | PARTIAL / DBA_MAC_POSTGRES_RECEIPT; original row criterion: طراحی ERD و Data dictionary; owner must deliver versioned artifact, SHA and target acceptance witness |
| P3M04-A02 | **Output:** تعریف Primary/Foreign key و Index; **Check:** test database constraints and query plans, including negative cases | DB; M03; retention policy | PARTIAL / DBA_MAC_POSTGRES_RECEIPT; original row criterion: تعریف Primary/Foreign key و Index; owner must deliver versioned artifact, SHA and target acceptance witness |
| P3M04-A03 | **Output:** افزودن `user_id` به تمام داده‌های کاربر; **Check:** versioned artifact plus reproducible source-specific acceptance check and evidence | DB; M03; retention policy | PARTIAL / DBA_MAC_POSTGRES_RECEIPT; original row criterion: افزودن `user_id` به تمام داده‌های کاربر; owner must deliver versioned artifact, SHA and target acceptance witness |
| P3M04-A04 | **Output:** ذخیره Citation و Attribution به‌صورت ساخت‌یافته; **Check:** source-aware provenance and permission checks; no invented locator or attribution | DB; M03; retention policy | PARTIAL / DBA_MAC_POSTGRES_RECEIPT; original row criterion: ذخیره Citation و Attribution به‌صورت ساخت‌یافته; owner must deliver versioned artifact, SHA and target acceptance witness |
| P3M04-A05 | **Output:** ذخیره Versionهای knowledge/retrieval/model/policy; **Check:** versioned artifact plus reproducible source-specific acceptance check and evidence | DB; M03; retention policy | PARTIAL / DBA_MAC_POSTGRES_RECEIPT; original row criterion: ذخیره Versionهای knowledge/retrieval/model/policy; owner must deliver versioned artifact, SHA and target acceptance witness |
| P3M04-A06 | **Output:** تعریف Migration forward و rollback; **Check:** reproducible migration/restore rollback plus consistency report in isolated test environment | DB; M03; retention policy | PARTIAL / DBA_MAC_POSTGRES_RECEIPT; original row criterion: تعریف Migration forward و rollback; owner must deliver versioned artifact, SHA and target acceptance witness |
| P3M04-A07 | **Output:** تست Migration روی دیتابیس خالی و دیتابیس دارای داده; **Check:** reproducible migration/restore rollback plus consistency report in isolated test environment | DB; M03; retention policy | PARTIAL / DBA_MAC_POSTGRES_RECEIPT; original row criterion: تست Migration روی دیتابیس خالی و دیتابیس دارای داده; owner must deliver versioned artifact, SHA and target acceptance witness |
| P3M04-A08 | **Output:** تعریف Retention و soft/hard delete; **Check:** policy-controlled privacy and leakage negative checks, no assumed success | DB; M03; retention policy | PARTIAL / DBA_MAC_POSTGRES_RECEIPT; original row criterion: تعریف Retention و soft/hard delete; owner must deliver versioned artifact, SHA and target acceptance witness |
| P3M04-A09 | **Output:** آماده‌سازی Namespace رزروشده برای موجودیت‌های فاز ۴ بدون فعال‌سازی آن‌ها.; **Check:** Phase4 namespace is design-only, no active tables | DB; M03; retention policy | PARTIAL / DBA_MAC_POSTGRES_RECEIPT; original row criterion: آماده‌سازی Namespace رزروشده برای موجودیت‌های فاز ۴ بدون فعال‌سازی آن‌ها.; owner must deliver versioned artifact, SHA and target acceptance witness |

### P3M05 — authentication_and_sessions

- [ ] **Independent Module Gate — NOT PASSED:** deliver module-level outcome. **Source:** modular plan Module 05 (line 298). **Owner:** api. **Dependencies:** M03-M04; auth policy. **Output:** module deliverables as specified below. **Acceptance Gate:** دسترسی بدون هویت به Endpoint محافظت‌شده صفر، Session پس از revoke نامعتبر و Secret در log صفر باشد.. **Status:** `planned`. **Implemented:** not verified. **Tested:** not run. **Supervisor approval:** pending. **Evidence:** `coordination/evidence/P3M05/` (future evidence only).

| ID | خروجی و معیار قبولی | مالک و وابستگی | وضعیت شروع / ورودی باقی‌مانده |
|---|---|---|---|
| P3M05-A01 | **Output:** انتخاب روش ورود طبق تصمیم کارفرما; **Check:** versioned artifact plus reproducible source-specific acceptance check and evidence | API; Auth policy pending; M03-M04; auth policy | PARTIAL / REAL_OIDC_MAC_HTTPS_AND_SESSION_TEST; original row criterion: انتخاب روش ورود طبق تصمیم کارفرما; owner must deliver versioned artifact, SHA and target acceptance witness |
| P3M05-A02 | **Output:** Password hashing استاندارد در صورت ورود رمزدار; **Check:** compare actual hashes and versioned manifests; zero mismatches | API; Auth policy pending; M03-M04; auth policy | PARTIAL / REAL_OIDC_MAC_HTTPS_AND_SESSION_TEST; original row criterion: Password hashing استاندارد در صورت ورود رمزدار; owner must deliver versioned artifact, SHA and target acceptance witness |
| P3M05-A03 | **Output:** Session token امن و rotation; **Check:** validate real Auth/session, revoke and invalid-user cases after policy approval | API; Auth policy pending; M03-M04; auth policy | PARTIAL / REAL_OIDC_MAC_HTTPS_AND_SESSION_TEST; original row criterion: Session token امن و rotation; owner must deliver versioned artifact, SHA and target acceptance witness |
| P3M05-A04 | **Output:** Cookie امن با `HttpOnly`، `Secure` و `SameSite`; **Check:** validate real Auth/session, revoke and invalid-user cases after policy approval | API; Auth policy pending; M03-M04; auth policy | PARTIAL / REAL_OIDC_MAC_HTTPS_AND_SESSION_TEST; original row criterion: Cookie امن با `HttpOnly`، `Secure` و `SameSite`; owner must deliver versioned artifact, SHA and target acceptance witness |
| P3M05-A05 | **Output:** CSRF policy; **Check:** validate real Auth/session, revoke and invalid-user cases after policy approval | API; Auth policy pending; M03-M04; auth policy | PARTIAL / REAL_OIDC_MAC_HTTPS_AND_SESSION_TEST; original row criterion: CSRF policy; owner must deliver versioned artifact, SHA and target acceptance witness |
| P3M05-A06 | **Output:** محدودیت تلاش ورود و lockout کنترل‌شده; **Check:** versioned artifact plus reproducible source-specific acceptance check and evidence | API; Auth policy pending; M03-M04; auth policy | PARTIAL / REAL_OIDC_MAC_HTTPS_AND_SESSION_TEST; original row criterion: محدودیت تلاش ورود و lockout کنترل‌شده; owner must deliver versioned artifact, SHA and target acceptance witness |
| P3M05-A07 | **Output:** Logout و revoke همه نشست‌ها; **Check:** validate real Auth/session, revoke and invalid-user cases after policy approval | API; Auth policy pending; M03-M04; auth policy | PARTIAL / REAL_OIDC_MAC_HTTPS_AND_SESSION_TEST; original row criterion: Logout و revoke همه نشست‌ها; owner must deliver versioned artifact, SHA and target acceptance witness |
| P3M05-A08 | **Output:** Expiration و refresh policy; **Check:** versioned artifact plus reproducible source-specific acceptance check and evidence | API; Auth policy pending; M03-M04; auth policy | PARTIAL / REAL_OIDC_MAC_HTTPS_AND_SESSION_TEST; original row criterion: Expiration و refresh policy; owner must deliver versioned artifact, SHA and target acceptance witness |
| P3M05-A09 | **Output:** ثبت Security event بدون ذخیره Secret; **Check:** policy-controlled privacy and leakage negative checks, no assumed success | API; Auth policy pending; M03-M04; auth policy | PARTIAL / REAL_OIDC_MAC_HTTPS_AND_SESSION_TEST; original row criterion: ثبت Security event بدون ذخیره Secret; owner must deliver versioned artifact, SHA and target acceptance witness |
| P3M05-A10 | **Output:** تست منفی Session theft و replay.; **Check:** validate real Auth/session, revoke and invalid-user cases after policy approval | API; Auth policy pending; M03-M04; auth policy | PARTIAL / REAL_OIDC_MAC_HTTPS_AND_SESSION_TEST; original row criterion: تست منفی Session theft و replay.; owner must deliver versioned artifact, SHA and target acceptance witness |

### P3M06 — tenant_isolation_and_rls

- [ ] **Independent Module Gate — NOT PASSED:** deliver module-level outcome. **Source:** modular plan Module 06 (line 323). **Owner:** database. **Dependencies:** M04-M05. **Output:** module deliverables as specified below. **Acceptance Gate:** Cross-user data exposure و RLS bypass در تست‌ها باید صفر باشد.. **Status:** `planned`. **Implemented:** not verified. **Tested:** not run. **Supervisor approval:** pending. **Evidence:** `coordination/evidence/P3M06/` (future evidence only).

| ID | خروجی و معیار قبولی | مالک و وابستگی | وضعیت شروع / ورودی باقی‌مانده |
|---|---|---|---|
| P3M06-A01 | **Output:** فعال‌سازی Row-Level Security برای جداول کاربرمحور; **Check:** versioned artifact plus reproducible source-specific acceptance check and evidence | DB + API; M04-M05 | PARTIAL / REAL_MAC_A_B_OWNER_ISOLATION; original row criterion: فعال‌سازی Row-Level Security برای جداول کاربرمحور; owner must deliver versioned artifact, SHA and target acceptance witness |
| P3M06-A02 | **Output:** تعریف Policy خواندن، نوشتن، ویرایش و حذف; **Check:** versioned artifact plus reproducible source-specific acceptance check and evidence | DB + API; M04-M05 | PARTIAL / REAL_MAC_A_B_OWNER_ISOLATION; original row criterion: تعریف Policy خواندن، نوشتن، ویرایش و حذف; owner must deliver versioned artifact, SHA and target acceptance witness |
| P3M06-A03 | **Output:** تنظیم Context امن user/tenant در هر Transaction; **Check:** test cross-user/role bypass with valid server identity; zero leaks | DB + API; M04-M05 | PARTIAL / REAL_MAC_A_B_OWNER_ISOLATION; original row criterion: تنظیم Context امن user/tenant در هر Transaction; owner must deliver versioned artifact, SHA and target acceptance witness |
| P3M06-A04 | **Output:** جلوگیری از دسترسی Background job خارج از Scope; **Check:** dated approved decision, diagrams/risk register and explicit Gate owner | DB + API; M04-M05 | PARTIAL / REAL_MAC_A_B_OWNER_ISOLATION; original row criterion: جلوگیری از دسترسی Background job خارج از Scope; owner must deliver versioned artifact, SHA and target acceptance witness |
| P3M06-A05 | **Output:** تست cross-user برای تمام Endpointها; **Check:** test cross-user/role bypass with valid server identity; zero leaks | DB + API; M04-M05 | PARTIAL / REAL_MAC_A_B_OWNER_ISOLATION; original row criterion: تست cross-user برای تمام Endpointها; owner must deliver versioned artifact, SHA and target acceptance witness |
| P3M06-A06 | **Output:** تست ID enumeration; **Check:** test cross-user/role bypass with valid server identity; zero leaks | DB + API; M04-M05 | PARTIAL / REAL_MAC_A_B_OWNER_ISOLATION; original row criterion: تست ID enumeration; owner must deliver versioned artifact, SHA and target acceptance witness |
| P3M06-A07 | **Output:** تست دسترسی مستقیم Repository layer; **Check:** versioned artifact plus reproducible source-specific acceptance check and evidence | DB + API; M04-M05 | PARTIAL / REAL_MAC_A_B_OWNER_ISOLATION; original row criterion: تست دسترسی مستقیم Repository layer; owner must deliver versioned artifact, SHA and target acceptance witness |
| P3M06-A08 | **Output:** ثبت Audit برای عملیات حساس; **Check:** server-issued trace correlation, redaction and alert test evidence | DB + API; M04-M05 | PARTIAL / REAL_MAC_A_B_OWNER_ISOLATION; original row criterion: ثبت Audit برای عملیات حساس; owner must deliver versioned artifact, SHA and target acceptance witness |
| P3M06-A09 | **Output:** ساخت Isolation matrix.; **Check:** test cross-user/role bypass with valid server identity; zero leaks | DB + API; M04-M05 | PARTIAL / REAL_MAC_A_B_OWNER_ISOLATION; original row criterion: ساخت Isolation matrix.; owner must deliver versioned artifact, SHA and target acceptance witness |

### P3M10 — answer_orchestration

- [ ] **Independent Module Gate — NOT PASSED:** deliver module-level outcome. **Source:** modular plan Module 10 (line 426). **Owner:** api. **Dependencies:** M08-M09; NB23. **Output:** module deliverables as specified below. **Acceptance Gate:** هر Answer باید `request_id`، نسخه دانش، Runها، Citation و وضعیت Safety داشته باشد. پاسخ ناقص نباید به‌عنوان موفق ثبت شود.. **Status:** `planned`. **Implemented:** not verified. **Tested:** not run. **Supervisor approval:** pending. **Evidence:** `coordination/evidence/P3M10/` (future evidence only).

| ID | خروجی و معیار قبولی | مالک و وابستگی | وضعیت شروع / ورودی باقی‌مانده |
|---|---|---|---|
| P3M10-A01 | **Output:** ساخت Query context از پیام جاری و تاریخچه محدود; **Check:** versioned artifact plus reproducible source-specific acceptance check and evidence | API + DB; M08-M09; NB23 | PARTIAL / REAL_T3_ANSWER_CITATION_E2E; original row criterion: ساخت Query context از پیام جاری و تاریخچه محدود; owner must deliver versioned artifact, SHA and target acceptance witness |
| P3M10-A02 | **Output:** Intent و Answerability; **Check:** distinct outcome/policy negative tests and measured calibration where required | API + DB; M08-M09; NB23 | PARTIAL / REAL_T3_ANSWER_CITATION_E2E; original row criterion: Intent و Answerability; owner must deliver versioned artifact, SHA and target acceptance witness |
| P3M10-A03 | **Output:** Retrieval و Context builder; **Check:** clean build and security scan in a separately authorized environment | API + DB; M08-M09; NB23 | PARTIAL / REAL_T3_ANSWER_CITATION_E2E; original row criterion: Retrieval و Context builder; owner must deliver versioned artifact, SHA and target acceptance witness |
| P3M10-A04 | **Output:** تولید پاسخ ساخت‌یافته; **Check:** versioned artifact plus reproducible source-specific acceptance check and evidence | API + DB; M08-M09; NB23 | PARTIAL / REAL_T3_ANSWER_CITATION_E2E; original row criterion: تولید پاسخ ساخت‌یافته; owner must deliver versioned artifact, SHA and target acceptance witness |
| P3M10-A05 | **Output:** Claim/Citation verification; **Check:** source-aware provenance and permission checks; no invented locator or attribution | API + DB; M08-M09; NB23 | PARTIAL / REAL_T3_ANSWER_CITATION_E2E; original row criterion: Claim/Citation verification; owner must deliver versioned artifact, SHA and target acceptance witness |
| P3M10-A06 | **Output:** اعمال Safety و No-answer; **Check:** distinct outcome/policy negative tests and measured calibration where required | API + DB; M08-M09; NB23 | PARTIAL / REAL_T3_ANSWER_CITATION_E2E; original row criterion: اعمال Safety و No-answer; owner must deliver versioned artifact, SHA and target acceptance witness |
| P3M10-A07 | **Output:** ساخت Confidence از اجزای قابل توضیح; **Check:** distinct outcome/policy negative tests and measured calibration where required | API + DB; M08-M09; NB23 | PARTIAL / REAL_T3_ANSWER_CITATION_E2E; original row criterion: ساخت Confidence از اجزای قابل توضیح; owner must deliver versioned artifact, SHA and target acceptance witness |
| P3M10-A08 | **Output:** ذخیره Runها و Versionها در یک Transaction منطقی; **Check:** transaction T1/T2/T3 + crash window review, NEEDS_API_DB_REVIEW | API + DB; M08-M09; NB23 | PARTIAL / REAL_T3_ANSWER_CITATION_E2E; original row criterion: ذخیره Runها و Versionها در یک Transaction منطقی; owner must deliver versioned artifact, SHA and target acceptance witness |
| P3M10-A09 | **Output:** مدیریت cancellation و duplicate request; **Check:** replay/cancel/unknown/ordering tests, no claim of exactly-once provider execution | API + DB; M08-M09; NB23 | PARTIAL / REAL_T3_ANSWER_CITATION_E2E; original row criterion: مدیریت cancellation و duplicate request; owner must deliver versioned artifact, SHA and target acceptance witness |
| P3M10-A10 | **Output:** Idempotency برای retry کلاینت.; **Check:** replay/cancel/unknown/ordering tests, no claim of exactly-once provider execution | API + DB; M08-M09; NB23 | PARTIAL / REAL_T3_ANSWER_CITATION_E2E; original row criterion: Idempotency برای retry کلاینت.; owner must deliver versioned artifact, SHA and target acceptance witness |

### P3M13 — product_api

- [ ] **Independent Module Gate — NOT PASSED:** deliver module-level outcome. **Source:** modular plan Module 13 (line 502). **Owner:** api. **Dependencies:** M03; M05-M12. **Output:** module deliverables as specified below. **Acceptance Gate:** OpenAPI validation، Contract suite، Authorization suite و Error contract صددرصد PASS.. **Status:** `planned`. **Implemented:** not verified. **Tested:** not run. **Supervisor approval:** pending. **Evidence:** `coordination/evidence/P3M13/` (future evidence only).

| ID | خروجی و معیار قبولی | مالک و وابستگی | وضعیت شروع / ورودی باقی‌مانده |
|---|---|---|---|
| P3M13-A01 | **Output:** OpenAPI نسخه‌دار; **Check:** run positive/negative Schema and version compatibility checks | API; M03; M05-M12 | PARTIAL / MAC_SIGNED_HTTP_POST_STATUS_EVIDENCE; original row criterion: OpenAPI نسخه‌دار; owner must deliver versioned artifact, SHA and target acceptance witness |
| P3M13-A02 | **Output:** Validation ورودی و محدودیت اندازه; **Check:** run positive/negative Schema and version compatibility checks | API; M03; M05-M12 | PARTIAL / MAC_SIGNED_HTTP_POST_STATUS_EVIDENCE; original row criterion: Validation ورودی و محدودیت اندازه; owner must deliver versioned artifact, SHA and target acceptance witness |
| P3M13-A03 | **Output:** Error code پایدار; **Check:** versioned artifact plus reproducible source-specific acceptance check and evidence | API; M03; M05-M12 | PARTIAL / MAC_SIGNED_HTTP_POST_STATUS_EVIDENCE; original row criterion: Error code پایدار; owner must deliver versioned artifact, SHA and target acceptance witness |
| P3M13-A04 | **Output:** Pagination تاریخچه; **Check:** stable user ownership, linked records and concurrency/retry checks | API; M03; M05-M12 | PARTIAL / MAC_SIGNED_HTTP_POST_STATUS_EVIDENCE; original row criterion: Pagination تاریخچه; owner must deliver versioned artifact, SHA and target acceptance witness |
| P3M13-A05 | **Output:** Streaming پاسخ با stateهای مشخص; **Check:** replay/cancel/unknown/ordering tests, no claim of exactly-once provider execution | API; M03; M05-M12 | PARTIAL / MAC_SIGNED_HTTP_POST_STATUS_EVIDENCE; original row criterion: Streaming پاسخ با stateهای مشخص; owner must deliver versioned artifact, SHA and target acceptance witness |
| P3M13-A06 | **Output:** Idempotency key; **Check:** replay/cancel/unknown/ordering tests, no claim of exactly-once provider execution | API; M03; M05-M12 | PARTIAL / MAC_SIGNED_HTTP_POST_STATUS_EVIDENCE; original row criterion: Idempotency key; owner must deliver versioned artifact, SHA and target acceptance witness |
| P3M13-A07 | **Output:** Request/Trace ID; **Check:** server-issued trace correlation, redaction and alert test evidence | API; M03; M05-M12 | PARTIAL / MAC_SIGNED_HTTP_POST_STATUS_EVIDENCE; original row criterion: Request/Trace ID; owner must deliver versioned artifact, SHA and target acceptance witness |
| P3M13-A08 | **Output:** Authorization در هر Endpoint; **Check:** test cross-user/role bypass with valid server identity; zero leaks | API; M03; M05-M12 | PARTIAL / MAC_SIGNED_HTTP_POST_STATUS_EVIDENCE; original row criterion: Authorization در هر Endpoint; owner must deliver versioned artifact, SHA and target acceptance witness |
| P3M13-A09 | **Output:** Contract test و backward compatibility; **Check:** run positive/negative Schema and version compatibility checks | API; M03; M05-M12 | PARTIAL / MAC_SIGNED_HTTP_POST_STATUS_EVIDENCE; original row criterion: Contract test و backward compatibility; owner must deliver versioned artifact, SHA and target acceptance witness |
| P3M13-A10 | **Output:** API abuse tests.; **Check:** positive/negative executable tests with reproducible result | API; M03; M05-M12 | PARTIAL / MAC_SIGNED_HTTP_POST_STATUS_EVIDENCE; original row criterion: API abuse tests.; owner must deliver versioned artifact, SHA and target acceptance witness |

### P3M15 — conversation_history_and_feedback

- [ ] **Independent Module Gate — NOT PASSED:** deliver module-level outcome. **Source:** modular plan Module 15 (line 573). **Owner:** database. **Dependencies:** M04; M06; M13-M14. **Output:** module deliverables as specified below. **Acceptance Gate:** History consistency، حذف مطابق Policy، cross-user exposure صفر و Feedback trace کامل.. **Status:** `planned`. **Implemented:** not verified. **Tested:** not run. **Supervisor approval:** pending. **Evidence:** `coordination/evidence/P3M15/` (future evidence only).

| ID | خروجی و معیار قبولی | مالک و وابستگی | وضعیت شروع / ورودی باقی‌مانده |
|---|---|---|---|
| P3M15-A01 | **Output:** ذخیره User message و Answer به‌صورت immutable event; **Check:** stable user ownership, linked records and concurrency/retry checks | DB + API + UI; M04; M06; M13-M14 | PARTIAL / REAL_MAC_HISTORY_RETENTION_DELETION; original row criterion: ذخیره User message و Answer به‌صورت immutable event; owner must deliver versioned artifact, SHA and target acceptance witness |
| P3M15-A02 | **Output:** عنوان‌گذاری مکالمه بدون تغییر محتوای اصلی; **Check:** versioned artifact plus reproducible source-specific acceptance check and evidence | DB + API + UI; M04; M06; M13-M14 | PARTIAL / REAL_MAC_HISTORY_RETENTION_DELETION; original row criterion: عنوان‌گذاری مکالمه بدون تغییر محتوای اصلی; owner must deliver versioned artifact, SHA and target acceptance witness |
| P3M15-A03 | **Output:** Pagination و مرتب‌سازی; **Check:** stable user ownership, linked records and concurrency/retry checks | DB + API + UI; M04; M06; M13-M14 | PARTIAL / REAL_MAC_HISTORY_RETENTION_DELETION; original row criterion: Pagination و مرتب‌سازی; owner must deliver versioned artifact, SHA and target acceptance witness |
| P3M15-A04 | **Output:** حذف مکالمه طبق Retention policy; **Check:** policy-controlled privacy and leakage negative checks, no assumed success | DB + API + UI; M04; M06; M13-M14 | PARTIAL / REAL_MAC_HISTORY_RETENTION_DELETION; original row criterion: حذف مکالمه طبق Retention policy; owner must deliver versioned artifact, SHA and target acceptance witness |
| P3M15-A05 | **Output:** Feedback مثبت/منفی و دسته خطا; **Check:** stable user ownership, linked records and concurrency/retry checks | DB + API + UI; M04; M06; M13-M14 | PARTIAL / REAL_MAC_HISTORY_RETENTION_DELETION; original row criterion: Feedback مثبت/منفی و دسته خطا; owner must deliver versioned artifact, SHA and target acceptance witness |
| P3M15-A06 | **Output:** ثبت Citation مشکل‌دار یا انتساب اشتباه; **Check:** source-aware provenance and permission checks; no invented locator or attribution | DB + API + UI; M04; M06; M13-M14 | PARTIAL / REAL_MAC_HISTORY_RETENTION_DELETION; original row criterion: ثبت Citation مشکل‌دار یا انتساب اشتباه; owner must deliver versioned artifact, SHA and target acceptance witness |
| P3M15-A07 | **Output:** جلوگیری از دسترسی کاربر دیگر; **Check:** versioned artifact plus reproducible source-specific acceptance check and evidence | DB + API + UI; M04; M06; M13-M14 | PARTIAL / REAL_MAC_HISTORY_RETENTION_DELETION; original row criterion: جلوگیری از دسترسی کاربر دیگر; owner must deliver versioned artifact, SHA and target acceptance witness |
| P3M15-A08 | **Output:** Export ساخت‌یافته در صورت تصویب Scope; **Check:** Export only after Scope approval; deletion independent | DB + API + UI; M04; M06; M13-M14 | PARTIAL / REAL_MAC_HISTORY_RETENTION_DELETION; original row criterion: Export ساخت‌یافته در صورت تصویب Scope; owner must deliver versioned artifact, SHA and target acceptance witness |
| P3M15-A09 | **Output:** Dataset بازخورد بدون PII برای ارزیابی بعدی; **Check:** policy-controlled privacy and leakage negative checks, no assumed success | DB + API + UI; M04; M06; M13-M14 | PARTIAL / REAL_MAC_HISTORY_RETENTION_DELETION; original row criterion: Dataset بازخورد بدون PII برای ارزیابی بعدی; owner must deliver versioned artifact, SHA and target acceptance witness |
| P3M15-A10 | **Output:** تست Race condition و duplicate write.; **Check:** replay/cancel/unknown/ordering tests, no claim of exactly-once provider execution | DB + API + UI; M04; M06; M13-M14 | PARTIAL / REAL_MAC_HISTORY_RETENTION_DELETION; original row criterion: تست Race condition و duplicate write.; owner must deliver versioned artifact, SHA and target acceptance witness |

### P3M16 — observability_and_audit

- [ ] **Independent Module Gate — NOT PASSED:** deliver module-level outcome. **Source:** modular plan Module 16 (line 598). **Owner:** foundation (human operational role pending where applicable). **Dependencies:** M13-M15; log policy. **Output:** module deliverables as specified below. **Acceptance Gate:** هر درخواست قابل ردیابی، Alertهای بحرانی آزمایش‌شده و Secret/PII leakage در log صفر.. **Status:** `planned`. **Implemented:** not verified. **Tested:** not run. **Supervisor approval:** pending. **Evidence:** `coordination/evidence/P3M16/` (future evidence only).

| ID | خروجی و معیار قبولی | مالک و وابستگی | وضعیت شروع / ورودی باقی‌مانده |
|---|---|---|---|
| P3M16-A01 | **Output:** Structured log با Request/Trace ID; **Check:** server-issued trace correlation, redaction and alert test evidence | Foundation; ops owner pending; M13-M15; log policy | NOT_VERIFIED / OPS_REAL_TRACING_ALERT_TEST_RECEIPT; original row criterion: Structured log با Request/Trace ID; owner must deliver versioned artifact, SHA and target acceptance witness |
| P3M16-A02 | **Output:** Metricهای request، latency، error، retrieval و model; **Check:** measured baseline and stress tests vs approved, non-invented thresholds | Foundation; ops owner pending; M13-M15; log policy | NOT_VERIFIED / OPS_REAL_TRACING_ALERT_TEST_RECEIPT; original row criterion: Metricهای request، latency، error، retrieval و model; owner must deliver versioned artifact, SHA and target acceptance witness |
| P3M16-A03 | **Output:** Dashboard سلامت سرویس; **Check:** versioned artifact plus reproducible source-specific acceptance check and evidence | Foundation; ops owner pending; M13-M15; log policy | NOT_VERIFIED / OPS_REAL_TRACING_ALERT_TEST_RECEIPT; original row criterion: Dashboard سلامت سرویس; owner must deliver versioned artifact, SHA and target acceptance witness |
| P3M16-A04 | **Output:** Alert برای Availability، error rate، DB pool و مصرف; **Check:** resource/abuse and cross-user-cache negative tests, with approved bounds | Foundation; ops owner pending; M13-M15; log policy | NOT_VERIFIED / OPS_REAL_TRACING_ALERT_TEST_RECEIPT; original row criterion: Alert برای Availability، error rate، DB pool و مصرف; owner must deliver versioned artifact, SHA and target acceptance witness |
| P3M16-A05 | **Output:** Audit event برای ورود و عملیات حساس; **Check:** server-issued trace correlation, redaction and alert test evidence | Foundation; ops owner pending; M13-M15; log policy | NOT_VERIFIED / OPS_REAL_TRACING_ALERT_TEST_RECEIPT; original row criterion: Audit event برای ورود و عملیات حساس; owner must deliver versioned artifact, SHA and target acceptance witness |
| P3M16-A06 | **Output:** Redaction داده مالی و Token; **Check:** validate real Auth/session, revoke and invalid-user cases after policy approval | Foundation; ops owner pending; M13-M15; log policy | NOT_VERIFIED / OPS_REAL_TRACING_ALERT_TEST_RECEIPT; original row criterion: Redaction داده مالی و Token; owner must deliver versioned artifact, SHA and target acceptance witness |
| P3M16-A07 | **Output:** ثبت نسخه Knowledge/Model/Policy; **Check:** versioned artifact plus reproducible source-specific acceptance check and evidence | Foundation; ops owner pending; M13-M15; log policy | NOT_VERIFIED / OPS_REAL_TRACING_ALERT_TEST_RECEIPT; original row criterion: ثبت نسخه Knowledge/Model/Policy; owner must deliver versioned artifact, SHA and target acceptance witness |
| P3M16-A08 | **Output:** Trace نمونه‌برداری‌شده برای مسیر پاسخ; **Check:** server-issued trace correlation, redaction and alert test evidence | Foundation; ops owner pending; M13-M15; log policy | NOT_VERIFIED / OPS_REAL_TRACING_ALERT_TEST_RECEIPT; original row criterion: Trace نمونه‌برداری‌شده برای مسیر پاسخ; owner must deliver versioned artifact, SHA and target acceptance witness |
| P3M16-A09 | **Output:** Runbook هشدارها; **Check:** versioned artifact plus reproducible source-specific acceptance check and evidence | Foundation; ops owner pending; M13-M15; log policy | NOT_VERIFIED / OPS_REAL_TRACING_ALERT_TEST_RECEIPT; original row criterion: Runbook هشدارها; owner must deliver versioned artifact, SHA and target acceptance witness |
| P3M16-A10 | **Output:** تست اینکه PII و Secret در Log وجود ندارد.; **Check:** policy-controlled privacy and leakage negative checks, no assumed success | Foundation; ops owner pending; M13-M15; log policy | NOT_VERIFIED / OPS_REAL_TRACING_ALERT_TEST_RECEIPT; original row criterion: تست اینکه PII و Secret در Log وجود ندارد.; owner must deliver versioned artifact, SHA and target acceptance witness |

### P3M18 — containerization_and_networking

- [ ] **Independent Module Gate — NOT PASSED:** deliver module-level outcome. **Source:** modular plan Module 18 (line 648). **Owner:** foundation (human operational role pending where applicable). **Dependencies:** M02-M17; hosting. **Output:** module deliverables as specified below. **Acceptance Gate:** Build تکرارپذیر، Critical image vulnerability حل‌نشده صفر و restart بدون از دست‌رفتن داده.. **Status:** `planned`. **Implemented:** not verified. **Tested:** not run. **Supervisor approval:** pending. **Evidence:** `coordination/evidence/P3M18/` (future evidence only).

| ID | خروجی و معیار قبولی | مالک و وابستگی | وضعیت شروع / ورودی باقی‌مانده |
|---|---|---|---|
| P3M18-A01 | **Output:** Dockerfile چندمرحله‌ای برای Web و API; **Check:** clean build and security scan in a separately authorized environment | Foundation; infrastructure owner pending; M02-M17; hosting | PARTIAL / ENGINE_LOCK_CLEAN_MAC_IMAGE_BUILD_SCAN; original row criterion: Dockerfile چندمرحله‌ای برای Web و API; owner must deliver versioned artifact, SHA and target acceptance witness |
| P3M18-A02 | **Output:** اجرای process با کاربر غیر root; **Check:** versioned artifact plus reproducible source-specific acceptance check and evidence | Foundation; infrastructure owner pending; M02-M17; hosting | PARTIAL / ENGINE_LOCK_CLEAN_MAC_IMAGE_BUILD_SCAN; original row criterion: اجرای process با کاربر غیر root; owner must deliver versioned artifact, SHA and target acceptance witness |
| P3M18-A03 | **Output:** Healthcheck و startup dependency; **Check:** accepted version/readiness, smoke and rollback evidence | Foundation; infrastructure owner pending; M02-M17; hosting | PARTIAL / ENGINE_LOCK_CLEAN_MAC_IMAGE_BUILD_SCAN; original row criterion: Healthcheck و startup dependency; owner must deliver versioned artifact, SHA and target acceptance witness |
| P3M18-A04 | **Output:** Network segmentation; **Check:** versioned artifact plus reproducible source-specific acceptance check and evidence | Foundation; infrastructure owner pending; M02-M17; hosting | PARTIAL / ENGINE_LOCK_CLEAN_MAC_IMAGE_BUILD_SCAN; original row criterion: Network segmentation; owner must deliver versioned artifact, SHA and target acceptance witness |
| P3M18-A05 | **Output:** Volume و persistence policy; **Check:** versioned artifact plus reproducible source-specific acceptance check and evidence | Foundation; infrastructure owner pending; M02-M17; hosting | PARTIAL / ENGINE_LOCK_CLEAN_MAC_IMAGE_BUILD_SCAN; original row criterion: Volume و persistence policy; owner must deliver versioned artifact, SHA and target acceptance witness |
| P3M18-A06 | **Output:** Secret injection در Runtime; **Check:** policy-controlled privacy and leakage negative checks, no assumed success | Foundation; infrastructure owner pending; M02-M17; hosting | PARTIAL / ENGINE_LOCK_CLEAN_MAC_IMAGE_BUILD_SCAN; original row criterion: Secret injection در Runtime; owner must deliver versioned artifact, SHA and target acceptance witness |
| P3M18-A07 | **Output:** محدودیت CPU/Memory; **Check:** versioned artifact plus reproducible source-specific acceptance check and evidence | Foundation; infrastructure owner pending; M02-M17; hosting | PARTIAL / ENGINE_LOCK_CLEAN_MAC_IMAGE_BUILD_SCAN; original row criterion: محدودیت CPU/Memory; owner must deliver versioned artifact, SHA and target acceptance witness |
| P3M18-A08 | **Output:** Image scanning و pin digest; **Check:** clean build and security scan in a separately authorized environment | Foundation; infrastructure owner pending; M02-M17; hosting | PARTIAL / ENGINE_LOCK_CLEAN_MAC_IMAGE_BUILD_SCAN; original row criterion: Image scanning و pin digest; owner must deliver versioned artifact, SHA and target acceptance witness |
| P3M18-A09 | **Output:** Compose برای Local و Deployment; **Check:** Compose only chosen for a later mission; run/build NOT_RUN | Foundation; infrastructure owner pending; M02-M17; hosting | PARTIAL / ENGINE_LOCK_CLEAN_MAC_IMAGE_BUILD_SCAN; original row criterion: Compose برای Local و Deployment; owner must deliver versioned artifact, SHA and target acceptance witness |
| P3M18-A10 | **Output:** Cold-start و restart test.; **Check:** positive/negative executable tests with reproducible result | Foundation; infrastructure owner pending; M02-M17; hosting | PARTIAL / ENGINE_LOCK_CLEAN_MAC_IMAGE_BUILD_SCAN; original row criterion: Cold-start و restart test.; owner must deliver versioned artifact, SHA and target acceptance witness |

### P3M19 — ci_cd_and_release_pipeline

- [ ] **Independent Module Gate — NOT PASSED:** deliver module-level outcome. **Source:** modular plan Module 19 (line 679). **Owner:** foundation (human operational role pending where applicable). **Dependencies:** M02-M18. **Output:** module deliverables as specified below. **Acceptance Gate:** هیچ Deployment تولیدی بدون Test report، Image digest، Migration check و Approval انجام نشود.. **Status:** `planned`. **Implemented:** not verified. **Tested:** not run. **Supervisor approval:** pending. **Evidence:** `coordination/evidence/P3M19/` (future evidence only).

| ID | خروجی و معیار قبولی | مالک و وابستگی | وضعیت شروع / ورودی باقی‌مانده |
|---|---|---|---|
| P3M19-A01 | **Output:** Lint، type check و unit tests; **Check:** clean build and security scan in a separately authorized environment | Foundation; CI owner pending; M02-M18 | PARTIAL / CI_CD_IMAGE_SCAN_APPROVAL_PUBLISHING_GATES; original row criterion: Lint، type check و unit tests; owner must deliver versioned artifact, SHA and target acceptance witness |
| P3M19-A02 | **Output:** Integration tests با سرویس‌های موقت; **Check:** positive/negative executable tests with reproducible result | Foundation; CI owner pending; M02-M18 | PARTIAL / CI_CD_IMAGE_SCAN_APPROVAL_PUBLISHING_GATES; original row criterion: Integration tests با سرویس‌های موقت; owner must deliver versioned artifact, SHA and target acceptance witness |
| P3M19-A03 | **Output:** Migration test; **Check:** reproducible migration/restore rollback plus consistency report in isolated test environment | Foundation; CI owner pending; M02-M18 | PARTIAL / CI_CD_IMAGE_SCAN_APPROVAL_PUBLISHING_GATES; original row criterion: Migration test; owner must deliver versioned artifact, SHA and target acceptance witness |
| P3M19-A04 | **Output:** Contract و security tests; **Check:** run positive/negative Schema and version compatibility checks | Foundation; CI owner pending; M02-M18 | PARTIAL / CI_CD_IMAGE_SCAN_APPROVAL_PUBLISHING_GATES; original row criterion: Contract و security tests; owner must deliver versioned artifact, SHA and target acceptance witness |
| P3M19-A05 | **Output:** Build و scan Image; **Check:** clean build and security scan in a separately authorized environment | Foundation; CI owner pending; M02-M18 | PARTIAL / CI_CD_IMAGE_SCAN_APPROVAL_PUBLISHING_GATES; original row criterion: Build و scan Image; owner must deliver versioned artifact, SHA and target acceptance witness |
| P3M19-A06 | **Output:** تولید Release manifest و SBOM; **Check:** compare actual hashes and versioned manifests; zero mismatches | Foundation; CI owner pending; M02-M18 | PARTIAL / CI_CD_IMAGE_SCAN_APPROVAL_PUBLISHING_GATES; original row criterion: تولید Release manifest و SBOM; owner must deliver versioned artifact, SHA and target acceptance witness |
| P3M19-A07 | **Output:** Deploy خودکار به Staging; **Check:** accepted version/readiness, smoke and rollback evidence | Foundation; CI owner pending; M02-M18 | PARTIAL / CI_CD_IMAGE_SCAN_APPROVAL_PUBLISHING_GATES; original row criterion: Deploy خودکار به Staging; owner must deliver versioned artifact, SHA and target acceptance witness |
| P3M19-A08 | **Output:** Approval دستی Production; **Check:** accepted version/readiness, smoke and rollback evidence | Foundation; CI owner pending; M02-M18 | PARTIAL / CI_CD_IMAGE_SCAN_APPROVAL_PUBLISHING_GATES; original row criterion: Approval دستی Production; owner must deliver versioned artifact, SHA and target acceptance witness |
| P3M19-A09 | **Output:** Rollback workflow; **Check:** reproducible migration/restore rollback plus consistency report in isolated test environment | Foundation; CI owner pending; M02-M18 | PARTIAL / CI_CD_IMAGE_SCAN_APPROVAL_PUBLISHING_GATES; original row criterion: Rollback workflow; owner must deliver versioned artifact, SHA and target acceptance witness |
| P3M19-A10 | **Output:** نگهداری Artifact و Test report; **Check:** positive/negative executable tests with reproducible result | Foundation; CI owner pending; M02-M18 | PARTIAL / CI_CD_IMAGE_SCAN_APPROVAL_PUBLISHING_GATES; original row criterion: نگهداری Artifact و Test report; owner must deliver versioned artifact, SHA and target acceptance witness |
| P3M19-A11 | **Output:** Branch protection و ممنوعیت Secret در log.; **Check:** policy-controlled privacy and leakage negative checks, no assumed success | Foundation; CI owner pending; M02-M18 | PARTIAL / CI_CD_IMAGE_SCAN_APPROVAL_PUBLISHING_GATES; original row criterion: Branch protection و ممنوعیت Secret در log.; owner must deliver versioned artifact, SHA and target acceptance witness |

### P3M20 — staging_deployment_and_e2e

- [ ] **Independent Module Gate — NOT PASSED:** deliver module-level outcome. **Source:** modular plan Module 20 (line 705). **Owner:** foundation (human operational role pending where applicable). **Dependencies:** M00; M03-M19. **Output:** module deliverables as specified below. **Acceptance Gate:** مسیرهای بحرانی E2E و UAT PASS، Issue بحرانی باز صفر و Staging قابل بازسازی باشد.. **Status:** `planned`. **Implemented:** not verified. **Tested:** not run. **Supervisor approval:** pending. **Evidence:** `coordination/evidence/P3M20/` (future evidence only).

| ID | خروجی و معیار قبولی | مالک و وابستگی | وضعیت شروع / ورودی باقی‌مانده |
|---|---|---|---|
| P3M20-A01 | **Output:** Provision محیط Staging نزدیک به Production; **Check:** accepted version/readiness, smoke and rollback evidence | Foundation; staging owner pending; M00; M03-M19 | NOT_RUN / REAL_7_SERVICE_OVERLAY_DB_AUTH_C018_MAC_E2E; original row criterion: Provision محیط Staging نزدیک به Production; owner must deliver versioned artifact, SHA and target acceptance witness |
| P3M20-A02 | **Output:** TLS و Domain آزمایشی; **Check:** versioned artifact plus reproducible source-specific acceptance check and evidence | Foundation; staging owner pending; M00; M03-M19 | NOT_RUN / REAL_7_SERVICE_OVERLAY_DB_AUTH_C018_MAC_E2E; original row criterion: TLS و Domain آزمایشی; owner must deliver versioned artifact, SHA and target acceptance witness |
| P3M20-A03 | **Output:** داده Test غیرشخصی; **Check:** positive/negative executable tests with reproducible result | Foundation; staging owner pending; M00; M03-M19 | NOT_RUN / REAL_7_SERVICE_OVERLAY_DB_AUTH_C018_MAC_E2E; original row criterion: داده Test غیرشخصی; owner must deliver versioned artifact, SHA and target acceptance witness |
| P3M20-A04 | **Output:** اجرای Migration; **Check:** reproducible migration/restore rollback plus consistency report in isolated test environment | Foundation; staging owner pending; M00; M03-M19 | NOT_RUN / REAL_7_SERVICE_OVERLAY_DB_AUTH_C018_MAC_E2E; original row criterion: اجرای Migration; owner must deliver versioned artifact, SHA and target acceptance witness |
| P3M20-A05 | **Output:** بارگذاری Release پذیرفته‌شده فاز ۲; **Check:** accepted version/readiness, smoke and rollback evidence | Foundation; staging owner pending; M00; M03-M19 | NOT_RUN / REAL_7_SERVICE_OVERLAY_DB_AUTH_C018_MAC_E2E; original row criterion: بارگذاری Release پذیرفته‌شده فاز ۲; owner must deliver versioned artifact, SHA and target acceptance witness |
| P3M20-A06 | **Output:** Smoke و E2E; **Check:** positive/negative executable tests with reproducible result | Foundation; staging owner pending; M00; M03-M19 | NOT_RUN / REAL_7_SERVICE_OVERLAY_DB_AUTH_C018_MAC_E2E; original row criterion: Smoke و E2E; owner must deliver versioned artifact, SHA and target acceptance witness |
| P3M20-A07 | **Output:** تست سه منبع و چهار نوع Citation; **Check:** source-aware provenance and permission checks; no invented locator or attribution | Foundation; staging owner pending; M00; M03-M19 | NOT_RUN / REAL_7_SERVICE_OVERLAY_DB_AUTH_C018_MAC_E2E; original row criterion: تست سه منبع و چهار نوع Citation; owner must deliver versioned artifact, SHA and target acceptance witness |
| P3M20-A08 | **Output:** تست نویسنده/سردبیر; **Check:** versioned artifact plus reproducible source-specific acceptance check and evidence | Foundation; staging owner pending; M00; M03-M19 | NOT_RUN / REAL_7_SERVICE_OVERLAY_DB_AUTH_C018_MAC_E2E; original row criterion: تست نویسنده/سردبیر; owner must deliver versioned artifact, SHA and target acceptance witness |
| P3M20-A09 | **Output:** تست No-answer و Safety; **Check:** distinct outcome/policy negative tests and measured calibration where required | Foundation; staging owner pending; M00; M03-M19 | NOT_RUN / REAL_7_SERVICE_OVERLAY_DB_AUTH_C018_MAC_E2E; original row criterion: تست No-answer و Safety; owner must deliver versioned artifact, SHA and target acceptance witness |
| P3M20-A10 | **Output:** تست Restart و dependency outage; **Check:** versioned artifact plus reproducible source-specific acceptance check and evidence | Foundation; staging owner pending; M00; M03-M19 | NOT_RUN / REAL_7_SERVICE_OVERLAY_DB_AUTH_C018_MAC_E2E; original row criterion: تست Restart و dependency outage; owner must deliver versioned artifact, SHA and target acceptance witness |
| P3M20-A11 | **Output:** UAT کارفرما و ثبت Issue.; **Check:** positive/negative executable tests with reproducible result | Foundation; staging owner pending; M00; M03-M19 | NOT_RUN / REAL_7_SERVICE_OVERLAY_DB_AUTH_C018_MAC_E2E; original row criterion: UAT کارفرما و ثبت Issue.; owner must deliver versioned artifact, SHA and target acceptance witness |

### P3M21 — security_privacy_and_threat_validation

- [ ] **Independent Module Gate — NOT PASSED:** deliver module-level outcome. **Source:** modular plan Module 21 (line 731). **Owner:** foundation (human operational role pending where applicable). **Dependencies:** M05-M06; M20; privacy. **Output:** module deliverables as specified below. **Acceptance Gate:** Critical/High vulnerability حل‌نشده صفر، Data isolation failure صفر و Incident runbook تأییدشده.. **Status:** `planned`. **Implemented:** not verified. **Tested:** not run. **Supervisor approval:** pending. **Evidence:** `coordination/evidence/P3M21/` (future evidence only).

| ID | خروجی و معیار قبولی | مالک و وابستگی | وضعیت شروع / ورودی باقی‌مانده |
|---|---|---|---|
| P3M21-A01 | **Output:** Threat model برای Web، API، DB، Qdrant و Model gateway; **Check:** versioned artifact plus reproducible source-specific acceptance check and evidence | Foundation; security owner pending; M05-M06; M20; privacy | NOT_VERIFIED / SECURITY_SCAN_HIGH_CRITICAL_RESOLUTION; original row criterion: Threat model برای Web، API، DB، Qdrant و Model gateway; owner must deliver versioned artifact, SHA and target acceptance witness |
| P3M21-A02 | **Output:** تست OWASP API/Web متناسب; **Check:** versioned artifact plus reproducible source-specific acceptance check and evidence | Foundation; security owner pending; M05-M06; M20; privacy | NOT_VERIFIED / SECURITY_SCAN_HIGH_CRITICAL_RESOLUTION; original row criterion: تست OWASP API/Web متناسب; owner must deliver versioned artifact, SHA and target acceptance witness |
| P3M21-A03 | **Output:** تست prompt injection و data exfiltration; **Check:** distinct outcome/policy negative tests and measured calibration where required | Foundation; security owner pending; M05-M06; M20; privacy | NOT_VERIFIED / SECURITY_SCAN_HIGH_CRITICAL_RESOLUTION; original row criterion: تست prompt injection و data exfiltration; owner must deliver versioned artifact, SHA and target acceptance witness |
| P3M21-A04 | **Output:** تست IDOR و RLS bypass; **Check:** test cross-user/role bypass with valid server identity; zero leaks | Foundation; security owner pending; M05-M06; M20; privacy | NOT_VERIFIED / SECURITY_SCAN_HIGH_CRITICAL_RESOLUTION; original row criterion: تست IDOR و RLS bypass; owner must deliver versioned artifact, SHA and target acceptance witness |
| P3M21-A05 | **Output:** TLS، headerهای امنیتی و CORS; **Check:** versioned artifact plus reproducible source-specific acceptance check and evidence | Foundation; security owner pending; M05-M06; M20; privacy | NOT_VERIFIED / SECURITY_SCAN_HIGH_CRITICAL_RESOLUTION; original row criterion: TLS، headerهای امنیتی و CORS; owner must deliver versioned artifact, SHA and target acceptance witness |
| P3M21-A06 | **Output:** Dependency و image scan; **Check:** clean build and security scan in a separately authorized environment | Foundation; security owner pending; M05-M06; M20; privacy | NOT_VERIFIED / SECURITY_SCAN_HIGH_CRITICAL_RESOLUTION; original row criterion: Dependency و image scan; owner must deliver versioned artifact, SHA and target acceptance witness |
| P3M21-A07 | **Output:** Consent و Retention validation; **Check:** run positive/negative Schema and version compatibility checks | Foundation; security owner pending; M05-M06; M20; privacy | NOT_VERIFIED / SECURITY_SCAN_HIGH_CRITICAL_RESOLUTION; original row criterion: Consent و Retention validation; owner must deliver versioned artifact, SHA and target acceptance witness |
| P3M21-A08 | **Output:** Account/data deletion test; **Check:** positive/negative executable tests with reproducible result | Foundation; security owner pending; M05-M06; M20; privacy | NOT_VERIFIED / SECURITY_SCAN_HIGH_CRITICAL_RESOLUTION; original row criterion: Account/data deletion test; owner must deliver versioned artifact, SHA and target acceptance witness |
| P3M21-A09 | **Output:** Incident response tabletop; **Check:** versioned artifact plus reproducible source-specific acceptance check and evidence | Foundation; security owner pending; M05-M06; M20; privacy | NOT_VERIFIED / SECURITY_SCAN_HIGH_CRITICAL_RESOLUTION; original row criterion: Incident response tabletop; owner must deliver versioned artifact, SHA and target acceptance witness |
| P3M21-A10 | **Output:** ثبت Risk acceptanceهای باقی‌مانده.; **Check:** dated approved decision, diagrams/risk register and explicit Gate owner | Foundation; security owner pending; M05-M06; M20; privacy | NOT_VERIFIED / SECURITY_SCAN_HIGH_CRITICAL_RESOLUTION; original row criterion: ثبت Risk acceptanceهای باقی‌مانده.; owner must deliver versioned artifact, SHA and target acceptance witness |

### P3M22 — backup_restore_and_disaster_recovery

- [ ] **Independent Module Gate — NOT PASSED:** deliver module-level outcome. **Source:** modular plan Module 22 (line 756). **Owner:** database. **Dependencies:** M04; M07; M18; RPO/RTO. **Output:** module deliverables as specified below. **Acceptance Gate:** Backup بدون Restore موفق ارزشی ندارد. Restore کامل باید در محدوده RPO/RTO مصوب PASS شود.. **Status:** `planned`. **Implemented:** not verified. **Tested:** not run. **Supervisor approval:** pending. **Evidence:** `coordination/evidence/P3M22/` (future evidence only).

| ID | خروجی و معیار قبولی | مالک و وابستگی | وضعیت شروع / ورودی باقی‌مانده |
|---|---|---|---|
| P3M22-A01 | **Output:** Backup نسخه‌دار PostgreSQL; **Check:** reproducible migration/restore rollback plus consistency report in isolated test environment | DB for PostgreSQL; Qdrant ops pending; M04; M07; M18; RPO/RTO | PARTIAL / TRUE_MAC_DATA_RESTORE_RPO_RTO; original row criterion: Backup نسخه‌دار PostgreSQL; owner must deliver versioned artifact, SHA and target acceptance witness |
| P3M22-A02 | **Output:** Snapshot و Restore Qdrant; **Check:** reproducible migration/restore rollback plus consistency report in isolated test environment | DB for PostgreSQL; Qdrant ops pending; M04; M07; M18; RPO/RTO | PARTIAL / TRUE_MAC_DATA_RESTORE_RPO_RTO; original row criterion: Snapshot و Restore Qdrant; owner must deliver versioned artifact, SHA and target acceptance witness |
| P3M22-A03 | **Output:** Backup Config و Release pointer; **Check:** reproducible migration/restore rollback plus consistency report in isolated test environment | DB for PostgreSQL; Qdrant ops pending; M04; M07; M18; RPO/RTO | PARTIAL / TRUE_MAC_DATA_RESTORE_RPO_RTO; original row criterion: Backup Config و Release pointer; owner must deliver versioned artifact, SHA and target acceptance witness |
| P3M22-A04 | **Output:** رمزگذاری و دسترسی محدود Backup; **Check:** reproducible migration/restore rollback plus consistency report in isolated test environment | DB for PostgreSQL; Qdrant ops pending; M04; M07; M18; RPO/RTO | PARTIAL / TRUE_MAC_DATA_RESTORE_RPO_RTO; original row criterion: رمزگذاری و دسترسی محدود Backup; owner must deliver versioned artifact, SHA and target acceptance witness |
| P3M22-A05 | **Output:** Retention و rotation; **Check:** policy-controlled privacy and leakage negative checks, no assumed success | DB for PostgreSQL; Qdrant ops pending; M04; M07; M18; RPO/RTO | PARTIAL / TRUE_MAC_DATA_RESTORE_RPO_RTO; original row criterion: Retention و rotation; owner must deliver versioned artifact, SHA and target acceptance witness |
| P3M22-A06 | **Output:** Restore در محیط خالی; **Check:** reproducible migration/restore rollback plus consistency report in isolated test environment | DB for PostgreSQL; Qdrant ops pending; M04; M07; M18; RPO/RTO | PARTIAL / TRUE_MAC_DATA_RESTORE_RPO_RTO; original row criterion: Restore در محیط خالی; owner must deliver versioned artifact, SHA and target acceptance witness |
| P3M22-A07 | **Output:** Point-in-time recovery در صورت امکان زیرساخت; **Check:** versioned artifact plus reproducible source-specific acceptance check and evidence | DB for PostgreSQL; Qdrant ops pending; M04; M07; M18; RPO/RTO | PARTIAL / TRUE_MAC_DATA_RESTORE_RPO_RTO; original row criterion: Point-in-time recovery در صورت امکان زیرساخت; owner must deliver versioned artifact, SHA and target acceptance witness |
| P3M22-A08 | **Output:** اندازه‌گیری RPO/RTO واقعی; **Check:** dated approved decision, diagrams/risk register and explicit Gate owner | DB for PostgreSQL; Qdrant ops pending; M04; M07; M18; RPO/RTO | PARTIAL / TRUE_MAC_DATA_RESTORE_RPO_RTO; original row criterion: اندازه‌گیری RPO/RTO واقعی; owner must deliver versioned artifact, SHA and target acceptance witness |
| P3M22-A09 | **Output:** تست خرابی جزئی و کامل; **Check:** versioned artifact plus reproducible source-specific acceptance check and evidence | DB for PostgreSQL; Qdrant ops pending; M04; M07; M18; RPO/RTO | PARTIAL / TRUE_MAC_DATA_RESTORE_RPO_RTO; original row criterion: تست خرابی جزئی و کامل; owner must deliver versioned artifact, SHA and target acceptance witness |
| P3M22-A10 | **Output:** Runbook و گزارش Restore.; **Check:** reproducible migration/restore rollback plus consistency report in isolated test environment | DB for PostgreSQL; Qdrant ops pending; M04; M07; M18; RPO/RTO | PARTIAL / TRUE_MAC_DATA_RESTORE_RPO_RTO; original row criterion: Runbook و گزارش Restore.; owner must deliver versioned artifact, SHA and target acceptance witness |

### P3M23 — performance_load_and_failure_testing

- [ ] **Independent Module Gate — NOT PASSED:** deliver module-level outcome. **Source:** modular plan Module 23 (line 781). **Owner:** foundation (human operational role pending where applicable). **Dependencies:** M20-M22; real workload. **Output:** module deliverables as specified below. **Acceptance Gate:** SLOهای Freeze‌شده، Error budget و ظرفیت Peak باید PASS شوند. اعداد نمونه یادداشت تصمیم، تا زمان Freeze تعهد قطعی نیستند.. **Status:** `planned`. **Implemented:** not verified. **Tested:** not run. **Supervisor approval:** pending. **Evidence:** `coordination/evidence/P3M23/` (future evidence only).

| ID | خروجی و معیار قبولی | مالک و وابستگی | وضعیت شروع / ورودی باقی‌مانده |
|---|---|---|---|
| P3M23-A01 | **Output:** Freeze workload model با اعداد تأییدشده; **Check:** real approved workload; sample SLO values are NONBINDING | Foundation; performance owner pending; M20-M22; real workload | NOT_RUN / REAL_APPROVED_WORKLOAD_LOAD_FAILURE_RECEIPTS; original row criterion: Freeze workload model با اعداد تأییدشده; owner must deliver versioned artifact, SHA and target acceptance witness |
| P3M23-A02 | **Output:** Baseline p50/p95/p99; **Check:** measured baseline and stress tests vs approved, non-invented thresholds | Foundation; performance owner pending; M20-M22; real workload | NOT_RUN / REAL_APPROVED_WORKLOAD_LOAD_FAILURE_RECEIPTS; original row criterion: Baseline p50/p95/p99; owner must deliver versioned artifact, SHA and target acceptance witness |
| P3M23-A03 | **Output:** Load، stress و soak test; **Check:** measured baseline and stress tests vs approved, non-invented thresholds | Foundation; performance owner pending; M20-M22; real workload | NOT_RUN / REAL_APPROVED_WORKLOAD_LOAD_FAILURE_RECEIPTS; original row criterion: Load، stress و soak test; owner must deliver versioned artifact, SHA and target acceptance witness |
| P3M23-A04 | **Output:** اندازه‌گیری saturation; **Check:** versioned artifact plus reproducible source-specific acceptance check and evidence | Foundation; performance owner pending; M20-M22; real workload | NOT_RUN / REAL_APPROVED_WORKLOAD_LOAD_FAILURE_RECEIPTS; original row criterion: اندازه‌گیری saturation; owner must deliver versioned artifact, SHA and target acceptance witness |
| P3M23-A05 | **Output:** Failure injection کنترل‌شده; **Check:** versioned artifact plus reproducible source-specific acceptance check and evidence | Foundation; performance owner pending; M20-M22; real workload | NOT_RUN / REAL_APPROVED_WORKLOAD_LOAD_FAILURE_RECEIPTS; original row criterion: Failure injection کنترل‌شده; owner must deliver versioned artifact, SHA and target acceptance witness |
| P3M23-A06 | **Output:** تحلیل Queue و timeout; **Check:** replay/cancel/unknown/ordering tests, no claim of exactly-once provider execution | Foundation; performance owner pending; M20-M22; real workload | NOT_RUN / REAL_APPROVED_WORKLOAD_LOAD_FAILURE_RECEIPTS; original row criterion: تحلیل Queue و timeout; owner must deliver versioned artifact, SHA and target acceptance witness |
| P3M23-A07 | **Output:** بررسی DB pool و Index latency; **Check:** test database constraints and query plans, including negative cases | Foundation; performance owner pending; M20-M22; real workload | NOT_RUN / REAL_APPROVED_WORKLOAD_LOAD_FAILURE_RECEIPTS; original row criterion: بررسی DB pool و Index latency; owner must deliver versioned artifact, SHA and target acceptance witness |
| P3M23-A08 | **Output:** اندازه‌گیری هزینه هر پاسخ; **Check:** versioned artifact plus reproducible source-specific acceptance check and evidence | Foundation; performance owner pending; M20-M22; real workload | NOT_RUN / REAL_APPROVED_WORKLOAD_LOAD_FAILURE_RECEIPTS; original row criterion: اندازه‌گیری هزینه هر پاسخ; owner must deliver versioned artifact, SHA and target acceptance witness |
| P3M23-A09 | **Output:** Capacity report و tuning; **Check:** resource/abuse and cross-user-cache negative tests, with approved bounds | Foundation; performance owner pending; M20-M22; real workload | NOT_RUN / REAL_APPROVED_WORKLOAD_LOAD_FAILURE_RECEIPTS; original row criterion: Capacity report و tuning; owner must deliver versioned artifact, SHA and target acceptance witness |
| P3M23-A10 | **Output:** Regression threshold.; **Check:** positive/negative executable tests with reproducible result | Foundation; performance owner pending; M20-M22; real workload | NOT_RUN / REAL_APPROVED_WORKLOAD_LOAD_FAILURE_RECEIPTS; original row criterion: Regression threshold.; owner must deliver versioned artifact, SHA and target acceptance witness |

### P3M24 — production_launch

- [ ] **Independent Module Gate — NOT PASSED:** deliver module-level outcome. **Source:** modular plan Module 24 (line 819). **Owner:** foundation (human operational role pending where applicable). **Dependencies:** M00-M23; Go/No-Go. **Output:** module deliverables as specified below. **Acceptance Gate:** تمام P0ها بسته، Rollback آماده، Backup معتبر، UAT تأییدشده و مانیتورینگ فعال باشد.. **Status:** `planned`. **Implemented:** not verified. **Tested:** not run. **Supervisor approval:** pending. **Evidence:** `coordination/evidence/P3M24/` (future evidence only).

| ID | خروجی و معیار قبولی | مالک و وابستگی | وضعیت شروع / ورودی باقی‌مانده |
|---|---|---|---|
| P3M24-A01 | **Output:** Go/No-Go checklist; **Check:** versioned artifact plus reproducible source-specific acceptance check and evidence | Foundation; launch approver pending; M00-M23; Go/No-Go | NOT_RUN / ARVAN_HOLD_GO_NO_GO; original row criterion: Go/No-Go checklist; owner must deliver versioned artifact, SHA and target acceptance witness |
| P3M24-A02 | **Output:** Freeze Image digest، DB migration و Knowledge release; **Check:** reproducible migration/restore rollback plus consistency report in isolated test environment | Foundation; launch approver pending; M00-M23; Go/No-Go | NOT_RUN / ARVAN_HOLD_GO_NO_GO; original row criterion: Freeze Image digest، DB migration و Knowledge release; owner must deliver versioned artifact, SHA and target acceptance witness |
| P3M24-A03 | **Output:** Backup قبل از استقرار; **Check:** reproducible migration/restore rollback plus consistency report in isolated test environment | Foundation; launch approver pending; M00-M23; Go/No-Go | NOT_RUN / ARVAN_HOLD_GO_NO_GO; original row criterion: Backup قبل از استقرار; owner must deliver versioned artifact, SHA and target acceptance witness |
| P3M24-A04 | **Output:** اجرای Deployment کنترل‌شده; **Check:** accepted version/readiness, smoke and rollback evidence | Foundation; launch approver pending; M00-M23; Go/No-Go | NOT_RUN / ARVAN_HOLD_GO_NO_GO; original row criterion: اجرای Deployment کنترل‌شده; owner must deliver versioned artifact, SHA and target acceptance witness |
| P3M24-A05 | **Output:** Migration و health verification; **Check:** reproducible migration/restore rollback plus consistency report in isolated test environment | Foundation; launch approver pending; M00-M23; Go/No-Go | NOT_RUN / ARVAN_HOLD_GO_NO_GO; original row criterion: Migration و health verification; owner must deliver versioned artifact, SHA and target acceptance witness |
| P3M24-A06 | **Output:** Smoke test با حساب آزمایشی; **Check:** positive/negative executable tests with reproducible result | Foundation; launch approver pending; M00-M23; Go/No-Go | NOT_RUN / ARVAN_HOLD_GO_NO_GO; original row criterion: Smoke test با حساب آزمایشی; owner must deliver versioned artifact, SHA and target acceptance witness |
| P3M24-A07 | **Output:** فعال‌سازی محدود کاربران اولیه; **Check:** versioned artifact plus reproducible source-specific acceptance check and evidence | Foundation; launch approver pending; M00-M23; Go/No-Go | NOT_RUN / ARVAN_HOLD_GO_NO_GO; original row criterion: فعال‌سازی محدود کاربران اولیه; owner must deliver versioned artifact, SHA and target acceptance witness |
| P3M24-A08 | **Output:** پایش Error، latency، cost و safety; **Check:** distinct outcome/policy negative tests and measured calibration where required | Foundation; launch approver pending; M00-M23; Go/No-Go | NOT_RUN / ARVAN_HOLD_GO_NO_GO; original row criterion: پایش Error، latency، cost و safety; owner must deliver versioned artifact, SHA and target acceptance witness |
| P3M24-A09 | **Output:** Rollback در عبور از Threshold; **Check:** reproducible migration/restore rollback plus consistency report in isolated test environment | Foundation; launch approver pending; M00-M23; Go/No-Go | NOT_RUN / ARVAN_HOLD_GO_NO_GO; original row criterion: Rollback در عبور از Threshold; owner must deliver versioned artifact, SHA and target acceptance witness |
| P3M24-A10 | **Output:** ثبت زمان، نسخه‌ها و مسئول تصمیم; **Check:** versioned artifact plus reproducible source-specific acceptance check and evidence | Foundation; launch approver pending; M00-M23; Go/No-Go | NOT_RUN / ARVAN_HOLD_GO_NO_GO; original row criterion: ثبت زمان، نسخه‌ها و مسئول تصمیم; owner must deliver versioned artifact, SHA and target acceptance witness |
| P3M24-A11 | **Output:** Production acceptance report.; **Check:** accepted version/readiness, smoke and rollback evidence | Foundation; launch approver pending; M00-M23; Go/No-Go | NOT_RUN / ARVAN_HOLD_GO_NO_GO; original row criterion: Production acceptance report.; owner must deliver versioned artifact, SHA and target acceptance witness |

### P3M25 — hypercare_and_phase4_handoff

- [ ] **Independent Module Gate — NOT PASSED:** deliver module-level outcome. **Source:** modular plan Module 25 (line 845). **Owner:** foundation (human operational role pending where applicable). **Dependencies:** M24; operations owner. **Output:** module deliverables as specified below. **Acceptance Gate:** Incident بحرانی باز صفر، Runbook و آموزش تحویل‌شده، Metrics پایدار و قرارداد ورودی فاز ۴ تأییدشده باشد.. **Status:** `planned`. **Implemented:** not verified. **Tested:** not run. **Supervisor approval:** pending. **Evidence:** `coordination/evidence/P3M25/` (future evidence only).

| ID | خروجی و معیار قبولی | مالک و وابستگی | وضعیت شروع / ورودی باقی‌مانده |
|---|---|---|---|
| P3M25-A01 | **Output:** بازه Hypercare با مالک مشخص; **Check:** versioned artifact plus reproducible source-specific acceptance check and evidence | Foundation; hypercare owner pending; M24; operations owner | NOT_RUN / NO_LAUNCH_HYPERCARE_NOT_STARTED; original row criterion: بازه Hypercare با مالک مشخص; owner must deliver versioned artifact, SHA and target acceptance witness |
| P3M25-A02 | **Output:** دسته‌بندی Incident و SLA پاسخ داخلی; **Check:** versioned artifact plus reproducible source-specific acceptance check and evidence | Foundation; hypercare owner pending; M24; operations owner | NOT_RUN / NO_LAUNCH_HYPERCARE_NOT_STARTED; original row criterion: دسته‌بندی Incident و SLA پاسخ داخلی; owner must deliver versioned artifact, SHA and target acceptance witness |
| P3M25-A03 | **Output:** مرور روزانه Error، latency، Citation و Safety; **Check:** source-aware provenance and permission checks; no invented locator or attribution | Foundation; hypercare owner pending; M24; operations owner | NOT_RUN / NO_LAUNCH_HYPERCARE_NOT_STARTED; original row criterion: مرور روزانه Error، latency، Citation و Safety; owner must deliver versioned artifact, SHA and target acceptance witness |
| P3M25-A04 | **Output:** تحلیل Feedback کاربران اولیه; **Check:** stable user ownership, linked records and concurrency/retry checks | Foundation; hypercare owner pending; M24; operations owner | NOT_RUN / NO_LAUNCH_HYPERCARE_NOT_STARTED; original row criterion: تحلیل Feedback کاربران اولیه; owner must deliver versioned artifact, SHA and target acceptance witness |
| P3M25-A05 | **Output:** اصلاح فقط Bugهای فاز ۳ و جلوگیری از Scope creep; **Check:** dated approved decision, diagrams/risk register and explicit Gate owner | Foundation; hypercare owner pending; M24; operations owner | NOT_RUN / NO_LAUNCH_HYPERCARE_NOT_STARTED; original row criterion: اصلاح فقط Bugهای فاز ۳ و جلوگیری از Scope creep; owner must deliver versioned artifact, SHA and target acceptance witness |
| P3M25-A06 | **Output:** Freeze Baseline عملیاتی پس از پایداری; **Check:** dated approved decision, diagrams/risk register and explicit Gate owner | Foundation; hypercare owner pending; M24; operations owner | NOT_RUN / NO_LAUNCH_HYPERCARE_NOT_STARTED; original row criterion: Freeze Baseline عملیاتی پس از پایداری; owner must deliver versioned artifact, SHA and target acceptance witness |
| P3M25-A07 | **Output:** ساخت Runbook بهره‌برداری; **Check:** versioned artifact plus reproducible source-specific acceptance check and evidence | Foundation; hypercare owner pending; M24; operations owner | NOT_RUN / NO_LAUNCH_HYPERCARE_NOT_STARTED; original row criterion: ساخت Runbook بهره‌برداری; owner must deliver versioned artifact, SHA and target acceptance witness |
| P3M25-A08 | **Output:** انتقال دانش به تیم نگهداری; **Check:** versioned artifact plus reproducible source-specific acceptance check and evidence | Foundation; hypercare owner pending; M24; operations owner | NOT_RUN / NO_LAUNCH_HYPERCARE_NOT_STARTED; original row criterion: انتقال دانش به تیم نگهداری; owner must deliver versioned artifact, SHA and target acceptance witness |
| P3M25-A09 | **Output:** تعریف Contract فاز ۴ برای Profile، Assessment، Goals و Action Plan; **Check:** run positive/negative Schema and version compatibility checks | Foundation; hypercare owner pending; M24; operations owner | NOT_RUN / NO_LAUNCH_HYPERCARE_NOT_STARTED; original row criterion: تعریف Contract فاز ۴ برای Profile، Assessment، Goals و Action Plan; owner must deliver versioned artifact, SHA and target acceptance witness |
| P3M25-A10 | **Output:** ثبت Tech debt و Deferred decisions; **Check:** versioned artifact plus reproducible source-specific acceptance check and evidence | Foundation; hypercare owner pending; M24; operations owner | NOT_RUN / NO_LAUNCH_HYPERCARE_NOT_STARTED; original row criterion: ثبت Tech debt و Deferred decisions; owner must deliver versioned artifact, SHA and target acceptance witness |
| P3M25-A11 | **Output:** Phase 3 closure report.; **Check:** versioned artifact plus reproducible source-specific acceptance check and evidence | Foundation; hypercare owner pending; M24; operations owner | NOT_RUN / NO_LAUNCH_HYPERCARE_NOT_STARTED; original row criterion: Phase 3 closure report.; owner must deliver versioned artifact, SHA and target acceptance witness |

## الزامات عملیاتی و نگاشت به فعالیت‌ها

95 شناسهٔ مرتبط از Crosswalk رسمی آمده است. الزامات هر بسته را همراه Gate و بخش‌های غیرشماره‌ای نقشه مرور کن. لینک خط‌های اصلی به نسخهٔ خواندنی مبنا اشاره می‌کنند.

| شناسه | الزام | فعالیت متناظر | وضعیت اولیه رجیستر |
|---|---|---|---|
| **P3OP01-R02**, §کارها | [L45](https://github.com/Shahbazi-Amir/RAG_finance/blob/7c74783c3dcda897b010ba9ea358d113f172ed1f/data/Road_Maps/RAG_finance_phase3_operational_roadmap.md#L45): تعریف نقش‌ها: user، support و admin محدود. | `P3M05-A01`, `P3M06-A02` | **GAP/CONFLICT, OPEN (non-counting):** support/admin role scope is not explicit in module activities; Auth/authorization approval required. |
| **P3OP01-R03**, §کارها | [L46](https://github.com/Shahbazi-Amir/RAG_finance/blob/7c74783c3dcda897b010ba9ea358d113f172ed1f/data/Road_Maps/RAG_finance_phase3_operational_roadmap.md#L46): API versioning، error model و idempotency policy. | `P3M03-A02`, `P3M03-A04`, `P3M10-A10` | Mapped only; required execution and the source Gate still unverified. |
| **P3OP01-R04**, §کارها | [L47](https://github.com/Shahbazi-Amir/RAG_finance/blob/7c74783c3dcda897b010ba9ea358d113f172ed1f/data/Road_Maps/RAG_finance_phase3_operational_roadmap.md#L47): Threat model و data classification. | `P3M21-A01`, `P3M01-A09` | Mapped only; required execution and the source Gate still unverified. |
| **P3OP01-R05**, §کارها | [L48](https://github.com/Shahbazi-Amir/RAG_finance/blob/7c74783c3dcda897b010ba9ea358d113f172ed1f/data/Road_Maps/RAG_finance_phase3_operational_roadmap.md#L48): ADR برای modular monolith، hosting، auth، queues و LLM gateway. | `P3M01-A03`, `P3M09-A01`, `P3M18-A09` | Mapped only; required execution and the source Gate still unverified. |
| **P3OP01-R07**, §خروجی | [L53](https://github.com/Shahbazi-Amir/RAG_finance/blob/7c74783c3dcda897b010ba9ea358d113f172ed1f/data/Road_Maps/RAG_finance_phase3_operational_roadmap.md#L53): docs/api/openapi.yaml | `P3M13-A01` | Mapped only; required execution and the source Gate still unverified. |
| **P3OP01-R08**, §خروجی | [L54](https://github.com/Shahbazi-Amir/RAG_finance/blob/7c74783c3dcda897b010ba9ea358d113f172ed1f/data/Road_Maps/RAG_finance_phase3_operational_roadmap.md#L54): docs/security/threat_model.md | `P3M21-A01` | Mapped only; required execution and the source Gate still unverified. |
| **P3OP02-R01**, §موجودیت‌های فعال | [L65](https://github.com/Shahbazi-Amir/RAG_finance/blob/7c74783c3dcda897b010ba9ea358d113f172ed1f/data/Road_Maps/RAG_finance_phase3_operational_roadmap.md#L65): users، identities، sessions و consents. | `P3M04-A01`, `P3M05-A01` | Mapped only; required execution and the source Gate still unverified. |
| **P3OP02-R02**, §موجودیت‌های فعال | [L66](https://github.com/Shahbazi-Amir/RAG_finance/blob/7c74783c3dcda897b010ba9ea358d113f172ed1f/data/Road_Maps/RAG_finance_phase3_operational_roadmap.md#L66): conversations، messages و citations. | `P3M04-A01`, `P3M04-A04` | Mapped only; required execution and the source Gate still unverified. |
| **P3OP02-R03**, §موجودیت‌های فعال | [L67](https://github.com/Shahbazi-Amir/RAG_finance/blob/7c74783c3dcda897b010ba9ea358d113f172ed1f/data/Road_Maps/RAG_finance_phase3_operational_roadmap.md#L67): retrieval_runs، model_runs و feedback. | `P3M04-A05`, `P3M10-A08`, `P3M15-A05` | Mapped only; required execution and the source Gate still unverified. |
| **P3OP02-R04**, §موجودیت‌های فعال | [L68](https://github.com/Shahbazi-Amir/RAG_finance/blob/7c74783c3dcda897b010ba9ea358d113f172ed1f/data/Road_Maps/RAG_finance_phase3_operational_roadmap.md#L68): audit_events، security_events و deletion_requests. | `P3M04-A01`, `P3M16-A05`, `P3M15-A04` | Mapped only; required execution and the source Gate still unverified. |
| **P3OP02-R05**, §موجودیت‌های رزروشده برای فاز ۴ | [L72](https://github.com/Shahbazi-Amir/RAG_finance/blob/7c74783c3dcda897b010ba9ea358d113f172ed1f/data/Road_Maps/RAG_finance_phase3_operational_roadmap.md#L72): financial_profiles و financial_snapshots. | `P3M04-A09` | **PHASE4 RESERVED ONLY** — design namespace, not active MVP tables/migrations. |
| **P3OP02-R06**, §موجودیت‌های رزروشده برای فاز ۴ | [L73](https://github.com/Shahbazi-Amir/RAG_finance/blob/7c74783c3dcda897b010ba9ea358d113f172ed1f/data/Road_Maps/RAG_finance_phase3_operational_roadmap.md#L73): assessments، scores، goals و action_plans. | `P3M04-A09` | **PHASE4 RESERVED ONLY** — design namespace, not active MVP tables/migrations. |
| **P3OP02-R07**, §موجودیت‌های رزروشده برای فاز ۴ | [L74](https://github.com/Shahbazi-Amir/RAG_finance/blob/7c74783c3dcda897b010ba9ea358d113f172ed1f/data/Road_Maps/RAG_finance_phase3_operational_roadmap.md#L74): risk_flags و human_referrals. | `P3M04-A09` | **PHASE4 RESERVED ONLY** — design namespace, not active MVP tables/migrations. |
| **P3OP02-R08**, §قواعد | [L78](https://github.com/Shahbazi-Amir/RAG_finance/blob/7c74783c3dcda897b010ba9ea358d113f172ed1f/data/Road_Maps/RAG_finance_phase3_operational_roadmap.md#L78): همه داده‌های کاربر user_id یا tenant_id داشته باشند. | `P3M04-A03`, `P3M06-A01` | Mapped only; required execution and the source Gate still unverified. |
| **P3OP02-R09**, §قواعد | [L79](https://github.com/Shahbazi-Amir/RAG_finance/blob/7c74783c3dcda897b010ba9ea358d113f172ed1f/data/Road_Maps/RAG_finance_phase3_operational_roadmap.md#L79): Migrationها نسخه‌دار و rollback plan داشته باشند. | `P3M04-A06` | Mapped only; required execution and the source Gate still unverified. |
| **P3OP02-R10**, §قواعد | [L80](https://github.com/Shahbazi-Amir/RAG_finance/blob/7c74783c3dcda897b010ba9ea358d113f172ed1f/data/Road_Maps/RAG_finance_phase3_operational_roadmap.md#L80): PII از log و model payload تا حد ممکن حذف شود. | `P3M09-A05`, `P3M16-A06` | Mapped only; required execution and the source Gate still unverified. |
| **P3OP02-R11**, §قواعد | [L81](https://github.com/Shahbazi-Amir/RAG_finance/blob/7c74783c3dcda897b010ba9ea358d113f172ed1f/data/Road_Maps/RAG_finance_phase3_operational_roadmap.md#L81): Foreign key، uniqueness و retention job تست شود. | `P3M04-A02`, `P3M04-A08`, `P3M19-A03` | Mapped only; required execution and the source Gate still unverified. |
| **P3OP03-R01**, §کارها | [L91](https://github.com/Shahbazi-Amir/RAG_finance/blob/7c74783c3dcda897b010ba9ea358d113f172ed1f/data/Road_Maps/RAG_finance_phase3_operational_roadmap.md#L91): ثبت‌نام، ورود، logout، session rotation و password reset. | `P3M05-A01`, `P3M05-A03`, `P3M05-A07` | **GAP/CONFLICT, OPEN (non-counting):** password reset not enumerated separately by M05; keep as operational acceptance. |
| **P3OP03-R02**, §کارها | [L92](https://github.com/Shahbazi-Amir/RAG_finance/blob/7c74783c3dcda897b010ba9ea358d113f172ed1f/data/Road_Maps/RAG_finance_phase3_operational_roadmap.md#L92): password hashing استاندارد، cookie امن و CSRF/CORS policy. | `P3M05-A02`, `P3M05-A04`, `P3M05-A05` | Mapped only; required execution and the source Gate still unverified. |
| **P3OP03-R03**, §کارها | [L93](https://github.com/Shahbazi-Amir/RAG_finance/blob/7c74783c3dcda897b010ba9ea358d113f172ed1f/data/Road_Maps/RAG_finance_phase3_operational_roadmap.md#L93): consent version، تاریخ پذیرش و امکان پس‌گرفتن. | `P3M21-A07`, `P3M05-A01` | **GAP/CONFLICT, OPEN (non-counting):** consent version, timestamp and withdrawal require more than modular consent validation. |
| **P3OP03-R04**, §کارها | [L94](https://github.com/Shahbazi-Amir/RAG_finance/blob/7c74783c3dcda897b010ba9ea358d113f172ed1f/data/Road_Maps/RAG_finance_phase3_operational_roadmap.md#L94): Row-Level Security و FORCE RLS در جداول کاربر. | `P3M06-A01`, `P3M06-A02`, `P3M06-A07` | Mapped only; required execution and the source Gate still unverified. |
| **P3OP03-R05**, §کارها | [L95](https://github.com/Shahbazi-Amir/RAG_finance/blob/7c74783c3dcda897b010ba9ea358d113f172ed1f/data/Road_Maps/RAG_finance_phase3_operational_roadmap.md#L95): تست‌های منفی افقی و عمودی دسترسی. | `P3M06-A05`, `P3M06-A06`, `P3M06-A07` | Mapped only; required execution and the source Gate still unverified. |
| **P3OP03-R06**, §کارها | [L96](https://github.com/Shahbazi-Amir/RAG_finance/blob/7c74783c3dcda897b010ba9ea358d113f172ed1f/data/Road_Maps/RAG_finance_phase3_operational_roadmap.md#L96): rate limit برای login، chat و feedback. | `P3M05-A06`, `P3M17-A01` | Mapped only; required execution and the source Gate still unverified. |
| **P3OP04-R01**, §Endpointهای حداقلی | [L108](https://github.com/Shahbazi-Amir/RAG_finance/blob/7c74783c3dcda897b010ba9ea358d113f172ed1f/data/Road_Maps/RAG_finance_phase3_operational_roadmap.md#L108): auth و session. | `P3M05-A01`, `P3M13-A01` | Mapped only; required execution and the source Gate still unverified. |
| **P3OP04-R02**, §Endpointهای حداقلی | [L109](https://github.com/Shahbazi-Amir/RAG_finance/blob/7c74783c3dcda897b010ba9ea358d113f172ed1f/data/Road_Maps/RAG_finance_phase3_operational_roadmap.md#L109): create/list conversation. | `P3M13-A04`, `P3M15-A03` | Mapped only; required execution and the source Gate still unverified. |
| **P3OP04-R03**, §Endpointهای حداقلی | [L110](https://github.com/Shahbazi-Amir/RAG_finance/blob/7c74783c3dcda897b010ba9ea358d113f172ed1f/data/Road_Maps/RAG_finance_phase3_operational_roadmap.md#L110): send message و stream answer. | `P3M13-A05`, `P3M14-A04` | Mapped only; required execution and the source Gate still unverified. |
| **P3OP04-R04**, §Endpointهای حداقلی | [L111](https://github.com/Shahbazi-Amir/RAG_finance/blob/7c74783c3dcda897b010ba9ea358d113f172ed1f/data/Road_Maps/RAG_finance_phase3_operational_roadmap.md#L111): get answer details/citations. | `P3M13-A01`, `P3M11-A01` | Mapped only; required execution and the source Gate still unverified. |
| **P3OP04-R05**, §Endpointهای حداقلی | [L112](https://github.com/Shahbazi-Amir/RAG_finance/blob/7c74783c3dcda897b010ba9ea358d113f172ed1f/data/Road_Maps/RAG_finance_phase3_operational_roadmap.md#L112): submit feedback. | `P3M13-A01`, `P3M15-A05` | Mapped only; required execution and the source Gate still unverified. |
| **P3OP04-R06**, §Endpointهای حداقلی | [L113](https://github.com/Shahbazi-Amir/RAG_finance/blob/7c74783c3dcda897b010ba9ea358d113f172ed1f/data/Road_Maps/RAG_finance_phase3_operational_roadmap.md#L113): export/delete account data. | `P3M13-A01`, `P3M15-A08`, `P3M21-A08` | Mapped only; required execution and the source Gate still unverified. |
| **P3OP04-R07**, §Endpointهای حداقلی | [L114](https://github.com/Shahbazi-Amir/RAG_finance/blob/7c74783c3dcda897b010ba9ea358d113f172ed1f/data/Road_Maps/RAG_finance_phase3_operational_roadmap.md#L114): health، readiness و version. | `P3M07-A07`, `P3M20-A06` | Mapped only; required execution and the source Gate still unverified. |
| **P3OP04-R08**, §ثبت هر پاسخ | [L118](https://github.com/Shahbazi-Amir/RAG_finance/blob/7c74783c3dcda897b010ba9ea358d113f172ed1f/data/Road_Maps/RAG_finance_phase3_operational_roadmap.md#L118): original/processed query. | `P3M10-A01`, `P3M16-A01` | Mapped only; required execution and the source Gate still unverified. |
| **P3OP04-R09**, §ثبت هر پاسخ | [L119](https://github.com/Shahbazi-Amir/RAG_finance/blob/7c74783c3dcda897b010ba9ea358d113f172ed1f/data/Road_Maps/RAG_finance_phase3_operational_roadmap.md#L119): dataset/index/retrieval/reranker/model/prompt/policy versions. | `P3M10-A08`, `P3M16-A07` | Mapped only; required execution and the source Gate still unverified. |
| **P3OP04-R10**, §ثبت هر پاسخ | [L120](https://github.com/Shahbazi-Amir/RAG_finance/blob/7c74783c3dcda897b010ba9ea358d113f172ed1f/data/Road_Maps/RAG_finance_phase3_operational_roadmap.md#L120): retrieved و selected chunk IDs. | `P3M08-A08`, `P3M10-A08` | Mapped only; required execution and the source Gate still unverified. |
| **P3OP04-R11**, §ثبت هر پاسخ | [L121](https://github.com/Shahbazi-Amir/RAG_finance/blob/7c74783c3dcda897b010ba9ea358d113f172ed1f/data/Road_Maps/RAG_finance_phase3_operational_roadmap.md#L121): answer claims/citations. | `P3M10-A05`, `P3M11-A01` | Mapped only; required execution and the source Gate still unverified. |
| **P3OP04-R12**, §ثبت هر پاسخ | [L122](https://github.com/Shahbazi-Amir/RAG_finance/blob/7c74783c3dcda897b010ba9ea358d113f172ed1f/data/Road_Maps/RAG_finance_phase3_operational_roadmap.md#L122): latency، tokens، cost estimate و status. | `P3M09-A04`, `P3M16-A02`, `P3M23-A08` | Mapped only; required execution and the source Gate still unverified. |
| **P3OP04-R14**, §قواعد | [L127](https://github.com/Shahbazi-Amir/RAG_finance/blob/7c74783c3dcda897b010ba9ea358d113f172ed1f/data/Road_Maps/RAG_finance_phase3_operational_roadmap.md#L127): request_id و trace_id سراسری. | `P3M03-A03`, `P3M13-A07` | Mapped only; required execution and the source Gate still unverified. |
| **P3OP04-R16**, §قواعد | [L129](https://github.com/Shahbazi-Amir/RAG_finance/blob/7c74783c3dcda897b010ba9ea358d113f172ed1f/data/Road_Maps/RAG_finance_phase3_operational_roadmap.md#L129): هیچ fallback نباید silently پاسخ بدون Citation بسازد. | `P3M10-A05`, `P3M12-A04` | Mapped only; required execution and the source Gate still unverified. |
| **P3OP05-R02**, §صفحات پایه | [L140](https://github.com/Shahbazi-Amir/RAG_finance/blob/7c74783c3dcda897b010ba9ea358d113f172ed1f/data/Road_Maps/RAG_finance_phase3_operational_roadmap.md#L140): signup/login/consent. | `P3M14-A01`, `P3M05-A01` | Mapped only; required execution and the source Gate still unverified. |
| **P3OP05-R03**, §صفحات پایه | [L141](https://github.com/Shahbazi-Amir/RAG_finance/blob/7c74783c3dcda897b010ba9ea358d113f172ed1f/data/Road_Maps/RAG_finance_phase3_operational_roadmap.md#L141): chat، conversation history و source drawer. | `P3M14-A03`, `P3M14-A05`, `P3M15-A03` | Mapped only; required execution and the source Gate still unverified. |
| **P3OP05-R04**, §صفحات پایه | [L142](https://github.com/Shahbazi-Amir/RAG_finance/blob/7c74783c3dcda897b010ba9ea358d113f172ed1f/data/Road_Maps/RAG_finance_phase3_operational_roadmap.md#L142): account/privacy/export/delete. | `P3M14-A01`, `P3M15-A04`, `P3M21-A08` | **GAP/CONFLICT, OPEN (non-counting):** Export operationally expected, while M15-A08 requires Scope approval; deletion independent. |
| **P3OP05-R05**, §صفحات پایه | [L143](https://github.com/Shahbazi-Amir/RAG_finance/blob/7c74783c3dcda897b010ba9ea358d113f172ed1f/data/Road_Maps/RAG_finance_phase3_operational_roadmap.md#L143): feedback و report answer. | `P3M15-A05`, `P3M14-A03` | Mapped only; required execution and the source Gate still unverified. |
| **P3OP05-R06**, §رفتار چت | [L147](https://github.com/Shahbazi-Amir/RAG_finance/blob/7c74783c3dcda897b010ba9ea358d113f172ed1f/data/Road_Maps/RAG_finance_phase3_operational_roadmap.md#L147): Streaming پاسخ و وضعیت retrieving/generating. | `P3M14-A04`, `P3M13-A05` | Mapped only; required execution and the source Gate still unverified. |
| **P3OP06-R01**, §اجزا | [L161](https://github.com/Shahbazi-Amir/RAG_finance/blob/7c74783c3dcda897b010ba9ea358d113f172ed1f/data/Road_Maps/RAG_finance_phase3_operational_roadmap.md#L161): Docker images نسخه‌دار برای Web، API و Worker. | `P3M18-A01` | **GAP/CONFLICT, OPEN (non-counting):** Worker image omitted from M18-A01 Web/API Dockerfiles. |
| **P3OP06-R02**, §اجزا | [L162](https://github.com/Shahbazi-Amir/RAG_finance/blob/7c74783c3dcda897b010ba9ea358d113f172ed1f/data/Road_Maps/RAG_finance_phase3_operational_roadmap.md#L162): PostgreSQL، Qdrant، Redis و Object Storage مدیریت‌شده یا self-host بر اساس تصمیم. | `P3M18-A05`, `P3M18-A09`, `P3M22-A02` | **GAP/CONFLICT, OPEN (non-counting):** managed/self-host and Qdrant/Object Storage operator assignment still pending. |
| **P3OP06-R03**, §اجزا | [L163](https://github.com/Shahbazi-Amir/RAG_finance/blob/7c74783c3dcda897b010ba9ea358d113f172ed1f/data/Road_Maps/RAG_finance_phase3_operational_roadmap.md#L163): Reverse proxy، TLS، domain و secure headers. | `P3M18-A04`, `P3M21-A05` | Mapped only; required execution and the source Gate still unverified. |
| **P3OP06-R04**, §اجزا | [L164](https://github.com/Shahbazi-Amir/RAG_finance/blob/7c74783c3dcda897b010ba9ea358d113f172ed1f/data/Road_Maps/RAG_finance_phase3_operational_roadmap.md#L164): environment separation برای local/staging/production. | `P3M01-A04`, `P3M18-A09` | Mapped only; required execution and the source Gate still unverified. |
| **P3OP06-R05**, §اجزا | [L165](https://github.com/Shahbazi-Amir/RAG_finance/blob/7c74783c3dcda897b010ba9ea358d113f172ed1f/data/Road_Maps/RAG_finance_phase3_operational_roadmap.md#L165): secrets management و rotation. | `P3M18-A06`, `P3M02-A04` | Mapped only; required execution and the source Gate still unverified. |
| **P3OP06-R06**, §اجزا | [L166](https://github.com/Shahbazi-Amir/RAG_finance/blob/7c74783c3dcda897b010ba9ea358d113f172ed1f/data/Road_Maps/RAG_finance_phase3_operational_roadmap.md#L166): migrations و seedهای کنترل‌شده. | `P3M19-A03`, `P3M04-A06` | Mapped only; required execution and the source Gate still unverified. |
| **P3OP06-R07**, §Release | [L170](https://github.com/Shahbazi-Amir/RAG_finance/blob/7c74783c3dcda897b010ba9ea358d113f172ed1f/data/Road_Maps/RAG_finance_phase3_operational_roadmap.md#L170): CI: lint، unit، integration، security و build. | `P3M19-A01`, `P3M19-A04` | Mapped only; required execution and the source Gate still unverified. |
| **P3OP06-R08**, §Release | [L171](https://github.com/Shahbazi-Amir/RAG_finance/blob/7c74783c3dcda897b010ba9ea358d113f172ed1f/data/Road_Maps/RAG_finance_phase3_operational_roadmap.md#L171): CD با approval، migration gate، smoke test و rollback. | `P3M19-A07`, `P3M19-A08`, `P3M19-A09` | Mapped only; required execution and the source Gate still unverified. |
| **P3OP06-R09**, §Release | [L172](https://github.com/Shahbazi-Amir/RAG_finance/blob/7c74783c3dcda897b010ba9ea358d113f172ed1f/data/Road_Maps/RAG_finance_phase3_operational_roadmap.md#L172): Infrastructure/Deployment runbook. | `P3M18-A09`, `P3M25-A07` | Mapped only; required execution and the source Gate still unverified. |
| **P3OP06-R10**, §Release | [L173](https://github.com/Shahbazi-Amir/RAG_finance/blob/7c74783c3dcda897b010ba9ea358d113f172ed1f/data/Road_Maps/RAG_finance_phase3_operational_roadmap.md#L173): Release manifest شامل app و RAG artifact versions. | `P3M19-A06`, `P3M24-A02` | Mapped only; required execution and the source Gate still unverified. |
| **P3OP07-R01**, §بسته | [L181](https://github.com/Shahbazi-Amir/RAG_finance/blob/7c74783c3dcda897b010ba9ea358d113f172ed1f/data/Road_Maps/RAG_finance_phase3_operational_roadmap.md#L181): backup رمزگذاری‌شده PostgreSQL و Qdrant snapshot. | `P3M22-A01`, `P3M22-A02`, `P3M22-A04` | Mapped only; required execution and the source Gate still unverified. |
| **P3OP07-R02**, §بسته | [L182](https://github.com/Shahbazi-Amir/RAG_finance/blob/7c74783c3dcda897b010ba9ea358d113f172ed1f/data/Road_Maps/RAG_finance_phase3_operational_roadmap.md#L182): retention و lifecycle برای object/log. | `P3M22-A05`, `P3M16-A06` | **GAP/CONFLICT, OPEN (non-counting):** Object Storage and log lifecycle are separately scoped and operator pending. |
| **P3OP07-R03**, §بسته | [L183](https://github.com/Shahbazi-Amir/RAG_finance/blob/7c74783c3dcda897b010ba9ea358d113f172ed1f/data/Road_Maps/RAG_finance_phase3_operational_roadmap.md#L183): restore drill و گزارش RPO/RTO واقعی. | `P3M22-A06`, `P3M22-A08` | Mapped only; required execution and the source Gate still unverified. |
| **P3OP07-R04**, §بسته | [L184](https://github.com/Shahbazi-Amir/RAG_finance/blob/7c74783c3dcda897b010ba9ea358d113f172ed1f/data/Road_Maps/RAG_finance_phase3_operational_roadmap.md#L184): export و deletion workflow. | `P3M15-A08`, `P3M21-A08`, `P3M15-A04` | **GAP/CONFLICT, OPEN (non-counting):** Export scope conflict; deletion not conditional on Export. |
| **P3OP07-R05**, §بسته | [L185](https://github.com/Shahbazi-Amir/RAG_finance/blob/7c74783c3dcda897b010ba9ea358d113f172ed1f/data/Road_Maps/RAG_finance_phase3_operational_roadmap.md#L185): tombstone/audit برای حذف و عدم بازگشت ناخواسته از backup. | `P3M15-A04`, `P3M22-A06` | **GAP/CONFLICT, OPEN (non-counting):** tombstone and preventing data resurrection after backup restore need explicit evidence. |
| **P3OP08-R01**, §Metrics | [L195](https://github.com/Shahbazi-Amir/RAG_finance/blob/7c74783c3dcda897b010ba9ea358d113f172ed1f/data/Road_Maps/RAG_finance_phase3_operational_roadmap.md#L195): request rate، error rate و latency p50/p95. | `P3M16-A02`, `P3M23-A02` | Mapped only; required execution and the source Gate still unverified. |
| **P3OP08-R02**, §Metrics | [L196](https://github.com/Shahbazi-Amir/RAG_finance/blob/7c74783c3dcda897b010ba9ea358d113f172ed1f/data/Road_Maps/RAG_finance_phase3_operational_roadmap.md#L196): retrieval/generation latency و provider errors. | `P3M16-A02` | Mapped only; required execution and the source Gate still unverified. |
| **P3OP08-R03**, §Metrics | [L197](https://github.com/Shahbazi-Amir/RAG_finance/blob/7c74783c3dcda897b010ba9ea358d113f172ed1f/data/Road_Maps/RAG_finance_phase3_operational_roadmap.md#L197): token/cost per successful answer. | `P3M16-A02`, `P3M23-A08` | Mapped only; required execution and the source Gate still unverified. |
| **P3OP08-R04**, §Metrics | [L198](https://github.com/Shahbazi-Amir/RAG_finance/blob/7c74783c3dcda897b010ba9ea358d113f172ed1f/data/Road_Maps/RAG_finance_phase3_operational_roadmap.md#L198): citation/no-answer/policy outcomes. | `P3M16-A02`, `P3M10-A06` | Mapped only; required execution and the source Gate still unverified. |
| **P3OP08-R05**, §Metrics | [L199](https://github.com/Shahbazi-Amir/RAG_finance/blob/7c74783c3dcda897b010ba9ea358d113f172ed1f/data/Road_Maps/RAG_finance_phase3_operational_roadmap.md#L199): cache hit و queue depth. | `P3M16-A02`, `P3M17-A08` | Mapped only; required execution and the source Gate still unverified. |
| **P3OP08-R06**, §Metrics | [L200](https://github.com/Shahbazi-Amir/RAG_finance/blob/7c74783c3dcda897b010ba9ea358d113f172ed1f/data/Road_Maps/RAG_finance_phase3_operational_roadmap.md#L200): DB/Qdrant health و saturation. | `P3M16-A04`, `P3M23-A07` | Mapped only; required execution and the source Gate still unverified. |
| **P3OP08-R07**, §عملیات | [L204](https://github.com/Shahbazi-Amir/RAG_finance/blob/7c74783c3dcda897b010ba9ea358d113f172ed1f/data/Road_Maps/RAG_finance_phase3_operational_roadmap.md#L204): structured logs بدون PII. | `P3M16-A01`, `P3M16-A06` | Mapped only; required execution and the source Gate still unverified. |
| **P3OP08-R08**, §عملیات | [L205](https://github.com/Shahbazi-Amir/RAG_finance/blob/7c74783c3dcda897b010ba9ea358d113f172ed1f/data/Road_Maps/RAG_finance_phase3_operational_roadmap.md#L205): traces بین Web/API/RAG/LLM. | `P3M16-A08`, `P3M13-A07` | Mapped only; required execution and the source Gate still unverified. |
| **P3OP08-R09**, §عملیات | [L206](https://github.com/Shahbazi-Amir/RAG_finance/blob/7c74783c3dcda897b010ba9ea358d113f172ed1f/data/Road_Maps/RAG_finance_phase3_operational_roadmap.md#L206): alerts، on-call contacts و incident runbook. | `P3M16-A04`, `P3M16-A09`, `P3M25-A01` | Mapped only; required execution and the source Gate still unverified. |
| **P3OP08-R10**, §عملیات | [L207](https://github.com/Shahbazi-Amir/RAG_finance/blob/7c74783c3dcda897b010ba9ea358d113f172ed1f/data/Road_Maps/RAG_finance_phase3_operational_roadmap.md#L207): admin operational view حداقلی؛ پنل گسترده در فاز ۴. | `P3M16-A03` | **GAP/CONFLICT, OPEN (non-counting):** minimum admin operational view is separate from Phase 4 admin panel. |
| **P3OP09-R01**, §بسته | [L215](https://github.com/Shahbazi-Amir/RAG_finance/blob/7c74783c3dcda897b010ba9ea358d113f172ed1f/data/Road_Maps/RAG_finance_phase3_operational_roadmap.md#L215): prompt injection tests برای Query و Retrieved content. | `P3M12-A05`, `P3M21-A03` | Mapped only; required execution and the source Gate still unverified. |
| **P3OP09-R02**, §بسته | [L216](https://github.com/Shahbazi-Amir/RAG_finance/blob/7c74783c3dcda897b010ba9ea358d113f172ed1f/data/Road_Maps/RAG_finance_phase3_operational_roadmap.md#L216): output validation و safe rendering. | `P3M09-A07`, `P3M21-A02`, `P3M14-A12` | **GAP/CONFLICT, OPEN (non-counting):** UI safe rendering requires distinct checks beyond model output validation. |
| **P3OP09-R03**, §بسته | [L217](https://github.com/Shahbazi-Amir/RAG_finance/blob/7c74783c3dcda897b010ba9ea358d113f172ed1f/data/Road_Maps/RAG_finance_phase3_operational_roadmap.md#L217): access control روی Sourceهای غیرعمومی. | `P3M06-A02`, `P3M21-A04` | Mapped only; required execution and the source Gate still unverified. |
| **P3OP09-R04**, §بسته | [L218](https://github.com/Shahbazi-Amir/RAG_finance/blob/7c74783c3dcda897b010ba9ea358d113f172ed1f/data/Road_Maps/RAG_finance_phase3_operational_roadmap.md#L218): dependency/container scanning و SBOM. | `P3M02-A05`, `P3M19-A05` | Mapped only; required execution and the source Gate still unverified. |
| **P3OP09-R05**, §بسته | [L219](https://github.com/Shahbazi-Amir/RAG_finance/blob/7c74783c3dcda897b010ba9ea358d113f172ed1f/data/Road_Maps/RAG_finance_phase3_operational_roadmap.md#L219): secret scanning، audit log و admin access review. | `P3M02-A05`, `P3M16-A05` | Mapped only; required execution and the source Gate still unverified. |
| **P3OP09-R06**, §بسته | [L220](https://github.com/Shahbazi-Amir/RAG_finance/blob/7c74783c3dcda897b010ba9ea358d113f172ed1f/data/Road_Maps/RAG_finance_phase3_operational_roadmap.md#L220): abuse، rate/cost limit و denial-of-wallet controls. | `P3M17-A01`, `P3M17-A02`, `P3M21-A02` | Mapped only; required execution and the source Gate still unverified. |
| **P3OP09-R07**, §بسته | [L221](https://github.com/Shahbazi-Amir/RAG_finance/blob/7c74783c3dcda897b010ba9ea358d113f172ed1f/data/Road_Maps/RAG_finance_phase3_operational_roadmap.md#L221): test برای sensitive information disclosure. | `P3M21-A02`, `P3M12-A09` | Mapped only; required execution and the source Gate still unverified. |
| **P3OP10-R01**, §سناریوهای تست | [L233](https://github.com/Shahbazi-Amir/RAG_finance/blob/7c74783c3dcda897b010ba9ea358d113f172ed1f/data/Road_Maps/RAG_finance_phase3_operational_roadmap.md#L233): chat cached و uncached. | `P3M23-A03`, `P3M17-A03` | Mapped only; required execution and the source Gate still unverified. |
| **P3OP10-R02**, §سناریوهای تست | [L234](https://github.com/Shahbazi-Amir/RAG_finance/blob/7c74783c3dcda897b010ba9ea358d113f172ed1f/data/Road_Maps/RAG_finance_phase3_operational_roadmap.md#L234): پاسخ کوتاه/بلند و چند Citation. | `P3M23-A03`, `P3M11-A07` | Mapped only; required execution and the source Gate still unverified. |
| **P3OP10-R03**, §سناریوهای تست | [L235](https://github.com/Shahbazi-Amir/RAG_finance/blob/7c74783c3dcda897b010ba9ea358d113f172ed1f/data/Road_Maps/RAG_finance_phase3_operational_roadmap.md#L235): provider کند یا unavailable. | `P3M23-A05`, `P3M09-A02` | Mapped only; required execution and the source Gate still unverified. |
| **P3OP10-R04**, §سناریوهای تست | [L236](https://github.com/Shahbazi-Amir/RAG_finance/blob/7c74783c3dcda897b010ba9ea358d113f172ed1f/data/Road_Maps/RAG_finance_phase3_operational_roadmap.md#L236): spike، sustained load و concurrent conversations. | `P3M23-A01`, `P3M23-A03` | Mapped only; required execution and the source Gate still unverified. |
| **P3OP10-R05**, §سناریوهای تست | [L237](https://github.com/Shahbazi-Amir/RAG_finance/blob/7c74783c3dcda897b010ba9ea358d113f172ed1f/data/Road_Maps/RAG_finance_phase3_operational_roadmap.md#L237): DB و Qdrant degradation. | `P3M23-A05`, `P3M23-A07` | Mapped only; required execution and the source Gate still unverified. |
| **P3OP10-R06**, §Targetهای اولیه غیرقراردادی | [L241](https://github.com/Shahbazi-Amir/RAG_finance/blob/7c74783c3dcda897b010ba9ea358d113f172ed1f/data/Road_Maps/RAG_finance_phase3_operational_roadmap.md#L241): Availability پایلوت: 99.5٪. | `P3M01-A06`, `P3M23-A10` | **GAP/CONFLICT, OPEN (non-counting):** pilot 99.5% availability is PROPOSED/NONBINDING. |
| **P3OP10-R07**, §Targetهای اولیه غیرقراردادی | [L242](https://github.com/Shahbazi-Amir/RAG_finance/blob/7c74783c3dcda897b010ba9ea358d113f172ed1f/data/Road_Maps/RAG_finance_phase3_operational_roadmap.md#L242): p95 مسیر غیر AI: کمتر از 500ms. | `P3M01-A06`, `P3M23-A02` | **GAP/CONFLICT, OPEN (non-counting):** non-AI 500ms p95 is PROPOSED/NONBINDING. |
| **P3OP10-R08**, §Targetهای اولیه غیرقراردادی | [L243](https://github.com/Shahbazi-Amir/RAG_finance/blob/7c74783c3dcda897b010ba9ea358d113f172ed1f/data/Road_Maps/RAG_finance_phase3_operational_roadmap.md#L243): p95 پاسخ AI: ترجیحاً کمتر از 15s، وابسته به مدل. | `P3M01-A06`, `P3M23-A02` | **GAP/CONFLICT, OPEN (non-counting):** AI 15s p95 is PROPOSED/NONBINDING. |
| **P3OP10-R09**, §Targetهای اولیه غیرقراردادی | [L244](https://github.com/Shahbazi-Amir/RAG_finance/blob/7c74783c3dcda897b010ba9ea358d113f172ed1f/data/Road_Maps/RAG_finance_phase3_operational_roadmap.md#L244): error budget، concurrent limit و daily cost cap پس از Load test فریز شوند. | `P3M23-A01`, `P3M17-A02` | Mapped only; required execution and the source Gate still unverified. |
| **P3OP11-R01**, §مراحل | [L254](https://github.com/Shahbazi-Amir/RAG_finance/blob/7c74783c3dcda897b010ba9ea358d113f172ed1f/data/Road_Maps/RAG_finance_phase3_operational_roadmap.md#L254): Internal alpha با حساب‌های تست. | `P3M20-A06`, `P3M24-A06` | Mapped only; required execution and the source Gate still unverified. |
| **P3OP11-R02**, §مراحل | [L255](https://github.com/Shahbazi-Amir/RAG_finance/blob/7c74783c3dcda897b010ba9ea358d113f172ed1f/data/Road_Maps/RAG_finance_phase3_operational_roadmap.md#L255): Closed beta با گروه محدود. | `P3M20-A11`, `P3M24-A07` | Mapped only; required execution and the source Gate still unverified. |
| **P3OP11-R03**, §مراحل | [L256](https://github.com/Shahbazi-Amir/RAG_finance/blob/7c74783c3dcda897b010ba9ea358d113f172ed1f/data/Road_Maps/RAG_finance_phase3_operational_roadmap.md#L256): رفع P0/P1 و کنترل هزینه/کیفیت. | `P3M24-A01`, `P3M25-A05` | Mapped only; required execution and the source Gate still unverified. |
| **P3OP11-R04**, §مراحل | [L257](https://github.com/Shahbazi-Amir/RAG_finance/blob/7c74783c3dcda897b010ba9ea358d113f172ed1f/data/Road_Maps/RAG_finance_phase3_operational_roadmap.md#L257): Production launch محدود. | `P3M24-A04`, `P3M24-A07` | Mapped only; required execution and the source Gate still unverified. |
| **P3OP11-R05**, §مراحل | [L258](https://github.com/Shahbazi-Amir/RAG_finance/blob/7c74783c3dcda897b010ba9ea358d113f172ed1f/data/Road_Maps/RAG_finance_phase3_operational_roadmap.md#L258): افزایش تدریجی ظرفیت با feature flags. | `P3M24-A07`, `P3M25-A05` | **GAP/CONFLICT, OPEN (non-counting):** feature-flag rollout not an explicit independent M24 activity. |
| **P3OP11-R06**, §Launch checklist | [L262](https://github.com/Shahbazi-Amir/RAG_finance/blob/7c74783c3dcda897b010ba9ea358d113f172ed1f/data/Road_Maps/RAG_finance_phase3_operational_roadmap.md#L262): Domain/TLS و privacy/terms links. | `P3M01-A08`, `P3M21-A05` | Mapped only; required execution and the source Gate still unverified. |
| **P3OP11-R07**, §Launch checklist | [L263](https://github.com/Shahbazi-Amir/RAG_finance/blob/7c74783c3dcda897b010ba9ea358d113f172ed1f/data/Road_Maps/RAG_finance_phase3_operational_roadmap.md#L263): backup/restore و rollback تست‌شده. | `P3M22-A06`, `P3M19-A09` | Mapped only; required execution and the source Gate still unverified. |
| **P3OP11-R08**, §Launch checklist | [L264](https://github.com/Shahbazi-Amir/RAG_finance/blob/7c74783c3dcda897b010ba9ea358d113f172ed1f/data/Road_Maps/RAG_finance_phase3_operational_roadmap.md#L264): monitoring/alerts فعال. | `P3M16-A04`, `P3M24-A08` | Mapped only; required execution and the source Gate still unverified. |
| **P3OP11-R09**, §Launch checklist | [L265](https://github.com/Shahbazi-Amir/RAG_finance/blob/7c74783c3dcda897b010ba9ea358d113f172ed1f/data/Road_Maps/RAG_finance_phase3_operational_roadmap.md#L265): support و incident ownership مشخص. | `P3M25-A01`, `P3M21-A09` | Mapped only; required execution and the source Gate still unverified. |
| **P3OP11-R10**, §Launch checklist | [L266](https://github.com/Shahbazi-Amir/RAG_finance/blob/7c74783c3dcda897b010ba9ea358d113f172ed1f/data/Road_Maps/RAG_finance_phase3_operational_roadmap.md#L266): RAG regression و security gate پاس. | `P3M20-A07`, `P3M21-A02` | Mapped only; required execution and the source Gate still unverified. |
| **P3OP11-R11**, §Launch checklist | [L267](https://github.com/Shahbazi-Amir/RAG_finance/blob/7c74783c3dcda897b010ba9ea358d113f172ed1f/data/Road_Maps/RAG_finance_phase3_operational_roadmap.md#L267): data deletion/export آماده. | `P3M15-A04`, `P3M15-A08`, `P3M21-A08` | **GAP/CONFLICT, OPEN (non-counting):** Export scope still conditional, deletion independent. |
| **P3OP11-R12**, §Launch checklist | [L268](https://github.com/Shahbazi-Amir/RAG_finance/blob/7c74783c3dcda897b010ba9ea358d113f172ed1f/data/Road_Maps/RAG_finance_phase3_operational_roadmap.md#L268): analytics حداقلی و consent-aware. | `P3M16-A02`, `P3M21-A07` | **GAP/CONFLICT, OPEN (non-counting):** consent-aware analytics needs an approved policy beyond modular metrics. |

## پیوست ممیزی تخصصی DB | وضعیت ۵۷ ردیف تحویل

# DATABASE_F3 — ردیف‌به‌ردیف فاز سه | بازبینی فنی 2026-11-23

**قواعد:** وضعیت ستون «پیاده‌سازی» صرفاً دامنهٔ شواهد همین ردیف را بیان می‌کند. `DONE` برای زیرکار DB/CI به معنای تأیید Gate/محیط مک نیست. ستون «پذیرش» برای همهٔ ردیف‌های مشترک با Foundation/API/ناظر همچنان `NOT_ACCEPTED` است تا صاحب ردیف تأیید دهد.

**مرجع:** `04_DATABASE_F3_Phase3_Completion(1).md` (57 شناسه)، رجیستر رسمی `coordination/phase3_checklist.md@2bddf96c5218caf63605e466a8ce3d30544f44ea` (Sole editor: Foundation)، دفتر تصمیم‌های باز `coordination/open_decisions.md @ 8e3eccd5fe8048585226818a8a998a08356b84e0`.
**شواهد:** CI `45082326382` (baseline DB+API/Bootstrap roles); CI `45108041850` **SUCCESS attempt 2** (rollback/FK/RLS and optional 011 separate); CI `45108527302` (14-table Catalog); **CI `45109023781` SUCCESS on exact SHA `0e301a26096cb9f8c2b8e3fde3e20e9a1add48a5`** (2 synthetic owners, backup/restore, soft deletion state preserved and 854ms fixture restore); none is Mac product HTTP.

| ID | مالک | معیار | فایل و SHA | محیط | پیاده‌سازی | تست | پذیرش | شاهد | مانع و ورودی دقیق |
|---|---|---|---|---|---|---|---|---|---|
| P3M03-A01 | Foundation + API/UI/DB | تعریف مرز Domain moduleها | packages/contracts/product.v1.schema.json @ 9faea26384dae1610425def25c3b7de2eabb280e | API source / offline CI; Mac L2 not run | OPEN — Proposed modular boundaries exist; not a joined runtime contract | Synthetic contracts only | NOT_ACCEPTED | API #61; Foundation #55; open decisions | Foundation/API approve and test full import graph |
| P3M03-A02 | Foundation + API/UI/DB | تعریف Error model مشترک | packages/contracts/product.v1.schema.json @ 9faea26384dae1610425def25c3b7de2eabb280e | API source / offline CI; Mac L2 not run | OPEN — Provisional versioned error schema exists | Synthetic only | NOT_ACCEPTED | API #61; Foundation #55; open decisions | Foundation/API error model acceptance |
| P3M03-A03 | Foundation + API/UI/DB | تعریف Request ID و Trace ID | apps/api/product_session_api.py @ c6502fe5fbf2ec786a4713d99d7be81ca0f52701 | API source / offline CI; Mac L2 not run | OPEN — Request/Trace correlation in signed API code | Synthetic CI; no Mac integrated trace | NOT_ACCEPTED | API #61; Foundation #55; open decisions | Mac signed HTTP trace/alert evidence |
| P3M03-A04 | Foundation + API/UI/DB | نسخه‌بندی API از `/v1` | apps/api/history_api.py @ 84199d167b2615540317c66fef26998f1cea031b | API source / offline CI; Mac L2 not run | OPEN — /v1 routes implemented on API source | Offline API CI only | NOT_ACCEPTED | API #61; Foundation #55; open decisions | Foundation canonical release merge and Mac versioned HTTP |
| P3M03-A05 | Foundation + API/UI/DB | ساخت Schemaهای User، Conversation، Message، Answer و Citation | packages/contracts/product.v1.schema.json @ 9faea26384dae1610425def25c3b7de2eabb280e | API source / offline CI; Mac L2 not run | OPEN — DTOs for message, conversation and answer; Citation contract partial | Contract CI only; physical citation table absent | NOT_ACCEPTED | API #61; Foundation #55; open decisions | Producer Citation/provenance contract and accepted physical model |
| P3M03-A06 | Foundation + API/UI/DB | تعریف فیلدهای Attribution | packages/contracts/product.v1.schema.json @ 9faea26384dae1610425def25c3b7de2eabb280e | API source / offline CI; Mac L2 not run | BLOCKED — Attribution contract provisional, no verified locator | Source observations explicitly UNVERIFIED | NOT_ACCEPTED | API #61; Foundation #55; open decisions | ENGINE source resolver and approved locator semantics |
| P3M03-A07 | Foundation + API/UI/DB | تعریف Compatibility policy | packages/contracts/product.v1.schema.json @ 9faea26384dae1610425def25c3b7de2eabb280e | API source / offline CI; Mac L2 not run | OPEN — Wire compatibility draft exists | Synthetic only | NOT_ACCEPTED | API #61; Foundation #55; open decisions | API/UI/DB freeze canonical forward-compatible variants |
| P3M03-A08 | Foundation + API/UI/DB | ساخت Contract tests بین Backend، Frontend و RAG runtime | packages/contracts/product.v1.schema.json @ 9faea26384dae1610425def25c3b7de2eabb280e | API source / offline CI; Mac L2 not run | OPEN — Consumer contracts tested in isolation | Offline synthetic API/UI CI, L2 NOT_RUN | NOT_ACCEPTED | API #61; Foundation #55; open decisions | Signed real Mac UI-BFF-API-DB-C018 L2 |
| P3M03-A09 | Foundation + API/UI/DB | ساخت Architecture dependency test برای جلوگیری از Import معکوس. | coordination/tasks/AGENT-DB-01.md @ f5cbacc4cadd15a423607e6c29bcbb4de41fb440 | API source / offline CI; Mac L2 not run | OPEN — Architecture ownership documented | No complete import-graph check of integrated release | NOT_ACCEPTED | API #61; Foundation #55; open decisions | Foundation architecture-dependency CI |
| P3M04-A01 | DB | طراحی ERD و Data dictionary | infra/postgres/migrations/001_history_l1.up.sql @ b4bbc8d4208dd87de692ee8ad3ac1b3847bc58a5 | GitHub Actions isolated PG17.11 / source-only | OPEN — Physical History/Auth partial; DB01-02 ERD remains draft | CI 14 tables/30 functions; no full phase3 ERD acceptance | NOT_ACCEPTED | CI 45082326382, sha b6b79369006eca3a1e4c8e75a9ba4ab14d0fab74 | API/DB review Consent, Feedback, Audit, deletion and retention |
| P3M04-A02 | DB | تعریف Primary/Foreign key و Index | infra/postgres/migrations/001_history_l1.up.sql @ b4bbc8d4208dd87de692ee8ad3ac1b3847bc58a5 | GitHub Actions isolated PG17.11 / source-only | OPEN — History composite PK/FK and cursor indexes implemented | Run 45108041850: cross-owner FK and duplicate NULL idempotency rejected | NOT_ACCEPTED | CI 45082326382, sha b6b79369006eca3a1e4c8e75a9ba4ab14d0fab74 | EXPLAIN and production-volume query plans still missing |
| P3M04-A03 | DB | افزودن `user_id` به تمام داده‌های کاربر | infra/postgres/migrations/001_history_l1.up.sql @ b4bbc8d4208dd87de692ee8ad3ac1b3847bc58a5 | GitHub Actions isolated PG17.11 / source-only | OPEN — Trusted History owner_id exists; literal user_id/tenant coverage not fully reconciled | Owner-specific SQL tests limited | NOT_ACCEPTED | CI 45082326382, sha b6b79369006eca3a1e4c8e75a9ba4ab14d0fab74 | Approve owner_id-to-user_id mapping, audit missing user tables |
| P3M04-A04 | DB | ذخیره Citation و Attribution به‌صورت ساخت‌یافته | packages/contracts/product.v1.schema.json @ 9faea26384dae1610425def25c3b7de2eabb280e | GitHub Actions isolated PG17.11 / source-only | BLOCKED — Citation wire schema provisional; database Citation persistence absent | Real producer locator not admitted | NOT_ACCEPTED | CI 45082326382, sha b6b79369006eca3a1e4c8e75a9ba4ab14d0fab74 | ENGINE/API define source evidence and storage contracts |
| P3M04-A05 | DB | ذخیره Versionهای knowledge/retrieval/model/policy | apps/api/product_session_api.py @ c6502fe5fbf2ec786a4713d99d7be81ca0f52701 | GitHub Actions isolated PG17.11 / source-only | BLOCKED — RAG result includes pinned engine metadata; full persisted versions not implemented | No real T3/Answer provenance test | NOT_ACCEPTED | CI 45082326382, sha b6b79369006eca3a1e4c8e75a9ba4ab14d0fab74 | Real producer version fields and required lineage |
| P3M04-A06 | DB | تعریف Migration forward و rollback | infra/postgres/dev_f3_isolated @ b6b79369006eca3a1e4c8e75a9ba4ab14d0fab74 | GitHub Actions isolated PG17.11 / source-only | DONE — 001-010 UP pinned, durable ledger and no unsafe replay; 009/010 guarded DOWN+UP in cloned disposable DB | Run 45108041850 source job: evidence-blocked DOWN refused, clean DOWN/UP and DB55 PASS | DB_CI_ONLY; MODULE_NOT_ACCEPTED | CI 45082326382, sha b6b79369006eca3a1e4c8e75a9ba4ab14d0fab74 | Limited 009/010 rollback only; not full all-001-010 data-bearing rollback |
| P3M04-A07 | DB | تست Migration روی دیتابیس خالی و دیتابیس دارای داده | infra/postgres/dev_f3_isolated @ b6b79369006eca3a1e4c8e75a9ba4ab14d0fab74 | GitHub Actions isolated PG17.11 / source-only | OPEN — Fresh empty 001–010 and populated guarded 009/010 rollback tested on separate clone | Run 45108041850 attempt 2: 10/10 UP, synthetic login blocks DOWN; clean DOWN/UP PASS, optional 011 separate PASS | NOT_ACCEPTED | CI 45082326382, sha b6b79369006eca3a1e4c8e75a9ba4ab14d0fab74 | Other migration data-bearing down/up + full Phase3 entity migration acceptance |
| P3M04-A08 | DB | تعریف Retention و soft/hard delete | coordination/open_decisions.md @ 8e3eccd5fe8048585226818a8a998a08356b84e0 | GitHub Actions isolated PG17.11 / source-only | BLOCKED — Deletion state present; retention/hard-delete mechanics not approved | No retention/resurrection restore proof | NOT_ACCEPTED | CI 45082326382, sha b6b79369006eca3a1e4c8e75a9ba4ab14d0fab74 | Owner/security approve retention, reappearance prevention and status access |
| P3M04-A09 | DB | آماده‌سازی Namespace رزروشده برای موجودیت‌های فاز ۴ بدون فعال‌سازی آن‌ها. | coordination/open_decisions.md @ 8e3eccd5fe8048585226818a8a998a08356b84e0 | GitHub Actions isolated PG17.11 / source-only | DONE — Phase4 entities reserved DESIGN-ONLY, no active DDL | Reviewed design scope, not runtime table | DB_CI_ONLY; MODULE_NOT_ACCEPTED | CI 45082326382, sha b6b79369006eca3a1e4c8e75a9ba4ab14d0fab74 | No active Phase4 tables; future activation distinct gate |
| P3M06-A01 | DB + API | فعال‌سازی Row-Level Security برای جداول کاربرمحور | infra/postgres/migrations/001_history_l1.up.sql @ b4bbc8d4208dd87de692ee8ad3ac1b3847bc58a5 | GitHub Actions isolated PG17.11 / source-only | OPEN — FORCE RLS on History and private Auth tables; not all future entities exist | CI four critical FORCE RLS and DB55 PASS | NOT_ACCEPTED | CI 45082326382, sha b6b79369006eca3a1e4c8e75a9ba4ab14d0fab74 | All active user-data paths + real API A/B L2 |
| P3M06-A02 | DB + API | تعریف Policy خواندن، نوشتن، ویرایش و حذف | infra/postgres/migrations/001_history_l1.up.sql @ b4bbc8d4208dd87de692ee8ad3ac1b3847bc58a5 | GitHub Actions isolated PG17.11 / source-only | OPEN — Scoped owner_only History policy and private Auth deny-direct | 9-role ACL/72 negative PASS | NOT_ACCEPTED | CI 45082326382, sha b6b79369006eca3a1e4c8e75a9ba4ab14d0fab74 | Deletion/feedback/write policies after product scope |
| P3M06-A03 | DB + API | تنظیم Context امن user/tenant در هر Transaction | src/phase3/storage/postgres/repository.py @ 14f97dd680425b74f8e12fa1696d423a20bf7d76 | GitHub Actions isolated PG17.11 / source-only | OPEN — SET LOCAL app.owner_id used under trusted service actor | Run 45108041850: other-owner SELECT invisible, cross-owner INSERT denied (disposable clone) | NOT_ACCEPTED | CI 45082326382, sha b6b79369006eca3a1e4c8e75a9ba4ab14d0fab74 | Full signed Mac actor binding and GUC ownership attack matrix |
| P3M06-A04 | DB + API | جلوگیری از دسترسی Background job خارج از Scope | src/phase3/storage/postgres/repository.py @ 14f97dd680425b74f8e12fa1696d423a20bf7d76 | GitHub Actions isolated PG17.11 / source-only | OPEN — No direct auth table SELECT, limited service roles | 9 role flags PASS; background job scopes not integrated | NOT_ACCEPTED | CI 45082326382, sha b6b79369006eca3a1e4c8e75a9ba4ab14d0fab74 | Worker/authenticated background identity and least privilege |
| P3M06-A05 | DB + API | تست cross-user برای تمام Endpointها | apps/api/product_session_api.py @ c6502fe5fbf2ec786a4713d99d7be81ca0f52701 | GitHub Actions isolated PG17.11 / source-only | BLOCKED — History API server auth exists; no complete endpoint suite cross-user Mac | No Mac L2 signed A/B test | NOT_ACCEPTED | CI 45082326382, sha b6b79369006eca3a1e4c8e75a9ba4ab14d0fab74 | Foundation/API full endpoint matrix after BFF/IdP/C018 |
| P3M06-A06 | DB + API | تست ID enumeration | src/phase3/storage/postgres/repository.py @ 14f97dd680425b74f8e12fa1696d423a20bf7d76 | GitHub Actions isolated PG17.11 / source-only | OPEN — Owner-scoped composite keys; generic non-enumerating errors in API | Synthetic negative tests; not real Mac | NOT_ACCEPTED | CI 45082326382, sha b6b79369006eca3a1e4c8e75a9ba4ab14d0fab74 | ID/owner enumeration timing/HTTP negative suite |
| P3M06-A07 | DB + API | تست دسترسی مستقیم Repository layer | src/phase3/storage/postgres/repository.py @ 14f97dd680425b74f8e12fa1696d423a20bf7d76 | GitHub Actions isolated PG17.11 / source-only | OPEN — PostgreSQL repository calls use transaction owner scope | Bounded DB tests; not full direct-call negative matrix | NOT_ACCEPTED | CI 45082326382, sha b6b79369006eca3a1e4c8e75a9ba4ab14d0fab74 | API/DB owner-context adversarial direct repository suite |
| P3M06-A08 | DB + API | ثبت Audit برای عملیات حساس | coordination/open_decisions.md @ 8e3eccd5fe8048585226818a8a998a08356b84e0 | GitHub Actions isolated PG17.11 / source-only | BLOCKED — Auth security ledger exists; general audit events not implemented | No full trace/redaction/alert proof | NOT_ACCEPTED | CI 45082326382, sha b6b79369006eca3a1e4c8e75a9ba4ab14d0fab74 | Agreed audit event schema, event retention and operator policy |
| P3M06-A09 | DB + API | ساخت Isolation matrix. | infra/postgres/migrations/001_history_l1.up.sql @ b4bbc8d4208dd87de692ee8ad3ac1b3847bc58a5 | GitHub Actions isolated PG17.11 / source-only | OPEN — Role negative matrix: 9 users x 8 auth tables | 72/72 PASS in source and restore; owner A/B runtime pending | NOT_ACCEPTED | CI 45082326382, sha b6b79369006eca3a1e4c8e75a9ba4ab14d0fab74 | Complete owner/route/background-job matrix |
| P3M10-A01 | API + DB | ساخت Query context از پیام جاری و تاریخچه محدود | apps/api/product_session_api.py @ c6502fe5fbf2ec786a4713d99d7be81ca0f52701 | API source / offline CI; Mac L2 not run | BLOCKED — History query context only partial | No Mac real C018 retriever authorized | NOT_ACCEPTED | API #61; Foundation #55; open decisions | API/Engine signed Q2 and history input contract |
| P3M10-A02 | API + DB | Intent و Answerability | apps/api/product_session_api.py @ c6502fe5fbf2ec786a4713d99d7be81ca0f52701 | API source / offline CI; Mac L2 not run | BLOCKED — No real Answerability/calibration integrated | No actual real producer L2 | NOT_ACCEPTED | API #61; Foundation #55; open decisions | Engine/API acceptance for intent/outcome |
| P3M10-A03 | API + DB | Retrieval و Context builder | apps/api/product_session_api.py @ c6502fe5fbf2ec786a4713d99d7be81ca0f52701 | API source / offline CI; Mac L2 not run | BLOCKED — C018 NO_DISPATCH source observations only | No exact full Mac C018 source receipt | NOT_ACCEPTED | API #61; Foundation #55; open decisions | Real retrieval snapshot and chunk/provenance binding |
| P3M10-A04 | API + DB | تولید پاسخ ساخت‌یافته | packages/contracts/product.v1.schema.json @ 9faea26384dae1610425def25c3b7de2eabb280e | API source / offline CI; Mac L2 not run | BLOCKED — No approved product.v1 T3 Answer | Only NO_GENERATION status | NOT_ACCEPTED | API #61; Foundation #55; open decisions | Approved producer and safety contract |
| P3M10-A05 | API + DB | Claim/Citation verification | packages/contracts/product.v1.schema.json @ 9faea26384dae1610425def25c3b7de2eabb280e | API source / offline CI; Mac L2 not run | BLOCKED — Unverified source observations; locators omitted | No real Citation resolution | NOT_ACCEPTED | API #61; Foundation #55; open decisions | Engine source locator + permission review |
| P3M10-A06 | API + DB | اعمال Safety و No-answer | packages/contracts/product.v1.schema.json @ 9faea26384dae1610425def25c3b7de2eabb280e | API source / offline CI; Mac L2 not run | BLOCKED — No-answer status design; real safety calibration absent | No real scored outcomes | NOT_ACCEPTED | API #61; Foundation #55; open decisions | API/Engine safety policy and real test |
| P3M10-A07 | API + DB | ساخت Confidence از اجزای قابل توضیح | packages/contracts/product.v1.schema.json @ 9faea26384dae1610425def25c3b7de2eabb280e | API source / offline CI; Mac L2 not run | BLOCKED — No accepted Confidence contract | No calibration measure | NOT_ACCEPTED | API #61; Foundation #55; open decisions | Engine/API confidence semantics and test design |
| P3M10-A08 | API + DB | ذخیره Runها و Versionها در یک Transaction منطقی | src/phase3/storage/postgres/repository.py @ 14f97dd680425b74f8e12fa1696d423a20bf7d76 | API source / offline CI; Mac L2 not run | OPEN — T1/T2/T3 atomic persistence within History DB is implemented | Isolated History DB test; no real T3 producer | NOT_ACCEPTED | API #61; Foundation #55; open decisions | Live T3 and crash/duplicate DB/API matrix |
| P3M10-A09 | API + DB | مدیریت cancellation و duplicate request | infra/postgres/migrations/002_one_attempt.up.sql @ d1a14f2ba16adb11c44122df1eded15f460d3c83 | API source / offline CI; Mac L2 not run | OPEN — One Attempt per Send; no implicit provider retry | CI one-attempt and 011 test separate; no live Gateway | NOT_ACCEPTED | API #61; Foundation #55; open decisions | Real cancellation/UNKNOWN, no paid Gateway double-send |
| P3M10-A10 | API + DB | Idempotency برای retry کلاینت. | infra/postgres/migrations/001_history_l1.up.sql @ b4bbc8d4208dd87de692ee8ad3ac1b3847bc58a5 | API source / offline CI; Mac L2 not run | OPEN — NULLS NOT DISTINCT and durable receipts for Send idempotency | Baseline isolated CI; adversarial data-bearing duplicate tests pending | NOT_ACCEPTED | API #61; Foundation #55; open decisions | Concurrent same/null-scope and replay after crash |
| P3M15-A01 | DB + API + UI | ذخیره User message و Answer به‌صورت immutable event | infra/postgres/migrations/001_history_l1.up.sql @ b4bbc8d4208dd87de692ee8ad3ac1b3847bc58a5 | GitHub Actions isolated PG17.11 / source-only | OPEN — Immutable History messages/answers tables and scoped grants | Source/DB tests; no real T3 Answer from C018 | NOT_ACCEPTED | CI 45082326382, sha b6b79369006eca3a1e4c8e75a9ba4ab14d0fab74 | Actual Message+Answer lifecycle on signed Mac |
| P3M15-A02 | DB + API + UI | عنوان‌گذاری مکالمه بدون تغییر محتوای اصلی | infra/postgres/migrations/001_history_l1.up.sql @ b4bbc8d4208dd87de692ee8ad3ac1b3847bc58a5 | GitHub Actions isolated PG17.11 / source-only | OPEN — Conversation title mutable, underlying content immutable | Database source-level semantics only | NOT_ACCEPTED | CI 45082326382, sha b6b79369006eca3a1e4c8e75a9ba4ab14d0fab74 | Actual Title update followed by Message identity proof |
| P3M15-A03 | DB + API + UI | Pagination و مرتب‌سازی | src/phase3/storage/postgres/repository.py @ 14f97dd680425b74f8e12fa1696d423a20bf7d76 | GitHub Actions isolated PG17.11 / source-only | OPEN — Owner cursor/list/message ordering query implemented | Isolated pagination; Mac L2 missing | NOT_ACCEPTED | CI 45082326382, sha b6b79369006eca3a1e4c8e75a9ba4ab14d0fab74 | Data-bearing stable pagination + A/B signed traces |
| P3M15-A04 | DB + API + UI | حذف مکالمه طبق Retention policy | coordination/open_decisions.md @ 8e3eccd5fe8048585226818a8a998a08356b84e0 | GitHub Actions isolated PG17.11 / source-only | BLOCKED — deletion_requested state exists, no approved wipe/restore-safe tombstone | CI 45109023781 synthetic owner data restore preserves deletion_requested and no active reappearance; hard-delete/tombstone untested | NOT_ACCEPTED | CI 45082326382, sha b6b79369006eca3a1e4c8e75a9ba4ab14d0fab74 | Security/Owner retention/deletion, post-restore tombstone policy |
| P3M15-A05 | DB + API + UI | Feedback مثبت/منفی و دسته خطا | packages/contracts/product.v1.schema.json @ 9faea26384dae1610425def25c3b7de2eabb280e | GitHub Actions isolated PG17.11 / source-only | BLOCKED — Feedback wire schema proposed; no active API endpoint/storage table | Only schema fixtures | NOT_ACCEPTED | CI 45082326382, sha b6b79369006eca3a1e4c8e75a9ba4ab14d0fab74 | API/UI Feedback payload, rating enums/idempotency and retention review |
| P3M15-A06 | DB + API + UI | ثبت Citation مشکل‌دار یا انتساب اشتباه | packages/contracts/product.v1.schema.json @ 9faea26384dae1610425def25c3b7de2eabb280e | GitHub Actions isolated PG17.11 / source-only | BLOCKED — Citation error report concept not mapped to real verified source | No real provenance links | NOT_ACCEPTED | CI 45082326382, sha b6b79369006eca3a1e4c8e75a9ba4ab14d0fab74 | Engine verified Citation and feedback permissions |
| P3M15-A07 | DB + API + UI | جلوگیری از دسترسی کاربر دیگر | infra/postgres/migrations/001_history_l1.up.sql @ b4bbc8d4208dd87de692ee8ad3ac1b3847bc58a5 | GitHub Actions isolated PG17.11 / source-only | OPEN — History RLS denies cross-owner without setting | CI role flags; real signed A/B HTTP not tested | NOT_ACCEPTED | CI 45082326382, sha b6b79369006eca3a1e4c8e75a9ba4ab14d0fab74 | Full endpoint owner isolation L2 |
| P3M15-A08 | DB + API + UI | Export ساخت‌یافته در صورت تصویب Scope | coordination/open_decisions.md @ 8e3eccd5fe8048585226818a8a998a08356b84e0 | GitHub Actions isolated PG17.11 / source-only | BLOCKED — Export scope is explicitly undecided | No export tested | NOT_ACCEPTED | CI 45082326382, sha b6b79369006eca3a1e4c8e75a9ba4ab14d0fab74 | Owner approve export scope independent of deletion |
| P3M15-A09 | DB + API + UI | Dataset بازخورد بدون PII برای ارزیابی بعدی | coordination/open_decisions.md @ 8e3eccd5fe8048585226818a8a998a08356b84e0 | GitHub Actions isolated PG17.11 / source-only | BLOCKED — Anonymized feedback evaluation dataset not designed | No PII leakage test | NOT_ACCEPTED | CI 45082326382, sha b6b79369006eca3a1e4c8e75a9ba4ab14d0fab74 | Approve minimization, anonymization and retention |
| P3M15-A10 | DB + API + UI | تست Race condition و duplicate write. | infra/postgres/migrations/002_one_attempt.up.sql @ d1a14f2ba16adb11c44122df1eded15f460d3c83 | GitHub Actions isolated PG17.11 / source-only | OPEN — Single Attempt uniqueness; dedupe route guarded | Isolated DB tests, no full feedback races | NOT_ACCEPTED | CI 45082326382, sha b6b79369006eca3a1e4c8e75a9ba4ab14d0fab74 | Concurrent Feedback and History duplicate-write tests |
| P3M22-A01 | DB/PostgreSQL + Ops/Qdrant | Backup نسخه‌دار PostgreSQL | infra/postgres/dev_f3_isolated @ b6b79369006eca3a1e4c8e75a9ba4ab14d0fab74 | GitHub Actions isolated PG17.11 / source-only | DONE — pg_dump -Fc+SHA256 with saved source evidence from lab | Actual PG17.11 CI backup PASS | DB_CI_ONLY; MODULE_NOT_ACCEPTED | CI 45082326382, sha b6b79369006eca3a1e4c8e75a9ba4ab14d0fab74 | Lab only; operational versioned encrypted backup needs policy |
| P3M22-A02 | DB/PostgreSQL + Ops/Qdrant | Snapshot و Restore Qdrant | coordination/open_decisions.md @ 8e3eccd5fe8048585226818a8a998a08356b84e0 | GitHub Actions isolated PG17.11 / source-only | BLOCKED — Qdrant embedded index not owned by DB role | No consistent no-write snapshot evidence | NOT_ACCEPTED | CI 45082326382, sha b6b79369006eca3a1e4c8e75a9ba4ab14d0fab74 | Qdrant/Engine owner no-write and validated snapshot |
| P3M22-A03 | DB/PostgreSQL + Ops/Qdrant | Backup Config و Release pointer | coordination/open_decisions.md @ 8e3eccd5fe8048585226818a8a998a08356b84e0 | GitHub Actions isolated PG17.11 / source-only | BLOCKED — DB lab code/version pinned; runtime config/IdP/secret pointer backup not assembled | No system-wide snapshot | NOT_ACCEPTED | CI 45082326382, sha b6b79369006eca3a1e4c8e75a9ba4ab14d0fab74 | Foundation/Ops approved config/release pointer recovery |
| P3M22-A04 | DB/PostgreSQL + Ops/Qdrant | رمزگذاری و دسترسی محدود Backup | coordination/open_decisions.md @ 8e3eccd5fe8048585226818a8a998a08356b84e0 | GitHub Actions isolated PG17.11 / source-only | BLOCKED — 0600 local pg_dump protects permissions, but backup encryption/key rotation policy not selected | No encrypted end-to-end restore | NOT_ACCEPTED | CI 45082326382, sha b6b79369006eca3a1e4c8e75a9ba4ab14d0fab74 | Security/Owner choose KMS/key custody/encryption |
| P3M22-A05 | DB/PostgreSQL + Ops/Qdrant | Retention و rotation | coordination/open_decisions.md @ 8e3eccd5fe8048585226818a8a998a08356b84e0 | GitHub Actions isolated PG17.11 / source-only | BLOCKED — No retention/rotation durations approved | No lifecycle test | NOT_ACCEPTED | CI 45082326382, sha b6b79369006eca3a1e4c8e75a9ba4ab14d0fab74 | Owner backup/deletion retention and rotation policy |
| P3M22-A06 | DB/PostgreSQL + Ops/Qdrant | Restore در محیط خالی | infra/postgres/dev_f3_isolated @ b6b79369006eca3a1e4c8e75a9ba4ab14d0fab74 | GitHub Actions isolated PG17.11 / source-only | DONE — Independent 2nd PG cluster and volume with separate system ID and role grants restored | Run 45109023781: independent DB55, exact 10-row ledger, 9-role verify-full/RLS plus 2 synthetic owners and soft-state preservation PASS | DB_CI_ONLY; MODULE_NOT_ACCEPTED | CI 45082326382, sha b6b79369006eca3a1e4c8e75a9ba4ab14d0fab74 | CI disposable only, not full Mac/product data restore |
| P3M22-A07 | DB/PostgreSQL + Ops/Qdrant | Point-in-time recovery در صورت امکان زیرساخت | coordination/open_decisions.md @ 8e3eccd5fe8048585226818a8a998a08356b84e0 | GitHub Actions isolated PG17.11 / source-only | BLOCKED — PITR/WAL shipping not configured | No failover or point-in-time drill | NOT_ACCEPTED | CI 45082326382, sha b6b79369006eca3a1e4c8e75a9ba4ab14d0fab74 | Ops choose PITR/backup topology and RPO |
| P3M22-A08 | DB/PostgreSQL + Ops/Qdrant | اندازه‌گیری RPO/RTO واقعی | coordination/open_decisions.md @ 8e3eccd5fe8048585226818a8a998a08356b84e0 | GitHub Actions isolated PG17.11 / source-only | BLOCKED — No approved numeric RPO/RTO or production workload | CI 45109023781 measured 854ms small synthetic restore; not an approved operational SLA | NOT_ACCEPTED | CI 45082326382, sha b6b79369006eca3a1e4c8e75a9ba4ab14d0fab74 | Owner/Ops RPO/RTO targets and realistic outage workload |
| P3M22-A09 | DB/PostgreSQL + Ops/Qdrant | تست خرابی جزئی و کامل | infra/postgres/dev_f3_isolated @ b6b79369006eca3a1e4c8e75a9ba4ab14d0fab74 | GitHub Actions isolated PG17.11 / source-only | OPEN — Guarded 009/010 rollback rejects existing Login evidence; separate clone cleanup | Run 45108041850 negative rollback PASS; no full disk/crash failure | NOT_ACCEPTED | CI 45082326382, sha b6b79369006eca3a1e4c8e75a9ba4ab14d0fab74 | Corrupt backup and crash recovery with real retention/tombstone policy |
| P3M22-A10 | DB/PostgreSQL + Ops/Qdrant | Runbook و گزارش Restore. | infra/postgres/dev_f3_isolated @ b6b79369006eca3a1e4c8e75a9ba4ab14d0fab74 | GitHub Actions isolated PG17.11 / source-only | OPEN — Fresh install and restore runbook exists | CI run, sanitized receipt | NOT_ACCEPTED | CI 45082326382, sha b6b79369006eca3a1e4c8e75a9ba4ab14d0fab74 | Foundation/Ops Mac full topology and authenticated restore attestation |

## تنها تصمیم‌های مشترک موردنیاز برای ادامهٔ DB-F3

1. **API + Owner + Security:** شناسهٔ قطعی مالک (`owner_id` در SQL در برابر `user_id` در نقشه)، Scope و نسخهٔ Consent/Withdraw، قرارداد Feedback، نوع‌های امتیاز/خطا و Idempotency.
2. **Owner/Security:** Retention، Tombstone، export scope، حساب حذف‌شده و وضعیت پس از Restore؛ بدون این تصمیم هیچ SQL حذف‌کننده/`012+` مجاز به طراحی نهایی نیست.
3. **Engine/API:** قرارداد واقعی Citation/Attribution، Knowledge/Model/Policy version، T3 Answer و provenance. source_id بدون locator تأییدشده سند Citation نیست.
4. **Foundation/Ops:** دسترسی خواندنی مجاز به Mac برای A/B Signed BFF→HTTP API، C018 و تشخیص 127.0.0.1 network namespace؛ آروان HOLD.
5. **Ops/Security:** RPO/RTO عددی، بکاپ رمزگذاری‌شده و مالکیت کلید، PITR/WAL، Qdrant embedded snapshot و تضمین حذف پس از Restore.

## نسخهٔ مصرفی و اصل عدم بازاجرای تاریخی

- DB آزمایشی اصلی: CI `45082326382` روی SHA `b6b793...`، مطابق رسید ثبت‌شده در PR #59.
- HEAD وقت بررسی: `da8d5b48...` فقط چهار commit مستنداتی جلوتر از SHA تست‌شده بود؛ بعدها CI جدید مربوط به تست rollback/negative مستقل باید با exact SHA خودش ارزیابی شود.
- DB دموی مک `rag_finance_f3_demo` و volume `rag_finance_f3_demo_pg17_20261121` بدون تغییر؛ استثنای تاریخی DB55 به عنوان Migration ledger واقعی ثبت نشود.
- `011`: فقط آزمون آزمایشی مجزا؛ Base `private_no_dispatch` = `001–010`.
- `012+`: `NO_MIGRATION_AUTHORIZED_WITHOUT_CONTRACT`; سازگاری با API جاری و سیاست مصوب شرط است.

## Crosswalk عدم دوباره‌شماری

P3OP02/03/07 و DB01-IDها طبق فایل مأموریت به همین ردیف‌ها نگاشت می‌شوند؛ به شمارش 57 شناسهٔ اصلی اضافه نمی‌شوند. مالک رسمی رجیستر اصلی Foundation است؛ این فایل صرفاً گزارش تخصصی DB است.

## آزمون‌ها و پایان پذیرش از متن نقشه

نام مسیرهای آزمون در نقشه پیشنهاد ساختار است. نام و مسیر واقعی مخزن را در handoff ثبت کن و همهٔ رفتارهای مربوط به دامنه را پوشش بده. در Gateهای مشترک هر تیم رسید بخش خودش را می‌دهد و Foundation نتیجهٔ کل مسیر را ثبت می‌کند.

## ۹. Test Suite الزامی

```text
tests/phase3/unit/
  test_contracts.py
  test_attribution_mapping.py
  test_policy.py
  test_cache_keys.py
  test_redaction.py

tests/phase3/integration/
  test_database_migrations.py
  test_rls_isolation.py
  test_rag_runtime.py
  test_model_gateway.py
  test_answer_persistence.py

tests/phase3/contracts/
  test_openapi.py
  test_frontend_backend_contract.py
  test_phase2_runtime_contract.py
  test_citation_attribution_contract.py

tests/phase3/e2e/
  test_login_chat_citation_history.py
  test_no_answer.py
  test_author_editor_display.py
  test_logout_and_revoke.py

tests/phase3/security/
  test_cross_user_access.py
  test_idor.py
  test_prompt_injection.py
  test_rate_limit.py
  test_log_leakage.py

tests/phase3/performance/
  load_chat.js
  load_history.js
  soak_chat.js
```

---

## ۱۰. معیارهای پذیرش اولیه

مقادیر عملکردی باید در Module 01 با بار واقعی Freeze شوند. معیارهای غیرقابل مذاکره:

| معیار | Gate |
|---|---:|
| Cross-user data exposure | 0 |
| Broken Phase 2 release hash | 0 |
| Invalid citation locator | 0 |
| خطای انتساب نویسنده/سردبیر در Suite | 0 |
| Unsupported critical claim | 0 |
| Critical safety violation | 0 |
| Secret یا PII در Log test | 0 |
| Migration/rollback failure | 0 |
| Backup بدون Restore تأییدشده | 0 |
| Critical/High security issue باز | 0 |
| E2E critical path failure | 0 |
| Release بدون manifest و rollback | 0 |

Targetهای پیشنهادی یادداشت تصمیم مانند Availability 99.5٪، p95 غیرمدلی کمتر از 500ms و p95 پاسخ مدل ترجیحاً کمتر از 15s فقط پس از تأیید زیرساخت و Load model به SLO تبدیل می‌شوند.

---

## ۱۱. Evidence Matrix دانش فنی فاز ۳

| حوزه | شاهد قابل ارائه | Module |
|---|---|---|
| معماری | C4، ADR، Dependency rules | 01 و 03 |
| مهندسی داده | ERD، Migration، RLS و Version trace | 04 و 06 |
| یکپارچه‌سازی RAG | Release lock، Runtime regression | 00، 07 و 08 |
| Citation و Attribution | DTO، UI snapshots و Misattribution tests | 11 و 14 |
| امنیت | Threat model، Negative tests و Scan report | 02، 05، 06 و 21 |
| پایداری | Circuit breaker، Retry، Failure tests | 09، 10 و 23 |
| عملیات | Metrics، Alert، Audit و Runbook | 16 و 25 |
| کنترل مصرف | Rate limit، Cache isolation و Cost report | 17 |
| بازتولیدپذیری | Container digest، SBOM و Release manifest | 18 و 19 |
| تداوم خدمت | Backup/Restore و Rollback evidence | 22 و 24 |
| ارزیابی | E2E، Load، Security و UAT reports | 20، 21 و 23 |

این شواهد دفاع فنی پروژه را از «قرار دادن یک رابط روی مدل و پایگاه برداری» فراتر می‌برد؛ با این حال هیچ نقشه فنی به‌تنهایی تأیید دانش‌بنیان را تضمین نمی‌کند.

---

## ۱۲. اولویت‌بندی

### P0 — الزامی پیش از Launch

Moduleهای 00 تا 16، 18 تا 24؛ به‌ویژه RLS، Citation/Attribution، Safety، Backup/Restore، Security و Rollback.

### P1 — لازم برای کنترل رشد

بهینه‌سازی Module 17، کامل‌کردن Dashboardها، Soak test طولانی‌تر و بهبود Cost report.

### P2 — پس از مشاهده مصرف واقعی

افزایش Replica، CDN، Queue پیشرفته، orchestration پیچیده‌تر و قابلیت‌های PWA. Kubernetes و Microservice بدون شواهد بار واقعی وارد Scope نمی‌شوند.

---

## ۱۳. تعریف Done هر Module

یک Module فقط زمانی Done است که:

- Scope و وابستگی آن ثبت شده باشد؛
- کد Production در ماژول مربوط قرار گرفته باشد؛
- Config و Secret از کد جدا باشند؛
- تست‌های مثبت و منفی مرتبط PASS باشند؛
- Artifact و گزارش مرحله تولید شده باشد؛
- Gate واقعی PASS شده باشد؛
- Known limitation و Risk باقی‌مانده ثبت شده باشد؛
- Runbook یا توضیح فارسی انتقال دانش تکمیل شده باشد؛
- ماژول بعدی بتواند فقط از Contract و Artifact آن استفاده کند.

---

## ۱۴. تعریف Done کل فاز ۳

فاز ۳ زمانی کامل است که Release ثابت فاز ۲ از طریق API و رابط وب چندکاربره در محیط Production قابل استفاده باشد؛ هر کاربر فقط داده خود را ببیند؛ پاسخ‌ها Claim-level Citation و Attribution درست داشته باشند؛ تاریخچه و بازخورد ذخیره شود؛ Safety و No-answer فعال باشد؛ استقرار، Migration، Backup، Restore، Monitoring و Rollback آزمایش شده باشند؛ Load و Security Gateها PASS شده باشند؛ و قرارداد ورودی فاز ۴ تحویل شود.

وجود یک صفحه چت یا اجرای Docker Compose به‌تنهایی به معنی تکمیل فاز ۳ نیست.

---
