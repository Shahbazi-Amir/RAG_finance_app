# DATABASE_F3 — رسید تحویل فاز سه به Foundation / API

**تاریخ:** 2026-11-23  
**وضعیت:** `DB_CANDIDATE_ISOLATED_CI_PASS` — `PHASE3_FULL_ACCEPTANCE=NOT_COMPLETE`  
**دامنهٔ پذیرش:** نصب تازهٔ PostgreSQL، Ledger، ACL/RLS، TLS، بررسی اتصال کد واقعی DB سرویس‌ها، Backup/Restore، آزمون Owner مصنوعی و بازگشت Migration 009/010 در **Docker آزمایشی GitHub**. **نه** HTTP Signed BFF یا پذیرش دموی مک.

## ۱. نسخهٔ قطعی و مرجع مصرف

| مشخصه | مقدار |
|---|---|
| مخزن / Draft PR | [Shahbazi-Amir/RAG_finance_app #59](https://github.com/Shahbazi-Amir/RAG_finance_app/pull/59) |
| SHA کد دقیقاً آزموده‌شده | `0e301a26096cb9f8c2b8e3fde3e20e9a1add48a5` |
| CI نهایی | [45109023781](https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/45109023781) — **SUCCESS** (Job اصلی؛ آزمون 011 عمداً SKIPPED) |
| آزمون 011 جدا | [45108041850](https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/45108041850)، attempt 2 — SUCCESS هر دو Job |
| image دیتابیس | `public.ecr.aws/docker/library/postgres@sha256:73bedc9eaa0121b92b9b26bb52e5141b3f6f37479c7ef913c0160455763ca80a` |
| platform / version | `linux/amd64` / PostgreSQL `17.11` |
| Manifest 001–010 SHA-256 | `9ff95a59570f5f6c6188479d9c37cf684ef836c599e89d9faa2bb0e17a4946f7` |
| DB کاندیدا / Restore | `rag_finance_f3_lab` / `rag_finance_f3_lab_restore` |
| کلاستر کاندیدا / Restore | `7711211396837249083` / `7711211511309865019` (متفاوت) |
| Backup SHA-256 | `4a033bde401cefbdc54fe1a1567fe204725cb7adbec045f634060b242d680d72` |
| ZIP شواهد CI SHA-256 | `039dab9a485e8c8f1ba67fe3a48463b63f1f30842b44f37d4f6f20c4548772ae` |

پس از همین SHA، فقط مستندات تخصصی و رسیدهای جدید به PR اضافه می‌شوند؛ برای مصرف کد اجرایی، **SHA آزموده‌شده بالا** را مبنا بگذارید، نه آخرین HEAD بدون مقایسهٔ Diff.

## ۲. نتایج ثبت‌شدهٔ اجرایی

- Manifest و سورس دقیق ۲۰ Git Blob برای 001–010؛ اجرای مرتب ۱۰ Migration و ثبت ۱۰ رکورد `APPLIED` دارای زمان، transaction ID، Git Blob و SHA-256؛ اگر `STARTED` بی‌نتیجه بماند بازپخش خودکار ممنوع.
- DB55 در حالت `private_no_dispatch` و Bridge Grantهای محدود؛ هیچ Migration شمارهٔ 011 در زنجیرهٔ پایه نیست.
- **۱۴ جدول** فعال، همگی FORCE RLS، **۱۷ Foreign Key** و **۳۸ Index** در PostgreSQL واقعی. Data Dictionary و دو Query Plan مربوط به دیتای کم‌حجم در ZIP موجود است؛ سرعت Query در بار واقعی هنوز پذیرفته نشده.
- اتصال **دو نقش Product** (`history_app`, `auth_revoker`) و **هفت نقش Bootstrap** (از جمله `auth_trust_api`, `auth_login_*`, `auth_mapper`) از داخل دو فرآیند مستقل که **توابع واقعی بررسی DB کد API/Bootstrap** را بارگذاری کرده‌اند؛ TLS `verify-full` در کلاستر اصلی و Restore، ۹/۹ PASS؛ معکوس‌سازی نقش و TLS ضعیف DENIED؛ Auth Direct SELECT منفی ۷۲/۷۲ PASS.
- Backup `pg_dump -Fc` و بازگردانی به Volume و **کلاستر PostgreSQL مستقل**؛ تطبیق رکوردبه‌رکورد Ledger، نقش‌ها، ACL/RLS، DB55 و اتصال مجدد ۲+۷ نقش به کلاستر دوم PASS.
- Downgrade مهاجرت‌های `009/010` با رکورد Login ساختگی: **REFUSED**؛ پس از برداشتن دادهٔ ساختگی، DOWN→UP و DB55 مجدد **PASS**؛ آزمون صرفاً در کپی دورریختنی DB، نه تغییر تاریخچهٔ اصلی.
- مالکیت مصنوعی: دو Conversation و دو Message ساختگی پس از Restore حفظ شدند، RLS مالک را جدا کرد، وضعیت `deletion_requested` حفظ شد و ۰ Conversationِ مجدداً فعال برای مالک حذف‌خواسته دیده شد. زمان اندازه‌گیری‌شدهٔ این Restore کوچک **854 ms** است و هرگز RTO عملیاتی یا اثبات Hard Delete محسوب نمی‌شود.
- نسخهٔ آزمایشی `011` مستقلاً با `DB55/live_011`، ACL و Claim نامجاز PASS شد؛ فراخوانی Gateway صفر. `012+` ساخته نشد چون شروط حقوقی/قراردادی آن تصویب نشده است.

## ۳. دستور نصب و راستی‌آزمایی تازه برای Foundation

دقیقاً فایل‌های این Commit را از `infra/postgres/dev_f3_isolated/` مصرف کنید. Checkout باید تمام Git Refهای پین‌شدهٔ `001–010`, `DB55`, و `c5e271d...` برای کد بررسی DB اپلیکیشن را در Object Store داشته باشد. روی Mac هیچ DB/Volume پذیرفته‌شده‌ای را انتخاب نکنید.

```bash
export SOURCE_REPO='/absolute/path/to/full/RAG_finance_app/git/checkout'
export LAB_ROOT='/absolute/new/f3-db-candidate-isolated'
cd "$SOURCE_REPO/infra/postgres/dev_f3_isolated"

bash scripts/00_prepare_source.sh
bash scripts/01_create_isolated_lab.sh
bash scripts/02_provision_roles.sh
bash scripts/03_apply_pinned_001_010.sh
bash scripts/04_bridge_and_db55.sh
bash scripts/05_test_roles_tls_rls.sh
bash scripts/09_shared_stack_db_preflight.sh
bash scripts/06_backup_restore_independent.sh
bash scripts/10_restored_stack_db_preflight.sh
bash scripts/13_catalog_erd_inventory.sh
bash scripts/12_rollback_rls_constraints_probe.sh
bash scripts/14_synthetic_owner_lifecycle_restore.sh

# مرحلهٔ صادرات رسید: مسیر خروجی صرفاً محلی و تازه است
export GITHUB_WORKSPACE="$LAB_ROOT/export"
mkdir -p "$GITHUB_WORKSPACE"
bash scripts/11_export_sanitized_receipt.sh
```

این بسته Docker Desktop/Compose، Git refs اصلی، Bash، OpenSSL، `shasum` و Python 3 را لازم دارد. نصب برای image `linux/amd64` و شبکهٔ داخلی بدون Port عمومی است. سرویس‌های DB-client آزمایشی **معادل راه‌اندازی ASGI HTTP نیستند**؛ Product و Bootstrap واقعی bind حلقه‌ای `127.0.0.1` دارند و Foundation باید توپولوژی مشترک BFF/namespace را تعیین کند.

## ۴. وضعیت ۵۷ ردیف و موانع واقعی

| وضعیت پیاده‌سازی در دامنهٔ محدود | تعداد |
|---|---:|
| DONE | **4** |
| OPEN | **29** |
| BLOCKED | **24** |

**منبع ردیف‌به‌ردیف:** `docs/PHASE3_57_ROW_DATABASE_AUDIT_20261123.md` در Draft #59، و فایل مستقل `DBF3_PHASE3_57_ROW_AUDIT_20261123.md`. هر ۵۷ ردیف دارای معیار، مالک، Source SHA، محیط، وضعیت آزمون، شاهد و ورودیِ باز است. دفتر رسمی `coordination/phase3_checklist.md` فقط توسط Foundation ویرایش می‌شود؛ این گزارش آن را تغییر نداده است.

مواردی که اکنون **مانع قرارداد/دسترسی تازه** هستند:

1. **Foundation/Ops:** رسید واقعی مک از HTTP/HTTPS Signed BFF→Product API/Bootstrap با احراز هویت IdP، `current_user` واقعی ۹ اتصال، CA/SAN، A/B isolation و Count=1 C018/Refresh=0. اسکریپت‌های CI جای این شاهد نیستند. درخواست دقیق در PR #55، Comment `7091123453` ثبت شد.
2. **API/Owner/Security:** Consent و Withdrawal، Feedback و Idempotency، Hard Delete/Tombstone و Retention، Export مستقل، Audit، هویت `owner_id` در برابر `user_id`، قرارداد واقعی Citation/Model/Knowledge lineage و T3. تا نسخه و سیاست تصویب نشود، SQL جدید `012+` حدسی ممنوع است. درخواست دقیق در PR #61، Comment `7091124216` ثبت شد.
3. **Security/Ops:** RPO/RTO عددی، رمزگذاری و مدیریت کلید بکاپ، PITR/WAL، Snapshot امن Qdrant و تضمین عدم بازگشت دادهٔ hard-deleted از Restore. زمان 854ms فقط روی دو رکورد ساختگی سنجیده شده و SLA نیست.
4. **CENTRAL:** اتمام واقعی Gateهای P3M03/04/06/10/15/22 پس از دریافت شاهد صاحبان مربوطه؛ CI موفق DB مجوز انتشار یا Merge نمی‌دهد.

## ۵. حفاظت دادهٔ مک و مرز انتقال

- DB پذیرفته‌شدهٔ مک: `rag_finance_f3_demo`. Volume پذیرفته‌شده: `rag_finance_f3_demo_pg17_20261121`. **هیچ SQL، Container یا Volume عملیاتی روی آن اجرا/تغییر نکرد.**
- استثنای تاریخی DB55 مک **دفتر واقعی اجرای 001–010 را بازسازی نمی‌کند**؛ Ledger واقعی این رسید فقط متعلق به کاندیدای آزمایشی جدید است.
- 011 در مسیر توسعه و تست جدا می‌ماند؛ `NO_DISPATCH_ONLY` و صفر Gateway حفظ شده‌اند. آروان تا تصمیم انتشار HOLD است.
- تمام داده‌های آزمون کاربران، مصنوعی‌اند؛ کلیدهای خصوصی TLS، فایل‌های Password، DSN واقعی، PII و Dump خام در ZIP تحویلی نیستند.

**نتیجهٔ مأموریت:** بستهٔ توسعهٔ مستقل برای نصب PostgreSQL و اتصال DB واقعی Product/Bootstrap و بازیابی کامل در آزمایشگاه **قابل‌مصرف و آزموده‌شده** است؛ ولی **پذیرش انتهابه‌انتهای مک و سیاست حذف/بکاپ کامل** به شاهد و تصمیم مالک دیگر وابسته است، بنابراین `PHASE3_FINAL_ADMISSION=NOT_ISSUED`.
