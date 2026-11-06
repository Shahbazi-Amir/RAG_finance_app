# AGENT-DB-01 — چک‌لیست مصوب v2

**وضعیت onboarding:** `ONBOARDING_ACCEPTED — IMPLEMENTATION_WAITING_FOR_FOUNDATION`. این فقط پذیرش نسخهٔ چک‌لیست است؛ **هیچ فعالیت اجرایی یا Gate پذیرفته یا تست نشده است**. صاحب پرونده متخصص مربوطه است؛ نسخهٔ اولیه با مجوز ناظر توسط Foundation ثبت شده است.

**دامنه:** PostgreSQL محصول؛ نه Qdrant و نه Object Storage. Commit تاریخی 660566e، Starting Commit اجرا نیست. پذیرش Foundation و تعیین commit و مسیرهای اجرایی شرط آغاز کار است.

**سیاست:** تیک صرفاً پس از اجرای واقعی معیار، ثبت شاهد و checks مجاز است. وضعیت‌ها `planned / active / blocked / review / accepted` و رأی ناظر جدا هستند. `P3Mxx` دفتر اصلی و تنها مرجع شمارش است.

## فعالیت‌ها — هیچ موردی اجرا نشده است

- [ ] **DB01-01** — بازبینی Foundation و مالکیت؛ M01/03
  - **ارتباط چک‌لیست اصلی:** P3M01, P3M03
  - **وابستگی:** Foundation پذیرفته‌شده
  - **خروجی/معیار پذیرش:** تطبیق HEAD، PR، AGENTS و ownership؛ بدون تداخل
  - **وضعیت:** `planned` (پیاده‌سازی هنوز مجاز نشده)؛ **Implemented:** NOT_RUN؛ **Checks:** NOT_RUN؛ **Evidence:** NOT_AVAILABLE؛ **پذیرش ناظر برای اجرا:** pending.

- [ ] **DB01-02** — ERD و Data Dictionary؛ M04، P3OP02
  - **ارتباط چک‌لیست اصلی:** P3M04, P3OP02
  - **وابستگی:** قرارداد پایه و Foundation
  - **خروجی/معیار پذیرش:** موجودیت‌ها، ستون‌ها، روابط و مالکیت مستند
  - **وضعیت:** `planned` (پیاده‌سازی هنوز مجاز نشده)؛ **Implemented:** NOT_RUN؛ **Checks:** NOT_RUN؛ **Evidence:** NOT_AVAILABLE؛ **پذیرش ناظر برای اجرا:** pending.

- [ ] **DB01-03** — PK/FK، Constraints و Index؛ M04
  - **ارتباط چک‌لیست اصلی:** P3M04
  - **وابستگی:** DB01-02
  - **خروجی/معیار پذیرش:** قیود معتبر؛ FK violation صفر؛ Query Plan بررسی‌شده برای مسیرهای مصوب
  - **وضعیت:** `planned` (پیاده‌سازی هنوز مجاز نشده)؛ **Implemented:** NOT_RUN؛ **Checks:** NOT_RUN؛ **Evidence:** NOT_AVAILABLE؛ **پذیرش ناظر برای اجرا:** pending.

- [ ] **DB01-04A** — Persistence با قرارداد provisional؛ M04/10/11
  - **ارتباط چک‌لیست اصلی:** P3M04, P3M10, P3M11
  - **وابستگی:** Draft مشترک و DB01-02
  - **خروجی/معیار پذیرش:** طراحی و آزمون ساختاری Answer/Claim/Citation/Attribution/Version Trace با Fixture؛ بدون ادعای صحت موتور
  - **وضعیت:** `planned` (پیاده‌سازی هنوز مجاز نشده)؛ **Implemented:** NOT_RUN؛ **Checks:** NOT_RUN؛ **Evidence:** NOT_AVAILABLE؛ **پذیرش ناظر برای اجرا:** pending.

- [ ] **DB01-04B** — تطبیق خروجی واقعی RAG؛ M00/04/11
  - **ارتباط چک‌لیست اصلی:** P3M00, P3M04, P3M11
  - **وابستگی:** Release و handoff پذیرفته‌شده
  - **خروجی/معیار پذیرش:** تطبیق واقعی schema، provenance، Citation و نسخه‌ها
  - **وضعیت:** `blocked` (پیاده‌سازی هنوز مجاز نشده)؛ **Implemented:** NOT_RUN؛ **Checks:** NOT_RUN؛ **Evidence:** NOT_AVAILABLE؛ **پذیرش ناظر برای اجرا:** pending.

- [ ] **DB01-05** — Migration و Rollback؛ M04، P3OP02
  - **ارتباط چک‌لیست اصلی:** P3M04, P3OP02
  - **وابستگی:** DB01-02/03
  - **خروجی/معیار پذیرش:** migration نسخه‌دار؛ اجرای موفق روی DB خالی و داده‌دار؛ rollback موفق
  - **وضعیت:** `planned` (پیاده‌سازی هنوز مجاز نشده)؛ **Implemented:** NOT_RUN؛ **Checks:** NOT_RUN؛ **Evidence:** NOT_AVAILABLE؛ **پذیرش ناظر برای اجرا:** pending.

- [ ] **DB01-06** — ذخیرهٔ Identity/Session/Consent؛ M04/05
  - **ارتباط چک‌لیست اصلی:** P3M04, P3M05
  - **وابستگی:** قرارداد Auth مصوب
  - **خروجی/معیار پذیرش:** Persistence و قیود متناسب؛ بدون پیاده‌سازی منطق ورود
  - **وضعیت:** `planned` (پیاده‌سازی هنوز مجاز نشده)؛ **Implemented:** NOT_RUN؛ **Checks:** NOT_RUN؛ **Evidence:** NOT_AVAILABLE؛ **پذیرش ناظر برای اجرا:** pending.

- [ ] **DB01-07** — Ownership Matrix و روابط امن؛ M04/06
  - **ارتباط چک‌لیست اصلی:** P3M04, P3M06
  - **وابستگی:** DB01-02 و Identity contract
  - **خروجی/معیار پذیرش:** مالک معتبر برای تمام داده‌های کاربر؛ مستقل از پذیرش RAG
  - **وضعیت:** `planned` (پیاده‌سازی هنوز مجاز نشده)؛ **Implemented:** NOT_RUN؛ **Checks:** NOT_RUN؛ **Evidence:** NOT_AVAILABLE؛ **پذیرش ناظر برای اجرا:** pending.

- [ ] **DB01-08** — RLS، FORCE RLS و نقش برنامه؛ M06، P3OP03
  - **ارتباط چک‌لیست اصلی:** P3M06, P3OP03
  - **وابستگی:** DB01-05/07 و Identity contract
  - **خروجی/معیار پذیرش:** USING/WITH CHECK، جلوگیری از bypass نقش برنامه و جداسازی Transaction Context
  - **وضعیت:** `planned` (پیاده‌سازی هنوز مجاز نشده)؛ **Implemented:** NOT_RUN؛ **Checks:** NOT_RUN؛ **Evidence:** NOT_AVAILABLE؛ **پذیرش ناظر برای اجرا:** pending.

- [ ] **DB01-09** — آزمون Cross-user و Repository؛ M06/21
  - **ارتباط چک‌لیست اصلی:** P3M06, P3M21
  - **وابستگی:** DB01-08
  - **خروجی/معیار پذیرش:** نشت افقی/عمودی و RLS bypass صفر؛ ID enumeration در همکاری با API
  - **وضعیت:** `planned` (پیاده‌سازی هنوز مجاز نشده)؛ **Implemented:** NOT_RUN؛ **Checks:** NOT_RUN؛ **Evidence:** NOT_AVAILABLE؛ **پذیرش ناظر برای اجرا:** pending.

- [ ] **DB01-10A** — ذخیرهٔ اتمیک با Fixture؛ M10
  - **ارتباط چک‌لیست اصلی:** P3M10
  - **وابستگی:** DB01-04A/05
  - **خروجی/معیار پذیرش:** Transaction، rollback خطا، عدم ثبت موفقیت ناقص و نبود Duplicate Persistence
  - **وضعیت:** `planned` (پیاده‌سازی هنوز مجاز نشده)؛ **Implemented:** NOT_RUN؛ **Checks:** NOT_RUN؛ **Evidence:** NOT_AVAILABLE؛ **پذیرش ناظر برای اجرا:** pending.

- [ ] **DB01-10B** — تطبیق Persistence با Runtime؛ M00/10
  - **ارتباط چک‌لیست اصلی:** P3M00, P3M10
  - **وابستگی:** DB01-04B و handoff معتبر
  - **خروجی/معیار پذیرش:** وضعیت واقعی پاسخ، Run، نسخه و خطا درست ثبت شوند
  - **وضعیت:** `blocked` (پیاده‌سازی هنوز مجاز نشده)؛ **Implemented:** NOT_RUN؛ **Checks:** NOT_RUN؛ **Evidence:** NOT_AVAILABLE؛ **پذیرش ناظر برای اجرا:** pending.

- [ ] **DB01-11** — تاریخچه و Feedback؛ M15
  - **ارتباط چک‌لیست اصلی:** P3M15
  - **وابستگی:** DB01-07 و قرارداد پیام/پاسخ
  - **خروجی/معیار پذیرش:** consistency، Pagination، مالکیت و کنترل Duplicate Write؛ مستقل از پذیرش RAG
  - **وضعیت:** `planned` (پیاده‌سازی هنوز مجاز نشده)؛ **Implemented:** NOT_RUN؛ **Checks:** NOT_RUN؛ **Evidence:** NOT_AVAILABLE؛ **پذیرش ناظر برای اجرا:** pending.

- [ ] **DB01-12** — Audit و Security Events؛ M04/16
  - **ارتباط چک‌لیست اصلی:** P3M04, P3M16
  - **وابستگی:** DB01-07/08 و Audit contract
  - **خروجی/معیار پذیرش:** Trace معتبر؛ بدون Secret و PII غیرضروری
  - **وضعیت:** `planned` (پیاده‌سازی هنوز مجاز نشده)؛ **Implemented:** NOT_RUN؛ **Checks:** NOT_RUN؛ **Evidence:** NOT_AVAILABLE؛ **پذیرش ناظر برای اجرا:** pending.

- [ ] **DB01-13** — Retention، Delete و Tombstone؛ M04/15، P3OP07
  - **ارتباط چک‌لیست اصلی:** P3M04, P3M15, P3OP07
  - **وابستگی:** سیاست Privacy/Retention مصوب
  - **خروجی/معیار پذیرش:** حذف و نگهداری مطابق تصمیم؛ مدت حدسی تعیین نشود؛ Export تصمیم مستقل و مانع حذف نیست
  - **وضعیت:** `planned` (پیاده‌سازی هنوز مجاز نشده)؛ **Implemented:** NOT_RUN؛ **Checks:** NOT_RUN؛ **Evidence:** NOT_AVAILABLE؛ **پذیرش ناظر برای اجرا:** pending.

- [ ] **DB01-14** — Backup/Restore PostgreSQL محصول؛ M22، P3OP07
  - **ارتباط چک‌لیست اصلی:** P3M22, P3OP07
  - **وابستگی:** DB01-05 و تصمیم زیرساخت
  - **خروجی/معیار پذیرش:** Restore مستقل با حفظ روابط و Trace؛ بدون ادعای بازیابی کل سامانه
  - **وضعیت:** `planned` (پیاده‌سازی هنوز مجاز نشده)؛ **Implemented:** NOT_RUN؛ **Checks:** NOT_RUN؛ **Evidence:** NOT_AVAILABLE؛ **پذیرش ناظر برای اجرا:** pending.

- [ ] **DB01-15A** — checks محلی؛ M04/06/15
  - **ارتباط چک‌لیست اصلی:** P3M04, P3M06, P3M15
  - **وابستگی:** هر جزء مستقل آماده
  - **خروجی/معیار پذیرش:** تست schema، migration، RLS، constraint و Fixture با شواهد قابل‌بازتولید
  - **وضعیت:** `planned` (پیاده‌سازی هنوز مجاز نشده)؛ **Implemented:** NOT_RUN؛ **Checks:** NOT_RUN؛ **Evidence:** NOT_AVAILABLE؛ **پذیرش ناظر برای اجرا:** pending.

- [ ] **DB01-15B** — آزمون اتصال و پذیرش نهایی؛ M20/21/22/23
  - **ارتباط چک‌لیست اصلی:** P3M20, P3M21, P3M22, P3M23
  - **وابستگی:** قراردادها، سرویس‌ها، محیط و وابستگی‌های نهایی
  - **خروجی/معیار پذیرش:** Runtime Persistence، Cross-user، Restore، Performance و Security در دامنهٔ مربوط؛ Gateها با شاهد
  - **وضعیت:** `blocked` (پیاده‌سازی هنوز مجاز نشده)؛ **Implemented:** NOT_RUN؛ **Checks:** NOT_RUN؛ **Evidence:** NOT_AVAILABLE؛ **پذیرش ناظر برای اجرا:** pending.

## جزئیات تکمیلی مصوب (عیناً از بستهٔ ناظر)

### مرز دیتابیس و API

دیتابیس مالک schema، constraint، index، RLS، role، Transaction، Atomic Persistence، جلوگیری از رکورد تکراری و آزمون rollback است.

API مالک ترتیب درخواست، orchestration، Retry، Timeout، Cancellation، Streaming، تولید Context هویت معتبر و تصمیم دربارهٔ فراخوانی مجدد موتور است.

قرارداد مشترک شامل:
request_id، trace_id، Idempotency Scope، هویت مالک، Transaction Boundary، وضعیت قابل‌ذخیره، Commit/Abort، Error Mapping و رفتار درخواست تکراری.

Atomicity دیتابیس تضمین Exactly-once Execution موتور یا Provider نیست.

### مالکیت و پذیرش دیتابیس

- مالکیت تست فقط به فایل‌ها/زیرپوشه‌های اختصاصی DB محدود شود؛ نه کل tests/phase3/integration/.
- Qdrant و Object Storage خارج از مأموریت این ایجنت‌اند.
- Local checks با Fixture، پذیرش Runtime یا Production نیستند.
- Namespace توسعهٔ فاز چهارم فقط در طراحی پیش‌بینی شود؛ جدول فعال ساخته نشود.
- Auth، Retention و زیرساخت بدون تصمیم مصوب قطعی نشوند.

## روش تحویل آینده

- فقط پس از پذیرش Foundation و مأموریت اجرایی جدید، Starting HEAD واقعی، مرز فایل‌ها، آزمون واقعی، نتیجه، محل شاهد و مانع هر شناسه ثبت شود.
- Mock/Fixture فقط در دامنهٔ خود شاهد است؛ پذیرش Runtime/Model یا امنیت نهایی نیست. هیچ درصد پیشرفت یا قبولی از ثبت این فایل نتیجه نمی‌شود.
