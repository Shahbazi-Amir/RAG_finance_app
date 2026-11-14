# راه‌اندازی محلی و تعاملی دموی فاز سه — مک / VS Code

این بسته **خود اپ** را در Terminal روشن نگه می‌دارد و به GitHub Actions برای اجرای دمو احتیاج ندارد. بستهٔ PDF/اسلاید نیست. کد نمایشی همیشه از SHA آزموده‌شدهٔ `fee20cc0992f4c26f76757e670cd6425400441cc` در یک Git Worktree موقت اجرا می‌شود؛ به فایل‌های کاری مخزن اصلی و `RAG_finance` دست نمی‌زند.

## پیش‌نیازها

- macOS با Docker Desktop روشن و امکان دریافت تصاویر `postgres:17.11` و `quay.io/keycloak/keycloak:26.8.2`؛ Docker باید به‌اندازهٔ کافی حافظه داشته باشد.
- Git با دسترسی خواندن به `Shahbazi-Amir/RAG_finance_app` و SHAهای #48/#50/#36 و Migrationهای 009/010.
- Python **3.11.3** نصب‌شده روی مک کافی است؛ Node.js سازگار (نسخهٔ 22.16.0 برای macOS 12 Intel/ARM)، npm، کتابخانه‌های Python و Chromium در صورت نیاز با همین راه‌انداز دانلود و فقط در فضای ایزوله نصب می‌شوند. اینترنت برای بار نخست لازم است.
- پورت‌های `127.0.0.1:5432`، `127.0.0.1:3000` و `127.0.0.1:3443` باید آزاد باشند. اگر اشغال باشند راه‌انداز **متوقف می‌شود**؛ سرویس، DB یا کانتینر دیگری را خاموش نمی‌کند. پورت Keycloak و APIها به‌شکل تصادفی فقط روی loopback انتخاب می‌شوند.
- روی **macOS 12.7.6** حتی اگر `node -v` نسخهٔ 24 را نشان دهد، راه‌انداز آن را انتخاب نمی‌کند (باینری رسمی Node 24 حداقل macOS 13.5 می‌خواهد) و از Node 22.16.0 ایزوله استفاده می‌کند. فقط PATH پردازهٔ دمو تغییر می‌کند؛ نصب Node موجود پاک/عوض نمی‌شود.
- نیازی به نصب دستی Python 3.13، Node 24 یا Homebrew نیست. راه‌انداز اگر Node مناسب پیدا نکند، باینری رسمی Node 22.16.0 با SHA-256 ثابت را در `~/.cache/rag-phase3-demo-node/` ذخیره می‌کند و به PATH فقط همین فرآیند می‌افزاید. Node 22.16.0 طبق مرجع رسمی برای macOS 11 به بالا ساخته شده است؛ Node 24 روی macOS 12 گزینهٔ مناسبی نیست. Docker Desktop باید جداگانه از قبل نصب و روشن باشد؛ منابع پروژه‌های دیگر دست‌نخورده می‌مانند.

## وضعیت مانع PyPI در مک Intel (۱۴ نوامبر ۲۰۲۶)

**محدودیت تأییدشده:** از نسخهٔ 49 به بعد، cryptography فایل wheel رسمی برای macOS Intel / x86_64 منتشر نمی‌کند. نسخهٔ اصلاح‌شدهٔ امنیتی 50.0.2 با Python 3.11 سازگار است، اما wheel مخصوص Intel ندارد؛ بنابراین ارتقای pip به‌تنهایی مشکل را حل نمی‌کند. maturin نسخهٔ 1.14.1 در PyPI wheel رسمی x86_64 دارد؛ علت دقیق شکست آن در Terminal مالک بدون لاگ کامل pip مشخص نیست.

نسخهٔ 48.0.1 wheel رسمی universal2 دارد، اما به‌ترتیب با GHSA-g6cj-pr64-35w5، GHSA-m2h6-j472-rp4c و GHSA-jwv3-5hgf-82ww آسیب‌پذیر شناخته شده است؛ downgrade خودکار به آن ممنوع است. اکنون روی Mac Intel راه‌انداز pip را فقط داخل venv موقت ارتقا می‌دهد و نصب فقط-باینری cryptography==50.0.2 را امتحان می‌کند. با نبود wheel مناسب خطای MAC_INTEL_OFFICIAL_SECURE_CRYPTO_WHEEL_UNAVAILABLE می‌دهد و READY جعلی اعلام نمی‌کند.

**جایگزین فقط با انتخاب آگاهانهٔ مالک:** اگر Rust toolchain و Xcode Command Line Tools از قبل روی همان Mac حاضر باشند، می‌توان فقط برای venv موقت ساخت از سورس رسمی نسخهٔ امن را با فرمان زیر صریحاً مجاز کرد. این روش پیش‌فرض نیست، به دریافت/کامپایل Rust و ابزارهای سیستم نیاز دارد و هنوز روی macOS 12.7.6 مالک آزمایش نشده؛ ممکن است باز هم روی maturin متوقف شود.

~~~bash
RAG_PHASE3_DEMO_ALLOW_CRYPTO_SOURCE=1 bash scripts/phase3-demo/demo.sh start
~~~

تا عبور واقعی از نصب امن و سپس Chromium، وضعیت دستگاه مالک BLOCKED / NOT_READY است؛ خروجی قبلی Ubuntu/CI به‌جای آزمون مک محسوب نمی‌شود.

منابع: https://cryptography.io/en/stable/changelog/ ؛ https://pypi.org/project/cryptography/50.0.2/ ؛ https://pypi.org/project/cryptography/48.0.1/ ؛ https://pypi.org/project/maturin/1.14.1/ ؛ https://github.com/advisories/GHSA-g6cj-pr64-35w5 ؛ https://github.com/advisories/GHSA-m2h6-j472-rp4c ؛ https://github.com/advisories/GHSA-jwv3-5hgf-82ww .

## Clone تازه و یک فرمان Start

در VS Code، از **Terminal همان مک**:

```bash
git clone https://github.com/Shahbazi-Amir/RAG_finance_app.git
cd RAG_finance_app
git fetch origin agent/ui-auth-bff-010-integration
git switch --track origin/agent/ui-auth-bff-010-integration
git pull --ff-only
bash scripts/phase3-demo/demo.sh preflight
bash scripts/phase3-demo/demo.sh start
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

## ادامه از Worktree موجود شما (بدون ساخت دوباره)

همین حالا که در `RAG_finance_app_demo` هستید، این دستور را از Terminal داخل VS Code اجرا کنید:

```bash
git status --short
git fetch origin agent/ui-auth-bff-010-integration
git switch --detach origin/agent/ui-auth-bff-010-integration
bash scripts/phase3-demo/demo.sh preflight
bash scripts/phase3-demo/demo.sh start
```

این دستور کد راه‌انداز تازه را دریافت می‌کند، بدون حذف Python 3.11 یا دست‌زدن به Docker پروژه‌های دیگر. `preflight` ممکن است Node سازگار را خودکار دانلود کند. `start` بقیهٔ وابستگی‌ها و تصاویر Docker را خودش می‌گیرد، محیط جدا می‌سازد، هر دو حساب و دادهٔ نمونه را آماده می‌کند و آزمون مرورگری را اجرا می‌کند. فقط پس از مشاهدهٔ `READY`، آدرس `https://127.0.0.1:3443/login` قابل استفاده است. مشخصات A/B: `bash scripts/phase3-demo/demo.sh credentials`، توقف و Reset: `stop` و `reset`. اگر `git switch` به علت تغییرات محلی متوقف شد، آن تغییرات را حذف نکنید و علت را بررسی کنید.

**محدودهٔ اثبات:** اجرای Ubuntu با Python 3.11 و Node 22 را جداگانه در GitHub Actions می‌آزماییم. امکان تأیید macOS 12 واقعی بدون اجرای دستور روی دستگاه شما وجود ندارد.
