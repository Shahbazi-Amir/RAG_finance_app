<div dir="rtl" align="right">
### NB23.C011 — راهنمای فارسی مصرف نمونهٔ گفت‌وگو و قرارداد فاز سوم

**وضعیت:** پیش‌نویس، غیرقابل معرفی به‌عنوان Release پذیرفته‌شده.

**مرجع نسخه:** `5e887e429a08bd6ca30297cc293912ddbd4b1b90f25f0ee0a2d894ee24cdc3d6`

#### قرارداد ورودی و پاسخ

- درخواست `nb23.request.v1` فقط `contract_version` و `question` دارد؛ `conversation_history`، `source_filter`، `authority_filter` و `context` ورودی تأییدشده نیستند.
- پاسخ `nb23.response.v1` شامل `outcome`، `answer_text`، `claims`، `citations`، `confidence`، `version_trace`، `provenance` و `error` است؛ تمام فیلدهای اجباری باید بررسی شوند.
- `version_trace.source_fingerprint` باید به Lock نسخهٔ انتخاب‌شده وصل باشد؛ `release_id` دقیقاً از `NB23_INPUT` خوانده می‌شود و برای ورودی‌های پذیرفته‌نشده `null` است.
- شش وضعیت پاسخ فقط Enum پیشنهادی مصرف‌کننده‌اند؛ نگاشت واقعی موتور NB19/NB20 و HTTP/Streaming هنوز آزموده نشده است.

#### Citation و Attribution

- `claims[].citation_ids` و `citations[].claim_ids` باید سازگار باشند؛ جزئیات منبع در `resolved_citations` فقط برای Fixtureهای آزمون ارائه شده‌اند و فیلد رسمی Response نیستند.
- نوع منبع `website`، `book` یا `transcript` است؛ Locator واقعی باید با سند کانونی هم‌خوان باشد.
- نقش `direct_author` با `editorial_supervision` متفاوت است. نام گویندهٔ نامعلوم را حدس نزنید و زمان یا صفحهٔ مفقود را جعل نکنید.
- شناسه‌های `SYNTHETIC_...`، دامنهٔ `example.invalid` و Locatorهای داخل نمونه‌ها ساختگی‌اند؛ نمونه‌ها **سند قابل استناد واقعی نیستند**.
- اعتبار ساختاری Citation به معنای اثبات معنایی Claim نیست؛ اتصال Chunk/Evidence نیز هنوز احراز نشده است.

#### گفت‌وگو، نبود پاسخ و ایمنی

- نمونهٔ clarification دو Turn دارد، اما history در Request جدید وارد نمی‌شود؛ مدیریت مکالمه، هویت کاربر و بازنویسی سؤال مسئولیت فاز سوم است.
- `NO_ANSWER` را با خطای Provider، Timeout یا وضعیت نامعلوم اشتباه نگیرید.
- مثال `SAFETY_REFUSAL` و مرز توصیهٔ مالی فقط Mock قراردادی است؛ آن را نتیجهٔ واقعی Policy یا تأیید ایمنی تلقی نکنید.
- `PARTIAL` فقط وضعیت Draft است و پاسخ ناقص به‌عنوان موفقیت کامل موتور اعلام نمی‌شود.

#### Confidence، خطا و منشأ

- `confidence: null` یعنی اندازه‌گیری ارائه نشده است؛ مقدار `0` تنها در صورت تعریف و ثبت اندازه‌گیری قابل تفسیر است.
- `error` برای `ERROR` الزامی است و خانوادهٔ خطاهای Draft را باید از تصمیم پاسخ تفکیک کرد.
- تمام نمونه‌های این بسته `SYNTHETIC_CONTRACT_FIXTURE` و `NOT_EXECUTED` هستند؛ نه Historical Saved Output، نه Replay، و نه Live Qwen.
- در خروجی اشتراکی Secret، توکن، اطلاعات کاربر، مکالمهٔ خصوصی و مسیر شخصی را قرار ندهید.

#### مسئولیت Module 00 فاز سوم

- قبل از تحویل رسمی: Release پذیرفته‌شده، Hashهای authoritative، Resolver کامل، Contract Test، Smoke، ایمنی و Compatibility واقعی باید جداگانه احراز شوند.
- وضعیت Release بالادستی از `NB23_INPUT` خوانده می‌شود؛ حتی اگر بالادست پذیرفته باشد، این Fixtureها پذیرش رسمی NB23 یا استقرار را اثبات نمی‌کنند.
- وضعیت Release ورودی انتخابی: `NOT_ACCEPTED_UPSTREAM`؛ این یک گزارش از Adapter است، نه تصمیم مستقل فاز سوم.

</div>