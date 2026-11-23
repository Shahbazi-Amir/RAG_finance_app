# DATABASE_F3 — گزارش تجمیعی تحویل اجرایی و مرز پذیرش فاز ۳
**تاریخ:** 2026-11-23 · **مخزن نوشتنی:** `Shahbazi-Amir/RAG_finance_app` · **شاخه:** `agent/database-f3-fresh-install-isolated-20261122` · **Draft PR:** [#59](https://github.com/Shahbazi-Amir/RAG_finance_app/pull/59)

> این گزارش شاهد کد و CI مستقل است؛ پذیرش واقعی مک/محصول، Gate ماژول، تولید پاسخ و انتشار را اعلام نمی‌کند. رجیستر رسمی فقط تحت اختیار Foundation/CENTRAL تغییر می‌کند. دادهٔ مصنوعی/CI جای دادهٔ واقعی و RTO مصوب نیست.

## ۱. پین نسخه و اختلاف Foundation
- **SHA آخرین کد آزموده‌شده:** `996dfc9b66cf8cbd4b37b7a267d08cc5acd5deba` — [CI 45202743968 SUCCESS](https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/45202743968). Job پایه SUCCESS و Job اختیاری 011 عمدتاً SKIPPED (موفقیت 011 از شاهد جدا).
- **پین قدیمی Foundation در `c2edbbf87f02ff2cfb8ba12a0a9594533324fd28`:** `b6b79369006eca3a1e4c8e75a9ba4ab14d0fab74` — [CI 45082326382](https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/45082326382).
- **تفاوت مؤثر:** SQL بیست‌فایلی و Migrationهای 001–010، Image PostgreSQL و قرارداد Runtime نقش‌ها **تغییر نکرده‌اند**؛ ولی **installer `scripts/03_apply_pinned_001_010.sh` تغییر اجرایی دارد**: Git Blob قدیم `a30dbebe5b787db61b4f91c035d255f8160029d1` ← **جدید `9cc9458c55b82f03811b346259ccf2ae3dce318d`**. این نسخهٔ جدید Ledger را علاوه بر manifest به SHA-256، source commit، هویت کلاستر، TX/time و وجود واقعی ۱۴ جدول و FORCE RLS گره می‌زند. Foundation باید installer و شواهد جدید را repin کند؛ نباید Migration یا SQL جدیدی اختراع شود.
- **Manifest SHA256:** `9ff95a59570f5f6c6188479d9c37cf684ef836c599e89d9faa2bb0e17a4946f7`، فایل نسخه‌دار `MIGRATIONS_001_010_PINNED.tsv`، Git Blob `f67f5e985c45ae9b6a6c68417ebc54ba05ec7fdf`.
- **Image digest:** `public.ecr.aws/docker/library/postgres@sha256:73bedc9eaa0121b92b9b26bb52e5141b3f6f37479c7ef913c0160455763ca80a` با `platform=linux/amd64`.
- **PG:** `17.11`، DB پایهٔ CI `rag_finance_f3_lab` و Restore `rag_finance_f3_lab_restore` در Docker private-network؛ محصول، IdP و C018 در CI دیتابیس راه‌اندازی کامل HTTP نشدند.

## ۲. نتیجهٔ اجرای مستقل روی محیط آزمایشی
| حوزه | شاهدِ مستقیم | نتیجه و مرز |
|---|---|---|
| Fresh | 20/20 pin، Ledger ده Entry، no-rerun و DB55 `private_no_dispatch` | PASS، با هویت اصلی کلاستر ثبت‌شده در Artifact |
| TLS و نقش‌ها | نه نقش با `verify-full`؛ Product `history_app` و `auth_revoker`، هفت نقش Bootstrap | 9/9 PASS؛ Product source preflight 2/2، Bootstrap source preflight 7/7 روی source و Restore |
| ACL/RLS | ۱۴ جدول واقعی Auth/History، ۱۷ FK، ۳۸ Index، تمام جدول‌ها FORCE RLS و ۷۲ تست منع SELECT | PASS در CI؛ تست HTTP Owner A/B مک هنوز NOT_RUN |
| Rollback 009/010 | DOWN در حضور Login Attempt رد شد؛ DOWN/UP بدون شواهد Login در clone با DB55 | PASS، فقط در clone؛ rollback همهٔ 001–010 روی دادهٔ واقعی اثبات نشده |
| Data-bearing upgrade | دیتابیس با History و session معتبر/لغوشده، Backup پیش از 009، Restore مستقل، سپس 009+010 روی هر دو کلاستر | PASS — [CI 45199834089](https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/45199834089) و CI نهایی؛ Ledger clone **تاریخچهٔ اجرای واقعی محسوب نشد** |
| Ledger fault injection | کلاستر دوم، STARTED، duplicate، digest drift، timestamp/TX missing، ده رکورد APPLIED ساختگی بدون Schema | همه Fail Closed/PASS؛ پروژه/Volume موقت تست حذف شد |
| Query plan | ۲۴۰۰ Conversation و ۴۸۰۰ Message دو مالک، `EXPLAIN ANALYZE` | هر دو ایندکس `conversation_order_idx` و `message_order_idx` استفاده شدند؛ پاسخ نمونه 0.050 و 0.047ms — **نه SLO عملیاتی** |
| Backup/Restore | `pg_dump -Fc` + SHA256 و بازیابی در کلاستر مستقل با Ledger، DB55، نقش‌ها و FORCE RLS | PASS؛ Backup SHA256 `24e01ee55b371a2611056f639de4f6c831b17aa5593c64ccf85872b6ba3f99e2` |
| Soft-state | دو مالک ساختگی و `deletion_requested` بعد از Restore | بدون reappearance در فهرست active، زمان Restore نمونهٔ کم‌داده 895ms؛ **Hard Delete/anti-resurrection و RPO/RTO مصوب، انجام‌نشده** |
| 011 | CI `45108041850` attempt 2، یک آزمایشگاه مجزا | DB Claim/RLS PASS و Gateway=0؛ **011 خارج از مسیر `private_no_dispatch`** |
| 012+ | Consent/Feedback/Deletion/Audit/Citation هنوز قرارداد مصوب ندارد | **هیچ SQL حدسیِ 012+ ساخته نشد** |

Artifact واقعی: [GitHub Actions #45202743968 / Artifact 14831408848](https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/45202743968/artifacts/14831408848) با ۹ فایل sanitized: Ledger و هویت کلاسترها، Data Dictionary واقعی ۱۴ جدول، Planهای خالی و داده‌دار، دو رسید Restore، Ledger-fault receipt و SHA کاتالوگ. `f3_db_candidate_consumption.json` شامل اطلاعات شخصی یا Secret نیست.

## ۳. نصب مصرف‌پذیر و ترتیب اجرا
در **کاندیدای تازه و مجاز**، اجرای Python/Mac محصول و PostgreSQL قدیمی دست‌نخورده می‌ماند. از `infra/postgres/dev_f3_isolated/`، پس از ساخت `LAB_ROOT` *کاملاً تازه* و `SOURCE_REPO` گیت:
```bash
bash scripts/00_prepare_source.sh
bash scripts/01_create_isolated_lab.sh
bash scripts/02_provision_roles.sh
bash scripts/03_apply_pinned_001_010.sh
bash scripts/04_bridge_and_db55.sh
bash scripts/05_test_roles_tls_rls.sh
bash scripts/09_shared_stack_db_preflight.sh
bash scripts/06_backup_restore_independent.sh
bash scripts/10_restored_stack_db_preflight.sh
```
اسکریپت‌های `12` تا `17` **فقط برای محیط CI disposable و کپی‌های جدا** هستند؛ روی DB محصول پذیرفته‌شده اجرا نشوند. Runbook اصلی: `contracts/FOUNDATION_CANDIDATE_SHARED_DB_HANDOFF.md`. Connection credentials، CA/private key و بافت host از Ops دریافت و در Secrets خارج از Git نگهداری شوند. هیچ PostgreSQL Port عمومی باز نشود. هویت Runtime نقش‌ها باید روی **Process واقعی Product/Bootstrap** و نه صرفاً preflight آزمایشی ثبت شود.

## ۴. تطبیق کامل با دو نقشهٔ رسمی
- نقشهٔ ماژولار فقط‌خواندنی `RAG_finance@7c74783c3dcda897b010ba9ea358d113f172ed1f`، blob `53b44fbc9196bdd7c2d4a8f84a90676894bc210d`؛ عملیاتی blob `8d7e9549f91369d9ca3bbfe107db8c62ca835f18`. هر دو با `references/phase2/source_manifest.json` سازگارند.
- رجیستر رسمی `coordination/phase3_checklist.md@c2edbbf87f02ff2cfb8ba12a0a9594533324fd28`، blob `2bddf96c5218caf63605e466a8ce3d30544f44ea`: **۲۶۲ فعالیت و ۲۶ Gate مستقل**، تاریخی `blocked=38`، `planned=172`، `review=41`، `active=11`. این اعداد بازشماری پیاده‌سازی نیستند.
- دستور آپلودی حاوی **۱۷۱** شناسهٔ P3M و **۹۵** شناسهٔ P3OP بود؛ رجیستر رسمی **۱۰۵** شناسهٔ P3OP دارد. **۱۰ شناسهٔ غایب از دستور در CSV نگه داشته شده‌اند**: `P3OP01-R01,R06,R09`, `P3OP04-R13,R15`, `P3OP05-R01,R07,R08,R09,R10`.
- پروندهٔ تخصصی ۵۷ ردیفی در `docs/PHASE3_57_ROW_DATABASE_AUDIT_20261123.md`: وضعیت **۴ DONE محدود DB/CI، ۲۹ OPEN، ۲۴ BLOCKED** در دامنهٔ همان سند. در ۱۰ ردیف مرتبط شاهد CI نهایی افزوده شد، ولی وضعیت Gateها بی‌سند تغییر نکرد.
- سه جدول CSV مستقل در همین پوشه: `PHASE3_262_ACTIVITY_DB_SCOPE_RECONCILIATION_20261123.csv`، `PHASE3_105_OP_NONCOUNTING_RECONCILIATION_20261123.csv`، `PHASE3_26_MODULE_GATES_RECONCILIATION_20261123.csv`. شناسهٔ P3OP شمارش مجدد ندارد. **CSV ۹۲ردیفی ادعاشده در دستور، مسیر/فایلِ قابل‌بازیابی نداشت؛ تطبیق ادعایی با آن انجام نشده است.**

## ۵. ورودی دقیق مالک‌های بعدی
- **Foundation/Ops:** در کاندیدای جدا، نسخهٔ دقیق installer blob `9cc9458...` و image/manifest بالا؛ اجرای واقعی Product/Bootstrap با ۹ نقش؛ `verify-full`، CA/SAN، Postgres hostname، A/B signed HTTPS/BFF/IdP، session/revoke/404، C018 فقط با اجازهٔ NO_DISPATCH_ONLY (یک OS spawn، top10=10، `generation_calls=0`, `answer=null`, بدون POST پس از Refresh)، یک رسید sanitize شدهٔ هم‌بسته با یک SHA. نزد Foundation وضعیت CI با پذیرش Mac یکی نیست.
- **API + Owner + Security:** قرارداد نسخه‌دار و تصمیم قابل‌اجرا برای `owner_id`/ `user_id`، Consent/withdraw، Feedback+Answer FK+idempotency، deletion/retention/tombstone و post-revoke، Audit/PII redaction. SQL 012+ فقط پس از این ورودی و آزمون‌های جدا.
- **ENGINE + API:** Release/NB23 پذیرفته، Citation/Attribution/Locator واقعی و نسخه‌های knowledge/retrieval/model/policy؛ هیچ `source_id` مشاهده‌شدهٔ تأییدنشده را Citation معتبر فرض نکن.
- **Ops/Security/Owner:** هدف عددی RPO/RTO با داده/بار واقعی، encryption و key custody، rotation/PITR و Qdrant snapshot تحت no-write window، سپس آزمایش Real restore.
- **CENTRAL:** تصمیم مستقل برای پذیرش Gate و هرگونه Arvan/Dispatch/انتشار؛ DB فقط بستهٔ شواهد می‌دهد.

## ۶. محافظت و پایان
`rag_finance_f3_demo` و Volume `rag_finance_f3_demo_pg17_20261121` در محیط مک در این مأموریت دست‌نخورده‌اند. استثنای تاریخی DB55 روی مک **نباید** به‌عنوان اجرای اثبات‌شدهٔ Migration Ledger بازنویسی شود. `011` صرفاً توسعهٔ جداست؛ `012+` بدون قرارداد مجاز نیست. Auth/OIDC واقعی، BFF/HTTP و C018 روی مک را این CI ثابت نمی‌کند؛ آروان HOLD.

**حالت نهایی:** `DATABASE_F3_ISOLATED_CI=PASS`، `FOUNDATION_INSTALL_CONSUMABLE=YES_WITH_REPIN`، `MAC_RUNTIME_ACCEPTANCE=NOT_PROVEN`، `P3M04/P3M06/P3M15/P3M22_GATE_ACCEPTANCE=NOT_GRANTED`، `PHASE3_100_PERCENT=FALSE`.
