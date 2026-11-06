# AGENT-UI-01 — چک‌لیست مصوب v1.1

**وضعیت onboarding:** `ONBOARDING_ACCEPTED`؛ Foundation در `main@2f59c3e3d571aedeef907b944b8273762338cf4e` پذیرفته شد. **بستهٔ طراحی اولیهٔ UI-01** و **بازبینی مصرف قرارداد** طبق اعلام ناظر پذیرفته شده‌اند؛ نه کل UI-01 و نه هیچ پیاده‌سازی، آزمون L1/L2 یا Gate. صاحب پرونده متخصص UI است و چک‌لیست v1.1 ابتدا با مجوز ناظر توسط Foundation ثبت شد.

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
**وضعیت این بسته:** طراحی اولیه با اعلام ناظر **ACCEPTED (design-package only)**؛ تطبیق مصرف قرارداد در بستهٔ مرتبط بعدی انجام شده است. وضعیت اجرای کامل UI-01 در چک‌لیست بالا همچنان `planned` و تیک‌نخورده است؛ **Product UI implemented: NOT_RUN / L1: NOT_RUN / L2: NOT_RUN / Gate: NOT_ASSESSED**.
**منبع:** نقشهٔ ماژولار فاز سوم M01/M03/M11/M13/M14/M15، نقشهٔ عملیاتی P3-01/P3-05، پروندهٔ مصوب UI v1.1، AGENTS.md و coordination/ownership.md.
**حدود:** فقط طراحی؛ انتخاب Stack، تعیین URL/Route نهایی، قرارداد مشترک، API Client، کدنویسی و تست در این بسته مجاز نیست.

### A) Journeyهای پیشنهادی کاربر (بدون فرض توان عملیاتی موتور)

| شناسه | مسیر کاربر | شاخه‌ها و پایان قابل مشاهده | وابستگی باز |
|---|---|---|---|
| J1 | Landing → معرفی دامنهٔ آموزش مالی → ورود/ثبت‌نام → Session → Consent → ورود به فضای مکالمه | خطای ورود، نشست منقضی، رضایت ردشده/نسخهٔ جدید؛ عبور فقط بعد از تأییدهای معتبر Backend | روش Auth، متن و نسخهٔ Consent و سیاست دسترسی |
| J2 | انتخاب/ایجاد مکالمه → کلید موقت **صرفاً محلی** برای نمای چت جدید → composing → ارسال پرسش فارسی با `requested_conversation_id=null` برای مکالمهٔ تازه (یا شناسهٔ واقعی مکالمهٔ قبلی)، `client_message_id` و `idempotency_key` ثابت → دریافت Receipt → جایگزینی کلید نمایشی با `resolved_conversation_id` فقط در `created/replayed` → مشاهدهٔ Answer/Claim | Receipt معتبر با `disposition=created/replayed` تنها مرجع تخصیص مکالمه و `message_id` است؛ Replay باید همان `resolved_conversation_id` و `message_id` را بازگرداند. `conflict` با شناسه‌های تخصیص‌نیافته و خطای صریح، نه موفقیت. پس از قطع ارتباط/Retry، درخواست اولیه با `requested_conversation_id` و متن و شناسه‌ها **بدون تغییر** تکرار می‌شود؛ هیچ اجرای دقیقاً یک‌بارهٔ مدل ادعا نمی‌شود | Product v1 `send_message_request/receipt`، هویت معتبر سرور، HTTP/Retry/Recovery و Answer/adapter هنوز provisional |
| J3 | انتخاب Claim → بازکردن **محلی** Source drawer → نمایش فقط دادهٔ دریافتی `source_type`، نقش‌ها و `display_title` اختیاری همراه با `display_title_origin` در صورت وجود؛ Locator فقط پس از `resolution_status=verified` و مجوز معتبر | `display_title` بدون Origin معتبر یا خالی جعل نشود؛ منشأ `source_record` / `catalog_record` / `SYNTHETIC` ادعای اصالت یا قابلیت بازکردن نیست. Resolution و Attribution مستقل‌اند؛ unresolved می‌تواند عنوان/Metadata داشته باشد، ولی `book_anchor` و `transcript_segment` URL ساختگی نمی‌سازند؛ Link نامعتبر غیرفعال است | صحت واقعی Metadata، مقصد قابل‌دسترسی Anchor، Resolver و مجوز بازکردن منبع همچنان وابستگی L2 اند |
| J4 | فهرست مکالمات خود کاربر → انتخاب گفتگو → تاریخچه → بازگشت به چت / Refresh | Empty، Loading، Error، Unauthorized، Session expired؛ عدم ادعای بازیابی پایدار تا اثبات سرور | History API، Pagination و isolation؛ NB23 history-input ندارد |
| J5 | پاسخ نمایش‌داده‌شده → انتخاب Feedback → ساخت `feedback_submit_request` با `client_feedback_id`، `conversation_id`، `answer_id`، `rating`، `reason` و `idempotency_key` → ارسال → دریافت `feedback_submit_receipt` | `created` یا `replayed` فقط با `feedback_id` و `persisted_at` معتبر و `error=null` تأیید ثبت است؛ `conflict` با error و بدون شناسه/زمان موفق نیست. Retry همان payload و key را حفظ می‌کند؛ `feedback_id`/`persisted_at` در Replay ثابت‌اند، ولی `request_id`/`trace_id` سروری به **تلاش جاری** تعلق دارند و ممکن است تغییر کنند. قطع ارتباط، **local unknown** است و موفقیت نیست | API واقعی، Auth/owner check، HTTP mapping/TTL، سیاست ویرایش یا چند Feedback و reconciliation پس از قطع ارتباط هنوز L2/open |
| J6 | حساب/حریم خصوصی → تأیید محلی حذف → ارسال `delete_command` با `confirmed_by_user=true`، `deletion_scope`، `conversation_id` و **فقط** `client_action_id` ساختهٔ Client → دریافت `delete_status` با شناسه‌های صادرشدهٔ سرور → استعلام مالکیت‌محور با `delete_status_query` (`deletion_request_id` + `client_action_id`) | Client `request_id`، `trace_id`، `deletion_request_id` یا `owner_user_id` تولید/ارسال نمی‌کند؛ سرور آن‌ها را صادر/اعتبارسنجی می‌کند. فقط `delete_status.state=succeeded` همراه با `backend_confirmed=true` و `completed_at` نتیجهٔ موفق است. **unknown-transport فقط State محلی** پس از قطع شبکه است، نه مقدار `delete_status.state` و نه موفقیت حذف | اگر پیش از دریافت `deletion_request_id` شبکه قطع شود، قرارداد فعلی راه بازیابی از `client_action_id` تنها را تعیین نمی‌کند. Auth مالک، استعلام پس از revoke نشست حساب، سیاست Retention و Recovery واقعی تصمیم باز L2؛ Export مستقل |

**قاعدهٔ عبور:** composing، navigation، باز/بسته‌شدن پنل و انتظار برای دریافت شبکه Stateهای **محلی** هستند و می‌توانند بدون تصمیم موتور نشان داده شوند؛ **پردازش موتور، ثبت پیام/Feedback، انتساب منبع و حذف موفق** فقط با شاهد معتبر سرور گزارش می‌شوند. J2/J3/J4 مشخصات تجربه‌اند، نه ادعای آمادگی RAG/History. منبع هویت معتبر سرور است؛ کاربر حق ارسال `owner_user_id` یا `trusted_actor_context` ندارد.

### B) فهرست صفحات و Stateهای نمایشی

این‌ها **مفهوم صفحه/ناحیه** هستند، نه URL قطعی یا انتخاب Router. واژه‌های State در این جدول زبان طراحی UI هستند و تا قرارداد محصول تصویب نشود Enum موتور/API محسوب نمی‌شوند.

| صفحه یا ناحیه | Stateهای UI پیشنهادی | شرط نمایش/محدودیت |
|---|---|---|
| Landing و مرز محصول | default، content-unavailable | توضیح دامنهٔ آموزشی و محدودیت؛ بدون قابلیت فاز ۴ |
| Sign-up / Login / Session | idle، validating، submitting، authenticated، rejected، expired، network-error | روش ورود و error mapping هنوز تصویب نشده |
| Consent | required، reviewing، submitting، accepted، declined، revoked، superseded، error | هیچ پذیرش ساختگی؛ نسخه و نتیجه از Backend |
| فهرست مکالمات | loading، empty، loaded، loading-more، error، unauthorized | Sorting/Pagination/History هنوز قرارداد محصول لازم دارند؛ عدم نشت بین کاربران |
| Chat / Composer | idle، composing، local-thread-pending، submitting، awaiting-receipt، receipt-replayed، receipt-conflict، response-visible، submit-failed، unknown-result | composing و کلید نمایشی مکالمه تازه **فقط محلی**؛ ارسال جدید `requested_conversation_id=null` و Retry همان ورودی اولیه/`client_message_id`/`idempotency_key` را حفظ می‌کند؛ فقط Receipt معتبر `created/replayed`، `resolved_conversation_id` و `message_id` را تثبیت می‌کند؛ `conflict` موفق نیست |
| ناحیهٔ نمایش پاسخ | answer، partial، no-answer، clarification، refusal، error، unknown، cancelled، confidence-unmeasured | بازنمایی فقط از `answer.state` و `answer.outcome` معتبر محصول؛ `error` فنی با `no_answer` متفاوت، `unknown` نه موفقیت، `partial` نه تکمیل کامل؛ `confidence=null` اندازه‌گیری‌نشده است؛ نگاشت زندهٔ موتور هنوز باز |
| Streaming / Cancellation | local connecting/receiving/display-stopped/cancel-action-pending؛ server-reported connected/retrieving/generating/delta/cancel_requested/display_cancelled/server_cancelled/completed/failed/unknown | Streaming/Cancellation الزام نقشه‌اند. `retrieving/generating` فقط از Event دارای `reported_by=backend`؛ `delta.data.text` **حتی Space و Newline** عیناً و بدون trim/normalization/حذف حفظ شود. پایان Stream (`completed`) می‌تواند `final_state=partial` داشته باشد و پایان با پاسخ کامل یکسان نیست؛ `display_cancelled` توقف نمایش، `cancel_requested` درخواست توقف، و فقط `server_cancelled` با `server_stopped=true` و `confirmation_ref` اثبات توقف سرور است. ترتیب seq/رویداد نهایی و Recovery به قرارداد/adapter واقعی وابسته‌اند |
| Citation / Source drawer | local closed/open/selection؛ server evidence: source resolution verified/unresolved، attribution verified/unknown، locator invalid/unavailable | `source_attribution.display_title` اختیاری است و فقط با `display_title_origin` متناسب نمایش داده می‌شود؛ Origin از `source_record`/`catalog_record`/`SYNTHETIC` دروغین فرض نمی‌شود و اصالت، Attribution، Resolution یا لینک بازشدنی را تضمین نمی‌کند. Locator فقط از `source.locator` معتبر و مجاز؛ هیچ عنوان، URL، صفحه یا زمان حدسی ساخته نشود. مقصد Anchor و Resolver واقعی باز است |
| Feedback / Report | local idle، editing، submitting، unknown-transport؛ server-reported created/replayed/conflict | `feedback_submit_request` فقط شناسهٔ محلی Feedback و داده‌های اصلی را دارد؛ در Retry ثابت. فقط `feedback_submit_receipt` با `created/replayed`، `feedback_id`، `persisted_at` و بدون error مجوز «ثبت شد» است. `conflict` موفقیت نیست. Trace مربوط به **تلاش جاری سرور** است، نه ورودی Client یا الزاماً Trace ثبت اولیه |
| Account / Privacy | loading، loaded، session-expired، error | حذف مستقل از تصمیم Export |
| حذف داده/حساب | local confirmation، cancel-before-send، submitting، **unknown-transport**؛ server-status **فقط** requesting، processing، succeeded، failed | Client فقط `client_action_id` را تولید/حفظ می‌کند. `delete_status_query` با `deletion_request_id` سروری و `client_action_id` انجام می‌شود و بدون Auth مالک معتبر نیست. `succeeded` فقط با `backend_confirmed=true` و `completed_at`؛ از دست‌رفتن پاسخ قبل از `deletion_request_id` شکاف Recovery باز است؛ وضعیت نشست بعد از حذف حساب تصمیم باز امنیت/Auth است |
| Export (در صورت تصویب) | out-of-scope-pending؛ Stateهای عملیاتی بعداً | نبود تصمیم Export نباید مسیر حذف را مسدود کند |

**قواعد مشترک State:** در همهٔ مسیرها بازخورد قابل‌فهم فارسی، RTL، Focus و اعلان دسترس‌پذیر، حالت Empty/Error واقعی، حفظ حریم خصوصی و عدم نمایش Prompt/Debug لازم است. وضعیت‌های داخلی موتور یا وضعیت‌های فرضی شبکه به موفقیت تبدیل نمی‌شوند.

### C) مرز کامپوننت‌ها — فقط مالکیت مفهومی

| ناحیهٔ UI | مسئولیت نمایش و تعامل | داده/عملیات خارج از مالکیت UI |
|---|---|---|
| Page shell / Navigation | RTL، چیدمان واکنش‌گرا، جابه‌جایی صفحات، Focus و دسترس‌پذیری | Auth policy، انتخاب Stack/Router |
| Auth & Consent views | فرم، وضعیت، اعلان خطا و تصمیم کاربر | هویت، نشست، versioning رضایت و ثبت آن در Backend |
| Conversation list / History view | فهرست و Empty/Error/Pagination UI، انتخاب و بازگشت | ذخیره/ایزولاسیون تاریخچه، عنوان‌سازی و قرارداد فیلتر |
| Chat composer / Message view | متن فارسی، کلید نمایشی محلی موقت، حفظ `requested_conversation_id` اصلی در Retry، تمایز `created/replayed/conflict` و آشتی با شناسهٔ سرور | persistence، تخصیص `resolved_conversation_id`، Idempotency معتبر، هویت کاربر، RAG orchestration |
| Answer state presenter | تفکیک وضعیت جواب، نبود پاسخ، سؤال روشن‌کننده، refusal، error و Confidence ناموجود | تصمیم Answerability/Safety، امتیاز یا Enum واقعی موتور |
| Stream / Cancel presenter | بازنمایی بی‌تغییر و مرتب Deltaهای واقعی، وضعیت لغو نمایشی مستقل، تفکیک terminal از `answer` کامل/partial و Recovery/Retry affordance | Event protocol زنده، تأیید server cancellation، بازیابی، billing و delivery guarantee |
| Claim + Citation presentation / Source drawer | بازشدن محلی Drawer، اتصال Claim/Citation معتبر، نمایش Title اختیاری **فقط با Origin دریافت‌شده**، Metadata و Locator موجود با Resolution و Attribution مستقل | Source resolver، صحت معنایی و منشأ Metadata، مقصد واقعی Anchor، تولید/حدس عنوان/URL/نام/Timestamp ممنوع |
| Feedback / Privacy / Deletion views | نگهداری payload اولیهٔ Feedback برای Retry، تفکیک `created/replayed/conflict`، نمایش `delete_status` و `unknown-transport` محلی با تأیید حذف فقط از سرور | تأیید واقعی Feedback persistence، تولید Trace و Operation ID سرور، Recovery قبل از Operation ID، Authorization استعلام حذف، سیاست Session پس از حذف، Retention و Export اختیاری |
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

## Checkpoint تجمعی — UI-01 قرارداد Product v1 (reviewed-design alignment)

**شناسهٔ بسته:** `UI-01-ALIGN-01`؛ ارتباط با `UI-01`, `UI-02`, `UI-05`, `UI-06`, `UI-07`, `UI-08`, `UI-09`, `UI-10`, `UI-13`؛ مرجع مشترک `P3M01` (Module 01 / journey و freeze تصمیم‌ها)، `P3M03` (Module 03 / Product contract)، `P3M10` (Module 10 / orchestration و idempotency)، `P3M11` (Module 11 / Citation و Attribution)، `P3M13` (Module 13 / API، Retry و Streaming)، `P3M14` (Module 14 / Web chat)، `P3M15` (Module 15 / History و Feedback)، `P3M21` (Module 21 / حریم خصوصی). `P3OP01` و `P3OP05` فقط overlay نقشهٔ عملیاتی‌اند؛ پیشرفت دوم ایجاد نمی‌کنند.

**مبنای ورودی:** `RAG_finance_app`، شاخهٔ `agent/ui`، HEAD اولیهٔ واقعاً مشاهده‌شده `4a3e778543d8a86c9b36b675ab5a263907261343`؛ برابری `compare_commits(start,agent/ui)=identical` قبل از تغییر. قرارداد **دقیقاً** `prep/product-contracts-v1@1937a91e63f0bb11b1fd2135dfa6e96983f813fb` (PR #4، Draft)، شامل [Schema](https://github.com/Shahbazi-Amir/RAG_finance_app/blob/1937a91e63f0bb11b1fd2135dfa6e96983f813fb/packages/contracts/product.v1.schema.json)، [README](https://github.com/Shahbazi-Amir/RAG_finance_app/blob/1937a91e63f0bb11b1fd2135dfa6e96983f813fb/packages/contracts/README.md) و [۷۴ Fixture مصنوعی](https://github.com/Shahbazi-Amir/RAG_finance_app/blob/1937a91e63f0bb11b1fd2135dfa6e96983f813fb/packages/contracts/fixtures/product.v1.cases.json). تصمیم‌های Product v1 همچنان `PROPOSED/NOT_FROZEN` اند.

**پذیرش‌های قبلی، جدا از اجرای محصول:** ناظر در بررسی PR #2، **فقط بستهٔ طراحی اولیهٔ UI-01** در commit `4a3e778543d8a86c9b36b675ab5a263907261343` را پذیرفت؛ این به معنی پذیرش کل UI-01، L1/L2 یا Gate نیست. ناظر همچنین **بازبینی مصرف قرارداد** را برای این تطبیق پذیرفت؛ نه خود قرارداد `product.v1` و نه Engine/Module 00/03 Gate نهایی را. هیچ Checkbox اجرایی تیک نخورده است.

**کار انجام‌شده و دلیل تغییر نسبت به طرح قبلی:** به‌روزرسانی *فقط* `coordination/tasks/AGENT-UI-01.md`: (۱) J2، Composer و Receipt/Retry برای شناسهٔ مکالمهٔ محلی، requested/resolved، Replay/Conflict و Request اصلی immutable؛ (۲) تفکیک State محلی از گزارش server، حفظ exact Delta، جداکردن terminal/partial و display cancel/server stop؛ (۳) Source drawer فقط دادهٔ موجود با Resolution/Attribution مستقل و Anchor حل‌نشده؛ (۴) تأیید موفقیت Feedback با رسید معتبر و ثبت ابهام‌های حذف؛ (۵) پذیرش محدود طراحی و بازبینی قرارداد. علت: اصلاح breaking شناسه‌ها و Locator و Delta در Product v1 regression.1؛ بدون ساخت قرارداد مشترک/DTO جایگزین.

**روش/شواهد بررسی این بسته:** خواندن محتوای دقیق GitHub در commit/شاخه‌های فوق و مقایسهٔ `agent/ui` با Starting SHA؛ بررسی متنی تطابق J2/J3/J5/J6، جدول Stateها، مرز Composer و فیلدهای موجود در `$defs`؛ بررسی ساختار Markdown table، لینک‌های منبع و محدودبودن Diff به همین پرونده. شواهد اصلی: [Draft PR #2](https://github.com/Shahbazi-Amir/RAG_finance_app/pull/2)، [پرونده UI](https://github.com/Shahbazi-Amir/RAG_finance_app/blob/agent/ui/coordination/tasks/AGENT-UI-01.md) و [PR #4 فقط به‌عنوان مرجع قرارداد](https://github.com/Shahbazi-Amir/RAG_finance_app/pull/4). نتیجهٔ Checks متنی و Git diff از گزارش بازبینی GitHub و تاریخچهٔ PR قابل بازیابی است؛ **تست اجرایی L1/L2: NOT_RUN**. Fixtureهای مصنوعی را خودمان اجرا یا به‌عنوان پذیرش موتور اعلام نکرده‌ایم.

**خطا/اصلاح/بررسی مجدد:** پیش از اصلاح، متن J2 شناسهٔ requested/resolved را تفکیک نمی‌کرد، Stateها provenance صریح نداشتند، و Source drawer / Feedback / حذف جزئیات تأیید معتبر یا سؤال‌های باز را کامل نمی‌گفتند؛ همین اصلاحات برای بازبینی اعمال شد. هیچ failure اجرای تست ادعا نشده است؛ هر اختلاف واقعی در Git diff یا لینک باید در همین پرونده پیگیری شود و بازنویسی تاریخچه ممنوع است.

**موانع و تصمیم‌های باز:** Product API final، Auth/Consent، Idempotency TTL و HTTP mapping، reconnect/recovery و transport Eventها، تأیید واقعی Stop سرور، Resume stream، فهرست و Pagination/History، Feedback Request/Receipt، deletion status polling و مالکیت `request_id/trace_id/client_action_id`، نشست پس از حذف، عنوان رسمی Source و مقصد book/transcript Anchor، Citation Resolver و speaker mapping، Retention/Export، Stack/Router/Accessibility targets. NB23 Draft و `provenance.rag_binding=provisional` هستند؛ L2، Module 00/03 و Runtime هنوز `BLOCKED`.

**وضعیت‌های مستقل:** Design-package `ACCEPTED_BY_SUPERVISOR`؛ Contract-consumer review `ACCEPTED_FOR_ALIGNMENT`؛ همین تطبیق `READY_FOR_REVIEW` (پذیرش ناظر برای این تغییر: `PENDING`)؛ Product UI `implemented=NOT_RUN`، `tested(L1/L2)=NOT_RUN`، `accepted=NOT_ACCEPTED`؛ Gateها `NOT_ASSESSED`.

**قدم بعد:** ناظر Diff همین PR #2 را ببیند؛ سپس بعد از تعیین قرارداد نهایی و مأموریت مستقل، پیاده‌سازی و آزمون‌های L1/L2 مشخص شوند. شناسه‌های بالا و لینک به PR #2 برای تطبیق دفتر اصلی به مالک Foundation تحویل می‌شود؛ متخصص UI چک‌لیست اصلی را ویرایش نمی‌کند.
## Checkpoint تجمعی — UI-01-ALIGN-02 / تطبیق با مبنای مشترک ادغام‌شده

**دامنه و شناسه‌ها:** `UI-01-ALIGN-02`؛ فعالیت‌های `UI-01` (Journey/State)، `UI-02` (مصرف قرارداد)، `UI-08` (Source drawer)، `UI-09` (Feedback) و `UI-13` (Deletion). ارجاع رسمی: `P3M01` / Phase 3 Modular Module 01 (scope)، `P3M03` / Module 03 (قرارداد و سازگاری)، `P3M06` / Module 06 (isolation)، `P3M11` / Module 11 (Citation/Attribution)، `P3M13` / Module 13 (Product API/Trace)، `P3M14` / Module 14 (Chat/UI)، `P3M15` / Module 15 (History/Feedback)، `P3M21` / Module 21 (Privacy/Deletion). `P3OP01` و `P3OP05` فقط overlay هستند، نه شمارش موازی پیشرفت.

**ورودی و مبنا:** مخزن `Shahbazi-Amir/RAG_finance_app`؛ HEAD واقعی شاخهٔ `agent/ui` پیش از این تغییر `06272c0f8b0292794c18c66d0b5b6086e83fa190` (برابر با Starting Commit اعلام‌شده؛ هیچ تغییر هم‌زمانی در شاخه مشاهده نشد). مبنای مشترک ادغام‌شده `main@51409d148581214bff916333a641d3871e8a486d`؛ قرارداد `product.v1` در `main` همچنان `PROVISIONAL / NOT_FROZEN`، دارای ۱۷ wire kind و ۲۶ definition و [۹۸ Fixture مصنوعی](https://github.com/Shahbazi-Amir/RAG_finance_app/blob/51409d148581214bff916333a641d3871e8a486d/packages/contracts/fixtures/product.v1.cases.json) است. [Schema](https://github.com/Shahbazi-Amir/RAG_finance_app/blob/51409d148581214bff916333a641d3871e8a486d/packages/contracts/product.v1.schema.json)، [README/CT-09–11 و Feedback Trace](https://github.com/Shahbazi-Amir/RAG_finance_app/blob/51409d148581214bff916333a641d3871e8a486d/packages/contracts/README.md#L108-L135)، [دستور AGENTS](https://github.com/Shahbazi-Amir/RAG_finance_app/blob/51409d148581214bff916333a641d3871e8a486d/AGENTS.md)، [Ownership](https://github.com/Shahbazi-Amir/RAG_finance_app/blob/51409d148581214bff916333a641d3871e8a486d/coordination/ownership.md). بررسی GitHub `compare` شاخه‌ها را diverged با merge-base `2f59c3e3d571aedeef907b944b8273762338cf4e` نشان داد؛ فایل مأموریت در `main` همان blob مبنای Foundation و تغییرات تخصصی فقط در `agent/ui` بود. ادغام به روش **دو-parent merge commit**، نه Rebase یا Force Push، همراه با همین به‌روزرسانی پرونده انجام می‌شود.

**ثبت پذیرش‌های محدود ناظر:** بستهٔ طراحی اولیه UI-01 در `4a3e778543d8a86c9b36b675ab5a263907261343` و بستهٔ تطبیق مستندی قبلی در `06272c0f8b0292794c18c66d0b5b6086e83fa190` با اعلام ناظر **ACCEPTED (documentation/design package only)** هستند. این پذیرش‌ها نه `UI-01` کامل، نه پیاده‌سازی، نه L1/L2 و نه `P3Mxx` Gate را تأیید می‌کنند. ثبت قبلی `UI-01-ALIGN-01` تاریخی است؛ این بخش تکمیل آن با قرارداد ادغام‌شده است.

**تغییر نسبت به طراحی قبلی و علت:** فقط همین فایل مأموریت اصلاح می‌شود. در J5/Feedback، Request/Receipt واقعی provisional `feedback_submit_request` و `feedback_submit_receipt` جای «قرارداد نامشخص» را می‌گیرند: `created/replayed` با ID و زمان ثبت معتبر، `conflict` بدون موفقیت؛ Retry ورودی اصلی و Idempotency ثابت و Trace متعلق به **HTTP attempt جاری** است. در J6/Deletion، کلاینت تنها `client_action_id` تولید می‌کند و `request_id/trace_id/deletion_request_id` از سرور می‌آیند؛ `delete_status_query` مالکیت‌محور است و `unknown-transport` **محلی** است، نه `delete_status.state`. در J3/Source، `display_title` اختیاری همراه `display_title_origin` قابل ارائه است، ولی اصالت و قابلیت بازشدن Anchor را تضمین نمی‌کند. دلیل: تغییرات CT-09، CT-10، CT-11 و Feedback Trace در Product v1 ادغام‌شده؛ بدون ایجاد DTO یا قرارداد موازی.

**روش Checks و شواهد:** GitHub read-only `fetch_file` برای AGENTS، Ownership، UI task، Schema/README/Fixture در SHA مشخص؛ `compare_commits(base=51409d148581214bff916333a641d3871e8a486d,head=06272c0f8b0292794c18c66d0b5b6086e83fa190)` برای بررسی اختلاف و merge-base؛ بررسی تطبیق J3/J5/J6 و Stateها با `$defs.feedback_submit_request`، `feedback_submit_receipt`، `delete_command`، `delete_status`، `delete_status_query` و `source_attribution`؛ بررسی ساختار جدول‌های Markdown، حضور لینک‌ها، ۱۴ چک‌باکس بدون تیک و Diff نسبت به `main`. شواهد قابل بازیابی: [Draft PR #2](https://github.com/Shahbazi-Amir/RAG_finance_app/pull/2) و GitHub compare/commits؛ ثبت نتیجهٔ کنترل پس از Push در گزارش تحویل؛ **هیچ آزمون اجرایی L1/L2 در این نوبت انجام نشده**. تست‌های synthetic متعلق به تیم قرارداد، نه اجرای UI.

**آمادگی L1 (فقط طراحی/Mock؛ اجرا نشده):** [UI-09] Pending/Created/Replayed/Conflict و Retry payload ثابت، تفاوت Trace هر تلاش، قطع شبکه = local unknown؛ [UI-13] تأیید و لغو قبل از ارسال، requesting/processing/succeeded/failed سرور، unknown-transport محلی، Query فقط پس از شناسهٔ معتبر و نمایش عدم بازیابی در فقدان آن؛ [UI-08] عنوان اختیاری/Origin، نبود Locator یا Attribution معتبر، لینک غیرفعال برای Anchor حل‌نشده؛ [UI-01] Journeyهای J3/J5/J6 و Stateها بدون Stack یا Backend واقعی.

**موانع L2 و موارد باز:** API/Auth/Ownership و تحقق واقعی Persistence/Feedback Receipt، HTTP status و Idempotency TTL/Feedback edit policy؛ Recovery حذف هنگام قطع ارتباط قبل از دریافت `deletion_request_id` (Query فعلی تنها `deletion_request_id + client_action_id` را دارد)؛ احراز مالکیت استعلام و سیاست نشست پس از حذف حساب/ابطال Session (تصمیم مستقل امنیت/Auth، بدون lookup ناشناس)؛ Resolver منبع، اثبات منشأ Title و مقصد/مجوز بازشدن Anchor؛ Auth/Consent و Retention؛ NB23 Runtime، Stream/Cancellation واقعی و Module 00/03 Gate. تصمیم Stack همچنان باز است.

**وضعیت‌های مستقل:** مستند این بسته: `implemented=documentation-only`، `review_checks=structural/read-only`، `L1=NOT_RUN`، `L2=NOT_RUN`، `accepted=PENDING_SUPERVISOR_REVIEW`؛ بستهٔ قبلی در `06272c0f8b0292794c18c66d0b5b6086e83fa190`: `ACCEPTED_DESIGN_ALIGNMENT_ONLY`. ۱۴ checkbox اجرایی تیک‌نخورده و کل UI-01، موتور و Gate پذیرفته نیستند.

**قدم بعد:** بازبینی Diff همان Draft PR #2 و تصمیم ناظر دربارهٔ ادامهٔ UI L1 و API/L2. برای انتقال به Foundation فقط شناسه‌های `UI-01,UI-02,UI-08,UI-09,UI-13` و نگاشت `P3Mxx` فوق همراه با شواهد PR آماده‌اند؛ چک‌لیست مشترک تغییر نمی‌کند. تاریخچه بازنویسی نمی‌شود، Main و RAG_finance فقط‌خواندنی باقی می‌مانند.

## Checkpoint تجمعی — UI-CHAT-L1-01 / اولین پیاده‌سازی مستقل چت فارسی

**شناسه و مرجع نقشه:** `UI-CHAT-L1-01`، زیرکارهای `UI-01`, `UI-02`, `UI-06`, `UI-07`, `UI-08`, `UI-10`, `UI-11`, `UI-12`, `UI-14`. ارجاع مستقیم به [Module 14 / Phase 3 modular activities 3–10 and 12](../../references/phase2/roadmaps/RAG_finance_phase3_modular_execution_plan.md#L552): `P3M14-A03` (Chat واکنش‌گرا)، `A04` (Streaming/Cancellation)، `A05` (Claim Citation)، `A06` (Author/Editor)، `A07` (Confidence)، `A08` (No-answer/Clarification)، `A09` (Error/Retry)، `A10` (Keyboard/Focus/Labels)، `A12` (عدم نمایش Debug/Prompt). `P3M14-A11` تنها بررسی محدود چیدمان موبایل/دسکتاپ، نه پذیرش مرورگرهای نهایی؛ `P3M14-A01/A02` (Auth/History واقعی) خارج از دامنه. مالک/دفتر اصلی: `P3M14` و `P3M03`، به‌علاوهٔ `P3M11` (Citation) و `P3M13` (API contract؛ **نه اتصال واقعی**). Gateها بدون تیک باقی‌اند.

**Baseline و کار قبلی:** `Shahbazi-Amir/RAG_finance_app`، `main@062e2b35abcf33007deb409000d94a9b3365fb80`، شاخهٔ مجاز جدید `agent/ui-l1-chat`. پیش از شروع، `main` دقیقاً روی SHA مبنا و شاخهٔ مأموریت/PR تکراری وجود نداشت. [AGENTS](../../AGENTS.md)، [ownership](../ownership.md)، [ADR 0001](../../docs/adr/0001-architecture-proposal.md)، [development environment](../../docs/architecture/development_environment.md)، [main checklist](../phase3_checklist.md)، همین پروندهٔ تاریخی و Schema/README/Fixture مشترک `product.v1.regression.2` بررسی شدند؛ `apps/web` در مبنای اصلی وجود نداشت، پس فقط همان مسیر مصوب ساخته شد. مبنای مشترک [Schema](../../packages/contracts/product.v1.schema.json) با ۱۷ kind/۲۶ $defs و [Fixtureهای Synthetic](../../packages/contracts/fixtures/product.v1.cases.json) با ۹۸ case **بدون ویرایش** مصرف شده است.

**Implemented — فقط L1 مستقل:** مسیرهای تازه `apps/web/**` (Next.js app-router، CSS فارسی/RTL، package manifest با نسخه‌های دقیق، UI و Mock transport مستقل)، `tests/phase3/ui/mock.test.mjs` و `tests/phase3/ui/README.md`؛ و تکمیل همین فایل مأموریت. طرح مستقل شامل ارسال سؤال، سناریوهای answer/partial/no_answer/clarification/refusal/error/unknown/malicious، Receipt created/replayed/conflict با original requested ID immutable، جریان Delta بدون trim، لغو نمایشی در مقابل درخواست/تأیید توقف Mock server، claim citation + drawer، title/role مستقل، null-confidence و rendering امن با React text/no unsafe URL است. تنها Stateهای دریافت‌شده از Mock معتبرند؛ این‌ها وقایع زندهٔ NB23 نیستند. هیچ API، DB، مدل، Auth/Consent، Feedback، حذف، History پایدار، PWA پیشرفته، Deploy یا فاز چهارم پیاده نشده است.

**Versions و دلیل:** Next.js `16.4.5` (Patch امنیتی منتشرشده 2026-11-03، Active LTS)، React/ReactDOM `19.3.1`، TypeScript `6.0.3`، Vitest `5.1.0` و ESLint `10.11.0` + eslint-config-next `16.4.5`، همگی Exact در `apps/web/package.json`. مراجع رسمی: https://github.com/vercel/next.js/releases ; https://github.com/react/react/releases ; https://www.npmjs.com/package/typescript ; https://vitest.dev/blog/vitest-5-1 ; https://nextjs.org/docs/app/getting-started/installation . Next minimum Node 20.9؛ Node 22.16.0 صرفاً Runtime مشاهده‌شدهٔ executor است و تأیید امنیت Patch یا هدف تولید نیست؛ `.nvmrc` ریشه دست نخورده است. برای عدم ساخت Lockfile ساختگی، `apps/web/package-lock.json` هنوز **BLOCKED/NOT_CREATED** تا resolve واقعی npm صورت گیرد؛ این کسری صریحاً شرط پذیرش Build و L1 کامل را مسدود می‌کند.

**روش و نتیجهٔ واقعی Checks در محیط ایزوله:** 
- `node -v` → `v22.16.0`، `npm -v` → `10.9.2`، `tsc -v` → `5.8.3` موجود (Global TypeScript صرفاً برای تشخیص/تست هسته؛ نسخهٔ هدف package.json متفاوت است).
- `timeout 12s npm view next@16.4.5 version --fetch-retries=0 --fetch-timeout=10000` → **FAILED / EAI_AGAIN**، DNS `registry.npmjs.org` قطع؛ `npm install --package-lock-only --offline --ignore-scripts --no-audit --no-fund` در `apps/web` → **FAILED / ENOTCACHED** برای @types/node. نصب/Lockfile/Resolution از رجیستری انجام نشد؛ هیچ نصب سراسری یا محیط Mac تغییر نکرد.
- `node --experimental-strip-types --test tests/phase3/ui/mock.test.mjs` با **سه نمونهٔ Temp محلی ساختاری از Fixtureهای مشترک، نه کل ۹۸ Fixture و نه تست اپ Next** → **7/7 PASS** (Mock idempotency/replay/conflict، حفظ Space/Newline، تمایز outcome و Cancellation، URL و متن مخرب). **این نتیجه پیش از ثبت نهایی و در workspace موقت** بود؛ اجرای suite از checkout واقعی GitHub/تمام Fixtureها: **NOT_RUN**؛ مسیر کد آزمون ثبت‌شده در [test](../../tests/phase3/ui/mock.test.mjs).
- `tsc --noEmit --strict --skipLibCheck --target ES2022 --module nodenext --moduleResolution nodenext --resolveJsonModule apps/web/src/mock/transport.ts` → **PASS فقط Transport** با compiler پیش‌نصب‌شده و Fixtureهای Temp محلی؛ این `npm run typecheck` نیست.
- `npm run typecheck` → **FAILED** با خطای `Cannot find module 'next'/'react'` و JSX types غایب، چون نصب مسدود است؛ `npm run lint` → **FAILED**, `eslint: not found`؛ `npm run build` → **FAILED**, `next: not found`. اجرای Next روی loopback، Browser review واقعی دسکتاپ/موبایل و Screenshot واقعی: **NOT_RUN / NOT_AVAILABLE**. هیچ Build/Lint/Typecheck یا Browser PASS ادعا نمی‌شود؛ فرایند Next/مرورگر موقتی برای توقف وجود نداشت.
- بازبینی ساختاری GitHub بعد از Push: محدودیت مسیرها، لینک‌ها، عدم وجود Schema/Root edits، Checkpoint و Diff/PR در گزارش تحویل بررسی می‌شود. شواهد ماندگار: [Mock transport](../../apps/web/src/mock/transport.ts)، [UI](../../apps/web/app/page.tsx)، [test](../../tests/phase3/ui/mock.test.mjs)، [Draft PR مأموریت](https://github.com/Shahbazi-Amir/RAG_finance_app/pulls). لاگ حجیم/Cache/Secret/Node modules وارد Git نشد.

**خطا و اصلاح:** محدودیت DNS و Cache باعث شد Install، Lockfile، Build، Typecheck کامل، ESLint و Screenshot واقعی مسدود بمانند؛ دورزدن با Lockfile جعلی یا ادعای اجرای مرورگر انجام نشد. در ممیزی قراردادِ Mock مشخص شد `stream_event.contract_version` لازم است؛ قبل از Commit به همهٔ Eventها افزوده شد. سایر خطاهای احتمالی فقط بعد از نصب و اجرای واقعی قابل تشخیص‌اند.

**وضعیت، وابستگی و قدم بعد:** `implemented=PARTIAL_L1_SOURCE`؛ `tested=NODE_MOCK_7_PASS_ON_TEMP_FIXTURES`؛ `full_L1_ACCEPTED=NO`؛ `L2=NOT_RUN`؛ `P3M14_GATE=NOT_PASSED`؛ `supervisor_approval=PENDING`. ۱۴ Checkbox بالای این پرونده عمداً بی‌تیک ماندند، چون معیار کامل شامل Build/Typecheck/Lint/Screenshot و بررسی واقعی موبایل/Focus انجام نشده است. گام بعد، **فقط با مأموریت/محیط مجاز**: resolve+install داخل `apps/web` و ساخت Lockfile واقعی، تکرار suite با Fixture کامل، Build/Typecheck/Lint، اجرای موقت UI روی loopback، آزمون واقعی مرورگر/Focus/موبایل و تهیهٔ Screenshot معتبر؛ سپس بازبینی PR و درخواست پذیرش محدود L1. برای L2 همچنان Auth/Backend و NB23 adapter، Citation Resolver، streaming/cancel واقعی و Gateهای ناظر بازند.
