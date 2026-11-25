# Execution log

## 2026-11-23 / CODEX-REPORTING-01

- Recorded the [starting baseline](BASELINE.md) and [sanitized backup assessment](BACKUP_STATUS_FA.md). Historical reports from both existing backup revisions were reviewed. No new restore or runtime test was performed.
- `git status --short --branch`, `git rev-parse HEAD`, `git remote -v` and `git worktree list` identified the clean detached workspace and the Phase 3 destination.
- Sandboxed GitHub access failed. The approved retry with `gh repo view` confirmed the non-fork repository and ADMIN permission. `git ls-remote --heads origin refs/heads/codex` returned no matching branch. A separate worktree was created from the observed starting SHA.
- Added the report index, baseline, log, Persian assessment, recovery plan and current status. Publication is tracked by Git history and verified against the remote branch ref at delivery.
- Roadmap references are P3M22-A06 and P3OP11-R07 for the recovery evidence. No gate or checklist progress is claimed. Supervisor acceptance is pending.
- Historical recovery issues included an unavailable Docker socket, incompatible compression and read-only extraction permissions. The local reports record a successful second Docker capture and successful rechecks of all six base archives after corrections.
- Generated the Persian HTML in the secure backup folder. The renderer checked UTF-8 round-trip and three table rows (header and two data rows). macOS `open` exited successfully.
- Staged only the six report Markdown files and the mission checkpoint. Review used `git diff --cached --check` and `git diff --cached --name-status`.

## Docker_3 / NB23-SESSION-RESUME-09

- بازیابی checkpointهای محلی ۰۱ تا ۰۹ و نتیجهٔ HTTP Callback، آزمون مالک دوم و restore منطقی با خروج ۰. Chrome Stable و Canary در DevTools timeout داشتند.
- مقایسهٔ Python روی ۱۰۲ مشاهدهٔ ONNX و شش مشاهدهٔ مشترک Native نتیجهٔ MatMulInteger شاخهٔ ۱ را محدود کرد. AST هر ۱۶ فایل Python و git diff --check موفق بود. قبلاً بازبینی خودکار با 404 متوقف شد؛ در این نوبت فهرست Docker و فرایندها از مسیر مجاز خوانده شد.
- وضعیت شمارش ۲/۲۰ → ۴/۲۰. [فهرست کد، خطاها، آزمون‌ها و ادامه](MAC_FIRST_START_FA.md#docker_3--بازیابی-پس-از-انتقال-حساب)

## NB23-SESSION-RESUME-10

- Docker exact-attention خروج ۰. عملوند چپ متفاوت، راست و هر دو zero point برابر، ضرب دقیق در هر دو محیط با صفر خطا. probe برای ورودی/خروجی Softmax گسترش یافت. افزایش پیشرفت صفر.

## NB23-SESSION-RESUME-11

- جفت Softmax خروج ۰، دو کنترل logits برقرار، ورودی برابر و خروجی متفاوت. فعالیت ۱۰ تکمیل شد.
- بازیابی DB روی tmpfs، تشخیص مجوز EXECUTE و اجرای سه GRANT محافظت‌شده، Chrome CDP روی صفحهٔ خالی خروج ۰. آزمون Browser E2E هنوز آغاز نشده است.

## NB23-SESSION-RESUME-12

- BFF و Bootstrap جداشده بازسازی شدند و هر دو HTTPS با TLS=0 پاسخ ۲۰۰ دادند. Chrome Page.navigate timeout داد. بازبینی آزمون navigation تغییرکرده HTTP 404 داد.
- Docker Softmax-reference خروج ۰. گزینهٔ نامزد دقت دوگانه برای یک Batch اضافه شد. پیشرفت بدون تغییر.

## NB23-SESSION-RESUME-13

- Native float64 reference خروج ۰، دو کنترل و fingerprintهای قبلی برابر. بازبینی Docker candidate و اولین تلاش انتشار گزارش تکمیلی با HTTP 404 خاتمه یافت. آزمون نامزد Native آغاز شد.

## NB23-SESSION-RESUME-14

- نامزد Native FP64 خروج ۰، کنترل‌ها برقرار، ولی اختلاف جدید logits برابر ۰٫۳۱۳۶۶۴۹۱۳۱۷۷۴۹۰۲۳. نامزد پذیرفته نشد و Golden کامل آغاز نشد. تلاش دوم commit/push در بازبینی خودکار HTTP 404 داد.

## NB23-SESSION-RESUME-15

- بازبینی Docker موفق شد. مسیر Worker آفلاین و API ایزوله پیاده شد. بررسی کد و سه fixture موجود موفق بودند. fixture سوکت sandbox-denied. آماده‌سازی PostgreSQL آغاز شد.

## NB23-SESSION-RESUME-16

- شروع پشته مستقل و HTTPS معتبر پس از گرم‌شدن Keycloak. چهار fixture موفق. Chrome Callback و History موفق؛ SEND_BUTTON_NOT_ENABLED قبل از POST. Harness با readiness و مسیر دو پرسش به‌روز شد.

## NB23-SESSION-RESUME-17

- Chrome Send و Refresh همان Attempt، یک POST، مهلت SQL معتبر. Worker واقعی CONTEXT_READY و ۹۵٫۵۳۷ ثانیه. ابزار مشاهدهٔ UI به ۹۵ ثانیه رسید؛ سقف هدفمند اصلاح شد. فایل‌های نمایش زمان و image مستقل آمادهٔ build هستند.

## NB23-SESSION-RESUME-18

- بازیابی Chrome نتیجهٔ واقعی ذخیره‌شده بدون POST، دو زمان از PID ثابت، build مشتق UI و آزمون ذخیرهٔ زمان و مالک در SQLite. بررسی UI فعال، سؤال دوم و Logout بازند.

## NB23-SESSION-RESUME-19

- تثبیت شاهد UNKNOWN، آزمون موفق مالک دوم در endpointهای Status، build مشتق بازیابی مالک و آماده‌سازی آزمون انقضای طبیعی. علت داخلی UNKNOWN تأیید نشده است.

## NB23-SESSION-RESUME-20

- cold readiness واقعی، HTTPS موفق، دو CDP timeout و حالت FAILED واقعی در ازدحام. تشخیص تمدید غیرمجاز replay و انتقال تمدید به Send تازه. fixture هم‌بستگی ۵/۵ PASS.

## NB23-SESSION-RESUME-21

- TimeoutError واقعی و حفظ UNKNOWN/FAILED، تشخیص 503 صفحه‌بندی، کلید محلی 0600 و آزمون نگهداشت آن. بازبینی Push قبلی HTTP 404؛ انتشار تجمعی دوباره از مسیر مجاز پیگیری می‌شود.

## NB23-SESSION-RESUME-22

- خروج API هم‌زمان با انتظار Worker، تفکیک readiness، بازآزمون واقعی History و FAILED replay بدون تمدید، همان Attempt. T17 PASS؛ Send تازه و Chrome نهایی بازند.

## NB23-SESSION-RESUME-23

- آخرین rollout عملی exit 1 با TimeoutError readiness. Send تازه و Chrome نهایی اجرا نشدند. جدول T01–T20 و روش شروع/بازگشت به‌روز شدند. HTTP 404 بازبینی ثبت شد.

## NB23-SESSION-RESUME-24

- شروع af57f26، گزارش b67d6a4. بازبینی منابع و Cache و بازیابی محدود پشته. خروجی قدیمی timeout با زمان startup جاری تفکیک شد. Chrome دو سؤال در جریان.

## NB23-SESSION-RESUME-25

- ورود و History امضاشده PASS، یک Send واقعی RUNNING→UNKNOWN، بازیابی خودکار یک Worker. Chrome pipe/WebSocket/DOM پیش از Send متوقف شدند. پیشرفت ۱۳/۲۰ خصوصی بدون افزایش.

## NB23-SESSION-RESUME-26

- نمونهٔ میزبان و همهٔ سرویس‌ها، نبود فرایند اضافی، و مرز دقیق ۱۸۰ ثانیه با یک Send تازه. بدون تغییر Docker، بدون تکرار Chrome، چک‌لیست دستی پیوست شد.

## NB23-SESSION-RESUME-27

- بازیابی ترتیبی پشته با Swap کمتر، HTTPS و Worker معتبر، یک Send واقعی CONTEXT_READY و آزمون replay/Logout امضاشده خروج ۰. پنجرهٔ اختصاصی Chrome راه‌اندازی شد و فرایندها روشن ماندند.

## NB23-SESSION-RESUME-28

- ثبت شاهد نخستین آزمون مالک، مهلت‌های نسخهٔ B، اصلاح draft و وضعیت/polling، Build آفلاین و جایگزینی محدود BFF/Bootstrap. آزمون واقعی HTTPS موفق و آزمون Chrome در Logout ابزار ناموفق بود.

## NB23-SESSION-RESUME-29

- ثبت موفقیت دستی قبلی، Build آفلاین، dry-run SQL و backfill بدون تغییر شمار ردیف‌ها، تعویض BFF و حفظ store، آزمون امضاشده موفق. Chrome جاری در Page.navigate timeout. [فهرست مستقل اصلاح‌ها](LOCAL_DOCKER_UI_FIXES.md).

## NB23-SESSION-RESUME-30

- ثبت تأیید انسانی شش آزمون checkpoint ۲۹. آرشیو خصوصی ۲۲۱ فایل، هفت ایمیج، Compose پین‌شده و دستور بازیابی ساخته و بدون شروع سرویس بررسی شدند.

## NB23-SESSION-RESUME-31

- استخراج فقط‌خواندنی قرارداد و pin، فایل خصوصی محدود و شش آزمون Mock. مانع انتقال Context و egress ثبت شد. آزمون واقعی، تغییر UI و Restart انجام نشد.

### NB23-SESSION-RESUME-32

مبنای اجرایی `ops/nb23-v4-staging` روی `af57f26` با WIP محفوظ و مبنای گزارش `a25d9df` است. Wrapper جاری از Attemptهای پیشین فقط هش و شمار شواهد به محصول رسانده است. نسخه محلی Mock برای Attempt تازه، تابع موجود `retrieve_context` را دقیقاً یک بار صدا می‌زند و Context را پس از تطبیق مالک، Attempt، Trace، هش سؤال و هش Context از سوکت خصوصی به API می‌دهد. Context در پاسخ HTTP، History و دفتر Mock ثبت نمی‌شود. موتور، مدل، منابع و الگوریتم تغییر نکردند.

مسیرهای تغییر یافته عبارت‌اند از `infra/nb23-v4/worker.py`، `session_worker_socket.py`، `session_product_api.py`، `session_generation_mock.py`، `session-generation-mock.compose.yaml`، `test_session_generation_bridge.py`، `test_session_generation_ui.mjs`، `src/phase3/rag_runtime/persistent_v4_pipe.py`، `apps/api/product_session_api.py`، `apps/web/src/history/client.ts` و `apps/web/src/ui/product-chat.tsx`. نام‌های کوتاه پس از worker.py همگی در `infra/nb23-v4/` قرار دارند. درج وضعیت اولیه Mock و CONTEXT_READY در همان تراکنش دفتر محلی انجام می‌شود. پاسخ ثابت ساختگی پس از اعتبارسنجی و ذخیره خصوصی، با GET احرازشده همان Attempt خوانده می‌شود. رابط از اتصال موجود سؤال با Message ID و تطبیق Attempt و Trace استفاده می‌کند. PostgreSQL و قرارداد عمومی تغییر نکرده‌اند. این پوشش با فلگ صریح محلی فعال می‌شود.

آزمون `python3 -m unittest -v infra/nb23-v4/test_session_generation_bridge.py` در ایمیج API، روی mount فقط‌خواندنی، با `--network none`، بدون Secret و Docker Volume نسخه B انجام شد. Worker ساختگی، فرایند و سوکت Unix واقعی، handler واقعی، SQLite واقعی و تابع وضعیت واقعی API پوشش داشتند. لایه احراز هویت امضاشده و History PostgreSQL در این آزمون با داده مصنوعی جایگزین شدند. اجرای نخست به دلیل تفسیر Payload بایتی به‌عنوان dict به OUTCOME_UNKNOWN رسید. دیکد JSON اصلاح شد و بازآزمون موفق بود: یک فراخوانی Retrieval و یک Mock، بازخوانی پس از بازگشایی دفتر، رد مالک و Trace دیگر، حذف Context از پاسخ عمومی. آزمون تازه Node با `node --disable-warning=MODULE_TYPELESS_PACKAGE_JSON --test infra/nb23-v4/test_session_generation_ui.mjs` موفق بود و GET، وضعیت Pending/Complete و رد فیلد Context اضافی را پوشش داد. بررسی TypeScript با `tsc --noEmit --incremental false` در ایمیج Web ابتدا دو TS2307 برای قرارداد و fixture داشت. اتصال فقط‌خواندنی `packages/contracts` به مسیر متناظر و بازآزمون خروجی صفر داد. `git diff --check` موفق بود. شش آزمون checkpoint 31 و آزمون‌های قبلی مالک تکرار نشدند. هیچ نتیجه Chrome تازه ثبت نشد.

پیشرفت مستقل Generation از قرارداد و harness آفلاین به پل خصوصی، ذخیره و نمایش Mock و آزمون مؤلفه‌ها رسیده است. آزمون کامل مرورگر، BFF و پایگاه داده در یک پشته پاک جداگانه، Adapter عملی HTTPS بیرونی و سیاست اعتبارسنجی معنایی پاسخ واقعی بازند. مجوز ارسال منابع به Gateway همچنان احراز نشده است. جست‌وجوی عمومی تعرفه همان اتصال آروان را احراز نکرد. برآورد تاریخی برنامه ۴۸۴٫۰۲ تومان برای حداکثر سه درخواست ثابت است: یک تست ساختگی ۱۰۰/۳۲ توکن و حداکثر دو سؤال مالی ۴۰۹۶/۶۰۰ توکن با Context دارای مجوز. قیمت جاری باید مستقل از برآورد تاریخی از مالک حساب Gateway احراز شود. Generation/Gateway نسخه B خاموش‌اند و هیچ درخواست پولی یا ارسال Context خارجی رخ نداد. رسمی ۵/۲۰، Golden و Freeze در انتظار، و پذیرش انسانی شش آزمون checkpoint 30 جداگانه محفوظ‌اند.

ادامه از همین Worktree با پشته Mock جداگانه و داده مصرف‌شدنی انجام شود. از Compose overlay محلی فقط روی نام پروژه، Volume، TLS و PostgreSQL مستقل استفاده شود. اولین آزمون باز شامل Send از Chrome، مشاهده پاسخ Mock زیر همان Message، Refresh و History با شمار dispatch ثابت است. سپس Adapter عملی HTTPS، اعتبارسنجی پاسخ واقعی و مجوز مستقل مالک برای منابع و بودجه بررسی شوند.


### NB23-SESSION-RESUME-33

مبنای گزارش 7eb548e و مبنای Worktree شاخه ops/nb23-v4-staging روی af57f26 با WIP قبلی است. هدف این مرحله آماده‌سازی رابط HTTPS مطابق قرارداد NB22E-v4 و آماده‌سازی پشته آزمایشی کامل مستقل است. شواهد checkpoint 31 و 32 و آزمون‌های موفق گذشته دوباره اجرا نشدند.

`infra/nb23-v4/deepseek_https.py` رابط HTTPS آروان را با مسیر پین‌شده، TLS همراه با احراز گواهی و میزبان، یک POST، محدودیت پاسخ، Timeout، ممنوعیت Redirect و منع ارسال مجدد پیاده کرد. تأیید سمت سرور به هش payload و مالک و Attempt وابسته است. `run_approved` از دفتر پیشین برای رزرو، حفظ نتیجه نامعلوم و ذخیره خصوصی پاسخ خام استفاده می‌کند. سقف ۶۰۰ توکن تاریخی و سقف ۳۲ برای smoke از هم جدا هستند. `deepseek_offline.py` سقف مصوب را در payload، رزرو و اعتبارسنجی اعمال می‌کند. مسیر HTTPS به نسخه B یا Mock متصل نشده و پاسخ واقعی در دفتر تحت بررسی معنایی باقی می‌ماند.

`PYTHONPATH=infra/nb23-v4 python3 -B -m unittest -v infra/nb23-v4/test_deepseek_https.py` سه آزمون موفق داشت. TLS اجباری و تک‌ارسال، رد payload/مالک، عدم دنبال‌کردن پاسخ ۳۰۲، حفظ وضعیت نامعلوم و عدم ارسال مجدد بعد از timeout، رزرو ۳۲ توکن و نگهداری 0600 پاسخ خام با transport ساختگی بررسی شدند. هیچ تماس شبکه خارجی انجام نشد یا Secret به کانتینر منتقل نشد. `git diff --check` موفق بود.

آزمون مرورگر در پروژه جداگانه `docker3-cp33-mock` با `session-generation-browser.compose.yaml`، `session_generation_fixture_worker.py`، `check_generation_browser.py` و گزینه محدود fixture در `check_session_browser.py`، `session_worker_socket.py`، `session_product_api.py` و `provision_session_postgres.py` آماده شد. Docker build با شبکه خاموش روی پایه محلی و bind قرارداد از روی نسخه موجود، Next و TypeScript را با موفقیت ساخت. دو هشدار tracing از کد session قبلی ثبت شد. ایمیج مستقل `rag-finance-f3/web:docker3-cp33-mock` است. پروژه جدید فقط PostgreSQL موقت، realm مصنوعی و Worker سبک دارد. دسترسی مرورگر روی loopback:19443 است و از حساب و داده مالک استفاده نمی‌کند.

در بازبینی، سوکت Docker Desktop غایب بود و با باز کردن عادی Docker برگشت. نسخه B پیش از بازبینی در حالت Exited بود و کانتینرهای آن Start یا بازسازی نشدند. PostgreSQL نسخه B از tmpfs استفاده می‌کند و ماندگاری داده آن بعد از توقف احراز نشده است. هیچ Restore بدون بررسی جداگانه انجام نشد. خطای نخست fixture به مسیر اشتباه migration و سپس اجرای mount به‌عنوان init hook با bad interpreter برمی‌گشت. PostgreSQL موقت از entrypoint عادی راه‌اندازی و SQL پین‌شده با Bash صریح در کانتینر اجرا شد. تأیید schema و TLS/role موفق بود. API و Worker سبک Ready بودند. پنجره اولیه بررسی HTTPS قبل از آماده‌شدن Keycloak تمام شد و آزمون DOM اجرا نشد. زمان گزارش‌شده startup Keycloak ۱۴۱٫۰۶۹ ثانیه بود. اجرای بعدی مهلت ۲۴۰ ثانیه دارد.

ادامه پس از readiness با `python3 -B infra/nb23-v4/check_generation_browser.py <fixture-material>` است. گواهی مستقل روی loopback اعتبارسنجی می‌شود. آزمون یک POST و شمار دقیق سطرهای PostgreSQL، فایل خام خصوصی و receipt را قبل و بعد Refresh/History مقایسه می‌کند. پذیرش ناظر، اجرای واقعی، مجوز egress و تعرفه جاری Gateway بازند. رسمی Docker_3، Freeze و Golden تغییری نکردند. هیچ آزمون زنده، درخواست پولی یا ارسال خارجی Context انجام نشد.


### NB23-SESSION-RESUME-34

مبنای گزارش 702fcdb و مبنای اجرای ops/nb23-v4-staging روی af57f26 با WIP محفوظ است. شناسه کار P3M10 (Attempt و منع تکرار)، P3M13 (API)، P3M14-A03/A09 (رابط و خطا) و P3M15-A01/A07 (History و مالکیت) است. آزمون Authority با realm و حساب کاملاً ساختگی اجرا شد. نسخه B و Phase 2 و شاخه‌های موازی باز یا جایگزین نشدند.

آزمون `python3 -B infra/nb23-v4/check_generation_browser.py <fixture-material>` پس از HTTPS readiness روی loopback:19443 و با CA مستقل، در پروژه `docker3-cp33-mock` خروجی صفر داد. آخرین شاهد `GENERATION_MOCK_CHROME_POSTGRES_REFRESH_HISTORY_SINGLE_DISPATCH_OK` بود. پیش از آن DOM صفحه Login و فرم Keycloak در Chrome دیده شد، callback نشست واقعی را برقرار کرد و BFF با API امضاشده و PostgreSQL آزمایشی ارتباط گرفت. Worker سبک از سوکت خصوصی Context ساختگی همان Attempt را تحویل داد. مسیر Provider واقعی فراخوانی نشد.

سناریو دقیقاً یک سؤال ساختگی را از Chrome ارسال کرد. اسکریپت تطبیق متن پرسش با مقاله Message و قرارگیری پاسخ Mock در عنصر بلافاصله بعد آن را بررسی کرد. سپس سه شاهد PostgreSQL یعنی Conversation، Message و Attempt و دو شاهد دفتر Generation یعنی رسید اعتبارسنجی و فایل خام خصوصی دقیقاً یک واحد افزایش یافتند. Refresh و تغییر به گفت‌وگوی تازه و سپس انتخاب همان History، متن پاسخ و همان شناسه Attempt را بازیابی کردند. شمار POST مرورگر یک و هر پنج شمار ذخیره در پایان ثابت بود. پاسخ Mock در دفتر خصوصی SQLite و فایل خام ذخیره است. PostgreSQL متادیتای محصول، سؤال و Attempt را ذخیره می‌کند. این شاهد برای مسیر واقعی تایید کیفیت مدل، پذیرش رسمی NB23 یا ماندگاری داده مالک پس از توقف Docker استفاده نمی‌شود.

پس از پایان پنجره اولیه readiness، برای Keycloak همان پشته تا ۲۴۰ ثانیه مهلت داده شد. برای اجرای دوباره فقط PostgreSQL موقت fixture که با tmpfs و پس از توقف خالی بود دوباره از migration پین‌شده بارگذاری شد. دسترسی‌های SQL و TLS برقرار شدند. ساخت ایمیج، آزمون موفق آداپتر و آزمون‌های قدیمی تکرار نشدند. مسیرهای تغییر و آماده‌سازی در checkpoint 33 ثبت هستند و این checkpoint فقط شاهد آزمون یکپارچه و ادامه کار را اضافه می‌کند.

پیشرفت آفلاین: قبلاً ۳/۳ آزمون آداپتر موفق و Chrome یکپارچه باز بود؛ اکنون همان ۳/۳ محفوظ و سناریوی Chrome یکپارچه ۱/۱ موفق است. این پشته به موتور سنگین دوم، داده مالک، Context واقعی، کلید Gateway یا قرارداد جدید نیاز نداشت. نسخه B در بررسی پیش از آزمون متوقف بود و دست‌نخورده ماند. اجرای زنده منوط به مجوز مستقل egress و بودجه، احراز تعرفه و بررسی پاسخ واقعی است. آداپتر کنترل‌شده `run_approved` در Worktree حاضر است و در Compose/محصول فعال نشده است. آزمون زنده مرحله بعد ابتدا با payload ساختگی دارای هش و تأیید مشخص، سپس فقط با Context صریحاً مجاز انجام می‌شود. صفر درخواست خارجی یا پولی. وضعیت رسمی Docker_3، پذیرش ناظر، Golden و Freeze تغییر نکردند.


### NB23-SESSION-RESUME-35

مبنای گزارش dc5fc23 و مبنای اجرایی ops/nb23-v4-staging روی af57f26 با WIP محفوظ است. شناسه‌ها P3M10 (Attempt و منع تکرار)، P3M13 (API و Provider)، P3M14-A03/A09 (نمایش و خطا) و P3M15-A01/A07 (History و مالکیت) هستند. آزمون یکپارچه Mock گذشته تکرار نشد. آزمون انسانی تازه انجام نشد.

در `infra/nb23-v4/run_deepseek_smoke.py` ورودی ثابت و کاملاً ساختگی برای تنها smoke آماده شد. `deepseek_https.py` برای فراخوانی زنده شواهد تعرفه همان حساب را الزامی و برآورد جاری را از نرخ تاریخی تفکیک می‌کند. `deepseek_offline.py` دفتر زنده مستقل، ثبت وضعیت HTTP و زمان، سقف سه رزرو، قفل نتیجه نامعلوم، و عبور به درخواست دوم فقط پس از شاهد معتبر smoke را اضافه کرد. smoke سقف خروجی ۳۲، ورودی محافظه‌کارانه ۵۱۲ بایت payload، و برآورد کل بسته با حداکثر دو ورودی ۴۰۹۶ و خروجی ۶۰۰ دارد. متن ساختگی پاسخ در فایل خصوصی باقی می‌ماند و فقط تطابق آن گزارش می‌شود. `test_deepseek_https.py` شاهد سقف و ترتیب بسته را اضافه کرد. دستور `PYTHONPATH=infra/nb23-v4 python3 -B -m unittest -v infra/nb23-v4/test_deepseek_https.py` در مسیر تغییرکرده چهار آزمون موفق داشت، به‌همراه `git diff --check`. این آزمون‌ها transport ساختگی داشتند. تنظیمات خصوصی قبلی بدون انتقال مجدد یا نمایش، در حالت فقط‌خواندنی از نظر fingerprint و mode تأیید شدند.

جست‌وجوی عمومی تعرفه برای همان Gateway و حساب، سند معتبر جاری به دست نداد. صفحه رسمی DeepSeek قیمت و alias سرویس مستقیم خودش را شرح می‌دهد و نرخ آروان را اثبات نمی‌کند. نرخ تاریخی و برآورد ۴۸۴٫۰۲ تومان از checkpoint قبلی حفظ شده‌اند. از آن برای رزرو یا جایگزینی تعرفه جاری استفاده نشد. حتی یک POST یا تلاش پولی انجام نشد. برای ادامه smoke، نرخ یا سقف رسمی همان حساب و alias لازم است. مسیر ارسال Context منابع واقعی هم جداگانه منتظر مجوز داده است. Generation در محصول فعال نشده است.

بازبینی فقط‌خواندنی Docker نشان داد نسخه B، Worker، PostgreSQL و Keycloak پیش از شروع متوقف بودند. عیب دسترسی مستقیم سوکت با بررسی مجاز فقط‌خواندنی رفع شد. PostgreSQL و Keycloak نسخه B هر دو محل داده tmpfs دارند. فایل import Keycloak دارای دو حساب ساختگی و صفر حساب غیرساختگی است. تنها dump یافت‌شده با `pg_restore --list` و شمارش COPY بدون چاپ داده بررسی شد. نتیجه دو owner و identity link، یک Conversation، یک Message، یک Attempt و صفر Answer بود. این تعداد کوچکتر از شواهد مرحله مالک است. Volume جداگانه API فقط ۶ CONTEXT_READY، ۱ FAILED و ۴ UNKNOWN دارد و بازیابی تاریخچه یا حساب از آن تأیید نشده است. فایل dump موجود، نقطه CP30 و Volumeها تغییر نکردند. هیچ بازآماده‌سازی PostgreSQL یا ساخت حساب جایگزین بدون تصمیم مالک انجام نشد.

سرویس‌های Mock شامل Keycloak، BFF، API، Edge، Bootstrap و Worker سبک متوقف شدند. PostgreSQL سبک Mock برای حفظ شواهد tmpfs روشن ماند. نسخه A، نسخه B، فاز دوم و شاخه‌های موازی دست نخورده‌اند. ادامه از همین checkpoint با مدرک نرخ Gateway و یک مسیر بازیابی معتبر حساب و History است. اگر بازیابی کامل ممکن نیست، راه‌اندازی آزمایشی مستقل با حساب جدید مستلزم تصمیم صریح مالک است. پس از smoke موفق فقط Context دارای مجوز ارسال وارد مسیر تأیید واقعی شود. UI و قرارداد عمومی تغییر نکردند. Golden، Freeze و پذیرش ناظر همچنان جدا و بازند.
