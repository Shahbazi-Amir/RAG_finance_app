# UI_F3 | چرخهٔ مستقل وارسی رسید L2 — 2026-11-23

> **Status: LOCAL_DELIVERABLE_ONLY / GITHUB_WRITE_BLOCKED / NOT_MERGED / NOT_DEPLOYED / NOT_L2_ACCEPTED**
>
> این خروجی برای ادغام در Draft PR #65 پیشنهاد شده و تا هنگام ثبت واقعی در GitHub، بخشی از HEAD آن PR یا CI رسمی نیست. هیچ عملیات Mac، OIDC، BFF/PG، C018، Gateway یا مدل زنده انجام نشد.

## 1. مبنا و شمارش ثابت

- سند مأموریت: `01_UI_F3_COMPLETE_EXECUTION_UPDATED_20261123(1).md` (بخش «مبنای فعلی»، «وضعیت آغاز» و چک‌لیست UI-01 تا UI-14)، `01_UI_F3_Phase3_Completion(2).md` (۱۴ کار تخصصی و Gateهای M03/M11/M14/M15)، و `01_UI_F3_ROADMAP_CHECKLIST_DONE_REMAINING_FA(1).md` (۱۵۴ فعالیت وابسته؛ Snapshot).
- آخرین UI SHA که در **چرخهٔ قبلی** با موفقیت GitHub CI تأیید شده بود: `f45caa45139d2e147c3e45fd7349033b212342c7` در Draft PR #65. جدیدترین SHA remote به‌علت اختلال اتصال GitHub از این نوبت **NOT_RECONFIRMED** است.
- پوشش داشتن مقداری کد UI: **11/14 = 78.5714%**؛ ۲ کاملاً source-level، ۹ partial، ۳ فاقد flow عملیاتی. عدد **کامل شدن پروژه نیست**.
- پذیرش واقعی UI: **0/14 = 0.00%**؛ ۱۴ فعالیت باز و نیازمند L2/مالک.
- ۱۵۴ ردیف وابستهٔ Snapshot: **81 PARTIAL (52.60%)**، **43 NOT_RUN (27.92%)**، **30 NOT_VERIFIED (19.48%)**؛ پذیرش سند **0/154**. این مخرج اختصاصاً متعلق به UI نیست.
- تغییر در درصدهای فوق در این چرخه: **+0.00 واحد درصد**. افزایش تعداد آزمون‌ها یا آماده‌سازی ابزار L2 به‌معنای پذیرش نیست. هیچ‌کدام از ۲۶ Gate مستقل بسته نشده و ۱۰۵ P3OP نباید دوباره به جمع اضافه شود.

```
SOURCE CODE COVERAGE  [███▒▒▒▒▒▒▒▒▒▒▒░░░] 78.57% (2 code-complete + 9 partial + 3 absent)
REAL L2 ACCEPTANCE    [░░░░░░░░░░░░░░░░░]  0.00% (14/14 open)
RELATED P3M ACCEPTED  [░░░░░░░░░░░░░░░░░]  0.00% (snapshot 0/154)
```

## 2. اقدام executable این چرخه

| ID/مرجع | کد قابل اجرا | Assert قابل بازتولید | محیط و شاهد | وضعیت پذیرش | شکاف/مالک |
|---|---|---|---|---|---|
| UI-03/05/06; P3M14-A01/A02/A09; P3M15-A07/A10 | `tests/phase3/integration/ui/l2_no_dispatch_receipt_gate.py` | ورود واقعی دو actor مجزا و signed context (به‌صورت دادهٔ نرمال‌شدهٔ تأییدنشده)، 401 پس از revoke و 404 برای B؛ post اصلی فقط یک بار، Refresh فقط GET | اجرای **محلی / ساختگی** Unit؛ real Mac receipt ندارد | **OPEN — 0 L2** | Foundation/Ops باید شواهد واقعی Browser+HTTP/DB/OS و integrated SHA، log دارای احراز هویت و approval مشخص بدهند |
| UI-05/06/10/12; P3M15-A01/A03/A10; P3M14-A09 | همان verifier | تساوی T2/Attempt/Trace across browser→API→DB→OS؛ یک POST user، یک write، صفر write/child مجدد after Refresh؛ NO_DISPATCH و top10=10 | `test_l2_no_dispatch_receipt_gate.py`: **31/31 PASS** در محیط local Python stdlib؛ نه GitHub CI | **OPEN — 0 L2** | Mac TLS/OIDC signed A/B و API61/DB59/Engine C018 واقعی با رسیدهای مستقل |
| UI-11/12/14; P3M14-A10/A11/A12; P3M21-A02/A04 | همان verifier و سند قرارداد رسید | اجازهٔ witness فقط داخل base و SHA256 واقعی، رد مسیر `../`, عدم reuse فایل هر لایه، منع لوکال HTTP، نیاز به evidence دسترس‌پذیری مرورگر | 31 تست شامل رد witness دستکاری‌شده، synthetic و double dispatch | **OPEN — 0 L2** | Ops وسنجش actual RTL/focus/contrast/screenshot sanitized؛ snapshot/CI مصنوعی کافی نیست |
| UI-01/02/07/08 | فقط consumer contract در همین verifier | SHAهای UI/API/DB/Engine/Integrated باید دقیق باشند؛ verifier هیچ Citation جدیدی تولید نمی‌کند | Schema **consumer-only** `ui.l2.nodispatch.v0_1`، نه Product wire DTO | **OPEN — 0 L2** | Foundation accepted integrated tree و API/Phase2 signed producer/Citation بعد از NB23 |
| UI-04/09/13 | دست‌نخورده | Consent/Feedback/Delete/Export endpoint فعال نمی‌کند | `NOT_IMPLEMENTED/CONTRACT_BLOCKED` | **OPEN — 0 L2** | API/DB/Product/Legal نسخه، متن سیاست، retention/revoke/terminal ack بدهند |


## 2.1 وضعیت تک‌تک ۱۴ فعالیت UI (همان مخرج رسمی)

| UI-ID | آخرین وضعیت شناخته‌شده در منبع | افزایش پذیرش در چرخهٔ جاری | شرط باز برای بستن |
|---|---|---:|---|
| UI-01 | source جزئی | ۰ | Architecture/Scope ADR و Journey روی integrated SHA، Foundation approval |
| UI-02 | source جزئی | ۰ | Contract توافقی و consumer/producer واقعی API و CI روی یک SHA |
| UI-03 | source جزئی | ۰ | signed A/B OIDC، logout/revoke/session rotation روی Mac |
| UI-04 | flow عملیاتی ندارد | ۰ | متن و نسخهٔ Consent، withdrawal، DB ledger و سیاست محصول |
| UI-05 | source جزئی | ۰ | History owner-bound و Pagination واقعی با 401/404، DB evidence |
| UI-06 | source جزئی | ۰ | RTL و Composer واقعی، Send/Refresh same-T2 و عدم ارسال تکراری |
| UI-07 | source جزئی | ۰ | Answer/Confidence مبتنی بر producer پذیرفته‌شده، no-answer/partial |
| UI-08 | source جزئی | ۰ | Claim-Citation-Resolver معتبر از Phase2؛ عدم انتساب ساختگی |
| UI-09 | flow عملیاتی ندارد | ۰ | Feedback دارای persisted Answer ID، receipt/idempotency/owner |
| UI-10 | source جزئی | ۰ | قرارداد versioned stream/cancel/terminal، producer and API owner |
| UI-11 | source/تست پیشرفته، هنوز نیازمند L2 | ۰ | ماتریس Mac Browser، RTL/Keyboard/contrast واقعی |
| UI-12 | source/تست پیشرفته، هنوز نیازمند L2 | ۰ | Browser→BFF→API→DB→OS + exact SHA و Gate مستقل |
| UI-13 | flow عملیاتی ندارد | ۰ | delete/restore tombstone، revoke و Export مستقل مصوب |
| UI-14 | source/تست دفاعی، هنوز نیازمند L2 | ۰ | XSS/URL/secret negative test بر دادهٔ واقعی و security acceptance |

**یادداشت وضعیت:** دسته‌بندی جدول بر اساس مبدأ ۱۱/۱۴ و ۲ source-complete و ۹ partial و ۳ بدون flow است؛ تعیین دقیقِ کدام دو فعالیت «کامل در سطح کد» در نسخهٔ مبنا برای این گزارش مجدداً از GitHub قابل راستی‌آزمایی نشد و بنابراین این جدول به‌جای تخصیص حدسی، وضعیت مستقل هر فعالیت را محافظه‌کارانه نوشته است. شاخص جمع ۱۱/۱۴ تغییری نکرده است.

## 3. فرمت محدود رسید و روش اجرا

- ورودی **JSON از رسید واقعی** برای یک اجرای مجاز مجزا با `kind=ui_f3_mac_no_dispatch_l2_receipt`, `schema_version=ui.l2.nodispatch.v0_1`, `fixture_only=false` و `environment=isolated_mac_https_oidc` است.
- `provenance` باید پنج SHA چهل‌رقمی `integrated_sha/ui_sha/api_sha/db_sha/engine_sha` + `ops_approval_ref` و `runner_mode=NO_DISPATCH_ONLY` را داشته باشد. این رشته‌ها به‌تنهایی صحت امضا، مجوز یا نصب را ثابت نمی‌کنند.
- `browser` فقط `actor_a_session_alias` و `actor_b_session_alias` غیرمحرمانه و مجزا دارد؛ **کوکی واقعی، JWT، توکن، اطلاعات شخصی یا Secret هرگز در رسید وارد نشوند**. ورود/خروج واقعی، مخفی‌شدن stale GET در recovery و revocation، focus/RTL و تب B باید توسط Ops در مرورگر واقعی شاهد مستقل داشته باشند.
- `correlation` حاوی `t2_id`, `attempt_id`, `attempt_trace_id`, `client_message_id`, `idempotency_key`, `question_sha256` است. `http_events` با Sequence صعودی و `actor/layer/phase/method/path/status` باید همین correlation را نشان دهند؛ ۱ POST اولیه در Browser و ۱ دریافت همان POST در API، GET status در ابتدا و پس از Refresh، جواب 503 برای فهرست در زمان قطعی و GET 200 برای همان actor در recovery، GET فهرست بعد از Refresh، 404 برای B و 401 پس از revoke برای A.
- `database` باید مالکیت A و رد B، یکتا بودن عملیات و **صفر رکورد تازه** after Refresh را گزارش کند. `runner` باید child واحد C018 before/after، top10 ده عدد، صفر generation و `dispatch_performed=false` باشد. تمام چهار فایل witness مستقل باید در پوشهٔ رسید موجود و SHA-256 آن‌ها مطابق باشند.
- ابزار صرفاً **انسجام ساختاری و متقاطع** را بررسی می‌کند؛ سندی که خودش می‌گوید real است ولی دروغ نوشته شده را نمی‌تواند کشف کند. خروجی موفق همچنان `RECEIPT_INTERNALLY_CONSISTENT_NOT_GATE_ACCEPTED` و `gate_accepted:false` است. پذیرش Gate فقط توسط owner و ارزیابی مستقل provenance و شواهد واقعی ممکن است.

```bash
# Local, completely offline unit tests (no model/API/DB/Git):
python3 -m unittest discover -s tests/phase3/integration/ui -p 'test_l2_no_dispatch_receipt_gate.py' -v

# Real receipts are supplied later by separately authorized Ops:
python3 tests/phase3/integration/ui/l2_no_dispatch_receipt_gate.py /path/to/authorized/sanitized/mac_l2_receipt.json
```

## 4. مرزهای ایمنی و گام بعدی

1. **ابتدا دسترسی GitHub را ترمیم کن**؛ قبل از ثبت هیچ commit/CI جدیدی در PR #65 ادعا نکن. فقط بعد از تأیید HEAD و SHA، این سه فایل را در مسیرهای ذکرشده اضافه کن، Node/Next/Chromium موجود را دوباره روی **exact new HEAD** اجرا کن و نتیجه را در PR و Foundation #55 بنویس.
2. Foundation/Ops باید نصب جداگانه و مجوز Mac real HTTPS/OIDC A/B را ثابت کنند؛ no-dispatch با C018 واقعی فقط تحت مجوز صریح؛ هیچ تولید پولی یا راه‌اندازی سرویس موجود از این سند مجاز نمی‌شود.
3. پس از receipt واقعی، verifier ممکن است بگوید تمام assertions ساختاری درست‌اند؛ کار بررسی امضا/مجوز/لاگ مستقل توسط Owner همچنان باقی است. اگر حتی یک Assertion قرمز ماند، UI L2 همان ردیف باز است.
4. قرارداد stream/consent/delete تنها پس از تأیید مالک و API/DB/Legal قابل پیاده‌سازی عملیاتی است. UI-01/02 و Gate M14 بعد از integration واقعی و UAT قابل پذیرش خواهند بود.

## 5. نتیجهٔ اجرای همین نوبت

- ۳۱ آزمون مستقل Stdlib در Python **PASS**؛ بدون دسترسی شبکه و بدون تغییر محصولات موجود.
- سه فایل جدید در بستهٔ قابل انتقال:
  - `tests/phase3/integration/ui/l2_no_dispatch_receipt_gate.py`
  - `tests/phase3/integration/ui/test_l2_no_dispatch_receipt_gate.py`
  - `coordination/handoffs/UI_F3_L2_NO_DISPATCH_EVIDENCE_CYCLE_20261123.md`
- GitHub commit جدید: **NOT_CREATED**؛ GitHub Actions جدید: **NOT_RUN**؛ `PR #65` remote جدید: **NOT_RECONFIRMED**؛ Mac L2: **NOT_RUN**؛ Acceptance delta: **0/14**.
