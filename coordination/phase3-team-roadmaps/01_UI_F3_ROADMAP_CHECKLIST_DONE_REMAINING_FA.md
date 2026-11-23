# رابط کاربری | نقشه، چک‌لیست و وضعیت اجرای فاز سه

**مبنای گزارش:** آخرین تحویل بررسی‌شدهٔ ۲۳ نوامبر ۲۰۲۶. **پیشرفت تخصصی:** ۷۹٪ پوشش کد (۱۱/۱۴، شامل ۲ کامل در سطح کد و ۹ جزئی)؛ ۰/۱۴ پذیرش.

## ۱. سهم این چت از نقشهٔ اصلی

- ماژول‌های اصلی این مأموریت: M14.
- ماژول‌های مشترک: M03، M11، M15.
- سایر ماژول‌های دارای وابستگی و شاهد مصرفی: M01، M05، M06، M10، M12، M13، M20، M21، M23، M24، M25.
- مالک هر ردیف از رجیستر خوانده می‌شود. گروه‌بندی ماژول‌ها جایگزین مالکیت رسمی ردیف نیست. ردیف‌های مشترک فقط یک بار در پیشرفت کل شمارش می‌شوند.
- [نقشهٔ ماژولار اصلی](https://github.com/Shahbazi-Amir/RAG_finance/blob/7c74783c3dcda897b010ba9ea358d113f172ed1f/data/Road_Maps/RAG_finance_phase3_modular_execution_plan.md) · [نقشهٔ عملیاتی اصلی](https://github.com/Shahbazi-Amir/RAG_finance/blob/7c74783c3dcda897b010ba9ea358d113f172ed1f/data/Road_Maps/RAG_finance_phase3_operational_roadmap.md)

## ۲. کارهای انجام‌شده و شاهد هر تحویل

| تحویل | کار انجام‌شده و دامنهٔ شاهد | شاهد |
|---|---|---|
| PR #62 و سابقهٔ L1 | 115 Node، Chromium مصنوعی دسکتاپ/موبایل، typecheck و build | [شاهد GitHub](https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/45108323298) |
| PR #65 و تغییر اجرایی | Owner fence، پاک‌کردن نمایش در تغییر مالک/401، صفحه حساب و حریم خصوصی، route خروج، keyboard موبایل. 118 Node، Build/Lint/Typecheck/Chromium سبز. شواهد مربوط به UI-03/05/06/11/12/14. | [شاهد GitHub](https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/45201568224) |
| پوشش نقشه و تحویل | ۱۵۴ ردیف مرتبط، ۸۰ نگاشت مرتبط از ۱۰۵ و Runbook L2. تغییر مالک و Refresh بدون POST اضافی در CI مصنوعی. | [شاهد GitHub](https://github.com/Shahbazi-Amir/RAG_finance_app/pull/65) |

این بخش پیشرفت اجرایی و مستنداتی را نشان می‌دهد. آزمون GitHub ایزوله و شاهد مقصد در رجیستر جدا ثبت می‌شوند.

## ۳. کارهای باقی‌مانده و ترتیب اجرا

- [ ] **UI-01/02** — Journey و معماری و تطبیق نسخه‌دار DTO/BFF را روی کاندیدای ادغام‌شده ببند.
- [ ] **UI-03/05/06/11/12/14** — ورود/خروج واقعی، History دو مالک، پاسخ دیررس، 401، Refresh روی همان Attempt، RTL، موبایل، keyboard و رندر دفاعی را روی SHA مشترک با Browser و HTTP/DB receipts ثابت کن.
- [ ] **UI-04/09/13** — پس از قرارداد API/DB و تصمیم محصول، Consent و withdrawal، Feedback روی Answer معتبر، حذف/وضعیت حساب، revoke و Export در دامنه مصوب را عملیاتی کن.
- [ ] **UI-07/08/10** — پس از قرارداد producer، حالت پاسخ، Citation/Attribution، Confidence، stream/cancel و recovery را با دادهٔ واقعی ثابت کن.

## ۴. چک‌لیست تمام فعالیت‌های مرتبط در رجیستر

این نمای اجرا 154 شناسه دارد. هر شناسه یک‌بار در این بخش آمده و شامل فعالیت‌های مستقیم و وابسته است. ستون وضعیت، snapshot مشترک Foundation است و شواهد تازه‌تر در بخش ۲ و پیوست آمده‌اند. برای هر ردیف، شاهد موجود را کنترل کن و مانده را تا معیار پذیرش همان ردیف اجرا کن. تیک نهایی پس از تأیید مقصد و مالک پذیرش ثبت شود.

### P3M01 · architecture_slo_and_scope_freeze

| چک | فعالیت و معیار | مالک | شاهد ثبت‌شده در ماتریس | ورودی یا اقدام باقی‌مانده |
|---|---|---|---|---|
| ☐ P3M01-A01 | **Output:** Freeze دامنه فاز ۳ و فهرست صریح موارد فاز ۴; **Check:** dated approved decision, diagrams/risk register and explicit Gate owner | Foundation/employer; M00; employer scope decisions | NOT_VERIFIED · Employer-approved architecture/ADR/SLO Freeze not proven | CENTRAL/employer and Ops: approve exact workload/cost/privacy/retention/SLO/RPO/RTO numbers or keep proposals nonbinding; then targeted positive and negative tests |
| ☐ P3M01-A02 | **Output:** ثبت Context diagram و Container diagram; **Check:** clean build and security scan in a separately authorized environment | Foundation/employer; M00; employer scope decisions | NOT_VERIFIED · Employer-approved architecture/ADR/SLO Freeze not proven | CENTRAL/employer and Ops: approve exact workload/cost/privacy/retention/SLO/RPO/RTO numbers or keep proposals nonbinding; then targeted positive and negative tests |
| ☐ P3M01-A03 | **Output:** تثبیت Stack با ADR; **Check:** ADR contains exact employer-approved Stack, but no Module01 Gate PASS. | Foundation/employer; M00; employer scope decisions | NOT_VERIFIED · Employer-approved architecture/ADR/SLO Freeze not proven | CENTRAL/employer and Ops: approve exact workload/cost/privacy/retention/SLO/RPO/RTO numbers or keep proposals nonbinding; then targeted positive and negative tests |
| ☐ P3M01-A04 | **Output:** تعیین محیط‌های Local، Test، Staging و Production; **Check:** accepted version/readiness, smoke and rollback evidence | Foundation/employer; M00; employer scope decisions | NOT_VERIFIED · Employer-approved architecture/ADR/SLO Freeze not proven | CENTRAL/employer and Ops: approve exact workload/cost/privacy/retention/SLO/RPO/RTO numbers or keep proposals nonbinding; then targeted positive and negative tests |
| ☐ P3M01-A05 | **Output:** تعیین DAU، پیام روزانه، Concurrent request و بودجه مصرف; **Check:** versioned artifact plus reproducible source-specific acceptance check and evidence | Foundation/employer; M00; employer scope decisions | NOT_VERIFIED · Employer-approved architecture/ADR/SLO Freeze not proven | CENTRAL/employer and Ops: approve exact workload/cost/privacy/retention/SLO/RPO/RTO numbers or keep proposals nonbinding; then targeted positive and negative tests |
| ☐ P3M01-A06 | **Output:** تعیین SLO اولیه Availability، latency و error rate; **Check:** resource/abuse and cross-user-cache negative tests, with approved bounds | Foundation/employer; M00; employer scope decisions | NOT_VERIFIED · Employer-approved architecture/ADR/SLO Freeze not proven | CENTRAL/employer and Ops: approve exact workload/cost/privacy/retention/SLO/RPO/RTO numbers or keep proposals nonbinding; then targeted positive and negative tests |
| ☐ P3M01-A07 | **Output:** تعیین RPO و RTO Backup; **Check:** reproducible migration/restore rollback plus consistency report in isolated test environment | Foundation/employer; M00; employer scope decisions | NOT_VERIFIED · Employer-approved architecture/ADR/SLO Freeze not proven | CENTRAL/employer and Ops: approve exact workload/cost/privacy/retention/SLO/RPO/RTO numbers or keep proposals nonbinding; then targeted positive and negative tests |
| ☐ P3M01-A08 | **Output:** ثبت محل میزبانی، دامنه، TLS و محدودیت انتقال داده; **Check:** versioned artifact plus reproducible source-specific acceptance check and evidence | Foundation/employer; M00; employer scope decisions | NOT_VERIFIED · Employer-approved architecture/ADR/SLO Freeze not proven | CENTRAL/employer and Ops: approve exact workload/cost/privacy/retention/SLO/RPO/RTO numbers or keep proposals nonbinding; then targeted positive and negative tests |
| ☐ P3M01-A09 | **Output:** ساخت Risk register و Dependency register; **Check:** dated approved decision, diagrams/risk register and explicit Gate owner | Foundation/employer; M00; employer scope decisions | NOT_VERIFIED · Employer-approved architecture/ADR/SLO Freeze not proven | CENTRAL/employer and Ops: approve exact workload/cost/privacy/retention/SLO/RPO/RTO numbers or keep proposals nonbinding; then targeted positive and negative tests |
| ☐ P3M01-A10 | **Output:** تعریف معیار Go/No-Go Launch.; **Check:** accepted version/readiness, smoke and rollback evidence | Foundation/employer; M00; employer scope decisions | NOT_VERIFIED · Employer-approved architecture/ADR/SLO Freeze not proven | CENTRAL/employer and Ops: approve exact workload/cost/privacy/retention/SLO/RPO/RTO numbers or keep proposals nonbinding; then targeted positive and negative tests |

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

### P3M11 · citation_and_attribution_delivery

| چک | فعالیت و معیار | مالک | شاهد ثبت‌شده در ماتریس | ورودی یا اقدام باقی‌مانده |
|---|---|---|---|---|
| ☐ P3M11-A01 | **Output:** تعریف Citation DTO مشترک Frontend/Backend; **Check:** run positive/negative Schema and version compatibility checks | API + UI; resolver pending; M10; NB23 | PARTIAL · Observed source list v1 is UNVERIFIED; real locator/author attribution not accepted; OWNER_L1_SOURCE_CI: https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/45081955496 (API61 L1 275 tests; not Mac); OWNER_L1_SOURCE_CI: https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/45108323298 (UI62 L1 Node115/Chromium synthetic) | PHASE2/ENGINE+API: approved release and genuine C018/C011/Locator/authority provenance; test source-specific author/editor/speaker and no-answer on approved dataset |
| ☐ P3M11-A02 | **Output:** ارسال URL و locator معتبر; **Check:** source-aware provenance and permission checks; no invented locator or attribution | API + UI; resolver pending; M10; NB23 | PARTIAL · Observed source list v1 is UNVERIFIED; real locator/author attribution not accepted; OWNER_L1_SOURCE_CI: https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/45081955496 (API61 L1 275 tests; not Mac); OWNER_L1_SOURCE_CI: https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/45108323298 (UI62 L1 Node115/Chromium synthetic) | PHASE2/ENGINE+API: approved release and genuine C018/C011/Locator/authority provenance; test source-specific author/editor/speaker and no-answer on approved dataset |
| ☐ P3M11-A03 | **Output:** ارسال `credited_author_name`; **Check:** validate real Auth/session, revoke and invalid-user cases after policy approval | API + UI; resolver pending; M10; NB23 | PARTIAL · Observed source list v1 is UNVERIFIED; real locator/author attribution not accepted; OWNER_L1_SOURCE_CI: https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/45081955496 (API61 L1 275 tests; not Mac); OWNER_L1_SOURCE_CI: https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/45108323298 (UI62 L1 Node115/Chromium synthetic) | PHASE2/ENGINE+API: approved release and genuine C018/C011/Locator/authority provenance; test source-specific author/editor/speaker and no-answer on approved dataset |
| ☐ P3M11-A04 | **Output:** ارسال جداگانه `editorial_supervisor_name`; **Check:** source-aware provenance and permission checks; no invented locator or attribution | API + UI; resolver pending; M10; NB23 | PARTIAL · Observed source list v1 is UNVERIFIED; real locator/author attribution not accepted; OWNER_L1_SOURCE_CI: https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/45081955496 (API61 L1 275 tests; not Mac); OWNER_L1_SOURCE_CI: https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/45108323298 (UI62 L1 Node115/Chromium synthetic) | PHASE2/ENGINE+API: approved release and genuine C018/C011/Locator/authority provenance; test source-specific author/editor/speaker and no-answer on approved dataset |
| ☐ P3M11-A05 | **Output:** ارسال `speaker_name` برای Transcript; **Check:** source-aware provenance and permission checks; no invented locator or attribution | API + UI; resolver pending; M10; NB23 | PARTIAL · Observed source list v1 is UNVERIFIED; real locator/author attribution not accepted; OWNER_L1_SOURCE_CI: https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/45081955496 (API61 L1 275 tests; not Mac); OWNER_L1_SOURCE_CI: https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/45108323298 (UI62 L1 Node115/Chromium synthetic) | PHASE2/ENGINE+API: approved release and genuine C018/C011/Locator/authority provenance; test source-specific author/editor/speaker and no-answer on approved dataset |
| ☐ P3M11-A06 | **Output:** ارسال `content_authority_type` و `attribution_status`; **Check:** validate real Auth/session, revoke and invalid-user cases after policy approval | API + UI; resolver pending; M10; NB23 | PARTIAL · Observed source list v1 is UNVERIFIED; real locator/author attribution not accepted; OWNER_L1_SOURCE_CI: https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/45081955496 (API61 L1 275 tests; not Mac); OWNER_L1_SOURCE_CI: https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/45108323298 (UI62 L1 Node115/Chromium synthetic) | PHASE2/ENGINE+API: approved release and genuine C018/C011/Locator/authority provenance; test source-specific author/editor/speaker and no-answer on approved dataset |
| ☐ P3M11-A07 | **Output:** نمایش Citation کنار Claim و فهرست منابع; **Check:** source-aware provenance and permission checks; no invented locator or attribution | API + UI; resolver pending; M10; NB23 | PARTIAL · Observed source list v1 is UNVERIFIED; real locator/author attribution not accepted; OWNER_L1_SOURCE_CI: https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/45081955496 (API61 L1 275 tests; not Mac); OWNER_L1_SOURCE_CI: https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/45108323298 (UI62 L1 Node115/Chromium synthetic) | PHASE2/ENGINE+API: approved release and genuine C018/C011/Locator/authority provenance; test source-specific author/editor/speaker and no-answer on approved dataset |
| ☐ P3M11-A08 | **Output:** Tooltip یا جزئیات «چرا این منبع استفاده شد»; **Check:** versioned artifact plus reproducible source-specific acceptance check and evidence | API + UI; resolver pending; M10; NB23 | PARTIAL · Observed source list v1 is UNVERIFIED; real locator/author attribution not accepted; OWNER_L1_SOURCE_CI: https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/45081955496 (API61 L1 275 tests; not Mac); OWNER_L1_SOURCE_CI: https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/45108323298 (UI62 L1 Node115/Chromium synthetic) | PHASE2/ENGINE+API: approved release and genuine C018/C011/Locator/authority provenance; test source-specific author/editor/speaker and no-answer on approved dataset |
| ☐ P3M11-A09 | **Output:** Broken link و Broken locator handling; **Check:** source-aware provenance and permission checks; no invented locator or attribution | API + UI; resolver pending; M10; NB23 | PARTIAL · Observed source list v1 is UNVERIFIED; real locator/author attribution not accepted; OWNER_L1_SOURCE_CI: https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/45081955496 (API61 L1 275 tests; not Mac); OWNER_L1_SOURCE_CI: https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/45108323298 (UI62 L1 Node115/Chromium synthetic) | PHASE2/ENGINE+API: approved release and genuine C018/C011/Locator/authority provenance; test source-specific author/editor/speaker and no-answer on approved dataset |
| ☐ P3M11-A10 | **Output:** تست Snapshot برای چهار نوع نمایش منبع; **Check:** positive/negative executable tests with reproducible result | API + UI; resolver pending; M10; NB23 | PARTIAL · Observed source list v1 is UNVERIFIED; real locator/author attribution not accepted; OWNER_L1_SOURCE_CI: https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/45081955496 (API61 L1 275 tests; not Mac); OWNER_L1_SOURCE_CI: https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/45108323298 (UI62 L1 Node115/Chromium synthetic) | PHASE2/ENGINE+API: approved release and genuine C018/C011/Locator/authority provenance; test source-specific author/editor/speaker and no-answer on approved dataset |
| ☐ P3M11-A11 | **Output:** تست ممنوعیت تبدیل سردبیر به نویسنده.; **Check:** versioned artifact plus reproducible source-specific acceptance check and evidence | API + UI; resolver pending; M10; NB23 | PARTIAL · Observed source list v1 is UNVERIFIED; real locator/author attribution not accepted; OWNER_L1_SOURCE_CI: https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/45081955496 (API61 L1 275 tests; not Mac); OWNER_L1_SOURCE_CI: https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/45108323298 (UI62 L1 Node115/Chromium synthetic) | PHASE2/ENGINE+API: approved release and genuine C018/C011/Locator/authority provenance; test source-specific author/editor/speaker and no-answer on approved dataset |

### P3M12 · safety_no_answer_and_policy

| چک | فعالیت و معیار | مالک | شاهد ثبت‌شده در ماتریس | ورودی یا اقدام باقی‌مانده |
|---|---|---|---|---|
| ☐ P3M12-A01 | **Output:** تفکیک آموزش مالی از توصیه سرمایه‌گذاری شخصی; **Check:** versioned artifact plus reproducible source-specific acceptance check and evidence | API; policy owner pending; M10; NB23 | NOT_VERIFIED · Safety corpus/threshold not accepted | PHASE2/ENGINE+API: approved release and genuine C018/C011/Locator/authority provenance; test source-specific author/editor/speaker and no-answer on approved dataset |
| ☐ P3M12-A02 | **Output:** تشخیص سؤال خارج از منبع یا مبهم; **Check:** versioned artifact plus reproducible source-specific acceptance check and evidence | API; policy owner pending; M10; NB23 | NOT_VERIFIED · Safety corpus/threshold not accepted | PHASE2/ENGINE+API: approved release and genuine C018/C011/Locator/authority provenance; test source-specific author/editor/speaker and no-answer on approved dataset |
| ☐ P3M12-A03 | **Output:** Clarification، Abstention و Safe completion; **Check:** versioned artifact plus reproducible source-specific acceptance check and evidence | API; policy owner pending; M10; NB23 | NOT_VERIFIED · Safety corpus/threshold not accepted | PHASE2/ENGINE+API: approved release and genuine C018/C011/Locator/authority provenance; test source-specific author/editor/speaker and no-answer on approved dataset |
| ☐ P3M12-A04 | **Output:** ممنوعیت ادعای قطعی بدون Citation; **Check:** source-aware provenance and permission checks; no invented locator or attribution | API; policy owner pending; M10; NB23 | NOT_VERIFIED · Safety corpus/threshold not accepted | PHASE2/ENGINE+API: approved release and genuine C018/C011/Locator/authority provenance; test source-specific author/editor/speaker and no-answer on approved dataset |
| ☐ P3M12-A05 | **Output:** Prompt injection defense برای ورودی و محتوای بازیابی‌شده; **Check:** distinct outcome/policy negative tests and measured calibration where required | API; policy owner pending; M10; NB23 | NOT_VERIFIED · Safety corpus/threshold not accepted | PHASE2/ENGINE+API: approved release and genuine C018/C011/Locator/authority provenance; test source-specific author/editor/speaker and no-answer on approved dataset |
| ☐ P3M12-A06 | **Output:** سیاست نمایش Disclaimer متناسب، نه ثابت و بی‌اثر; **Check:** distinct outcome/policy negative tests and measured calibration where required | API; policy owner pending; M10; NB23 | NOT_VERIFIED · Safety corpus/threshold not accepted | PHASE2/ENGINE+API: approved release and genuine C018/C011/Locator/authority provenance; test source-specific author/editor/speaker and no-answer on approved dataset |
| ☐ P3M12-A07 | **Output:** ثبت Policy version; **Check:** versioned artifact plus reproducible source-specific acceptance check and evidence | API; policy owner pending; M10; NB23 | NOT_VERIFIED · Safety corpus/threshold not accepted | PHASE2/ENGINE+API: approved release and genuine C018/C011/Locator/authority provenance; test source-specific author/editor/speaker and no-answer on approved dataset |
| ☐ P3M12-A08 | **Output:** ساخت Red-team corpus فارسی; **Check:** versioned artifact plus reproducible source-specific acceptance check and evidence | API; policy owner pending; M10; NB23 | NOT_VERIFIED · Safety corpus/threshold not accepted | PHASE2/ENGINE+API: approved release and genuine C018/C011/Locator/authority provenance; test source-specific author/editor/speaker and no-answer on approved dataset |
| ☐ P3M12-A09 | **Output:** تست درخواست افشای داده کاربر دیگر; **Check:** versioned artifact plus reproducible source-specific acceptance check and evidence | API; policy owner pending; M10; NB23 | NOT_VERIFIED · Safety corpus/threshold not accepted | PHASE2/ENGINE+API: approved release and genuine C018/C011/Locator/authority provenance; test source-specific author/editor/speaker and no-answer on approved dataset |
| ☐ P3M12-A10 | **Output:** تست توصیه خرید/فروش و پاسخ پرریسک.; **Check:** versioned artifact plus reproducible source-specific acceptance check and evidence | API; policy owner pending; M10; NB23 | NOT_VERIFIED · Safety corpus/threshold not accepted | PHASE2/ENGINE+API: approved release and genuine C018/C011/Locator/authority provenance; test source-specific author/editor/speaker and no-answer on approved dataset |

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

### P3M14 · web_chat_interface

| چک | فعالیت و معیار | مالک | شاهد ثبت‌شده در ماتریس | ورودی یا اقدام باقی‌مانده |
|---|---|---|---|---|
| ☐ P3M14-A01 | **Output:** صفحه ورود و مدیریت Session; **Check:** validate real Auth/session, revoke and invalid-user cases after policy approval | UI; M05; M11-M13 | PARTIAL · UI60 synthetic Chromium PASS prior owner CI; Mac real browser NOT_RUN; OWNER_L1_SOURCE_CI: https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/45108323298 (UI62 L1 Node115/Chromium synthetic) | API/UI/DB/Ops: separate real HTTPS/IdP + BFF signed mTLS + original T2 tests, C018 one OS spawn if authorized, two account Refresh/A-B/401 proof; sanitized receipt on exact SHA |
| ☐ P3M14-A02 | **Output:** فهرست گفت‌وگوهای خود کاربر; **Check:** versioned artifact plus reproducible source-specific acceptance check and evidence | UI; M05; M11-M13 | PARTIAL · UI60 synthetic Chromium PASS prior owner CI; Mac real browser NOT_RUN; OWNER_L1_SOURCE_CI: https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/45108323298 (UI62 L1 Node115/Chromium synthetic) | API/UI/DB/Ops: separate real HTTPS/IdP + BFF signed mTLS + original T2 tests, C018 one OS spawn if authorized, two account Refresh/A-B/401 proof; sanitized receipt on exact SHA |
| ☐ P3M14-A03 | **Output:** صفحه Chat واکنش‌گرا; **Check:** versioned artifact plus reproducible source-specific acceptance check and evidence | UI; M05; M11-M13 | PARTIAL · UI60 synthetic Chromium PASS prior owner CI; Mac real browser NOT_RUN; OWNER_L1_SOURCE_CI: https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/45108323298 (UI62 L1 Node115/Chromium synthetic) | API/UI/DB/Ops: separate real HTTPS/IdP + BFF signed mTLS + original T2 tests, C018 one OS spawn if authorized, two account Refresh/A-B/401 proof; sanitized receipt on exact SHA |
| ☐ P3M14-A04 | **Output:** Streaming پاسخ و امکان لغو; **Check:** replay/cancel/unknown/ordering tests, no claim of exactly-once provider execution | UI; M05; M11-M13 | PARTIAL · UI60 synthetic Chromium PASS prior owner CI; Mac real browser NOT_RUN; OWNER_L1_SOURCE_CI: https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/45108323298 (UI62 L1 Node115/Chromium synthetic) | API/UI/DB/Ops: separate real HTTPS/IdP + BFF signed mTLS + original T2 tests, C018 one OS spawn if authorized, two account Refresh/A-B/401 proof; sanitized receipt on exact SHA |
| ☐ P3M14-A05 | **Output:** نمایش Citation در سطح Claim; **Check:** source-aware provenance and permission checks; no invented locator or attribution | UI; M05; M11-M13 | PARTIAL · UI60 synthetic Chromium PASS prior owner CI; Mac real browser NOT_RUN; OWNER_L1_SOURCE_CI: https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/45108323298 (UI62 L1 Node115/Chromium synthetic) | API/UI/DB/Ops: separate real HTTPS/IdP + BFF signed mTLS + original T2 tests, C018 one OS spawn if authorized, two account Refresh/A-B/401 proof; sanitized receipt on exact SHA |
| ☐ P3M14-A06 | **Output:** نمایش صحیح نویسنده و سردبیر; **Check:** versioned artifact plus reproducible source-specific acceptance check and evidence | UI; M05; M11-M13 | PARTIAL · UI60 synthetic Chromium PASS prior owner CI; Mac real browser NOT_RUN; OWNER_L1_SOURCE_CI: https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/45108323298 (UI62 L1 Node115/Chromium synthetic) | API/UI/DB/Ops: separate real HTTPS/IdP + BFF signed mTLS + original T2 tests, C018 one OS spawn if authorized, two account Refresh/A-B/401 proof; sanitized receipt on exact SHA |
| ☐ P3M14-A07 | **Output:** نمایش Confidence به زبان قابل فهم; **Check:** distinct outcome/policy negative tests and measured calibration where required | UI; M05; M11-M13 | PARTIAL · UI60 synthetic Chromium PASS prior owner CI; Mac real browser NOT_RUN; OWNER_L1_SOURCE_CI: https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/45108323298 (UI62 L1 Node115/Chromium synthetic) | API/UI/DB/Ops: separate real HTTPS/IdP + BFF signed mTLS + original T2 tests, C018 one OS spawn if authorized, two account Refresh/A-B/401 proof; sanitized receipt on exact SHA |
| ☐ P3M14-A08 | **Output:** نمایش No-answer و سؤال روشن‌کننده; **Check:** distinct outcome/policy negative tests and measured calibration where required | UI; M05; M11-M13 | PARTIAL · UI60 synthetic Chromium PASS prior owner CI; Mac real browser NOT_RUN; OWNER_L1_SOURCE_CI: https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/45108323298 (UI62 L1 Node115/Chromium synthetic) | API/UI/DB/Ops: separate real HTTPS/IdP + BFF signed mTLS + original T2 tests, C018 one OS spawn if authorized, two account Refresh/A-B/401 proof; sanitized receipt on exact SHA |
| ☐ P3M14-A09 | **Output:** Error/Retry state بدون تکرار پیام; **Check:** replay/cancel/unknown/ordering tests, no claim of exactly-once provider execution | UI; M05; M11-M13 | PARTIAL · UI60 synthetic Chromium PASS prior owner CI; Mac real browser NOT_RUN; OWNER_L1_SOURCE_CI: https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/45108323298 (UI62 L1 Node115/Chromium synthetic) | API/UI/DB/Ops: separate real HTTPS/IdP + BFF signed mTLS + original T2 tests, C018 one OS spawn if authorized, two account Refresh/A-B/401 proof; sanitized receipt on exact SHA |
| ☐ P3M14-A10 | **Output:** Accessibility پایه Keyboard، focus، contrast و screen-reader label; **Check:** positive/negative executable tests with reproducible result | UI; M05; M11-M13 | PARTIAL · UI60 synthetic Chromium PASS prior owner CI; Mac real browser NOT_RUN; OWNER_L1_SOURCE_CI: https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/45108323298 (UI62 L1 Node115/Chromium synthetic) | API/UI/DB/Ops: separate real HTTPS/IdP + BFF signed mTLS + original T2 tests, C018 one OS spawn if authorized, two account Refresh/A-B/401 proof; sanitized receipt on exact SHA |
| ☐ P3M14-A11 | **Output:** تست موبایل و مرورگرهای هدف; **Check:** versioned artifact plus reproducible source-specific acceptance check and evidence | UI; M05; M11-M13 | PARTIAL · UI60 synthetic Chromium PASS prior owner CI; Mac real browser NOT_RUN; OWNER_L1_SOURCE_CI: https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/45108323298 (UI62 L1 Node115/Chromium synthetic) | API/UI/DB/Ops: separate real HTTPS/IdP + BFF signed mTLS + original T2 tests, C018 one OS spawn if authorized, two account Refresh/A-B/401 proof; sanitized receipt on exact SHA |
| ☐ P3M14-A12 | **Output:** ممنوعیت نمایش اطلاعات Debug یا Prompt داخلی.; **Check:** versioned artifact plus reproducible source-specific acceptance check and evidence | UI; M05; M11-M13 | PARTIAL · UI60 synthetic Chromium PASS prior owner CI; Mac real browser NOT_RUN; OWNER_L1_SOURCE_CI: https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/45108323298 (UI62 L1 Node115/Chromium synthetic) | API/UI/DB/Ops: separate real HTTPS/IdP + BFF signed mTLS + original T2 tests, C018 one OS spawn if authorized, two account Refresh/A-B/401 proof; sanitized receipt on exact SHA |

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

## Module 01 — `architecture_slo_and_scope_freeze`

### توضیح برای کارفرما

این مرحله تصمیم‌های مبهم را به قرارداد فنی قابل اندازه‌گیری تبدیل می‌کند تا وسط استقرار معماری یا Scope تغییر نکند.

### فعالیت‌ها

1. Freeze دامنه فاز ۳ و فهرست صریح موارد فاز ۴؛
2. ثبت Context diagram و Container diagram؛
3. تثبیت Stack با ADR؛
4. تعیین محیط‌های Local، Test، Staging و Production؛
5. تعیین DAU، پیام روزانه، Concurrent request و بودجه مصرف؛
6. تعیین SLO اولیه Availability، latency و error rate؛
7. تعیین RPO و RTO Backup؛
8. ثبت محل میزبانی، دامنه، TLS و محدودیت انتقال داده؛
9. ساخت Risk register و Dependency register؛
10. تعریف معیار Go/No-Go Launch.

### خروجی و Gate

`docs/phase3/architecture.md`، `docs/phase3/scope.md`، `docs/phase3/slo.md` و ADRها باید تأیید شوند. مقدار حل‌نشده‌ای که روی امنیت یا هزینه اثر دارد، Gate را Fail می‌کند.

### شاهد دانش فنی

Architecture decision record، SLO engineering، Capacity assumptions و Scope control.

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

## Module 11 — `citation_and_attribution_delivery`

### فعالیت‌ها

1. تعریف Citation DTO مشترک Frontend/Backend؛
2. ارسال URL و locator معتبر؛
3. ارسال `credited_author_name`؛
4. ارسال جداگانه `editorial_supervisor_name`؛
5. ارسال `speaker_name` برای Transcript؛
6. ارسال `content_authority_type` و `attribution_status`؛
7. نمایش Citation کنار Claim و فهرست منابع؛
8. Tooltip یا جزئیات «چرا این منبع استفاده شد»؛
9. Broken link و Broken locator handling؛
10. تست Snapshot برای چهار نوع نمایش منبع؛
11. تست ممنوعیت تبدیل سردبیر به نویسنده.

### Gate

Citation correctness و Attribution correctness باید Target فاز ۲ را حفظ کنند؛ نام حدسی و locator ساختگی صفر.

### شاهد دانش فنی

Claim-level citation delivery، Attribution-safe UI contract و Misattribution regression.

---

## Module 12 — `safety_no_answer_and_policy`

### فعالیت‌ها

1. تفکیک آموزش مالی از توصیه سرمایه‌گذاری شخصی؛
2. تشخیص سؤال خارج از منبع یا مبهم؛
3. Clarification، Abstention و Safe completion؛
4. ممنوعیت ادعای قطعی بدون Citation؛
5. Prompt injection defense برای ورودی و محتوای بازیابی‌شده؛
6. سیاست نمایش Disclaimer متناسب، نه ثابت و بی‌اثر؛
7. ثبت Policy version؛
8. ساخت Red-team corpus فارسی؛
9. تست درخواست افشای داده کاربر دیگر؛
10. تست توصیه خرید/فروش و پاسخ پرریسک.

### Gate

Critical policy violation در Suite مصوب باید صفر و No-answer F1 در محدوده پذیرش باشد.

### شاهد دانش فنی

Domain policy، Adversarial testing، calibrated abstention و prompt-injection controls.

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

## Module 14 — `web_chat_interface`

### توضیح برای کارفرما

این بخش رابط واقعی کاربر در سایت است؛ نه پنل مدیریتی فاز ۴. تمرکز روی پرسش، پاسخ مستند، تاریخچه و تجربه خطای قابل فهم است.

### فعالیت‌ها

1. صفحه ورود و مدیریت Session؛
2. فهرست گفت‌وگوهای خود کاربر؛
3. صفحه Chat واکنش‌گرا؛
4. Streaming پاسخ و امکان لغو؛
5. نمایش Citation در سطح Claim؛
6. نمایش صحیح نویسنده و سردبیر؛
7. نمایش Confidence به زبان قابل فهم؛
8. نمایش No-answer و سؤال روشن‌کننده؛
9. Error/Retry state بدون تکرار پیام؛
10. Accessibility پایه Keyboard، focus، contrast و screen-reader label؛
11. تست موبایل و مرورگرهای هدف؛
12. ممنوعیت نمایش اطلاعات Debug یا Prompt داخلی.

### Gate

مسیر Login→Chat→Citation→History روی مرورگرهای مصوب و موبایل PASS؛ خطای انتساب UI صفر.

### شاهد دانش فنی

Source-aware UX، streaming state machine، accessibility و resilient client behavior.

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

## ۳. بسته P3-01 - Product و Architecture Contract

### کارها

- تعریف User journey ثبت‌نام تا چت و مشاهده Source.
- تعریف نقش‌ها: user، support و admin محدود.
- API versioning، error model و idempotency policy.
- Threat model و data classification.
- ADR برای modular monolith، hosting، auth، queues و LLM gateway.

### خروجی

- docs/architecture/phase3.md
- docs/api/openapi.yaml
- docs/security/threat_model.md
- docs/adr/

### Gate

API، مدل اعتماد، مرز داده شخصی و مسئول هر سرویس تصویب شده باشد.

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

## ۷. بسته P3-05 - Web/PWA و تجربه چت

### صفحات پایه

- landing و توضیح مرز محصول.
- signup/login/consent.
- chat، conversation history و source drawer.
- account/privacy/export/delete.
- feedback و report answer.

### رفتار چت

- Streaming پاسخ و وضعیت retrieving/generating.
- Citation کنار Claim و صفحه جزئیات منبع.
- پیام واضح برای no-answer، ambiguity و safety refusal.
- نمایش اینکه پاسخ آموزشی است و چه منبعی استفاده شده.
- دسترس‌پذیری، RTL، موبایل و خطاهای بازیابی.

### Gate

مسیر اصلی روی موبایل و دسکتاپ، با network failure و refresh، بدون از دست رفتن یا اختلاط مکالمه کار کند.

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

## ۶. دستور کامل اجرا، Gateها، Crosswalk و پیوست تخصصی

# رابط کاربری UI_F3 | دستور مستقل برای چت تازه

## مبنای فعلی و ترتیب اجرای این نسخه

این فایل به‌تنهایی دستور کامل این چت است. مبنای شروع فعلی: **PR #65 / ac0e7159e6c7d673fb5607c0b7824a0981f7ceef؛ #62 خط مبنای مقایسه است.** شواهد قبلی و نسخه‌های ذکرشده در متن و پیوست برای مقایسه تاریخی‌اند. هر جا دستور قدیمی دربارهٔ نسخه یا تقدم کار با این بخش تفاوت دارد، همین بخش ملاک اجراست. تطبیق ۹۲→۱۰۵ Crosswalk در Foundation انجام شده و کار دوباره برای شمارش لازم نیست. شواهد جدید هر ردیف را به رجیستر اضافه کن.

از #65 SHA `ac0e7159e6c7d673fb5607c0b7824a0981f7ceef` ادامه بده. Owner fence و ۱۱۸ تست را baseline کن. ممیزی ۱۵۴ ردیف یا Crosswalk را از نو نساز. CSV 105 Foundation را مرجع قرار بده. تحویل خودت را روی همان کد موجود ادامه بده.

1. برای UI-03/05/06/11/12/14، یک ماتریس `ID → Changed path → Assert → CI witness → L2 gap` بساز. Account/Privacy و خروج را با رسید owner-bound و navigation واقعی، mixed-owner و late-response، switch session و چند tab به‌صورت دفاعی اعتبارسنجی کن. Read-only shell برای Consent/Feedback/حذف را در سه ردیف باز ثبت کن. رفتار موجود را فقط جایی تغییر بده که یک سناریوی جدیدِ مستند لازم دارد.
2. به Foundation فایل‌های UI65 و آزمون‌ها را بده و در نسخهٔ یکپارچه از صفر شمارش نکن. real HTTPS/OIDC + A/B و Refresh را به رسید مرورگر و API/DB وصل کن. Smoke مجاز باید same-T2 و همان Attempt، صفر POST و فرزند اضافه پس از Refresh و پاک‌شدن نمایش پس از 401/تغییر Owner را ثابت کند.
3. برای UI-04/09/13 با API و DB قرارداد نسخه‌دار بنویس: actor، precondition، خطا، idempotency، وضعیت پایانی، revoke، retention و export. پس از تصمیم مالک، جریان را کامل و تست کن. UI-07/08/10 را با fixtures نسخه‌دار و پس از تحویل producer با Citation معتبر، confidence، stream/cancel و خروجی واقعی ببند. UI-01/02 و سازگاری schema را به SHA یکپارچه و تصمیم معماری وصل کن. خروجی این نوبت باید پذیرش ردیفی یا مانع دقیق قابل رفع را نشان دهد.

## قالب ثابت برای گزارش بعدی

برای هر تیم `baseline SHA → tested SHA → PR HEAD → integrated/deployed SHA`، diff اجرایی، CI و محیط، IDهایی که شواهد/پذیرششان عوض شده، تعداد انجام‌شده و باقی‌مانده با همان مخرج، مانع و درخواست بعدی. گزارش تازه با آخرین وضعیت مقایسه می‌شود. از یک تست سبز یا یک فایل ممیزی افزایش خودکار پذیرش ثبت نکن.

## دستور کامل و معیارهای نقشه

این متن را به‌صورت کامل به چت اجرایی بده. معیارهای نهایی و مسیر ادامه پس از رفع وابستگی در خود فایل آمده‌اند.

## راه‌اندازی چت تازه و معماری‌ای که باید بشناسی

هدف یک رابط واقعی فارسی برای محصول چت چندکاربره است. Next.js/TypeScript مسئول Web/BFF است. Browser از BFF استفاده می‌کند. BFF به FastAPI امضاشده متصل است و Owner/session از نشست معتبر استنتاج می‌شود. History و T2 در PostgreSQL محصول‌اند. مشاهدات بازیابی مجموعه‌ای از شناسه‌ها در همان Attempt هستند. Answer و Citation واقعی قراردادهای بعد از پذیرش موتورند. UI نباید از روی طول لیست بازیابی هیچ پاسخ، لینک، نویسنده یا confidence بسازد.

۱. PR #62 و رسید CI آن را باز کن و به شاخهٔ ادامه وصل شو. کد قبلی را بازنویسی نکن. مسیرهای `apps/web/src/ui/product-chat.tsx`، `apps/web/src/history/{client,proxy}.ts`، `apps/web/src/auth/server/product-session.ts`، stylesheet، routeهای Login/Callback/History و test harness مرورگر را از Git شناسایی کن. نسخهٔ Node/package lock و فرمان lint/typecheck/build/browser را از کد و workflow همان شاخه بگیر. فایل تاریخچهٔ چت شرط شروع نیست.
۲. قبل از تغییر UI، یک خط مبنای دقیق از Navigation و state موجود بنویس: landing→login/consent→conversation list→chat→Send→pending→observations→Refresh→History→logout. جریان Account/privacy/delete و Feedback/Answer/Citation را به‌صورت قرارداد وابسته مشخص کن. Navigation موبایل و دسکتاپ، راهنمای قابلیت آموزشی و نشانه‌گذاری حالت‌های واقعی را در همان سبک فعلی کامل کن.
۳. ماشین حالت نمای محصول باید استقلال fetching، submitting، pending، recovering، ready، failed، unknown و signed-out را حفظ کند. بعد از owner/session change، 401، wrong Attempt یا دادهٔ بد، نمایش قبلی را پاک کند. درخواست دیررس پس از logout/revoke وارد UI نشود. دوبار کلیک، refresh روی همان conversation، قطع شبکه و بازکردن چند tab را در تست consumer پوشش بده. Trace داخلی و secret را در UI نیاور.
۴. بعد از قراردادهای آماده، UI نهایی باید وضعیت‌های صف/بازیابی/تولید، partial response، empty/clarification/refusal و cancel را از API دریافت کند. Source drawer، انواع سایت/کتاب/Transcript و چهار snapshot نقشه، اختلاف author/editor/speaker، locator خراب، permission source و کاراکترهای فارسی/لاتین را با fixture و سپس شاهد واقعی بسنج. معیارهای accessibility و نمودار حالت‌ها را با reference به UI-01…14 به handoff اضافه کن.
۵. پذیرش L2 روی SHA یکپارچه شامل Browser A و B واقعی، login/callback HTTPS، revoke/outstanding response، composer RTL موبایل و دسکتاپ، same-T2 refresh، history پایدار، و بعد از پذیرش موتور Answer و Citation قابل پیگیری است. در نبود محیط، سناریو و محتویات رسید را آماده کن و آزمون L1 کامل را بگیر. از مرورگر اجرای دوبارهٔ Runner انجام نده.

### وضعیت آغاز برای این چت

۱۱ از ۱۴ وظیفه بخشی از کد دارند (۲ کامل در سطح source، ۹ جزئی، ۳ بدون پیاده‌سازی)، پذیرش مقصد ۰/۱۴. CI #62 شاهد L1 است. ۵۶ ردیف دفتر UI از ۱۴ وظیفهٔ تخصصی و ۴۲ فعالیت مرتبط تشکیل شده است. پیوست ردیف‌های این فایل دامنه‌های وابستهٔ دیگری را هم برای جلوگیری از حذف کار پوشش می‌دهد. ردیف‌های مصرفی مالکیتشان طبق رجیستر باقی می‌ماند.

تو مجری UI فاز ۳ هستی. از Draft [#62](https://github.com/Shahbazi-Amir/RAG_finance_app/pull/62)، شاخه `agent/ui-f3-api61-completion-20261123`، HEAD `86bf2c2f1a0491d20496c704dbdfe3f9f1696d85` و API #61 `c02ba7896edb78febd2042f7afb1243f2a6aca34` ادامه بده. در #62 کد `05063c86204498ddf03c8f83507f181e51ae312c` و آخرین HEAD با CI `45108323298` گزارش شده‌اند: Typecheck، Lint، Build، Node 115/115 و Chromium مصنوعی موبایل/دسکتاپ سبز. #60 و #58 تاریخچه‌اند. ابتدا `coordination/tasks/AGENT-UI-01.md` و `coordination/handoffs/UI_F3_API61_COMPLETION.md` (۱۴ کار تخصصی + ۴۲ ردیف M03/M11/M14/M15) را بخوان، به Foundation برای بازپین #62 و بررسی هم‌پوشانی با API61 رسید بده. دامنهٔ تکمیلی M01/M05/M12/M13/M20/M21 و P3OP01/03/05/09 را از رجیستر reconcile کن.

- [ ] UI-01/02: Journey، landing و حدود محصول؛ معماری Frontend و قراردادهای versioned. تطابق client/proxy/امضای BFF/render با API #61 و انجام آزمون سازگاری روی SHA ادغام‌شده.
- [ ] UI-03/04: Login/Logout/Session/account/privacy با OIDC حقیقی؛ A/B، 401، فقدان و تغییر نسخهٔ Consent، ثبت و withdrawal طبق قرارداد محصول و DB. پس از revoke یا تغییر Owner، دادهٔ کش و پاسخ دیررس را پاک یا رد کن. Reset تازه تابع مسیر C2 است. ورود اولیه را مستقل پیش ببر.
- [ ] UI-05/06: History خصوصی و Pagination پایدار، فارسی RTL، موبایل/دسکتاپ و حالت‌های Loading/Empty/Error/Unknown. Refresh وضعیت و پوشش browser روی همان T2. عنوان مکالمه با حفظ پیام‌های اصلی. Retry بدون ایجاد پیام تکراری.
- [ ] UI-07/08: Outcomeهای Answer/Partial/No-answer/Clarification/Refusal/Error و Confidence null/معنادار. GET `api.retrieved_sources.v1` فقط بر اساس سه correlator اصلی و همان Attempt با پاک‌کردن نتیجهٔ نامعتبر یا کهنه. رتبه و ID مشاهده‌شده به‌صورت غیرقابل کلیک. Claim Citation، URL مجاز، page/time، نویسنده، سردبیر و گوینده فقط با محصول و resolver تأییدشده. تست چهار نمای منبع، locator خراب و جدایی نویسنده/سردبیر.
- [ ] UI-09/13: Feedback روی Answer معتبر، دستهٔ خطا و گزارش انتساب، dedupe و رسید ذخیره؛ حذف داده/حساب با تأیید، وضعیت واقعی، هم‌زمانی History، revoke و عدم بازگشت در Restore. Export طبق تصمیم جدا. قراردادهای تأییدنشده را صریحاً blocked ثبت کن و حالت‌های قابل تست را با برچسب fixture بساز.
- [ ] UI-10: قرارداد versioned event را با API تطبیق بده. ترتیب، partial، قطع ارتباط، بازیابی، لغو واقعی، race پایان و Cancel، refresh و عدم ارسال تکراری. وضعیت cancellation طبق producer.
- [ ] UI-11/12/14: RTL ترکیبی، Keyboard/focus/contrast/ARIA، موبایل و مرورگرهای مصوب؛ رندر ایمن متن، Markdown و URL، حذف debug/token/prompt. CI شامل typecheck/lint/build/Node/Chromium. در L2 واقعی تصویر sanitize شده، assertion مرورگر و هم‌بستگی با API/DB/OS را برای Login→Chat→observations→History تحویل بده. مسیر Answer/Citation واقعی را پس از اتصال مجاز جدا اثبات کن.

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

این پیوست 154 فعالیت مسئولیتی یا وابستگی مرتبط دارد. ستون مالک از رجیستر است. ردیف‌های مشترک برای تطبیق قرارداد و شواهد درج شده‌اند. مسئولیت اجرای کد طبق مالکیت تخصصی است. وضعیت شروع snapshot است. برای بسته‌شدن هر ردیف، شاهد مستقیم و تازه لازم را در دفتر اجرا درج کن.

### P3M01 — architecture_slo_and_scope_freeze

- [ ] **Independent Module Gate — NOT PASSED:** deliver module-level outcome. **Source:** modular plan Module 01 (line 166). **Owner:** foundation (human operational role pending where applicable). **Dependencies:** M00; employer scope decisions. **Output:** module deliverables as specified below. **Acceptance Gate:** `docs/phase3/architecture.md`، `docs/phase3/scope.md`، `docs/phase3/slo.md` و ADRها باید تأیید شوند. مقدار حل‌نشده‌ای که روی امنیت یا هزینه اثر دارد، Gate را Fail می‌کند.. **Status:** `planned`. **Implemented:** not verified. **Tested:** not run. **Supervisor approval:** pending. **Evidence:** `coordination/evidence/P3M01/` (future evidence only).

| ID | خروجی و معیار قبولی | مالک و وابستگی | وضعیت شروع / ورودی باقی‌مانده |
|---|---|---|---|
| P3M01-A01 | **Output:** Freeze دامنه فاز ۳ و فهرست صریح موارد فاز ۴; **Check:** dated approved decision, diagrams/risk register and explicit Gate owner | Foundation/employer; M00; employer scope decisions | NOT_VERIFIED / FREEZE_OR_ADR_EMPLOYER_APPROVAL_MISSING; original row criterion: Freeze دامنه فاز ۳ و فهرست صریح موارد فاز ۴; owner must deliver versioned artifact, SHA and target acceptance witness |
| P3M01-A02 | **Output:** ثبت Context diagram و Container diagram; **Check:** clean build and security scan in a separately authorized environment | Foundation/employer; M00; employer scope decisions | NOT_VERIFIED / FREEZE_OR_ADR_EMPLOYER_APPROVAL_MISSING; original row criterion: ثبت Context diagram و Container diagram; owner must deliver versioned artifact, SHA and target acceptance witness |
| P3M01-A03 | **Output:** تثبیت Stack با ADR; **Check:** ADR contains exact employer-approved Stack, but no Module01 Gate PASS. | Foundation/employer; M00; employer scope decisions | NOT_VERIFIED / FREEZE_OR_ADR_EMPLOYER_APPROVAL_MISSING; original row criterion: تثبیت Stack با ADR; owner must deliver versioned artifact, SHA and target acceptance witness |
| P3M01-A04 | **Output:** تعیین محیط‌های Local، Test، Staging و Production; **Check:** accepted version/readiness, smoke and rollback evidence | Foundation/employer; M00; employer scope decisions | NOT_VERIFIED / FREEZE_OR_ADR_EMPLOYER_APPROVAL_MISSING; original row criterion: تعیین محیط‌های Local، Test، Staging و Production; owner must deliver versioned artifact, SHA and target acceptance witness |
| P3M01-A05 | **Output:** تعیین DAU، پیام روزانه، Concurrent request و بودجه مصرف; **Check:** versioned artifact plus reproducible source-specific acceptance check and evidence | Foundation/employer; M00; employer scope decisions | NOT_VERIFIED / FREEZE_OR_ADR_EMPLOYER_APPROVAL_MISSING; original row criterion: تعیین DAU، پیام روزانه، Concurrent request و بودجه مصرف; owner must deliver versioned artifact, SHA and target acceptance witness |
| P3M01-A06 | **Output:** تعیین SLO اولیه Availability، latency و error rate; **Check:** resource/abuse and cross-user-cache negative tests, with approved bounds | Foundation/employer; M00; employer scope decisions | NOT_VERIFIED / FREEZE_OR_ADR_EMPLOYER_APPROVAL_MISSING; original row criterion: تعیین SLO اولیه Availability، latency و error rate; owner must deliver versioned artifact, SHA and target acceptance witness |
| P3M01-A07 | **Output:** تعیین RPO و RTO Backup; **Check:** reproducible migration/restore rollback plus consistency report in isolated test environment | Foundation/employer; M00; employer scope decisions | NOT_VERIFIED / FREEZE_OR_ADR_EMPLOYER_APPROVAL_MISSING; original row criterion: تعیین RPO و RTO Backup; owner must deliver versioned artifact, SHA and target acceptance witness |
| P3M01-A08 | **Output:** ثبت محل میزبانی، دامنه، TLS و محدودیت انتقال داده; **Check:** versioned artifact plus reproducible source-specific acceptance check and evidence | Foundation/employer; M00; employer scope decisions | NOT_VERIFIED / FREEZE_OR_ADR_EMPLOYER_APPROVAL_MISSING; original row criterion: ثبت محل میزبانی، دامنه، TLS و محدودیت انتقال داده; owner must deliver versioned artifact, SHA and target acceptance witness |
| P3M01-A09 | **Output:** ساخت Risk register و Dependency register; **Check:** dated approved decision, diagrams/risk register and explicit Gate owner | Foundation/employer; M00; employer scope decisions | NOT_VERIFIED / FREEZE_OR_ADR_EMPLOYER_APPROVAL_MISSING; original row criterion: ساخت Risk register و Dependency register; owner must deliver versioned artifact, SHA and target acceptance witness |
| P3M01-A10 | **Output:** تعریف معیار Go/No-Go Launch.; **Check:** accepted version/readiness, smoke and rollback evidence | Foundation/employer; M00; employer scope decisions | NOT_VERIFIED / FREEZE_OR_ADR_EMPLOYER_APPROVAL_MISSING; original row criterion: تعریف معیار Go/No-Go Launch.; owner must deliver versioned artifact, SHA and target acceptance witness |

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

### P3M11 — citation_and_attribution_delivery

- [ ] **Independent Module Gate — NOT PASSED:** deliver module-level outcome. **Source:** modular plan Module 11 (line 451). **Owner:** api. **Dependencies:** M10; NB23. **Output:** module deliverables as specified below. **Acceptance Gate:** Citation correctness و Attribution correctness باید Target فاز ۲ را حفظ کنند؛ نام حدسی و locator ساختگی صفر.. **Status:** `planned`. **Implemented:** not verified. **Tested:** not run. **Supervisor approval:** pending. **Evidence:** `coordination/evidence/P3M11/` (future evidence only).

| ID | خروجی و معیار قبولی | مالک و وابستگی | وضعیت شروع / ورودی باقی‌مانده |
|---|---|---|---|
| P3M11-A01 | **Output:** تعریف Citation DTO مشترک Frontend/Backend; **Check:** run positive/negative Schema and version compatibility checks | API + UI; resolver pending; M10; NB23 | PARTIAL / REAL_SAME_ATTEMPT_LOCATOR_VALIDATION; original row criterion: تعریف Citation DTO مشترک Frontend/Backend; owner must deliver versioned artifact, SHA and target acceptance witness |
| P3M11-A02 | **Output:** ارسال URL و locator معتبر; **Check:** source-aware provenance and permission checks; no invented locator or attribution | API + UI; resolver pending; M10; NB23 | PARTIAL / REAL_SAME_ATTEMPT_LOCATOR_VALIDATION; original row criterion: ارسال URL و locator معتبر; owner must deliver versioned artifact, SHA and target acceptance witness |
| P3M11-A03 | **Output:** ارسال `credited_author_name`; **Check:** validate real Auth/session, revoke and invalid-user cases after policy approval | API + UI; resolver pending; M10; NB23 | PARTIAL / REAL_SAME_ATTEMPT_LOCATOR_VALIDATION; original row criterion: ارسال `credited_author_name`; owner must deliver versioned artifact, SHA and target acceptance witness |
| P3M11-A04 | **Output:** ارسال جداگانه `editorial_supervisor_name`; **Check:** source-aware provenance and permission checks; no invented locator or attribution | API + UI; resolver pending; M10; NB23 | PARTIAL / REAL_SAME_ATTEMPT_LOCATOR_VALIDATION; original row criterion: ارسال جداگانه `editorial_supervisor_name`; owner must deliver versioned artifact, SHA and target acceptance witness |
| P3M11-A05 | **Output:** ارسال `speaker_name` برای Transcript; **Check:** source-aware provenance and permission checks; no invented locator or attribution | API + UI; resolver pending; M10; NB23 | PARTIAL / REAL_SAME_ATTEMPT_LOCATOR_VALIDATION; original row criterion: ارسال `speaker_name` برای Transcript; owner must deliver versioned artifact, SHA and target acceptance witness |
| P3M11-A06 | **Output:** ارسال `content_authority_type` و `attribution_status`; **Check:** validate real Auth/session, revoke and invalid-user cases after policy approval | API + UI; resolver pending; M10; NB23 | PARTIAL / REAL_SAME_ATTEMPT_LOCATOR_VALIDATION; original row criterion: ارسال `content_authority_type` و `attribution_status`; owner must deliver versioned artifact, SHA and target acceptance witness |
| P3M11-A07 | **Output:** نمایش Citation کنار Claim و فهرست منابع; **Check:** source-aware provenance and permission checks; no invented locator or attribution | API + UI; resolver pending; M10; NB23 | PARTIAL / REAL_SAME_ATTEMPT_LOCATOR_VALIDATION; original row criterion: نمایش Citation کنار Claim و فهرست منابع; owner must deliver versioned artifact, SHA and target acceptance witness |
| P3M11-A08 | **Output:** Tooltip یا جزئیات «چرا این منبع استفاده شد»; **Check:** versioned artifact plus reproducible source-specific acceptance check and evidence | API + UI; resolver pending; M10; NB23 | PARTIAL / REAL_SAME_ATTEMPT_LOCATOR_VALIDATION; original row criterion: Tooltip یا جزئیات «چرا این منبع استفاده شد»; owner must deliver versioned artifact, SHA and target acceptance witness |
| P3M11-A09 | **Output:** Broken link و Broken locator handling; **Check:** source-aware provenance and permission checks; no invented locator or attribution | API + UI; resolver pending; M10; NB23 | PARTIAL / REAL_SAME_ATTEMPT_LOCATOR_VALIDATION; original row criterion: Broken link و Broken locator handling; owner must deliver versioned artifact, SHA and target acceptance witness |
| P3M11-A10 | **Output:** تست Snapshot برای چهار نوع نمایش منبع; **Check:** positive/negative executable tests with reproducible result | API + UI; resolver pending; M10; NB23 | PARTIAL / REAL_SAME_ATTEMPT_LOCATOR_VALIDATION; original row criterion: تست Snapshot برای چهار نوع نمایش منبع; owner must deliver versioned artifact, SHA and target acceptance witness |
| P3M11-A11 | **Output:** تست ممنوعیت تبدیل سردبیر به نویسنده.; **Check:** versioned artifact plus reproducible source-specific acceptance check and evidence | API + UI; resolver pending; M10; NB23 | PARTIAL / REAL_SAME_ATTEMPT_LOCATOR_VALIDATION; original row criterion: تست ممنوعیت تبدیل سردبیر به نویسنده.; owner must deliver versioned artifact, SHA and target acceptance witness |

### P3M12 — safety_no_answer_and_policy

- [ ] **Independent Module Gate — NOT PASSED:** deliver module-level outcome. **Source:** modular plan Module 12 (line 477). **Owner:** api. **Dependencies:** M10; NB23. **Output:** module deliverables as specified below. **Acceptance Gate:** Critical policy violation در Suite مصوب باید صفر و No-answer F1 در محدوده پذیرش باشد.. **Status:** `planned`. **Implemented:** not verified. **Tested:** not run. **Supervisor approval:** pending. **Evidence:** `coordination/evidence/P3M12/` (future evidence only).

| ID | خروجی و معیار قبولی | مالک و وابستگی | وضعیت شروع / ورودی باقی‌مانده |
|---|---|---|---|
| P3M12-A01 | **Output:** تفکیک آموزش مالی از توصیه سرمایه‌گذاری شخصی; **Check:** versioned artifact plus reproducible source-specific acceptance check and evidence | API; policy owner pending; M10; NB23 | NOT_VERIFIED / APPROVED_POLICY_RED_TEAM_CORPUS_AND_EVAL; original row criterion: تفکیک آموزش مالی از توصیه سرمایه‌گذاری شخصی; owner must deliver versioned artifact, SHA and target acceptance witness |
| P3M12-A02 | **Output:** تشخیص سؤال خارج از منبع یا مبهم; **Check:** versioned artifact plus reproducible source-specific acceptance check and evidence | API; policy owner pending; M10; NB23 | NOT_VERIFIED / APPROVED_POLICY_RED_TEAM_CORPUS_AND_EVAL; original row criterion: تشخیص سؤال خارج از منبع یا مبهم; owner must deliver versioned artifact, SHA and target acceptance witness |
| P3M12-A03 | **Output:** Clarification، Abstention و Safe completion; **Check:** versioned artifact plus reproducible source-specific acceptance check and evidence | API; policy owner pending; M10; NB23 | NOT_VERIFIED / APPROVED_POLICY_RED_TEAM_CORPUS_AND_EVAL; original row criterion: Clarification، Abstention و Safe completion; owner must deliver versioned artifact, SHA and target acceptance witness |
| P3M12-A04 | **Output:** ممنوعیت ادعای قطعی بدون Citation; **Check:** source-aware provenance and permission checks; no invented locator or attribution | API; policy owner pending; M10; NB23 | NOT_VERIFIED / APPROVED_POLICY_RED_TEAM_CORPUS_AND_EVAL; original row criterion: ممنوعیت ادعای قطعی بدون Citation; owner must deliver versioned artifact, SHA and target acceptance witness |
| P3M12-A05 | **Output:** Prompt injection defense برای ورودی و محتوای بازیابی‌شده; **Check:** distinct outcome/policy negative tests and measured calibration where required | API; policy owner pending; M10; NB23 | NOT_VERIFIED / APPROVED_POLICY_RED_TEAM_CORPUS_AND_EVAL; original row criterion: Prompt injection defense برای ورودی و محتوای بازیابی‌شده; owner must deliver versioned artifact, SHA and target acceptance witness |
| P3M12-A06 | **Output:** سیاست نمایش Disclaimer متناسب، نه ثابت و بی‌اثر; **Check:** distinct outcome/policy negative tests and measured calibration where required | API; policy owner pending; M10; NB23 | NOT_VERIFIED / APPROVED_POLICY_RED_TEAM_CORPUS_AND_EVAL; original row criterion: سیاست نمایش Disclaimer متناسب، نه ثابت و بی‌اثر; owner must deliver versioned artifact, SHA and target acceptance witness |
| P3M12-A07 | **Output:** ثبت Policy version; **Check:** versioned artifact plus reproducible source-specific acceptance check and evidence | API; policy owner pending; M10; NB23 | NOT_VERIFIED / APPROVED_POLICY_RED_TEAM_CORPUS_AND_EVAL; original row criterion: ثبت Policy version; owner must deliver versioned artifact, SHA and target acceptance witness |
| P3M12-A08 | **Output:** ساخت Red-team corpus فارسی; **Check:** versioned artifact plus reproducible source-specific acceptance check and evidence | API; policy owner pending; M10; NB23 | NOT_VERIFIED / APPROVED_POLICY_RED_TEAM_CORPUS_AND_EVAL; original row criterion: ساخت Red-team corpus فارسی; owner must deliver versioned artifact, SHA and target acceptance witness |
| P3M12-A09 | **Output:** تست درخواست افشای داده کاربر دیگر; **Check:** versioned artifact plus reproducible source-specific acceptance check and evidence | API; policy owner pending; M10; NB23 | NOT_VERIFIED / APPROVED_POLICY_RED_TEAM_CORPUS_AND_EVAL; original row criterion: تست درخواست افشای داده کاربر دیگر; owner must deliver versioned artifact, SHA and target acceptance witness |
| P3M12-A10 | **Output:** تست توصیه خرید/فروش و پاسخ پرریسک.; **Check:** versioned artifact plus reproducible source-specific acceptance check and evidence | API; policy owner pending; M10; NB23 | NOT_VERIFIED / APPROVED_POLICY_RED_TEAM_CORPUS_AND_EVAL; original row criterion: تست توصیه خرید/فروش و پاسخ پرریسک.; owner must deliver versioned artifact, SHA and target acceptance witness |

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

### P3M14 — web_chat_interface

- [ ] **Independent Module Gate — NOT PASSED:** deliver module-level outcome. **Source:** modular plan Module 14 (line 542). **Owner:** ui. **Dependencies:** M05; M11-M13. **Output:** module deliverables as specified below. **Acceptance Gate:** مسیر Login→Chat→Citation→History روی مرورگرهای مصوب و موبایل PASS؛ خطای انتساب UI صفر.. **Status:** `planned`. **Implemented:** not verified. **Tested:** not run. **Supervisor approval:** pending. **Evidence:** `coordination/evidence/P3M14/` (future evidence only).

| ID | خروجی و معیار قبولی | مالک و وابستگی | وضعیت شروع / ورودی باقی‌مانده |
|---|---|---|---|
| P3M14-A01 | **Output:** صفحه ورود و مدیریت Session; **Check:** validate real Auth/session, revoke and invalid-user cases after policy approval | UI; M05; M11-M13 | PARTIAL / MAC_BROWSER_HTTPS_OIDC_C018; original row criterion: صفحه ورود و مدیریت Session; owner must deliver versioned artifact, SHA and target acceptance witness |
| P3M14-A02 | **Output:** فهرست گفت‌وگوهای خود کاربر; **Check:** versioned artifact plus reproducible source-specific acceptance check and evidence | UI; M05; M11-M13 | PARTIAL / MAC_BROWSER_HTTPS_OIDC_C018; original row criterion: فهرست گفت‌وگوهای خود کاربر; owner must deliver versioned artifact, SHA and target acceptance witness |
| P3M14-A03 | **Output:** صفحه Chat واکنش‌گرا; **Check:** versioned artifact plus reproducible source-specific acceptance check and evidence | UI; M05; M11-M13 | PARTIAL / MAC_BROWSER_HTTPS_OIDC_C018; original row criterion: صفحه Chat واکنش‌گرا; owner must deliver versioned artifact, SHA and target acceptance witness |
| P3M14-A04 | **Output:** Streaming پاسخ و امکان لغو; **Check:** replay/cancel/unknown/ordering tests, no claim of exactly-once provider execution | UI; M05; M11-M13 | PARTIAL / MAC_BROWSER_HTTPS_OIDC_C018; original row criterion: Streaming پاسخ و امکان لغو; owner must deliver versioned artifact, SHA and target acceptance witness |
| P3M14-A05 | **Output:** نمایش Citation در سطح Claim; **Check:** source-aware provenance and permission checks; no invented locator or attribution | UI; M05; M11-M13 | PARTIAL / MAC_BROWSER_HTTPS_OIDC_C018; original row criterion: نمایش Citation در سطح Claim; owner must deliver versioned artifact, SHA and target acceptance witness |
| P3M14-A06 | **Output:** نمایش صحیح نویسنده و سردبیر; **Check:** versioned artifact plus reproducible source-specific acceptance check and evidence | UI; M05; M11-M13 | PARTIAL / MAC_BROWSER_HTTPS_OIDC_C018; original row criterion: نمایش صحیح نویسنده و سردبیر; owner must deliver versioned artifact, SHA and target acceptance witness |
| P3M14-A07 | **Output:** نمایش Confidence به زبان قابل فهم; **Check:** distinct outcome/policy negative tests and measured calibration where required | UI; M05; M11-M13 | PARTIAL / MAC_BROWSER_HTTPS_OIDC_C018; original row criterion: نمایش Confidence به زبان قابل فهم; owner must deliver versioned artifact, SHA and target acceptance witness |
| P3M14-A08 | **Output:** نمایش No-answer و سؤال روشن‌کننده; **Check:** distinct outcome/policy negative tests and measured calibration where required | UI; M05; M11-M13 | PARTIAL / MAC_BROWSER_HTTPS_OIDC_C018; original row criterion: نمایش No-answer و سؤال روشن‌کننده; owner must deliver versioned artifact, SHA and target acceptance witness |
| P3M14-A09 | **Output:** Error/Retry state بدون تکرار پیام; **Check:** replay/cancel/unknown/ordering tests, no claim of exactly-once provider execution | UI; M05; M11-M13 | PARTIAL / MAC_BROWSER_HTTPS_OIDC_C018; original row criterion: Error/Retry state بدون تکرار پیام; owner must deliver versioned artifact, SHA and target acceptance witness |
| P3M14-A10 | **Output:** Accessibility پایه Keyboard، focus، contrast و screen-reader label; **Check:** positive/negative executable tests with reproducible result | UI; M05; M11-M13 | PARTIAL / MAC_BROWSER_HTTPS_OIDC_C018; original row criterion: Accessibility پایه Keyboard، focus، contrast و screen-reader label; owner must deliver versioned artifact, SHA and target acceptance witness |
| P3M14-A11 | **Output:** تست موبایل و مرورگرهای هدف; **Check:** versioned artifact plus reproducible source-specific acceptance check and evidence | UI; M05; M11-M13 | PARTIAL / MAC_BROWSER_HTTPS_OIDC_C018; original row criterion: تست موبایل و مرورگرهای هدف; owner must deliver versioned artifact, SHA and target acceptance witness |
| P3M14-A12 | **Output:** ممنوعیت نمایش اطلاعات Debug یا Prompt داخلی.; **Check:** versioned artifact plus reproducible source-specific acceptance check and evidence | UI; M05; M11-M13 | PARTIAL / MAC_BROWSER_HTTPS_OIDC_C018; original row criterion: ممنوعیت نمایش اطلاعات Debug یا Prompt داخلی.; owner must deliver versioned artifact, SHA and target acceptance witness |

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

80 شناسهٔ مرتبط از Crosswalk رسمی آمده است. الزامات هر بسته را همراه Gate و بخش‌های غیرشماره‌ای نقشه مرور کن. لینک خط‌های اصلی به نسخهٔ خواندنی مبنا اشاره می‌کنند.

| شناسه | الزام | فعالیت متناظر | وضعیت اولیه رجیستر |
|---|---|---|---|
| **P3OP01-R01**, §کارها | [L44](https://github.com/Shahbazi-Amir/RAG_finance/blob/7c74783c3dcda897b010ba9ea358d113f172ed1f/data/Road_Maps/RAG_finance_phase3_operational_roadmap.md#L44): تعریف User journey ثبت‌نام تا چت و مشاهده Source. | `P3M14-A03`, `P3M01-A01` | Mapped only; required execution and the source Gate still unverified. |
| **P3OP01-R02**, §کارها | [L45](https://github.com/Shahbazi-Amir/RAG_finance/blob/7c74783c3dcda897b010ba9ea358d113f172ed1f/data/Road_Maps/RAG_finance_phase3_operational_roadmap.md#L45): تعریف نقش‌ها: user، support و admin محدود. | `P3M05-A01`, `P3M06-A02` | **GAP/CONFLICT, OPEN (non-counting):** support/admin role scope is not explicit in module activities; Auth/authorization approval required. |
| **P3OP01-R03**, §کارها | [L46](https://github.com/Shahbazi-Amir/RAG_finance/blob/7c74783c3dcda897b010ba9ea358d113f172ed1f/data/Road_Maps/RAG_finance_phase3_operational_roadmap.md#L46): API versioning، error model و idempotency policy. | `P3M03-A02`, `P3M03-A04`, `P3M10-A10` | Mapped only; required execution and the source Gate still unverified. |
| **P3OP01-R04**, §کارها | [L47](https://github.com/Shahbazi-Amir/RAG_finance/blob/7c74783c3dcda897b010ba9ea358d113f172ed1f/data/Road_Maps/RAG_finance_phase3_operational_roadmap.md#L47): Threat model و data classification. | `P3M21-A01`, `P3M01-A09` | Mapped only; required execution and the source Gate still unverified. |
| **P3OP01-R05**, §کارها | [L48](https://github.com/Shahbazi-Amir/RAG_finance/blob/7c74783c3dcda897b010ba9ea358d113f172ed1f/data/Road_Maps/RAG_finance_phase3_operational_roadmap.md#L48): ADR برای modular monolith، hosting، auth، queues و LLM gateway. | `P3M01-A03`, `P3M09-A01`, `P3M18-A09` | Mapped only; required execution and the source Gate still unverified. |
| **P3OP01-R06**, §خروجی | [L52](https://github.com/Shahbazi-Amir/RAG_finance/blob/7c74783c3dcda897b010ba9ea358d113f172ed1f/data/Road_Maps/RAG_finance_phase3_operational_roadmap.md#L52): docs/architecture/phase3.md | `P3M01-A02` | Mapped only; required execution and the source Gate still unverified. |
| **P3OP01-R07**, §خروجی | [L53](https://github.com/Shahbazi-Amir/RAG_finance/blob/7c74783c3dcda897b010ba9ea358d113f172ed1f/data/Road_Maps/RAG_finance_phase3_operational_roadmap.md#L53): docs/api/openapi.yaml | `P3M13-A01` | Mapped only; required execution and the source Gate still unverified. |
| **P3OP01-R08**, §خروجی | [L54](https://github.com/Shahbazi-Amir/RAG_finance/blob/7c74783c3dcda897b010ba9ea358d113f172ed1f/data/Road_Maps/RAG_finance_phase3_operational_roadmap.md#L54): docs/security/threat_model.md | `P3M21-A01` | Mapped only; required execution and the source Gate still unverified. |
| **P3OP01-R09**, §خروجی | [L55](https://github.com/Shahbazi-Amir/RAG_finance/blob/7c74783c3dcda897b010ba9ea358d113f172ed1f/data/Road_Maps/RAG_finance_phase3_operational_roadmap.md#L55): docs/adr/ | `P3M01-A03` | Mapped only; required execution and the source Gate still unverified. |
| **P3OP02-R01**, §موجودیت‌های فعال | [L65](https://github.com/Shahbazi-Amir/RAG_finance/blob/7c74783c3dcda897b010ba9ea358d113f172ed1f/data/Road_Maps/RAG_finance_phase3_operational_roadmap.md#L65): users، identities، sessions و consents. | `P3M04-A01`, `P3M05-A01` | Mapped only; required execution and the source Gate still unverified. |
| **P3OP02-R03**, §موجودیت‌های فعال | [L67](https://github.com/Shahbazi-Amir/RAG_finance/blob/7c74783c3dcda897b010ba9ea358d113f172ed1f/data/Road_Maps/RAG_finance_phase3_operational_roadmap.md#L67): retrieval_runs، model_runs و feedback. | `P3M04-A05`, `P3M10-A08`, `P3M15-A05` | Mapped only; required execution and the source Gate still unverified. |
| **P3OP02-R04**, §موجودیت‌های فعال | [L68](https://github.com/Shahbazi-Amir/RAG_finance/blob/7c74783c3dcda897b010ba9ea358d113f172ed1f/data/Road_Maps/RAG_finance_phase3_operational_roadmap.md#L68): audit_events، security_events و deletion_requests. | `P3M04-A01`, `P3M16-A05`, `P3M15-A04` | Mapped only; required execution and the source Gate still unverified. |
| **P3OP02-R08**, §قواعد | [L78](https://github.com/Shahbazi-Amir/RAG_finance/blob/7c74783c3dcda897b010ba9ea358d113f172ed1f/data/Road_Maps/RAG_finance_phase3_operational_roadmap.md#L78): همه داده‌های کاربر user_id یا tenant_id داشته باشند. | `P3M04-A03`, `P3M06-A01` | Mapped only; required execution and the source Gate still unverified. |
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
| **P3OP05-R01**, §صفحات پایه | [L139](https://github.com/Shahbazi-Amir/RAG_finance/blob/7c74783c3dcda897b010ba9ea358d113f172ed1f/data/Road_Maps/RAG_finance_phase3_operational_roadmap.md#L139): landing و توضیح مرز محصول. | `P3M01-A01`, `P3M14-A03` | **GAP/CONFLICT, OPEN (non-counting):** landing page/product boundaries not listed as separate M14 numbered activity. |
| **P3OP05-R02**, §صفحات پایه | [L140](https://github.com/Shahbazi-Amir/RAG_finance/blob/7c74783c3dcda897b010ba9ea358d113f172ed1f/data/Road_Maps/RAG_finance_phase3_operational_roadmap.md#L140): signup/login/consent. | `P3M14-A01`, `P3M05-A01` | Mapped only; required execution and the source Gate still unverified. |
| **P3OP05-R03**, §صفحات پایه | [L141](https://github.com/Shahbazi-Amir/RAG_finance/blob/7c74783c3dcda897b010ba9ea358d113f172ed1f/data/Road_Maps/RAG_finance_phase3_operational_roadmap.md#L141): chat، conversation history و source drawer. | `P3M14-A03`, `P3M14-A05`, `P3M15-A03` | Mapped only; required execution and the source Gate still unverified. |
| **P3OP05-R04**, §صفحات پایه | [L142](https://github.com/Shahbazi-Amir/RAG_finance/blob/7c74783c3dcda897b010ba9ea358d113f172ed1f/data/Road_Maps/RAG_finance_phase3_operational_roadmap.md#L142): account/privacy/export/delete. | `P3M14-A01`, `P3M15-A04`, `P3M21-A08` | **GAP/CONFLICT, OPEN (non-counting):** Export operationally expected, while M15-A08 requires Scope approval; deletion independent. |
| **P3OP05-R05**, §صفحات پایه | [L143](https://github.com/Shahbazi-Amir/RAG_finance/blob/7c74783c3dcda897b010ba9ea358d113f172ed1f/data/Road_Maps/RAG_finance_phase3_operational_roadmap.md#L143): feedback و report answer. | `P3M15-A05`, `P3M14-A03` | Mapped only; required execution and the source Gate still unverified. |
| **P3OP05-R06**, §رفتار چت | [L147](https://github.com/Shahbazi-Amir/RAG_finance/blob/7c74783c3dcda897b010ba9ea358d113f172ed1f/data/Road_Maps/RAG_finance_phase3_operational_roadmap.md#L147): Streaming پاسخ و وضعیت retrieving/generating. | `P3M14-A04`, `P3M13-A05` | Mapped only; required execution and the source Gate still unverified. |
| **P3OP05-R07**, §رفتار چت | [L148](https://github.com/Shahbazi-Amir/RAG_finance/blob/7c74783c3dcda897b010ba9ea358d113f172ed1f/data/Road_Maps/RAG_finance_phase3_operational_roadmap.md#L148): Citation کنار Claim و صفحه جزئیات منبع. | `P3M14-A05`, `P3M11-A07` | Mapped only; required execution and the source Gate still unverified. |
| **P3OP05-R08**, §رفتار چت | [L149](https://github.com/Shahbazi-Amir/RAG_finance/blob/7c74783c3dcda897b010ba9ea358d113f172ed1f/data/Road_Maps/RAG_finance_phase3_operational_roadmap.md#L149): پیام واضح برای no-answer، ambiguity و safety refusal. | `P3M14-A08`, `P3M12-A03` | Mapped only; required execution and the source Gate still unverified. |
| **P3OP05-R09**, §رفتار چت | [L150](https://github.com/Shahbazi-Amir/RAG_finance/blob/7c74783c3dcda897b010ba9ea358d113f172ed1f/data/Road_Maps/RAG_finance_phase3_operational_roadmap.md#L150): نمایش اینکه پاسخ آموزشی است و چه منبعی استفاده شده. | `P3M12-A06`, `P3M14-A05` | Mapped only; required execution and the source Gate still unverified. |
| **P3OP05-R10**, §رفتار چت | [L151](https://github.com/Shahbazi-Amir/RAG_finance/blob/7c74783c3dcda897b010ba9ea358d113f172ed1f/data/Road_Maps/RAG_finance_phase3_operational_roadmap.md#L151): دسترس‌پذیری، RTL، موبایل و خطاهای بازیابی. | `P3M14-A10`, `P3M14-A11`, `P3M14-A09` | Mapped only; required execution and the source Gate still unverified. |
| **P3OP06-R03**, §اجزا | [L163](https://github.com/Shahbazi-Amir/RAG_finance/blob/7c74783c3dcda897b010ba9ea358d113f172ed1f/data/Road_Maps/RAG_finance_phase3_operational_roadmap.md#L163): Reverse proxy، TLS، domain و secure headers. | `P3M18-A04`, `P3M21-A05` | Mapped only; required execution and the source Gate still unverified. |
| **P3OP06-R04**, §اجزا | [L164](https://github.com/Shahbazi-Amir/RAG_finance/blob/7c74783c3dcda897b010ba9ea358d113f172ed1f/data/Road_Maps/RAG_finance_phase3_operational_roadmap.md#L164): environment separation برای local/staging/production. | `P3M01-A04`, `P3M18-A09` | Mapped only; required execution and the source Gate still unverified. |
| **P3OP06-R09**, §Release | [L172](https://github.com/Shahbazi-Amir/RAG_finance/blob/7c74783c3dcda897b010ba9ea358d113f172ed1f/data/Road_Maps/RAG_finance_phase3_operational_roadmap.md#L172): Infrastructure/Deployment runbook. | `P3M18-A09`, `P3M25-A07` | Mapped only; required execution and the source Gate still unverified. |
| **P3OP06-R10**, §Release | [L173](https://github.com/Shahbazi-Amir/RAG_finance/blob/7c74783c3dcda897b010ba9ea358d113f172ed1f/data/Road_Maps/RAG_finance_phase3_operational_roadmap.md#L173): Release manifest شامل app و RAG artifact versions. | `P3M19-A06`, `P3M24-A02` | Mapped only; required execution and the source Gate still unverified. |
| **P3OP07-R04**, §بسته | [L184](https://github.com/Shahbazi-Amir/RAG_finance/blob/7c74783c3dcda897b010ba9ea358d113f172ed1f/data/Road_Maps/RAG_finance_phase3_operational_roadmap.md#L184): export و deletion workflow. | `P3M15-A08`, `P3M21-A08`, `P3M15-A04` | **GAP/CONFLICT, OPEN (non-counting):** Export scope conflict; deletion not conditional on Export. |
| **P3OP07-R05**, §بسته | [L185](https://github.com/Shahbazi-Amir/RAG_finance/blob/7c74783c3dcda897b010ba9ea358d113f172ed1f/data/Road_Maps/RAG_finance_phase3_operational_roadmap.md#L185): tombstone/audit برای حذف و عدم بازگشت ناخواسته از backup. | `P3M15-A04`, `P3M22-A06` | **GAP/CONFLICT, OPEN (non-counting):** tombstone and preventing data resurrection after backup restore need explicit evidence. |
| **P3OP08-R01**, §Metrics | [L195](https://github.com/Shahbazi-Amir/RAG_finance/blob/7c74783c3dcda897b010ba9ea358d113f172ed1f/data/Road_Maps/RAG_finance_phase3_operational_roadmap.md#L195): request rate، error rate و latency p50/p95. | `P3M16-A02`, `P3M23-A02` | Mapped only; required execution and the source Gate still unverified. |
| **P3OP08-R03**, §Metrics | [L197](https://github.com/Shahbazi-Amir/RAG_finance/blob/7c74783c3dcda897b010ba9ea358d113f172ed1f/data/Road_Maps/RAG_finance_phase3_operational_roadmap.md#L197): token/cost per successful answer. | `P3M16-A02`, `P3M23-A08` | Mapped only; required execution and the source Gate still unverified. |
| **P3OP08-R04**, §Metrics | [L198](https://github.com/Shahbazi-Amir/RAG_finance/blob/7c74783c3dcda897b010ba9ea358d113f172ed1f/data/Road_Maps/RAG_finance_phase3_operational_roadmap.md#L198): citation/no-answer/policy outcomes. | `P3M16-A02`, `P3M10-A06` | Mapped only; required execution and the source Gate still unverified. |
| **P3OP08-R06**, §Metrics | [L200](https://github.com/Shahbazi-Amir/RAG_finance/blob/7c74783c3dcda897b010ba9ea358d113f172ed1f/data/Road_Maps/RAG_finance_phase3_operational_roadmap.md#L200): DB/Qdrant health و saturation. | `P3M16-A04`, `P3M23-A07` | Mapped only; required execution and the source Gate still unverified. |
| **P3OP08-R08**, §عملیات | [L205](https://github.com/Shahbazi-Amir/RAG_finance/blob/7c74783c3dcda897b010ba9ea358d113f172ed1f/data/Road_Maps/RAG_finance_phase3_operational_roadmap.md#L205): traces بین Web/API/RAG/LLM. | `P3M16-A08`, `P3M13-A07` | Mapped only; required execution and the source Gate still unverified. |
| **P3OP08-R09**, §عملیات | [L206](https://github.com/Shahbazi-Amir/RAG_finance/blob/7c74783c3dcda897b010ba9ea358d113f172ed1f/data/Road_Maps/RAG_finance_phase3_operational_roadmap.md#L206): alerts، on-call contacts و incident runbook. | `P3M16-A04`, `P3M16-A09`, `P3M25-A01` | Mapped only; required execution and the source Gate still unverified. |
| **P3OP09-R01**, §بسته | [L215](https://github.com/Shahbazi-Amir/RAG_finance/blob/7c74783c3dcda897b010ba9ea358d113f172ed1f/data/Road_Maps/RAG_finance_phase3_operational_roadmap.md#L215): prompt injection tests برای Query و Retrieved content. | `P3M12-A05`, `P3M21-A03` | Mapped only; required execution and the source Gate still unverified. |
| **P3OP09-R02**, §بسته | [L216](https://github.com/Shahbazi-Amir/RAG_finance/blob/7c74783c3dcda897b010ba9ea358d113f172ed1f/data/Road_Maps/RAG_finance_phase3_operational_roadmap.md#L216): output validation و safe rendering. | `P3M09-A07`, `P3M21-A02`, `P3M14-A12` | **GAP/CONFLICT, OPEN (non-counting):** UI safe rendering requires distinct checks beyond model output validation. |
| **P3OP09-R03**, §بسته | [L217](https://github.com/Shahbazi-Amir/RAG_finance/blob/7c74783c3dcda897b010ba9ea358d113f172ed1f/data/Road_Maps/RAG_finance_phase3_operational_roadmap.md#L217): access control روی Sourceهای غیرعمومی. | `P3M06-A02`, `P3M21-A04` | Mapped only; required execution and the source Gate still unverified. |
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
| **P3OP11-R08**, §Launch checklist | [L264](https://github.com/Shahbazi-Amir/RAG_finance/blob/7c74783c3dcda897b010ba9ea358d113f172ed1f/data/Road_Maps/RAG_finance_phase3_operational_roadmap.md#L264): monitoring/alerts فعال. | `P3M16-A04`, `P3M24-A08` | Mapped only; required execution and the source Gate still unverified. |
| **P3OP11-R09**, §Launch checklist | [L265](https://github.com/Shahbazi-Amir/RAG_finance/blob/7c74783c3dcda897b010ba9ea358d113f172ed1f/data/Road_Maps/RAG_finance_phase3_operational_roadmap.md#L265): support و incident ownership مشخص. | `P3M25-A01`, `P3M21-A09` | Mapped only; required execution and the source Gate still unverified. |
| **P3OP11-R10**, §Launch checklist | [L266](https://github.com/Shahbazi-Amir/RAG_finance/blob/7c74783c3dcda897b010ba9ea358d113f172ed1f/data/Road_Maps/RAG_finance_phase3_operational_roadmap.md#L266): RAG regression و security gate پاس. | `P3M20-A07`, `P3M21-A02` | Mapped only; required execution and the source Gate still unverified. |
| **P3OP11-R11**, §Launch checklist | [L267](https://github.com/Shahbazi-Amir/RAG_finance/blob/7c74783c3dcda897b010ba9ea358d113f172ed1f/data/Road_Maps/RAG_finance_phase3_operational_roadmap.md#L267): data deletion/export آماده. | `P3M15-A04`, `P3M15-A08`, `P3M21-A08` | **GAP/CONFLICT, OPEN (non-counting):** Export scope still conditional, deletion independent. |
| **P3OP11-R12**, §Launch checklist | [L268](https://github.com/Shahbazi-Amir/RAG_finance/blob/7c74783c3dcda897b010ba9ea358d113f172ed1f/data/Road_Maps/RAG_finance_phase3_operational_roadmap.md#L268): analytics حداقلی و consent-aware. | `P3M16-A02`, `P3M21-A07` | **GAP/CONFLICT, OPEN (non-counting):** consent-aware analytics needs an approved policy beyond modular metrics. |

## معیارهای تفصیلی UI-01 تا UI-14

[دفتر مصوب](https://github.com/Shahbazi-Amir/RAG_finance_app/blob/21fe24913f85cb9cc013ce01b1d5dbb4bc97774f/coordination/tasks/AGENT-UI-01.md) · [وضعیت تحویل قبلی هر ۱۴ فعالیت](https://github.com/Shahbazi-Amir/RAG_finance_app/blob/21fe24913f85cb9cc013ce01b1d5dbb4bc97774f/coordination/handoffs/UI_F3_API7C6_INTEGRATION.md)

- [ ] **UI-01** — دامنه، Journey و ساختار Frontend؛ M01/03/14، P3OP01
  - **ارتباط چک‌لیست اصلی:** P3M01, P3M03, P3M14, P3OP01
  - **وابستگی:** Foundation و تصمیم معماری/Stack
  - **خروجی/معیار پذیرش:** مسیرهای کاربر، مرز کامپوننت و Stateها؛ بدون قابلیت فعال فاز چهارم

- [ ] **UI-02** — تطبیق قرارداد Frontend/API؛ M03/11/13
  - **ارتباط چک‌لیست اصلی:** P3M03, P3M11, P3M13
  - **وابستگی:** قرارداد مشترک نسخه‌دار
  - **خروجی/معیار پذیرش:** API Client و Contract checks؛ بدون فیلد یا قرارداد موازی فرضی

- [ ] **UI-03** — ورود، نشست و مدیریت حساب؛ M05/13/14
  - **ارتباط چک‌لیست اصلی:** P3M05, P3M13, P3M14
  - **وابستگی:** روش ورود مصوب و قرارداد Auth
  - **خروجی/معیار پذیرش:** صفحات متناسب با روش مصوب؛ ورود، خروج، انقضا و خطاهای دسترسی درست

- [ ] **UI-04** — Consent و Privacy؛ M05/14، P3OP03/05
  - **ارتباط چک‌لیست اصلی:** P3M05, P3M14, P3OP03, P3OP05
  - **وابستگی:** قرارداد Consent و متن نسخه‌دار
  - **خروجی/معیار پذیرش:** نمایش و تغییر وضعیت رضایت؛ بدون ثبت پذیرش ساختگی

- [ ] **UI-05** — مکالمه و تاریخچه؛ M14/15
  - **ارتباط چک‌لیست اصلی:** P3M14, P3M15
  - **وابستگی:** قرارداد فهرست، جزئیات، Pagination و دسترسی
  - **خروجی/معیار پذیرش:** Loading/Empty/Error و بازیابی پس از Refresh؛ بدون نمایش دادهٔ کاربر دیگر

- [ ] **UI-06** — چت فارسی و RTL؛ M13/14
  - **ارتباط چک‌لیست اصلی:** P3M13, P3M14
  - **وابستگی:** قرارداد پیام و پاسخ
  - **خروجی/معیار پذیرش:** Composer و پیام‌ها روی موبایل و دسکتاپ؛ بدون تکثیر یا جابه‌جایی ناخواسته

- [ ] **UI-07** — وضعیت پاسخ و Confidence؛ M10/12/14
  - **ارتباط چک‌لیست اصلی:** P3M10, P3M12, P3M14
  - **وابستگی:** قرارداد محصول؛ نگاشت واقعی موتور بعداً
  - **خروجی/معیار پذیرش:** Answer/Partial/No-answer/Clarification/Refusal/Error؛ خطای فنی no-answer نشود و confidence:null عددسازی نشود

- [ ] **UI-08** — Citation و Attribution؛ M11/14
  - **ارتباط چک‌لیست اصلی:** P3M11, P3M14
  - **وابستگی:** DTO مشترک؛ Resolver واقعی برای پذیرش اتصال
  - **خروجی/معیار پذیرش:** Citation کنار Claim و جزئیات منبع؛ نویسنده، سردبیر و گوینده جدا؛ بدون نام، لینک، صفحه یا زمان جعلی

- [ ] **UI-09** — Feedback و گزارش پاسخ؛ M13/15، P3OP05
  - **ارتباط چک‌لیست اصلی:** P3M13, P3M15, P3OP05
  - **وابستگی:** قرارداد بازخورد و Answer ID
  - **خروجی/معیار پذیرش:** اتصال به پاسخ درست؛ مدیریت خطا و ارسال تکراری

- [ ] **UI-10** — Streaming، Cancellation و Recovery؛ M13/14/15
  - **ارتباط چک‌لیست اصلی:** P3M13, P3M14, P3M15
  - **وابستگی:** قرارداد Event، Idempotency، لغو و بازیابی
  - **خروجی/معیار پذیرش:** State machine، Retry/Refresh و پاسخ ناقص؛ تفاوت لغو نمایش با توقف واقعی سرور محفوظ

- [ ] **UI-11** — Accessibility، موبایل و مرورگر؛ M14، P3OP05
  - **ارتباط چک‌لیست اصلی:** P3M14, P3OP05
  - **وابستگی:** مرورگرها و معیارهای مصوب
  - **خروجی/معیار پذیرش:** RTL، Layout واکنش‌گرا، Keyboard، Focus، Contrast و Screen-reader labels؛ checks مصوب پاس

- [ ] **UI-12** — آزمون و تحویل UI؛ M03/11/14/15 و Test Suite نقشه
  - **ارتباط چک‌لیست اصلی:** P3M03, P3M11, P3M14, P3M15
  - **وابستگی:** اجزای آماده؛ اتصال واقعی برای L2
  - **خروجی/معیار پذیرش:** آزمون‌های متناسب، مستند اجرا و محدودیت‌ها؛ مسیر Login→Chat→Citation→History؛ Mock شاهد کیفیت موتور نیست

- [ ] **UI-13** — حذف داده و حساب؛ M14/15/21، P3OP05/07
  - **ارتباط چک‌لیست اصلی:** P3M14, P3M15, P3M21, P3OP05, P3OP07
  - **وابستگی:** سیاست حذف و قرارداد Backend
  - **خروجی/معیار پذیرش:** تأیید کاربر، ثبت درخواست و وضعیت واقعی؛ موفقیت فقط پس از تأیید نهایی Backend؛ Export تصمیم مستقل

- [ ] **UI-14** — نمایش امن محتوا؛ M14/21، P3OP09
  - **ارتباط چک‌لیست اصلی:** P3M14, P3M21, P3OP09
  - **وابستگی:** قواعد rendering و خطای API
  - **خروجی/معیار پذیرش:** جلوگیری از اجرای HTML/Script و URL خطرناک؛ عدم نمایش Prompt، Stack trace، Debug، Token و Secret

## شواهد و وضعیت ۱۴ وظیفهٔ UI روی #62

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

سطرهای L1 pending در متن دفتر UI با نتیجهٔ سبز Run 45108323298 در #62 reconcile شوند. L2 همچنان به اجرای مقصد نیاز دارد.

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
