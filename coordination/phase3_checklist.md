# Phase 3 canonical acceptance checklist (DRAFT)

Source: `Shahbazi-Amir/RAG_finance@7c74783c3dcda897b010ba9ea358d113f172ed1f`; see `references/phase2/roadmaps/`. Sole editor: **foundation**. Supervisor: **«مغز فاز سوم»**. This is preparatory, never a Module 00/01 PASS.

## Evidence and counting policy

- States: `planned / active / blocked / review / accepted`. Only a completed activity with demonstrated acceptance criteria and linked evidence may be checked; **supervisor approval stays separate**. Current checks all unchecked.
- Specialist tasks cite canonical `P3Mxx` IDs. Only foundation changes this file. UI/database/API agents edit only their own mission records. Operational P3OP items cross-map, never double count.
- Owners below provide accountability. Foundation coordinates security/integration/ops/final Gate; human deployment and operations approver still **assignment pending**.
- `blocked` and untested are never checked. Phase 2 release unaccepted; NB23 C012 formal readiness BLOCKED; Module 00 BLOCKED.

## Module obligations and Gates (source: phase3 modular plan, Modules 00–25)

### P3M00 — phase2_handoff_acceptance

- [ ] **Acceptance activity:** deliver module-level outcome. **Source:** modular plan Module 00 (line 131). **Owner:** foundation (human operational role pending where applicable). **Dependencies:** Phase2 accepted + NB23 + M00 Gate. **Output:** module deliverables as specified below. **Acceptance Gate:** Hash mismatch، Broken contract، Broken locator و Invalid attribution باید صفر باشد. Release فاز ۲ باید وضعیت `accepted_for_phase3=true` بگیرد.. **Status:** `blocked`. **Implemented:** not verified. **Tested:** not run. **Supervisor approval:** pending. **Evidence:** `coordination/evidence/P3M00/` (future evidence only).
- **Required deliverables and acceptance work:** 1. دریافت `release_id` و Release Manifest فاز ۲؛ · 2. اعتبارسنجی `rag_request.schema.json` و `rag_response.schema.json`؛ · 3. کنترل Hash داده، Chunk، Embedding، Index و Config؛ · 4. اجرای Contract test روی نمونه درخواست‌ها؛ · 5. کنترل Citation locator برای سایت، کتاب و Transcript؛ · 6. کنترل وجود فیلدهای نویسنده، سردبیر، گوینده و نوع اختیار محتوایی؛ · 7. اجرای Smoke benchmark فاز ۲؛ · 8. ثبت Compatibility matrix و نتیجه پذیرش.

### P3M01 — architecture_slo_and_scope_freeze

- [ ] **Acceptance activity:** deliver module-level outcome. **Source:** modular plan Module 01 (line 166). **Owner:** foundation (human operational role pending where applicable). **Dependencies:** M00; employer scope decisions. **Output:** module deliverables as specified below. **Acceptance Gate:** `docs/phase3/architecture.md`، `docs/phase3/scope.md`، `docs/phase3/slo.md` و ADRها باید تأیید شوند. مقدار حل‌نشده‌ای که روی امنیت یا هزینه اثر دارد، Gate را Fail می‌کند.. **Status:** `planned`. **Implemented:** not verified. **Tested:** not run. **Supervisor approval:** pending. **Evidence:** `coordination/evidence/P3M01/` (future evidence only).
- **Required deliverables and acceptance work:** 1. Freeze دامنه فاز ۳ و فهرست صریح موارد فاز ۴؛ · 2. ثبت Context diagram و Container diagram؛ · 3. تثبیت Stack با ADR؛ · 4. تعیین محیط‌های Local، Test، Staging و Production؛ · 5. تعیین DAU، پیام روزانه، Concurrent request و بودجه مصرف؛ · 6. تعیین SLO اولیه Availability، latency و error rate؛ · 7. تعیین RPO و RTO Backup؛ · 8. ثبت محل میزبانی، دامنه، TLS و محدودیت انتقال داده؛ · 9. ساخت Risk register و Dependency register؛ · 10. تعریف معیار Go/No-Go Launch.

### P3M02 — environment_and_security_baseline

- [ ] **Acceptance activity:** deliver module-level outcome. **Source:** modular plan Module 02 (line 195). **Owner:** foundation (human operational role pending where applicable). **Dependencies:** M01. **Output:** module deliverables as specified below. **Acceptance Gate:** Build پاک روی محیط جدید، Secret leakage صفر، Dependency بحرانی حل‌نشده صفر و فرمان واحد تست موفق باشد. شواهد: SBOM، Environment manifest و Security baseline report.. **Status:** `planned`. **Implemented:** not verified. **Tested:** not run. **Supervisor approval:** pending. **Evidence:** `coordination/evidence/P3M02/` (future evidence only).
- **Required deliverables and acceptance work:** 1. Freeze نسخه Python، Node، PostgreSQL، Qdrant، Redis و Docker؛ · 2. ساخت lockfileهای وابستگی؛ · 3. تعریف `.env.example` بدون Secret؛ · 4. ممنوع‌کردن Secret در Repository؛ · 5. فعال‌کردن Dependency و Secret scanning؛ · 6. تنظیم Lint، Type check و Test command واحد؛ · 7. ساخت SBOM و گزارش Dependency؛ · 8. ثبت Timezone، Locale و Encoding؛ · 9. تعیین Log redaction policy؛ · 10. ساخت Environment manifest.

### P3M03 — project_structure_and_contracts

- [ ] **Acceptance activity:** deliver module-level outcome. **Source:** modular plan Module 03 (line 216). **Owner:** foundation (human operational role pending where applicable). **Dependencies:** M01-M02. **Output:** module deliverables as specified below. **Acceptance Gate:** Schema validation و Contract test صددرصد PASS و Circular dependency صفر باشد.. **Status:** `planned`. **Implemented:** not verified. **Tested:** not run. **Supervisor approval:** pending. **Evidence:** `coordination/evidence/P3M03/` (future evidence only).
- **Required deliverables and acceptance work:** 1. تعریف مرز Domain moduleها؛ · 2. تعریف Error model مشترک؛ · 3. تعریف Request ID و Trace ID؛ · 4. نسخه‌بندی API از `/v1`؛ · 5. ساخت Schemaهای User، Conversation، Message، Answer و Citation؛ · 6. تعریف فیلدهای Attribution؛ · 7. تعریف Compatibility policy؛ · 8. ساخت Contract tests بین Backend، Frontend و RAG runtime؛ · 9. ساخت Architecture dependency test برای جلوگیری از Import معکوس.

### P3M04 — database_schema_and_migrations

- [ ] **Acceptance activity:** deliver module-level outcome. **Source:** modular plan Module 04 (line 260). **Owner:** database. **Dependencies:** M03; retention policy. **Output:** module deliverables as specified below. **Acceptance Gate:** Migration clean، rollback test، FK violation صفر و Query plan قابل قبول برای مسیرهای اصلی.. **Status:** `planned`. **Implemented:** not verified. **Tested:** not run. **Supervisor approval:** pending. **Evidence:** `coordination/evidence/P3M04/` (future evidence only).
- **Required deliverables and acceptance work:** 1. طراحی ERD و Data dictionary؛ · 2. تعریف Primary/Foreign key و Index؛ · 3. افزودن `user_id` به تمام داده‌های کاربر؛ · 4. ذخیره Citation و Attribution به‌صورت ساخت‌یافته؛ · 5. ذخیره Versionهای knowledge/retrieval/model/policy؛ · 6. تعریف Migration forward و rollback؛ · 7. تست Migration روی دیتابیس خالی و دیتابیس دارای داده؛ · 8. تعریف Retention و soft/hard delete؛ · 9. آماده‌سازی Namespace رزروشده برای موجودیت‌های فاز ۴ بدون فعال‌سازی آن‌ها.

### P3M05 — authentication_and_sessions

- [ ] **Acceptance activity:** deliver module-level outcome. **Source:** modular plan Module 05 (line 298). **Owner:** api. **Dependencies:** M03-M04; auth policy. **Output:** module deliverables as specified below. **Acceptance Gate:** دسترسی بدون هویت به Endpoint محافظت‌شده صفر، Session پس از revoke نامعتبر و Secret در log صفر باشد.. **Status:** `planned`. **Implemented:** not verified. **Tested:** not run. **Supervisor approval:** pending. **Evidence:** `coordination/evidence/P3M05/` (future evidence only).
- **Required deliverables and acceptance work:** 1. انتخاب روش ورود طبق تصمیم کارفرما؛ · 2. Password hashing استاندارد در صورت ورود رمزدار؛ · 3. Session token امن و rotation؛ · 4. Cookie امن با `HttpOnly`، `Secure` و `SameSite`؛ · 5. CSRF policy؛ · 6. محدودیت تلاش ورود و lockout کنترل‌شده؛ · 7. Logout و revoke همه نشست‌ها؛ · 8. Expiration و refresh policy؛ · 9. ثبت Security event بدون ذخیره Secret؛ · 10. تست منفی Session theft و replay.

### P3M06 — tenant_isolation_and_rls

- [ ] **Acceptance activity:** deliver module-level outcome. **Source:** modular plan Module 06 (line 323). **Owner:** database. **Dependencies:** M04-M05. **Output:** module deliverables as specified below. **Acceptance Gate:** Cross-user data exposure و RLS bypass در تست‌ها باید صفر باشد.. **Status:** `planned`. **Implemented:** not verified. **Tested:** not run. **Supervisor approval:** pending. **Evidence:** `coordination/evidence/P3M06/` (future evidence only).
- **Required deliverables and acceptance work:** 1. فعال‌سازی Row-Level Security برای جداول کاربرمحور؛ · 2. تعریف Policy خواندن، نوشتن، ویرایش و حذف؛ · 3. تنظیم Context امن user/tenant در هر Transaction؛ · 4. جلوگیری از دسترسی Background job خارج از Scope؛ · 5. تست cross-user برای تمام Endpointها؛ · 6. تست ID enumeration؛ · 7. تست دسترسی مستقیم Repository layer؛ · 8. ثبت Audit برای عملیات حساس؛ · 9. ساخت Isolation matrix.

### P3M07 — knowledge_release_loader

- [ ] **Acceptance activity:** deliver module-level outcome. **Source:** modular plan Module 07 (line 351). **Owner:** api. **Dependencies:** M00; M03; accepted release. **Output:** module deliverables as specified below. **Acceptance Gate:** سرویس نباید با Release ناسازگار Ready شود. Rollback باید بدون بازسازی Index ممکن باشد.. **Status:** `planned`. **Implemented:** not verified. **Tested:** not run. **Supervisor approval:** pending. **Evidence:** `coordination/evidence/P3M07/` (future evidence only).
- **Required deliverables and acceptance work:** 1. خواندن `knowledge_release.lock`؛ · 2. کنترل Hash و Schema پیش از Startup؛ · 3. اتصال به Collection نسخه‌دار Qdrant؛ · 4. اعتبارسنجی Point count و Payload schema؛ · 5. کنترل فیلدهای Source locator و Attribution؛ · 6. ممنوع‌کردن اتصال به Index بدون Release ID؛ · 7. Health check مستقل دانش؛ · 8. Warm-up محدود؛ · 9. Rollback به Release قبلی؛ · 10. تست خرابی Release و Fail-closed.

### P3M08 — retrieval_runtime

- [ ] **Acceptance activity:** deliver module-level outcome. **Source:** modular plan Module 08 (line 376). **Owner:** api. **Dependencies:** M07; NB23. **Output:** module deliverables as specified below. **Acceptance Gate:** Metricهای فاز ۲ در Runtime نباید بیش از Tolerance مصوب افت کنند؛ Misattribution filter failure صفر باشد.. **Status:** `planned`. **Implemented:** not verified. **Tested:** not run. **Supervisor approval:** pending. **Evidence:** `coordination/evidence/P3M08/` (future evidence only).
- **Required deliverables and acceptance work:** 1. تبدیل Config برنده فاز ۲ به Runtime package؛ · 2. Dense/Sparse/Hybrid/Rerank pipeline؛ · 3. Metadata filter برای Source و Authority type؛ · 4. Intent-aware filter برای «نظر مستقیم مؤلف»؛ · 5. Timeout و retry محدود؛ · 6. Candidate و final-k ثابت و نسخه‌دار؛ · 7. عدم ثبت Query حساس به شکل Raw در log عمومی؛ · 8. ثبت Retrieval run و scoreها؛ · 9. Regression test با Golden set؛ · 10. Fallback کنترل‌شده در خرابی جزء غیرضروری.

### P3M09 — model_gateway

- [ ] **Acceptance activity:** deliver module-level outcome. **Source:** modular plan Module 09 (line 401). **Owner:** api. **Dependencies:** M08; model/provider decision. **Output:** module deliverables as specified below. **Acceptance Gate:** وابستگی مستقیم Domain code به SDK ارائه‌دهنده صفر، خروجی نامعتبر مدیریت‌نشده صفر و Cost guard فعال باشد.. **Status:** `planned`. **Implemented:** not verified. **Tested:** not run. **Supervisor approval:** pending. **Evidence:** `coordination/evidence/P3M09/` (future evidence only).
- **Required deliverables and acceptance work:** 1. تعریف Interface مستقل از Provider؛ · 2. Timeout، retry و circuit breaker؛ · 3. محدودیت Token و هزینه؛ · 4. ثبت مدل و نسخه در هر run؛ · 5. حذف یا ماسک داده غیرضروری پیش از ارسال؛ · 6. Streaming adapter؛ · 7. خروجی ساخت‌یافته و Schema validation؛ · 8. Fallback model طبق Policy؛ · 9. تست خطا، کندی و پاسخ نامعتبر؛ · 10. Benchmark کیفیت/هزینه/latency پیش از Freeze Provider.

### P3M10 — answer_orchestration

- [ ] **Acceptance activity:** deliver module-level outcome. **Source:** modular plan Module 10 (line 426). **Owner:** api. **Dependencies:** M08-M09; NB23. **Output:** module deliverables as specified below. **Acceptance Gate:** هر Answer باید `request_id`، نسخه دانش، Runها، Citation و وضعیت Safety داشته باشد. پاسخ ناقص نباید به‌عنوان موفق ثبت شود.. **Status:** `planned`. **Implemented:** not verified. **Tested:** not run. **Supervisor approval:** pending. **Evidence:** `coordination/evidence/P3M10/` (future evidence only).
- **Required deliverables and acceptance work:** 1. ساخت Query context از پیام جاری و تاریخچه محدود؛ · 2. Intent و Answerability؛ · 3. Retrieval و Context builder؛ · 4. تولید پاسخ ساخت‌یافته؛ · 5. Claim/Citation verification؛ · 6. اعمال Safety و No-answer؛ · 7. ساخت Confidence از اجزای قابل توضیح؛ · 8. ذخیره Runها و Versionها در یک Transaction منطقی؛ · 9. مدیریت cancellation و duplicate request؛ · 10. Idempotency برای retry کلاینت.

### P3M11 — citation_and_attribution_delivery

- [ ] **Acceptance activity:** deliver module-level outcome. **Source:** modular plan Module 11 (line 451). **Owner:** api. **Dependencies:** M10; NB23. **Output:** module deliverables as specified below. **Acceptance Gate:** Citation correctness و Attribution correctness باید Target فاز ۲ را حفظ کنند؛ نام حدسی و locator ساختگی صفر.. **Status:** `planned`. **Implemented:** not verified. **Tested:** not run. **Supervisor approval:** pending. **Evidence:** `coordination/evidence/P3M11/` (future evidence only).
- **Required deliverables and acceptance work:** 1. تعریف Citation DTO مشترک Frontend/Backend؛ · 2. ارسال URL و locator معتبر؛ · 3. ارسال `credited_author_name`؛ · 4. ارسال جداگانه `editorial_supervisor_name`؛ · 5. ارسال `speaker_name` برای Transcript؛ · 6. ارسال `content_authority_type` و `attribution_status`؛ · 7. نمایش Citation کنار Claim و فهرست منابع؛ · 8. Tooltip یا جزئیات «چرا این منبع استفاده شد»؛ · 9. Broken link و Broken locator handling؛ · 10. تست Snapshot برای چهار نوع نمایش منبع؛ · 11. تست ممنوعیت تبدیل سردبیر به نویسنده.

### P3M12 — safety_no_answer_and_policy

- [ ] **Acceptance activity:** deliver module-level outcome. **Source:** modular plan Module 12 (line 477). **Owner:** api. **Dependencies:** M10; NB23. **Output:** module deliverables as specified below. **Acceptance Gate:** Critical policy violation در Suite مصوب باید صفر و No-answer F1 در محدوده پذیرش باشد.. **Status:** `planned`. **Implemented:** not verified. **Tested:** not run. **Supervisor approval:** pending. **Evidence:** `coordination/evidence/P3M12/` (future evidence only).
- **Required deliverables and acceptance work:** 1. تفکیک آموزش مالی از توصیه سرمایه‌گذاری شخصی؛ · 2. تشخیص سؤال خارج از منبع یا مبهم؛ · 3. Clarification، Abstention و Safe completion؛ · 4. ممنوعیت ادعای قطعی بدون Citation؛ · 5. Prompt injection defense برای ورودی و محتوای بازیابی‌شده؛ · 6. سیاست نمایش Disclaimer متناسب، نه ثابت و بی‌اثر؛ · 7. ثبت Policy version؛ · 8. ساخت Red-team corpus فارسی؛ · 9. تست درخواست افشای داده کاربر دیگر؛ · 10. تست توصیه خرید/فروش و پاسخ پرریسک.

### P3M13 — product_api

- [ ] **Acceptance activity:** deliver module-level outcome. **Source:** modular plan Module 13 (line 502). **Owner:** api. **Dependencies:** M03; M05-M12. **Output:** module deliverables as specified below. **Acceptance Gate:** OpenAPI validation، Contract suite، Authorization suite و Error contract صددرصد PASS.. **Status:** `planned`. **Implemented:** not verified. **Tested:** not run. **Supervisor approval:** pending. **Evidence:** `coordination/evidence/P3M13/` (future evidence only).
- **Required deliverables and acceptance work:** 1. OpenAPI نسخه‌دار؛ · 2. Validation ورودی و محدودیت اندازه؛ · 3. Error code پایدار؛ · 4. Pagination تاریخچه؛ · 5. Streaming پاسخ با stateهای مشخص؛ · 6. Idempotency key؛ · 7. Request/Trace ID؛ · 8. Authorization در هر Endpoint؛ · 9. Contract test و backward compatibility؛ · 10. API abuse tests.

### P3M14 — web_chat_interface

- [ ] **Acceptance activity:** deliver module-level outcome. **Source:** modular plan Module 14 (line 542). **Owner:** ui. **Dependencies:** M05; M11-M13. **Output:** module deliverables as specified below. **Acceptance Gate:** مسیر Login→Chat→Citation→History روی مرورگرهای مصوب و موبایل PASS؛ خطای انتساب UI صفر.. **Status:** `planned`. **Implemented:** not verified. **Tested:** not run. **Supervisor approval:** pending. **Evidence:** `coordination/evidence/P3M14/` (future evidence only).
- **Required deliverables and acceptance work:** 1. صفحه ورود و مدیریت Session؛ · 2. فهرست گفت‌وگوهای خود کاربر؛ · 3. صفحه Chat واکنش‌گرا؛ · 4. Streaming پاسخ و امکان لغو؛ · 5. نمایش Citation در سطح Claim؛ · 6. نمایش صحیح نویسنده و سردبیر؛ · 7. نمایش Confidence به زبان قابل فهم؛ · 8. نمایش No-answer و سؤال روشن‌کننده؛ · 9. Error/Retry state بدون تکرار پیام؛ · 10. Accessibility پایه Keyboard، focus، contrast و screen-reader label؛ · 11. تست موبایل و مرورگرهای هدف؛ · 12. ممنوعیت نمایش اطلاعات Debug یا Prompt داخلی.

### P3M15 — conversation_history_and_feedback

- [ ] **Acceptance activity:** deliver module-level outcome. **Source:** modular plan Module 15 (line 573). **Owner:** database. **Dependencies:** M04; M06; M13-M14. **Output:** module deliverables as specified below. **Acceptance Gate:** History consistency، حذف مطابق Policy، cross-user exposure صفر و Feedback trace کامل.. **Status:** `planned`. **Implemented:** not verified. **Tested:** not run. **Supervisor approval:** pending. **Evidence:** `coordination/evidence/P3M15/` (future evidence only).
- **Required deliverables and acceptance work:** 1. ذخیره User message و Answer به‌صورت immutable event؛ · 2. عنوان‌گذاری مکالمه بدون تغییر محتوای اصلی؛ · 3. Pagination و مرتب‌سازی؛ · 4. حذف مکالمه طبق Retention policy؛ · 5. Feedback مثبت/منفی و دسته خطا؛ · 6. ثبت Citation مشکل‌دار یا انتساب اشتباه؛ · 7. جلوگیری از دسترسی کاربر دیگر؛ · 8. Export ساخت‌یافته در صورت تصویب Scope؛ · 9. Dataset بازخورد بدون PII برای ارزیابی بعدی؛ · 10. تست Race condition و duplicate write.

### P3M16 — observability_and_audit

- [ ] **Acceptance activity:** deliver module-level outcome. **Source:** modular plan Module 16 (line 598). **Owner:** foundation (human operational role pending where applicable). **Dependencies:** M13-M15; log policy. **Output:** module deliverables as specified below. **Acceptance Gate:** هر درخواست قابل ردیابی، Alertهای بحرانی آزمایش‌شده و Secret/PII leakage در log صفر.. **Status:** `planned`. **Implemented:** not verified. **Tested:** not run. **Supervisor approval:** pending. **Evidence:** `coordination/evidence/P3M16/` (future evidence only).
- **Required deliverables and acceptance work:** 1. Structured log با Request/Trace ID؛ · 2. Metricهای request، latency، error، retrieval و model؛ · 3. Dashboard سلامت سرویس؛ · 4. Alert برای Availability، error rate، DB pool و مصرف؛ · 5. Audit event برای ورود و عملیات حساس؛ · 6. Redaction داده مالی و Token؛ · 7. ثبت نسخه Knowledge/Model/Policy؛ · 8. Trace نمونه‌برداری‌شده برای مسیر پاسخ؛ · 9. Runbook هشدارها؛ · 10. تست اینکه PII و Secret در Log وجود ندارد.

### P3M17 — cache_rate_limit_and_cost_control

- [ ] **Acceptance activity:** deliver module-level outcome. **Source:** modular plan Module 17 (line 623). **Owner:** api. **Dependencies:** M09-M10; cost policy. **Output:** module deliverables as specified below. **Acceptance Gate:** Rate-limit bypass، cross-user cache leak و stale citation پس از Release باید صفر باشد.. **Status:** `planned`. **Implemented:** not verified. **Tested:** not run. **Supervisor approval:** pending. **Evidence:** `coordination/evidence/P3M17/` (future evidence only).
- **Required deliverables and acceptance work:** 1. Rate limit بر اساس کاربر و IP؛ · 2. Daily quota و budget guard؛ · 3. Cache فقط برای خروجی‌های مجاز؛ · 4. Cache key شامل Release، Policy، Authority filter و Locale؛ · 5. ممنوعیت Cache مشترک برای پاسخ شخصی یا تاریخچه؛ · 6. TTL و invalidation هنگام Release جدید؛ · 7. Idempotency store؛ · 8. Queue/backpressure در پیک؛ · 9. تست bypass و cache poisoning؛ · 10. گزارش هزینه هر پاسخ موفق.

### P3M18 — containerization_and_networking

- [ ] **Acceptance activity:** deliver module-level outcome. **Source:** modular plan Module 18 (line 648). **Owner:** foundation (human operational role pending where applicable). **Dependencies:** M02-M17; hosting. **Output:** module deliverables as specified below. **Acceptance Gate:** Build تکرارپذیر، Critical image vulnerability حل‌نشده صفر و restart بدون از دست‌رفتن داده.. **Status:** `planned`. **Implemented:** not verified. **Tested:** not run. **Supervisor approval:** pending. **Evidence:** `coordination/evidence/P3M18/` (future evidence only).
- **Required deliverables and acceptance work:** 1. Dockerfile چندمرحله‌ای برای Web و API؛ · 2. اجرای process با کاربر غیر root؛ · 3. Healthcheck و startup dependency؛ · 4. Network segmentation؛ · 5. Volume و persistence policy؛ · 6. Secret injection در Runtime؛ · 7. محدودیت CPU/Memory؛ · 8. Image scanning و pin digest؛ · 9. Compose برای Local و Deployment؛ · 10. Cold-start و restart test.

### P3M19 — ci_cd_and_release_pipeline

- [ ] **Acceptance activity:** deliver module-level outcome. **Source:** modular plan Module 19 (line 679). **Owner:** foundation (human operational role pending where applicable). **Dependencies:** M02-M18. **Output:** module deliverables as specified below. **Acceptance Gate:** هیچ Deployment تولیدی بدون Test report، Image digest، Migration check و Approval انجام نشود.. **Status:** `planned`. **Implemented:** not verified. **Tested:** not run. **Supervisor approval:** pending. **Evidence:** `coordination/evidence/P3M19/` (future evidence only).
- **Required deliverables and acceptance work:** 1. Lint، type check و unit tests؛ · 2. Integration tests با سرویس‌های موقت؛ · 3. Migration test؛ · 4. Contract و security tests؛ · 5. Build و scan Image؛ · 6. تولید Release manifest و SBOM؛ · 7. Deploy خودکار به Staging؛ · 8. Approval دستی Production؛ · 9. Rollback workflow؛ · 10. نگهداری Artifact و Test report؛ · 11. Branch protection و ممنوعیت Secret در log.

### P3M20 — staging_deployment_and_e2e

- [ ] **Acceptance activity:** deliver module-level outcome. **Source:** modular plan Module 20 (line 705). **Owner:** foundation (human operational role pending where applicable). **Dependencies:** M00; M03-M19. **Output:** module deliverables as specified below. **Acceptance Gate:** مسیرهای بحرانی E2E و UAT PASS، Issue بحرانی باز صفر و Staging قابل بازسازی باشد.. **Status:** `planned`. **Implemented:** not verified. **Tested:** not run. **Supervisor approval:** pending. **Evidence:** `coordination/evidence/P3M20/` (future evidence only).
- **Required deliverables and acceptance work:** 1. Provision محیط Staging نزدیک به Production؛ · 2. TLS و Domain آزمایشی؛ · 3. داده Test غیرشخصی؛ · 4. اجرای Migration؛ · 5. بارگذاری Release پذیرفته‌شده فاز ۲؛ · 6. Smoke و E2E؛ · 7. تست سه منبع و چهار نوع Citation؛ · 8. تست نویسنده/سردبیر؛ · 9. تست No-answer و Safety؛ · 10. تست Restart و dependency outage؛ · 11. UAT کارفرما و ثبت Issue.

### P3M21 — security_privacy_and_threat_validation

- [ ] **Acceptance activity:** deliver module-level outcome. **Source:** modular plan Module 21 (line 731). **Owner:** foundation (human operational role pending where applicable). **Dependencies:** M05-M06; M20; privacy. **Output:** module deliverables as specified below. **Acceptance Gate:** Critical/High vulnerability حل‌نشده صفر، Data isolation failure صفر و Incident runbook تأییدشده.. **Status:** `planned`. **Implemented:** not verified. **Tested:** not run. **Supervisor approval:** pending. **Evidence:** `coordination/evidence/P3M21/` (future evidence only).
- **Required deliverables and acceptance work:** 1. Threat model برای Web، API، DB، Qdrant و Model gateway؛ · 2. تست OWASP API/Web متناسب؛ · 3. تست prompt injection و data exfiltration؛ · 4. تست IDOR و RLS bypass؛ · 5. TLS، headerهای امنیتی و CORS؛ · 6. Dependency و image scan؛ · 7. Consent و Retention validation؛ · 8. Account/data deletion test؛ · 9. Incident response tabletop؛ · 10. ثبت Risk acceptanceهای باقی‌مانده.

### P3M22 — backup_restore_and_disaster_recovery

- [ ] **Acceptance activity:** deliver module-level outcome. **Source:** modular plan Module 22 (line 756). **Owner:** database. **Dependencies:** M04; M07; M18; RPO/RTO. **Output:** module deliverables as specified below. **Acceptance Gate:** Backup بدون Restore موفق ارزشی ندارد. Restore کامل باید در محدوده RPO/RTO مصوب PASS شود.. **Status:** `planned`. **Implemented:** not verified. **Tested:** not run. **Supervisor approval:** pending. **Evidence:** `coordination/evidence/P3M22/` (future evidence only).
- **Required deliverables and acceptance work:** 1. Backup نسخه‌دار PostgreSQL؛ · 2. Snapshot و Restore Qdrant؛ · 3. Backup Config و Release pointer؛ · 4. رمزگذاری و دسترسی محدود Backup؛ · 5. Retention و rotation؛ · 6. Restore در محیط خالی؛ · 7. Point-in-time recovery در صورت امکان زیرساخت؛ · 8. اندازه‌گیری RPO/RTO واقعی؛ · 9. تست خرابی جزئی و کامل؛ · 10. Runbook و گزارش Restore.

### P3M23 — performance_load_and_failure_testing

- [ ] **Acceptance activity:** deliver module-level outcome. **Source:** modular plan Module 23 (line 781). **Owner:** foundation (human operational role pending where applicable). **Dependencies:** M20-M22; real workload. **Output:** module deliverables as specified below. **Acceptance Gate:** SLOهای Freeze‌شده، Error budget و ظرفیت Peak باید PASS شوند. اعداد نمونه یادداشت تصمیم، تا زمان Freeze تعهد قطعی نیستند.. **Status:** `planned`. **Implemented:** not verified. **Tested:** not run. **Supervisor approval:** pending. **Evidence:** `coordination/evidence/P3M23/` (future evidence only).
- **Required deliverables and acceptance work:** 1. Freeze workload model با اعداد تأییدشده؛ · 2. Baseline p50/p95/p99؛ · 3. Load، stress و soak test؛ · 4. اندازه‌گیری saturation؛ · 5. Failure injection کنترل‌شده؛ · 6. تحلیل Queue و timeout؛ · 7. بررسی DB pool و Index latency؛ · 8. اندازه‌گیری هزینه هر پاسخ؛ · 9. Capacity report و tuning؛ · 10. Regression threshold.

### P3M24 — production_launch

- [ ] **Acceptance activity:** deliver module-level outcome. **Source:** modular plan Module 24 (line 819). **Owner:** foundation (human operational role pending where applicable). **Dependencies:** M00-M23; Go/No-Go. **Output:** module deliverables as specified below. **Acceptance Gate:** تمام P0ها بسته، Rollback آماده، Backup معتبر، UAT تأییدشده و مانیتورینگ فعال باشد.. **Status:** `planned`. **Implemented:** not verified. **Tested:** not run. **Supervisor approval:** pending. **Evidence:** `coordination/evidence/P3M24/` (future evidence only).
- **Required deliverables and acceptance work:** 1. Go/No-Go checklist؛ · 2. Freeze Image digest، DB migration و Knowledge release؛ · 3. Backup قبل از استقرار؛ · 4. اجرای Deployment کنترل‌شده؛ · 5. Migration و health verification؛ · 6. Smoke test با حساب آزمایشی؛ · 7. فعال‌سازی محدود کاربران اولیه؛ · 8. پایش Error، latency، cost و safety؛ · 9. Rollback در عبور از Threshold؛ · 10. ثبت زمان، نسخه‌ها و مسئول تصمیم؛ · 11. Production acceptance report.

### P3M25 — hypercare_and_phase4_handoff

- [ ] **Acceptance activity:** deliver module-level outcome. **Source:** modular plan Module 25 (line 845). **Owner:** foundation (human operational role pending where applicable). **Dependencies:** M24; operations owner. **Output:** module deliverables as specified below. **Acceptance Gate:** Incident بحرانی باز صفر، Runbook و آموزش تحویل‌شده، Metrics پایدار و قرارداد ورودی فاز ۴ تأییدشده باشد.. **Status:** `planned`. **Implemented:** not verified. **Tested:** not run. **Supervisor approval:** pending. **Evidence:** `coordination/evidence/P3M25/` (future evidence only).
- **Required deliverables and acceptance work:** 1. بازه Hypercare با مالک مشخص؛ · 2. دسته‌بندی Incident و SLA پاسخ داخلی؛ · 3. مرور روزانه Error، latency، Citation و Safety؛ · 4. تحلیل Feedback کاربران اولیه؛ · 5. اصلاح فقط Bugهای فاز ۳ و جلوگیری از Scope creep؛ · 6. Freeze Baseline عملیاتی پس از پایداری؛ · 7. ساخت Runbook بهره‌برداری؛ · 8. انتقال دانش به تیم نگهداری؛ · 9. تعریف Contract فاز ۴ برای Profile، Assessment، Goals و Action Plan؛ · 10. ثبت Tech debt و Deferred decisions؛ · 11. Phase 3 closure report.

## Operational plan packages (source: phase3 operational roadmap P3-01..P3-11)

These operational rows capture additional package obligations without duplicating modular acceptance credit. Their acceptance needs both mapped modular gates and the operational Gate in the source.

| ID | Owner | Modules (single count) | Operational acceptance | Status | Evidence | Supervisor |
|---|---|---|---|---|---|---|
| P3OP01 Product/Architecture | foundation | P3M01, P3M03 | Approved API/privacy/ownership contract; operational source P3-01 Gate must be evidenced | blocked | `coordination/evidence/P3OP01/` | pending |
| P3OP02 Data model | database | P3M04, P3M06 | Migration and cross-user checks; operational source P3-02 Gate must be evidenced | planned | `coordination/evidence/P3OP02/` | pending |
| P3OP03 Auth/Consent/Isolation | database | P3M05, P3M06 | Cross-user exposure 0; operational source P3-03 Gate must be evidenced | planned | `coordination/evidence/P3OP03/` | pending |
| P3OP04 API/RAG orchestration | api | P3M10, P3M11, P3M12, P3M13 | Preserve Citation/abstention/version trace; operational source P3-04 Gate must be evidenced | planned | `coordination/evidence/P3OP04/` | pending |
| P3OP05 Web/PWA experience | ui | P3M14, P3M15 | Mobile/desktop network failure recovery; operational source P3-05 Gate must be evidenced | planned | `coordination/evidence/P3OP05/` | pending |
| P3OP06 Deployment | foundation | P3M18, P3M19, P3M20, P3M24 | Rebuild, smoke and rollback; operational source P3-06 Gate must be evidenced | planned | `coordination/evidence/P3OP06/` | pending |
| P3OP07 Data lifecycle | database | P3M04, P3M15, P3M22 | Restore and deletion consistency; operational source P3-07 Gate must be evidenced | planned | `coordination/evidence/P3OP07/` | pending |
| P3OP08 Observability | foundation | P3M16, P3M25 | Failure detection without PII; operational source P3-08 Gate must be evidenced | planned | `coordination/evidence/P3OP08/` | pending |
| P3OP09 Security/GenAI | foundation | P3M02, P3M06, P3M12, P3M21 | No critical open finding; operational source P3-09 Gate must be evidenced | planned | `coordination/evidence/P3OP09/` | pending |
| P3OP10 Capacity/performance | foundation | P3M17, P3M23 | Measured approved workload; operational source P3-10 Gate must be evidenced | planned | `coordination/evidence/P3OP10/` | pending |
| P3OP11 Beta/launch | foundation | P3M20, P3M24, P3M25 | Launch evidence and supervisor Go/No-Go; operational source P3-11 Gate must be evidenced | planned | `coordination/evidence/P3OP11/` | pending |

## Independent cross-cutting acceptance items

- [ ] **P3X01** mandatory unit/contracts, API+DB migration, cross-user/RLS, browser E2E, RAG regression, load/soak/provider outage, backup/restore, Web/API/GenAI security, RTL/accessibility. Source: operational §14. Owner foundation coordinator + specialist test owners. Dependencies M03–M23. Output real test reports. Criterion all required checks evidenced; state planned; evidence `coordination/evidence/P3X01/`; supervisor pending.
- [ ] **P3X02** Phase 4 handoff and nonactivation: prepare extension contracts only, exclude assessments, financial files, personal action/coaching and broad admin. Source: operational §17–18; master roadmap §8–9. Owner foundation. Dependencies M24–25. Output handoff decision. Criterion supervisor-confirmed boundary and operational handoff; state planned; evidence `coordination/evidence/P3X02/`; supervisor pending.

## Document conflicts — hold for decision

1. Export: operational P3-04/P3-07/P3-11 require export in flows/launch; modular M15 says export only if Scope approved. **Unresolved**.
2. Support: operational limited support/admin, while full panel belongs to Phase 4. **Propose minimal audited operations; unresolved access policy**.
3. Web/PWA: operational responsive Web/PWA baseline vs modular §12 defers advanced PWA. **No advanced feature activated**.
4. Sample SLOs in operational plan are nonbinding until real workload/Module 01 Freeze.
5. NB23 draft schema and C012 readiness do not satisfy Module 00 accepted handoff.

## Parallel work sequencing

**Now:** foundation docs/checklist, UI RTL and safe states as draft, DB conceptual entities/isolation, API draft product envelope only. **Blocked by NB23/Module00:** live RAG adapter, streaming, source resolver, real producer outcome mapping, authoritative version lock, production readiness. **Later:** migration, integration, auth, operations, staging, production and full Gates after decisions and evidence.

**Links:** UI task records `coordination/tasks/AGENT-UI-*.md`, DB `coordination/tasks/AGENT-DATABASE-*.md`, API `coordination/tasks/AGENT-API-*.md`; refer to canonical P3M IDs and report evidence, never separate progress scores.
