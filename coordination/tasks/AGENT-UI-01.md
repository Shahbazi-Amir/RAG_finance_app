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

---

## بستهٔ برنامه‌ریزی UI-01 — Journey، صفحات/Stateها و مرز کامپوننت‌ها

**نوع خروجی:** طراحی مستند در پروندهٔ مأموریت، نه پیاده‌سازی Frontend. **نسخه:** UI-01 planning v1 (provisional). **Starting commit:** 2f59c3e3d571aedeef907b944b8273762338cf4e، شاخهٔ agent/ui.
**وضعیت این بسته:** آمادهٔ بازبینی ناظر (review). وضعیت اجرایی UI-01 در چک‌لیست بالا همچنان planned و تیک‌نخورده است؛ **Implemented: NOT_RUN / L1: NOT_RUN / L2: NOT_RUN / Gate: NOT_ASSESSED**.
**منبع:** نقشهٔ ماژولار فاز سوم M01/M03/M11/M13/M14/M15، نقشهٔ عملیاتی P3-01/P3-05، پروندهٔ مصوب UI v1.1، AGENTS.md و coordination/ownership.md.
**حدود:** فقط طراحی؛ انتخاب Stack، تعیین URL/Route نهایی، قرارداد مشترک، API Client، کدنویسی و تست در این بسته مجاز نیست.

### A) Journeyهای پیشنهادی کاربر (بدون فرض توان عملیاتی موتور)

| شناسه | مسیر کاربر | شاخه‌ها و پایان قابل مشاهده | وابستگی باز |
|---|---|---|---|
| J1 | Landing → معرفی دامنهٔ آموزش مالی → ورود/ثبت‌نام → Session → Consent → ورود به فضای مکالمه | خطای ورود، نشست منقضی، رضایت ردشده/نسخهٔ جدید؛ عبور فقط بعد از تأییدهای معتبر Backend | روش Auth، متن و نسخهٔ Consent و سیاست دسترسی |
| J2 | فضای مکالمه → ایجاد/انتخاب مکالمه → نوشتن پرسش فارسی → ارسال → دریافت وضعیت/پاسخ → مشاهده Claim و منبع مرتبط | Answer یا No-answer یا Clarification یا Refusal یا Partial یا Error فقط بر مبنای نتیجهٔ معتبر Product API؛ خطای Provider نباید به No-answer تبدیل شود | قرارداد Message/Answer، adapter، نگاشت Outcome، Citation Resolver |
| J3 | انتخاب Claim → بازکردن Source drawer → مشاهدهٔ نوع منبع، نقش‌های انتساب و Locator معتبر → بازکردن منبع در صورت مجازبودن | نبود/خرابی Locator و انتساب نامشخص با توضیح شفاف؛ هرگز نام/زمان/صفحه/URL ساخته نشود | Source-details DTO، سیاست URL و Resolver معتبر |
| J4 | فهرست مکالمات خود کاربر → انتخاب گفتگو → تاریخچه → بازگشت به چت / Refresh | Empty، Loading، Error، Unauthorized، Session expired؛ عدم ادعای بازیابی پایدار تا اثبات سرور | History API، Pagination و isolation؛ NB23 history-input ندارد |
| J5 | پاسخ نمایش‌داده‌شده → ثبت Feedback یا گزارش Citation/Attribution نادرست → مشاهدهٔ نتیجهٔ ثبت | Pending، Submitted، Failed؛ بدون نمایش موفقیت صرفاً با تعامل محلی | قرارداد Feedback و Answer ID معتبر |
| J6 | حساب/حریم خصوصی → Consent status → درخواست حذف داده یا حساب → تأیید → پردازش → نتیجه | قبل از ارسال: Cancel؛ بعد از ارسال: requesting/processing/succeeded/failed؛ فقط تأیید نهایی Backend موفقیت است؛ Export جدا و تصمیم‌باز | سیاست Retention/Deletion، نشست پس از حذف و endpointهای محصول |

**قاعدهٔ عبور:** سیستم فقط وضعیت‌هایی را در رابط نشان می‌دهد که از قرارداد تأییدشده و پاسخ واقعی API حاصل شوند. مسیرهای J2/J3/J4 هم‌اکنون مشخصات تجربهٔ کاربرند، نه ادعای آمادگی RAG/History.

### B) فهرست صفحات و Stateهای نمایشی

این‌ها **مفهوم صفحه/ناحیه** هستند، نه URL قطعی یا انتخاب Router. واژه‌های State در این جدول زبان طراحی UI هستند و تا قرارداد محصول تصویب نشود Enum موتور/API محسوب نمی‌شوند.

| صفحه یا ناحیه | Stateهای UI پیشنهادی | شرط نمایش/محدودیت |
|---|---|---|
| Landing و مرز محصول | default، content-unavailable | توضیح دامنهٔ آموزشی و محدودیت؛ بدون قابلیت فاز ۴ |
| Sign-up / Login / Session | idle، validating، submitting، authenticated، rejected، expired، network-error | روش ورود و error mapping هنوز تصویب نشده |
| Consent | required، reviewing، submitting، accepted، declined، revoked، superseded، error | هیچ پذیرش ساختگی؛ نسخه و نتیجه از Backend |
| فهرست مکالمات | loading، empty، loaded، loading-more، error، unauthorized | Sorting/Pagination/History هنوز قرارداد محصول لازم دارند؛ عدم نشت بین کاربران |
| Chat / Composer | idle، composing، submitting، awaiting-response، response-visible، submit-failed، unknown-result | پیام و status به شناسهٔ معتبر مربوط؛ جلوگیری از ارسال تکراری پس از Retry/Refresh |
| ناحیهٔ نمایش پاسخ | answer، partial، no-answer، clarification، safety-refusal، error، confidence-unmeasured | این‌ها فقط حالت‌های پیشنهادی ارائه‌اند؛ نگاشت واقعی Outcome/Confidence اثبات نشده |
| Streaming / Cancellation | connecting، receiving، cancelling، cancelled، completed، failed، unknown؛ نمایش جزئی retrieving/generating فقط در صورت Event معتبر | **Streaming و Cancellation الزام باقی می‌مانند**؛ ترتیب رویداد، توقف واقعی سرور و بازیابی هنوز قرارداد/adapter معتبر ندارند؛ UI حدس نمی‌زند |
| Citation / Source drawer | closed، loading، resolved، unresolved، unavailable، invalid-locator، unsafe-link، error | resolved_citations فیلد رسمی NB23 Response نیست؛ ارتباط Claim/Citation و صحت محل شاهد باید از قرارداد محصول تأیید شود |
| Feedback / Report | idle، submitting، submitted، failed | با Answer ID و تأیید ثبت از API |
| Account / Privacy | loading، loaded، session-expired، error | حذف مستقل از تصمیم Export |
| حذف داده/حساب | confirmation، requesting، processing، succeeded، failed | succeeded فقط بر اساس تأیید نهایی Backend؛ حذف واقعی جزو مسئولیت UI نیست |
| Export (در صورت تصویب) | out-of-scope-pending؛ Stateهای عملیاتی بعداً | نبود تصمیم Export نباید مسیر حذف را مسدود کند |

**قواعد مشترک State:** در همهٔ مسیرها بازخورد قابل‌فهم فارسی، RTL، Focus و اعلان دسترس‌پذیر، حالت Empty/Error واقعی، حفظ حریم خصوصی و عدم نمایش Prompt/Debug لازم است. وضعیت‌های داخلی موتور یا وضعیت‌های فرضی شبکه به موفقیت تبدیل نمی‌شوند.

### C) مرز کامپوننت‌ها — فقط مالکیت مفهومی

| ناحیهٔ UI | مسئولیت نمایش و تعامل | داده/عملیات خارج از مالکیت UI |
|---|---|---|
| Page shell / Navigation | RTL، چیدمان واکنش‌گرا، جابه‌جایی صفحات، Focus و دسترس‌پذیری | Auth policy، انتخاب Stack/Router |
| Auth & Consent views | فرم، وضعیت، اعلان خطا و تصمیم کاربر | هویت، نشست، versioning رضایت و ثبت آن در Backend |
| Conversation list / History view | فهرست و Empty/Error/Pagination UI، انتخاب و بازگشت | ذخیره/ایزولاسیون تاریخچه، عنوان‌سازی و قرارداد فیلتر |
| Chat composer / Message view | متن فارسی، ارسال کاربر، جلوگیری از تعامل تکراری در UI، ترتیب پیام‌ها | persistence، idempotency واقعی، RAG orchestration |
| Answer state presenter | تفکیک وضعیت جواب، نبود پاسخ، سؤال روشن‌کننده، refusal، error و Confidence ناموجود | تصمیم Answerability/Safety، امتیاز یا Enum واقعی موتور |
| Stream / Cancel presenter | بازنمایی Eventهای معتبر، لغو نمایشی، Recovery/Retry affordance | event protocol، توقف پردازش سرور، billing و delivery guarantee |
| Claim + Citation presentation / Source drawer | اتصال دیداری Claim به Citation، نمایش نقش‌های مستقل نویسنده/سردبیر/گوینده و Locator دریافتی | Source resolver، اعتبار علمی/معنایی شاهد، تولید URL/نام/Timestamp |
| Feedback / Privacy / Deletion views | ثبت تعامل، وضعیت ارسال و نتیجهٔ تأییدشده، درخواست حذف | Feedback persistence، حذف واقعی، Retention، export |
| Safe content renderer | escaped-by-default rendering، لینک‌های مجاز، عدم اجرای HTML/Script و مخفی‌کردن Debug | پاک‌سازی upstream، سیاست امنیت سرور و اعتبار منبع |
| Product API boundary (مصرف‌کننده در آینده) | فقط مصرف DTO تأییدشده در محدودهٔ مجاز | تعریف/ویرایش packages/contracts، API endpoint، adapter و schema |

**مرز مسیر:** مالک فعلی این سند فقط coordination/tasks/AGENT-UI-01.md است. مسیرهای احتمالی کد UI بعداً صرفاً زیر apps/web/** و تست‌های نام‌فضادار tests/phase3/ui/** و tests/phase3/integration/ui/** و فقط با مجوز مأموریت بعدی قابل استفاده‌اند؛ هیچ مسیر/اسکلت جدیدی در این مأموریت ساخته نمی‌شود.

### D) وابستگی‌ها، دو سطح شاهد و شرط پذیرش UI-01

| بخش | L1 — شاهد مستقل UI/Mock (آینده) | L2 — اتصال واقعی و پذیرش (آینده) |
|---|---|---|
| Journey و Navigation | مرور مسیرها و تست نمایشی با Fixture برچسب‌خوردهٔ مصنوعی، آزمون Focus/RTL | E2E مسیر Login → Chat → Citation → History روی API و نشست واقعی مصوب |
| Stateهای پاسخ، خطا و Recovery | تست State و پیام‌ها با Fixtureهای صریحاً Synthetic؛ پاسخ خطا از No-answer تفکیک شود | تأیید نگاشت Response/HTTP و retry/idempotency با API/adapter واقعی |
| Streaming و Cancellation | Mock انتقال Event/قطع ارتباط/لغو/Retry/Refresh و نمایش نامعلوم | آزمون ترتیب و پایان رویدادها، لغو واقعی سرور و وضعیت پایدار پس از قطع اتصال |
| Source، Privacy و امنیت نمایش | Fixtureهای Claim/Citation، misattribution، Missing locator، HTML/Script و URL خطرناک | Resolver/Locator و منبع مجاز، عدم افشای Debug/Prompt و کنترل یکپارچهٔ امنیت |
| حذف داده/حساب | Mock حالت‌های درخواست، پردازش، موفقیت/شکست و لغو پیش از ارسال | نتیجهٔ قطعی حذف و رفتار نشست از Backend و آزمون مستقل عدم دسترسی |

**وضعیت فعلی:** هر دو سطح L1 و L2: **NOT_RUN**؛ شواهد اجرایی: **NOT_AVAILABLE**؛ تأیید نهایی ناظر: **PENDING**. طراحی UI-01 برای بازبینی آماده است اما به معنی PASS شدن UI-01، P3M14، Module 00 یا پذیرش کل محصول نیست.

**تصمیم‌های باز:** روش ورود، متن Consent، قرارداد Product API و error/identity، تاریخچه/Pagination، Event/Cancel/Retry، Citation/Attribution و نگاشت speaker ↔ speaker_name، policy حذف، معیارهای مرورگر/Accessibility، Stack و Router. هیچ‌کدام در این سند Freeze یا جایگزین نشده‌اند.

**موانع فاز دوم:** NB23 Draft فقط question و contract_version را در Request تأیید می‌کند؛ source filters و history را پشتیبانی اثبات‌شده فرض نکنید. وضعیت‌های Outcome پیشنهاد مصرف‌کننده‌اند؛ resolved_citations رسمی نیست؛ confidence: null مقدار اندازه‌گیری‌نشده است. استفاده از Synthetic Fixture هرگز مدرک Citation واقعی، عملکرد موتور، Safety یا قابلیت Streaming زنده نیست.

**گام بعدی (بدون اجرا در این مأموریت):** بازبینی همین بسته توسط ناظر و سپس تطبیق با Contract و مسیرهای نهایی پس از صدور مأموریت مستقل. هیچ Dependency نصب، UI Code، API Code، قرارداد مشترک، Test execution یا Deploy در این بسته انجام نشده است.
