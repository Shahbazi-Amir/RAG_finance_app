# راه‌اندازی محلی و تعاملی دموی فاز سه — مک / VS Code

این بسته **خود اپ** را در Terminal روشن نگه می‌دارد و به GitHub Actions برای اجرای دمو احتیاج ندارد. بستهٔ PDF/اسلاید نیست. کد نمایشی همیشه از SHA آزموده‌شدهٔ `fee20cc0992f4c26f76757e670cd6425400441cc` در یک Git Worktree موقت اجرا می‌شود؛ به فایل‌های کاری مخزن اصلی و `RAG_finance` دست نمی‌زند.

## پیش‌نیازها

- macOS با Docker Desktop روشن و امکان دریافت تصاویر `postgres:17.11` و `quay.io/keycloak/keycloak:26.8.2`؛ Docker باید به‌اندازهٔ کافی حافظه داشته باشد.
- Git با دسترسی خواندن به `Shahbazi-Amir/RAG_finance_app` و SHAهای #48/#50/#36 و Migrationهای 009/010.
- Python **دقیقاً 3.11.3** با `venv` برای مسیر سازگاری، یا مسیر قدیمی Python 3.13 که پوشش CI آن محفوظ است؛ **Node.js 24** و npm همچنان اجرای Next.js را بر عهده دارند. اینترنت برای دریافت وابستگی‌ها و Chromium لازم است.
- پورت‌های `127.0.0.1:5432`، `127.0.0.1:3000` و `127.0.0.1:3443` باید آزاد باشند. اگر اشغال باشند راه‌انداز **متوقف می‌شود**؛ سرویس، DB یا کانتینر دیگری را خاموش نمی‌کند. پورت Keycloak و APIها به‌شکل تصادفی فقط روی loopback انتخاب می‌شوند.
- **نکتهٔ Mac Intel:** Node.js 24 رسمی به **macOS 13.5 یا جدیدتر** نیاز دارد (https://nodejs.org/en/blog/migrations/v22-to-v24). بنابراین روی macOS **12.7.6** حتی اگر Python 3.11.3 کاملاً سالم باشد، Next.js/Chromium و Launcher کامل هنوز NOT_RUN/نامعتبرند؛ این مانع **macOS/Node** است، نه Python. برای اجرای کامل، macOS پشتیبانی‌شده یا محیط Linux مشابه آزمون را فراهم کنید؛ Node 22 را خودکار جایگزین Node 24 نکنید. Docker Desktop نیز باید برای نسخهٔ macOS مورد استفاده واقعاً پشتیبانی شود.

## آزمون Mac Intel / macOS 12.7.6 با Python دقیق 3.11.3 (Mac هنوز NOT_RUN)

فرمان‌های زیر برای اجرای **واقعی روی همان مک** هستند، نه خروجی Linux CI. ابتدا در clone تازهٔ `RAG_finance_app` شاخهٔ `compat/phase3-python-3.11` را checkout کنید. اگر `pyenv` ندارید، راه‌اندازی آن به Command Line Tools/OpenSSL سازگار نیاز دارد؛ محدودیت Homebrew/ساخت Python روی Monterey را با خطای بسته‌های Python خلط نکنید.

```bash
uname -m
sw_vers -productVersion
git fetch origin compat/phase3-python-3.11
git switch --track origin/compat/phase3-python-3.11
pyenv install -s 3.11.3
PYENV_VERSION=3.11.3 pyenv exec python -m venv .venv-3113
. .venv-3113/bin/activate
python -VV
python -c 'import sys; assert sys.version_info[:3] == (3,11,3)'
python -m pip install --no-cache-dir \
  -r apps/api/requirements-ci.txt \
  -r tests/phase3/contracts/requirements.txt \
  'PyJWT[crypto]==2.15.1' 'uvicorn==0.34.3' 'playwright==1.64.1'
python -m pip freeze
python -m compileall -q apps/api src/phase3/auth scripts/phase3-demo
python -m unittest discover -s tests/phase3/api -p 'test_*.py' -v
python -m unittest discover -s tests/phase3/contracts -p 'test_history.py' -v
node -v
docker info --format '{{.ServerVersion}}'
RAG_PHASE3_PYTHON="$PWD/.venv-3113/bin/python" bash scripts/phase3-demo/demo.sh preflight
```

اگر در Mac 12.7.6 اجرای Node 24، Docker Desktop یا Chromium شکست بخورد، آن را **MAC_PLATFORM_BLOCKED** ثبت کنید؛ حتی اگر `python -VV` و آزمون‌های API پاک باشند. **بدون نصب macOS سازگار یا محیط Linux، مرحلهٔ کامل Browser A/B، History، Logout و Reset را PASS حساب نکنید.** Log را پس از حذف Cookie، رمز و Secret ارسال کنید؛ فایل credentials/State محلی به مخزن یا چت منتقل نشود.

**شاهد مستقل Linux:** Python 3.11.3 واقعی در Ubuntu22.04؛ [Run #43522491601](https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/43522491601) / [Job #132219979981](https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/43522491601/job/132219979981) = SUCCESS برای نصب API، ۸۳ آزمون در ۷ suite غیرتکراری، Migrationهای 001–010، Node24 و Chromium A/B/History/Logout و Reset. این **شاهد Mac نیست**. نسخهٔ قرارداد و بستهٔ نهایی پس از هر commit README/.python-version باید روی SHA جدید CI شود.

## Clone تازه و یک فرمان Start

در VS Code، از **Terminal همان مک**:

```bash
git clone https://github.com/Shahbazi-Amir/RAG_finance_app.git
cd RAG_finance_app
git fetch origin compat/phase3-python-3.11
git switch --track origin/compat/phase3-python-3.11
git pull --ff-only
# Select a fresh exact 3.11.3 venv as documented above.
RAG_PHASE3_PYTHON="$PWD/.venv-3113/bin/python" bash scripts/phase3-demo/demo.sh preflight
RAG_PHASE3_PYTHON="$PWD/.venv-3113/bin/python" bash scripts/phase3-demo/demo.sh start
```

راه‌انداز هنگام Start وابستگی‌های پین‌شده را با `git fetch` دریافت و با SHA کامل بررسی می‌کند؛ یک Worktree جداگانه در `/tmp` ایجاد می‌کند، Python venv و Node modules را فقط همان‌جا نصب و Build می‌کند، یک **PostgreSQL موقت مستقل Docker** با دادهٔ کاملاً مصنوعی می‌سازد، 001 تا 010 را اجرا می‌کند، مجوزهای لازم #50 را **فقط به همین DB موقت** می‌دهد، Keycloak/HTTPS/mTLS/Next/API را روشن می‌کند و قبل از READY مسیر واقعی A/B، Logout و 401 را با Chromium در هر دو اندازه تمرین می‌کند. اگر مرحله‌ای شکست بخورد، موفقیت اعلام نمی‌شود. برنامه‌ها پس از آماده‌شدن روشن می‌مانند تا `stop` اجرا شود.

**آدرس ورود در مرورگر مک:** `https://127.0.0.1:3443/login` (گواهی HTTPS آزمایشی خودامضا است؛ فقط برای همین آدرس loopback هشدار مرورگر را بررسی و ادامه دهید). این آدرس تا زمانی که Start واقعاً موفق نشده باز نمی‌شود.

## حساب‌ها و داده‌های ساختگی

پس از READY، برای مشاهدهٔ دو Username/Password **فقط در Terminal محلی**:

```bash
bash scripts/phase3-demo/demo.sh credentials
```

رمزها هر بار تصادفی ساخته می‌شوند و داخل `/tmp/rag-phase3-local-.../synthetic-accounts.json` با مجوز `0600` ذخیره می‌شوند. آن‌ها را در Git، اسکرین‌شات یا گزارش قرار ندهید.

- **حساب نمایشی الف / A:** «گزارش نمونهٔ سپهر — حساب نمایشی الف» و «مقایسهٔ موجودی — حساب نمایشی الف».
- **حساب نمایشی ب / B:** «گزارش نمونهٔ دماوند — حساب نمایشی ب» و «روند هزینه‌ها — حساب نمایشی ب».

حساب‌ها از Keycloak واقعی و دو `(issuer, sub)` متفاوت ساخته می‌شوند، نه از Owner انتخاب‌شده در مرورگر. History فقط `GET /v1/conversations` را از PostgreSQL ایزوله نشان می‌دهد. رابط گفت‌وگوی زنده، موتور پاسخ‌دهی، امکانات فاز چهار و ارسال پیام خارج از این دمو هستند.

## نمایش برای کارفرما

۱. در یک پنجرهٔ Chrome، `/login` را باز کنید؛ با **A** از صفحهٔ واقعی Keycloak وارد شوید و دو عنوان سپهر و موجودی را ببینید.

۲. برای **B** پنجره/پروفایل کاملاً جدا باز کنید (مثلاً Chrome معمولی برای A و Safari برای B). با B وارد شوید و فقط عناوین دماوند و روند هزینه‌ها را نشان دهید.

۳. در مرورگر A از `/login`، دکمهٔ «خروج امن از حساب» را بزنید. پیام موفقیت **فقط پس از** `REVOKED_COMMITTED` واقعی از API #50 نمایش داده می‌شود. صفحهٔ History بازماندهٔ A با Refresh به خطای دسترسی واقعی Next می‌رسد و دادهٔ خصوصی را پاک می‌کند؛ API نیز نشست Product قبلی را با 401 واقعی رد می‌کند. در پنجرهٔ B، تاریخچه همچنان 200 و متعلق به B است.

۴. «سه دقیقه»: ۰۰:۰۰ ورود فارسی؛ ۰۰:۳۰ ورود A؛ ۰۱:۰۰ History A؛ ۰۱:۳۰ ورود/History B؛ ۰۲:۰۰ Logout A؛ ۰۲:۳۰ رد نشست A و ادامهٔ B.

## وضعیت، توقف و بازنشانی امن

```bash
bash scripts/phase3-demo/demo.sh status
bash scripts/phase3-demo/demo.sh stop
bash scripts/phase3-demo/demo.sh reset
```

- `stop` فقط پردازه‌های همین دمو، کانتینر PostgreSQL با ID/Label ثبت‌شده و کانتینر/شبکهٔ Keycloak تولیدشدهٔ همین اجرا را متوقف می‌کند. PostgreSQL موقت حافظه‌ای است و با توقف پاک می‌شود؛ هیچ DB یا کانتینر دیگری حذف نمی‌شود.
- `reset` به‌صورت Stop و Start انجام می‌شود، با حساب‌های تازه و داده‌های نو. از آن برای آماده‌سازی مجدد ارائه استفاده کنید.
- فایل‌های Log و عکس‌های آزمون فقط در پوشهٔ محلی موقت همین دمو هستند و با Stop پاک می‌شوند.
- اگر خطایی رخ داد، به `service.log` در پوشهٔ `/tmp/rag-phase3-local-...` نگاه کنید. در صورت تضاد پورت، سرویس خودتان را جداگانه بررسی کنید؛ راه‌انداز عمداً چیزی را Reset/Kill نمی‌کند.

## مرزهای امنیتی و نسخه‌های مرجع

نسخهٔ UI: `fee20cc0992f4c26f76757e670cd6425400441cc`؛ API #50: `62d40f4b4ed254de0aa0dfc21c17d809e24423db`؛ Bootstrap #48: `1998b31c86155a972b11ea745d6bb37e09549392`؛ Transaction #36: `99a917c2f2c519027d0e71643bbbf6973a6c8ac3`؛ Migration 009: `656604356dadea953031fcdb74650a5d42df4e9b`؛ 010: `1678e87b7984094b74ec995383b8d4383e5f5ae7`.

دوتغییر کوچک سازگاری صرفاً در **Worktree موقت** اجرا می‌شوند: جایگزینی قفل `GITHUB_ACTIONS` با `RAG_PHASE3_DEMO_LOCAL` برای Demo Harness و API درحالی‌که نقش/پایگاه جدا بررسی شده، و استفاده از Docker image موجود با pull-on-missing برای Keycloak. هیچ SHA پین‌شده‌ای در خود مخزن تغییر داده نمی‌شود. این یک محیط آزمون محلی، نه Production یا مجوز دائمی DB، است.

**نکتهٔ صداقت آزمون:** CI قبلی مسیر کامل را با واقعیات DB/Keycloak در Runner تأیید کرده است. این Launcher جدید فقط وقتی در مک ارائه نیز اجرا و تست کامل روی همان مک تمام شود، محلی READY می‌دهد؛ تا آن زمان آماده بودن روی آن مک ادعا نمی‌شود.
