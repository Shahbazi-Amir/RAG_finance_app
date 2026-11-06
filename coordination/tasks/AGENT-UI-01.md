# AGENT-UI-01 — چک‌لیست مصوب v1.1

**وضعیت onboarding:** `ONBOARDING_ACCEPTED — IMPLEMENTATION_WAITING_FOR_FOUNDATION`. این فقط پذیرش نسخهٔ چک‌لیست است؛ **هیچ فعالیت اجرایی یا Gate پذیرفته یا تست نشده است**. صاحب پرونده متخصص مربوطه است؛ نسخهٔ اولیه با مجوز ناظر توسط Foundation ثبت شده است.

**دامنه:** Frontend و مصرف قرارداد محصول؛ بدون API، migration و امنیت Backend.

**سیاست:** تیک صرفاً پس از اجرای واقعی معیار، ثبت شاهد و checks مجاز است. وضعیت‌ها `planned / active / blocked / review / accepted` و رأی ناظر جدا هستند. `P3Mxx` دفتر اصلی و تنها مرجع شمارش است.

## فعالیت‌ها — هیچ موردی اجرا نشده است

- [ ] **UI-01** — دامنه، Journey و ساختار Frontend؛ M01/03/14، P3OP01
  - **ارتباط چک‌لیست اصلی:** P3M01, P3M03, P3M14, P3OP01
  - **وابستگی:** Foundation و تصمیم معماری/Stack
  - **خروجی/معیار پذیرش:** مسیرهای کاربر، مرز کامپوننت و Stateها؛ بدون قابلیت فعال فاز چهارم
  - **وضعیت:** `planned` (پیاده‌سازی هنوز مجاز نشده)؛ **Implemented:** NOT_RUN؛ **Checks:** NOT_RUN؛ **Evidence:** NOT_AVAILABLE؛ **پذیرش ناظر برای اجرا:** pending.

- [ ] **UI-02** — تطبیق قرارداد Frontend/API؛ M03/11/13
  - **ارتباط چک‌لیست اصلی:** P3M03, P3M11, P3M13
  - **وابستگی:** قرارداد مشترک نسخه‌دار
  - **خروجی/معیار پذیرش:** API Client و Contract checks؛ بدون فیلد یا قرارداد موازی فرضی
  - **وضعیت:** `planned` (پیاده‌سازی هنوز مجاز نشده)؛ **Implemented:** NOT_RUN؛ **Checks:** NOT_RUN؛ **Evidence:** NOT_AVAILABLE؛ **پذیرش ناظر برای اجرا:** pending.

- [ ] **UI-03** — ورود، نشست و مدیریت حساب؛ M05/13/14
  - **ارتباط چک‌لیست اصلی:** P3M05, P3M13, P3M14
  - **وابستگی:** روش ورود مصوب و قرارداد Auth
  - **خروجی/معیار پذیرش:** صفحات متناسب با روش مصوب؛ ورود، خروج، انقضا و خطاهای دسترسی درست
  - **وضعیت:** `planned` (پیاده‌سازی هنوز مجاز نشده)؛ **Implemented:** NOT_RUN؛ **Checks:** NOT_RUN؛ **Evidence:** NOT_AVAILABLE؛ **پذیرش ناظر برای اجرا:** pending.

- [ ] **UI-04** — Consent و Privacy؛ M05/14، P3OP03/05
  - **ارتباط چک‌لیست اصلی:** P3M05, P3M14, P3OP03, P3OP05
  - **وابستگی:** قرارداد Consent و متن نسخه‌دار
  - **خروجی/معیار پذیرش:** نمایش و تغییر وضعیت رضایت؛ بدون ثبت پذیرش ساختگی
  - **وضعیت:** `planned` (پیاده‌سازی هنوز مجاز نشده)؛ **Implemented:** NOT_RUN؛ **Checks:** NOT_RUN؛ **Evidence:** NOT_AVAILABLE؛ **پذیرش ناظر برای اجرا:** pending.

- [ ] **UI-05** — مکالمه و تاریخچه؛ M14/15
  - **ارتباط چک‌لیست اصلی:** P3M14, P3M15
  - **وابستگی:** قرارداد فهرست، جزئیات، Pagination و دسترسی
  - **خروجی/معیار پذیرش:** Loading/Empty/Error و بازیابی پس از Refresh؛ بدون نمایش دادهٔ کاربر دیگر
  - **وضعیت:** `planned` (پیاده‌سازی هنوز مجاز نشده)؛ **Implemented:** NOT_RUN؛ **Checks:** NOT_RUN؛ **Evidence:** NOT_AVAILABLE؛ **پذیرش ناظر برای اجرا:** pending.

- [ ] **UI-06** — چت فارسی و RTL؛ M13/14
  - **ارتباط چک‌لیست اصلی:** P3M13, P3M14
  - **وابستگی:** قرارداد پیام و پاسخ
  - **خروجی/معیار پذیرش:** Composer و پیام‌ها روی موبایل و دسکتاپ؛ بدون تکثیر یا جابه‌جایی ناخواسته
  - **وضعیت:** `planned` (پیاده‌سازی هنوز مجاز نشده)؛ **Implemented:** NOT_RUN؛ **Checks:** NOT_RUN؛ **Evidence:** NOT_AVAILABLE؛ **پذیرش ناظر برای اجرا:** pending.

- [ ] **UI-07** — وضعیت پاسخ و Confidence؛ M10/12/14
  - **ارتباط چک‌لیست اصلی:** P3M10, P3M12, P3M14
  - **وابستگی:** قرارداد محصول؛ نگاشت واقعی موتور بعداً
  - **خروجی/معیار پذیرش:** Answer/Partial/No-answer/Clarification/Refusal/Error؛ خطای فنی no-answer نشود و confidence:null عددسازی نشود
  - **وضعیت:** `planned` (پیاده‌سازی هنوز مجاز نشده)؛ **Implemented:** NOT_RUN؛ **Checks:** NOT_RUN؛ **Evidence:** NOT_AVAILABLE؛ **پذیرش ناظر برای اجرا:** pending.

- [ ] **UI-08** — Citation و Attribution؛ M11/14
  - **ارتباط چک‌لیست اصلی:** P3M11, P3M14
  - **وابستگی:** DTO مشترک؛ Resolver واقعی برای پذیرش اتصال
  - **خروجی/معیار پذیرش:** Citation کنار Claim و جزئیات منبع؛ نویسنده، سردبیر و گوینده جدا؛ بدون نام، لینک، صفحه یا زمان جعلی
  - **وضعیت:** `planned` (پیاده‌سازی هنوز مجاز نشده)؛ **Implemented:** NOT_RUN؛ **Checks:** NOT_RUN؛ **Evidence:** NOT_AVAILABLE؛ **پذیرش ناظر برای اجرا:** pending.

- [ ] **UI-09** — Feedback و گزارش پاسخ؛ M13/15، P3OP05
  - **ارتباط چک‌لیست اصلی:** P3M13, P3M15, P3OP05
  - **وابستگی:** قرارداد بازخورد و Answer ID
  - **خروجی/معیار پذیرش:** اتصال به پاسخ درست؛ مدیریت خطا و ارسال تکراری
  - **وضعیت:** `planned` (پیاده‌سازی هنوز مجاز نشده)؛ **Implemented:** NOT_RUN؛ **Checks:** NOT_RUN؛ **Evidence:** NOT_AVAILABLE؛ **پذیرش ناظر برای اجرا:** pending.

- [ ] **UI-10** — Streaming، Cancellation و Recovery؛ M13/14/15
  - **ارتباط چک‌لیست اصلی:** P3M13, P3M14, P3M15
  - **وابستگی:** قرارداد Event، Idempotency، لغو و بازیابی
  - **خروجی/معیار پذیرش:** State machine، Retry/Refresh و پاسخ ناقص؛ تفاوت لغو نمایش با توقف واقعی سرور محفوظ
  - **وضعیت:** `planned` (پیاده‌سازی هنوز مجاز نشده)؛ **Implemented:** NOT_RUN؛ **Checks:** NOT_RUN؛ **Evidence:** NOT_AVAILABLE؛ **پذیرش ناظر برای اجرا:** pending.

- [ ] **UI-11** — Accessibility، موبایل و مرورگر؛ M14، P3OP05
  - **ارتباط چک‌لیست اصلی:** P3M14, P3OP05
  - **وابستگی:** مرورگرها و معیارهای مصوب
  - **خروجی/معیار پذیرش:** RTL، Layout واکنش‌گرا، Keyboard، Focus، Contrast و Screen-reader labels؛ checks مصوب پاس
  - **وضعیت:** `planned` (پیاده‌سازی هنوز مجاز نشده)؛ **Implemented:** NOT_RUN؛ **Checks:** NOT_RUN؛ **Evidence:** NOT_AVAILABLE؛ **پذیرش ناظر برای اجرا:** pending.

- [ ] **UI-12** — آزمون و تحویل UI؛ M03/11/14/15 و Test Suite نقشه
  - **ارتباط چک‌لیست اصلی:** P3M03, P3M11, P3M14, P3M15
  - **وابستگی:** اجزای آماده؛ اتصال واقعی برای L2
  - **خروجی/معیار پذیرش:** آزمون‌های متناسب، مستند اجرا و محدودیت‌ها؛ مسیر Login→Chat→Citation→History؛ Mock شاهد کیفیت موتور نیست
  - **وضعیت:** `planned` (پیاده‌سازی هنوز مجاز نشده)؛ **Implemented:** NOT_RUN؛ **Checks:** NOT_RUN؛ **Evidence:** NOT_AVAILABLE؛ **پذیرش ناظر برای اجرا:** pending.

- [ ] **UI-13** — حذف داده و حساب؛ M14/15/21، P3OP05/07
  - **ارتباط چک‌لیست اصلی:** P3M14, P3M15, P3M21, P3OP05, P3OP07
  - **وابستگی:** سیاست حذف و قرارداد Backend
  - **خروجی/معیار پذیرش:** تأیید کاربر، ثبت درخواست و وضعیت واقعی؛ موفقیت فقط پس از تأیید نهایی Backend؛ Export تصمیم مستقل
  - **وضعیت:** `planned` (پیاده‌سازی هنوز مجاز نشده)؛ **Implemented:** NOT_RUN؛ **Checks:** NOT_RUN؛ **Evidence:** NOT_AVAILABLE؛ **پذیرش ناظر برای اجرا:** pending.

- [ ] **UI-14** — نمایش امن محتوا؛ M14/21، P3OP09
  - **ارتباط چک‌لیست اصلی:** P3M14, P3M21, P3OP09
  - **وابستگی:** قواعد rendering و خطای API
  - **خروجی/معیار پذیرش:** جلوگیری از اجرای HTML/Script و URL خطرناک؛ عدم نمایش Prompt، Stack trace، Debug، Token و Secret
  - **وضعیت:** `planned` (پیاده‌سازی هنوز مجاز نشده)؛ **Implemented:** NOT_RUN؛ **Checks:** NOT_RUN؛ **Evidence:** NOT_AVAILABLE؛ **پذیرش ناظر برای اجرا:** pending.

## جزئیات تکمیلی مصوب (عیناً از بستهٔ ناظر)

### جزئیات لازم UI-10

Stateهای پیشنهادی connecting، retrieving، generating، completed، cancelling، cancelled، failed و unknown فقط مطابق قرارداد واقعی نهایی شوند. UI وضعیت داخلی موتور را حدس نزند.

آزمون Mock شامل ترتیب رویداد، قطع ارتباط، لغو، پاسخ ناقص، Retry و Refresh باشد. آزمون اتصال واقعی شامل پایان پردازش، رفتار لغو سرور و بازیابی وضعیت پس از قطع ارتباط است.

### جزئیات لازم UI-13

Stateهای requesting، processing، succeeded و failed طبق قرارداد Backend تعریف شوند. لغو پیش از ارسال و تغییر نشست پس از حذف پوشش داده شود. ارسال درخواست به‌تنهایی موفقیت حذف نیست. عدم دسترسی به دادهٔ حذف‌شده با همکاری API در آزمون یکپارچه بررسی شود.

### جزئیات لازم UI-14

Fixtureهای کنترل‌شده برای HTML/Script، Markdown ناامن، پروتکل URL خطرناک، Metadata مخرب و افشای اطلاعات Debug استفاده شوند. Citation تأییدنشده به‌عنوان منبع معتبر معرفی نشود.

### دو سطح شاهد UI

- L1 — UI/Mock: تست کامپوننت، State، Contract و Accessibility با Mock نسخه‌دار؛ فقط رفتار مستقل Frontend را اثبات می‌کند.
- L2 — Integration: اتصال واقعی به API/adapter و آزمون E2E؛ فقط یکپارچگی در دامنهٔ آزموده‌شده را اثبات می‌کند.

قبولی L1، قبولی L2 یا پذیرش موتور نیست. Fixture مصنوعی صحت معنایی Citation، Confidence یا Safety را اثبات نمی‌کند.
هر مورد نوع شاهد، نتیجهٔ checks، محدودیت و پذیرش ناظر را جدا ثبت کند.

محدودیت NB23:
history و فیلترها ورودی تأییدشدهٔ موتور نیستند؛ resolved_citations فیلد رسمی Response فعلی نیست؛ outcomeها نگاشت اثبات‌شدهٔ Producer نیستند. نگاشت speaker و speaker_name در قرارداد مشترک تعیین شود.

## روش تحویل آینده

- فقط پس از پذیرش Foundation و مأموریت اجرایی جدید، Starting HEAD واقعی، مرز فایل‌ها، آزمون واقعی، نتیجه، محل شاهد و مانع هر شناسه ثبت شود.
- Mock/Fixture فقط در دامنهٔ خود شاهد است؛ پذیرش Runtime/Model یا امنیت نهایی نیست. هیچ درصد پیشرفت یا قبولی از ثبت این فایل نتیجه نمی‌شود.
