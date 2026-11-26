# تصمیم‌های رسمی مالک (CENTRAL / Owner) — ۲۶ نوامبر ۲۰۲۶

**وضعیت:** APPROVED_BY_OWNER  
**دامنه:** فاز سوم (`app-only`) — مخزن `Shahbazi-Amir/RAG_finance_app`  
**مبنای اجرا:** PR #143 (`bbb0faa82a3dbf9e63bafe9fb4437717f7c02550`)

## ۱. تثبیت تنها خط تحویل (P0-1)
- **کاندیدای واحد:** شاخهٔ `#143` (`bbb0faa82a3dbf9e63bafe9fb4437717f7c02550`) به‌عنوان تنها خط تحویل آزمایشگاهی و مبنای ترفیع داخلی روی `#84` تأیید می‌شود.
- **بستن شاخه‌های موازی:** پس از انتقال دلتاهای ضروری از `#146` (API)، `#134` (DB) و `#147` (UI) به خط واحد، تمام PRهای موازی و قدیمی به‌عنوان `superseded` نشانه‌گذاری و بسته می‌شوند. هیچ شاخهٔ کاندیدای جدیدی ساخته نشود.

## ۲. تعیین تکلیف ۱۶ مسیر اختلافی ممیزی ۵۸ مسیر
- نسخهٔ نگه‌داشته‌شدهٔ Foundation در `#143` برای هر ۱۶ مسیر (`proposed_keep`) به‌صورت رسمی **تأیید و امضا** می‌شود تا مانع `owner_signed=0` برطرف شود.
- هرگونه تغییر بعدی روی این ۱۶ فایل فقط با گزارش باگ یا assertion شکست‌خورده در CI واحد مجاز است.

## ۳. تصمیم‌های محصولی و امنیتی برای باز کردن M01 / M05 / M10 / M15
- **روش ورود (H-DEC-01 / M05-A02):** روش ورود محصول منحصراً OIDC است. ورود با رمز عبور داخلی در فاز ۳ خارج از دامنه است؛ بنابراین `P3M05-A02` (Password hashing) رسماً `N/A_APPROVED` ثبت می‌شود.
- **رفتار Send در `app-only` (H-DEC-02 / M10):** دکمهٔ Send تا زمان اتصال رسمی موتور غیرفعال می‌ماند و endpoint مربوط با کد قراردادی `503` و صفر اثر durable/DB/dispatch پاسخ می‌دهد.
- **دامنهٔ Privacy و Mutation (H-DEC-05 / M15):** پیاده‌سازی نهایی Consent/Withdrawal، Delete، Export و Feedback به فاز بعد از استقرار `app-only` موکول می‌شود. در این مرحله فقط قراردادها (Schema/Contract tests) معتبرند و مسیرها read-only باقی می‌مانند.

## ۴. فریز مخرج `app-only` (P0-6)
- معیار خروج مرحلهٔ `app-only` (پیش از مرحلهٔ سرور و موتور) منحصراً بستن شواهد روی SHA واحد برای این مجموعه است:
  `M02`، `M03`، `M04`، `M05 (OIDC subset)`، `M06`، `M13 (History/Health subset)`، `M14 (History/A11y/3-browser subset)`، `M18`، `M22 (PG Backup/Restore/PITR)`.
- Gateهای وابسته به موتور (`M00`، `M07–M12`، بخش‌های تولیدی `M13–M17` و `M23–M25`) تا زمان صدور فرمان صریح «مرحله موتور» و «مرحله سرور» در وضعیت `DEFERRED_BY_SCOPE` باقی می‌مانند.

## ۵. پذیرش موقت ریسک و بستن دامنهٔ آزمایشگاهی app-only — ۲۶ نوامبر ۲۰۲۶

**وضعیت: APPROVED_BY_OWNER**

- **پذیرش ریسک موقت (Lab / App-Only):** سه CVE فاقد نسخهٔ اصلاحی در Debian Bookworm (`CVE-2023-45853`، `CVE-2025-7458`، `CVE-2026-6653`) و مرز اعتماد فعلی `app.owner_id` (مستندشده در [APP_ONLY_SECURITY_CRITICAL_GUC_20261126.md](integration/APP_ONLY_SECURITY_CRITICAL_GUC_20261126.md)) برای محیط آزمایشگاهی `app-only` به‌صورت موقت پذیرفته می‌شوند و بازبینی نهایی آن‌ها به پیش از Production Launch موکول می‌شود. ۶ Critical و ۲۰۹ High در چهار ایمیج محصولی باقی است؛ این تصمیم پذیرش کلی Highها یا مجوز Production نیست. GUC برای SQL مستقیم همچنان قابل جعل است. هیچ یافته‌ای حذف یا threshold تغییر نمی‌کند.
- **شاهد اجرایی:** PR #143 روی SHA آزموده‌شده `4882df4ba3026ea5ab8ad1c473d50aa0d07ca6b5`؛ هر ۹ Run موفق: [45740167408](https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/45740167408)، [45740167477](https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/45740167477)، [45740167492](https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/45740167492)، [45740167493](https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/45740167493)، [45740167509](https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/45740167509)، [45740167575](https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/45740167575)، [45740175901](https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/45740175901)، [45740175904](https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/45740175904)، [45740175994](https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/45740175994). [اسکن ایمیج](https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/45740175994/artifacts/15081395511)، [شواهد DB](https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/45740175994/artifacts/15080419641)، [اسکن منبع](https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/45740175994/artifacts/15080841624). پذیرش صرفاً شواهد آزمایشگاهی همین SHA است؛ CI کامیت مستنداتی بعدی جداگانه باید بررسی شود.
- **رجیستر:** 9 Gate در دامنهٔ محدود app-only و 64 فعالیت دارای شاهد با `CI_VERIFIED / APP_ONLY_LAB_ACCEPTED` ثبت شدند؛ نه پذیرش کامل معیارهای اصلی Gateها. `git_sha` منشأ تاریخی معیار است و ثابت مانده؛ SHA اجرای واقعی در `tested_scope` و `run_or_env` ثبت شده. همهٔ ۳۹۳ شناسه، متن معیار/dependency، ۱۰۵ Crosswalk، سطرهای خارج از دامنه و سطرهای بدون شاهد کافی بدون تغییر باقی مانده‌اند. آزمون تاریخی `test_no_acceptance_without_real_receipts` انتظار frozen/NOT_ACCEPTED همهٔ سطرها را دارد و پس از این تصمیم نیازمند بازنگری مجاز جداگانه است؛ این نوبت هیچ تست یا کدی تغییر نمی‌کند. M05-A02 طبق بخش ۳ N/A_APPROVED است، نه CI_VERIFIED.

| ماژول | فعالیت‌های دارای شاهد و پذیرش آزمایشگاهی | سطرهای دیگر همان ماژول (بدون تغییر؛ خارج از slice یا فاقد شاهد کافی) |
|---|---|---|
| M02 (8) | A01، A02، A03، A04، A05، A07، A09، A10 | A06، A08 |
| M03 (7) | A01، A02، A03، A04، A05، A08، A09 | A06، A07 |
| M04 (5) | A01، A02، A03، A06، A07 | A04، A05، A08، A09 |
| M05 (6) | A01، A03، A04، A05، A07، A10 | A02، A06، A08، A09 |
| M06 (7) | A01، A02، A03، A05، A06، A07، A09 | A04، A08 |
| M13 (8) | A02، A03، A04، A06، A07، A08، A09، A10 | A01، A05 |
| M14 (7) | A01، A02، A03، A09، A10، A11، A12 | A04، A05، A06، A07، A08 |
| M18 (10) | A01، A02، A03، A04، A05، A06، A07، A08، A09، A10 | — |
| M22 (6) | A01، A06، A07، A08، A09، A10 | A02، A03، A04، A05 |

**مرز پذیرش:** Gateها فقط برای شواهد History/Health/OIDC و PG و قراردادها/زیرساخت آزمایشگاهی موجود هستند. اعتبارسنجی کامل OpenAPI، سیاست‌های تأییدنشده، revoke-all/lockout، رمزگذاری/retention بکاپ، RPO/RTO مقصد، Qdrant، موتور، داده/مدل واقعی و Production خارج از پذیرش این تصمیم‌اند. M21 خارج از مخرج مصوب و بدون تغییر است.

### صف بستن دستی PRهای موازی

PRهای صریحاً تعیین‌شده توسط مالک: #88، #116، #134، #146، #147؛ پیام پیشنهادی `superseded by #143 (4882df4b)`. سایر کاندیداهای موازی باز (بازبینی دلتاهای اختصاصی قبل از بستن، بدون ادعای انتقال کامل همهٔ قابلیت‌ها): #79، #80، #81، #85، #86، #87، #89، #90، #91، #92، #93، #94، #95، #96، #97، #98، #99، #100، #101، #102، #103، #104، #105، #106، #107، #108، #109، #110، #111، #112، #113، #114، #115، #117، #118، #119، #120، #121، #122، #123، #124، #125، #126، #127، #128، #129، #130، #131، #132، #133، #135، #136، #137، #138، #139، #140، #141، #142، #144، #145. در مجموع 65 PR باز در این صف؛ #84 (مبنای ترفیع) و #143 حفظ شوند. هیچ PR یا شاخه‌ای در این نوبت بسته/حذف نشده است.
