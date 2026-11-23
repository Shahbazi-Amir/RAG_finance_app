# راه‌اندازی محلی فاز سوم روی مک

## خط مبنا و بازیابی

نسخهٔ کاری detached و تمیز بود. HEAD برابر `67ffa71f4dc43b29e8df7b74bd40f7bd16875cde` و مبنای گزارش‌ها روی شاخهٔ codex برابر `552ab762736dfb9df3d6c428e056cec0b282d9d6` بود. فایل محصول، فاز دوم و Volumeهای اصلی تعویض نشدند.

در مسیر محلی `AMIR_DATA/_SAFE_BACKUPS/RAG_finance_phase3`، اجرای `shasum -a 256 -c SHA256SUMS` در مجموعهٔ پایه (۱۵ مورد) و مکمل Docker (۴۰ مورد) موفق بود. Manifestها و RESTORE_REPORT سابق بررسی شدند. گزارش پایه استخراج تنظیمات خصوصی، PKI و کپی C018 و سلامت SQLite را ثبت کرده است. گزارش مکمل بازیابی فیزیکی روی Volume تازه و بازیابی منطقی هشت dump را ثبت کرده است. اجرای دوبارهٔ Restore، بازپخش Globals، بارگذاری ایمیج در daemon جداگانه و بازیابی عملیاتی C018 تأیید نشده‌اند. بکاپ و بازیابی جزئی‌اند. برای بازگرداندن مرحلهٔ حاضر به وضعیت اولیه فقط کانتینر PostgreSQL محصول با `docker stop rag-f3-db-rotate-local-demo-db-1` متوقف می‌شود. برای Restore از روش مقصد ایزوله در گزارش مکمل استفاده شود.

## Docker و آزمون اجرا

خروجی `docker info` دو CPU، ۴۱۰۴۸۸۰۱۲۸ بایت حافظه و معماری x86_64 را نشان داد. دیسک میزبان ۱۲۰ GiB فضای آزاد داشت. Healthcheck قبلی پایگاه محصول timeout داشته است. هیچ‌یک از چهار کانتینر پروژه OOM گزارش نکرد. رابطهٔ منابع با خطای API اثبات نشد. دسترسی Docker در sandbox رد شد و اجرای با مجوز بیرون از sandbox موفق بود.

| سرویس | وضعیت مشاهده‌شده | شناسهٔ کانتینر | شناسهٔ ایمیج |
| --- | --- | --- | --- |
| demo-db | Running / Healthy. آزمون `docker exec … pg_isready` اتصال محلی را تأیید کرد | ceb8cfcc9b1a | ff87138949ad |
| product-api | Exited 78 پس از شروع مجدد با پایگاه آماده | cae606674972 | 2de6c25d8bd1 |
| idp-db | Exited 0 از اجرای قبلی | f1ce62cc6476 | ff87138949ad |
| idp-keycloak | Created | 5b4c6b0af692 | 7e66a96e4739 |
| auth-bootstrap | کانتینر مشاهده نشد | — | ایمیج موجود 2cc8118c40a3 |
| web-bff | کانتینر مشاهده نشد | — | ایمیج موجود ead7afb7f9ec |
| web-https | کانتینر مشاهده نشد | — | ایمیج موجود caf4e1e032a2 |

پروژهٔ فعال `rag-f3-db-rotate-local` است. فهرست فایل‌های Compose از برچسب کانتینر استخراج شد و شامل Compose محصول، https اختیاری، جداسازی PKI، سه override پایگاه، routing، IdP REV3 و overrideهای private-sibling و home-ledger است. شبکه‌های product_private و idp_storage موجودند. Volume اصلی پایگاه محصول، Volume پایگاه IdP و Volume تنظیمات API روی کانتینرهای قبلی حفظ شدند.

`docker logs --tail 8 rag-f3-db-rotate-local-product-api-1` در اجرای اصلی دو بار PRIVATE_STAGING_STARTUP_DENIED ثبت کرد. لاگ عمومی مرحلهٔ داخلی یا علت را مشخص نمی‌کند. کانتینر تشخیصی موقت با ایمیج و UID سرویس، شبکهٔ همان پروژه و mountهای فقط‌خواندنی، پیش از preflight هنگام خواندن فایل ماژول Python با PermissionError متوقف شد. این خطای probe از خروج کنترل‌شدهٔ API اصلی متمایز است. علت اصلی API هنوز تعیین نشده و اصلاح نسخه‌دار تحویل نشده است.

مسیر موجود خصوصی به NO_DISPATCH_ONLY مقید است. برای پذیرش بازیابی واقعی، پروفایل retrieval مجاز باید با حفاظت‌های TLS، BFF امضاشده و هویت پایگاه ادغام و آزموده شود. مرورگر، OIDC، Signed BFF، C018، منابع، شمارنده‌های Generation/Gateway و رفتار Refresh آزمایش نشده‌اند. فریز و پذیرش سرپرست ثبت نشده‌اند. آروان HOLD است.

مقایسهٔ docker diff، docker cp و stat نشان داد که ایمیج linux/amd64 فایل entrypoint را با مالک root و mode 0600 دارد، در حالی که کانتینر اصلی همان فایل را با مالک 11001 و mode 0440 در لایهٔ نوشتنی دارد. docker diff تغییر مسیرهای دیگر کد را نیز نشان می‌دهد. آرشیو ایمیج این لایه را پوشش نمی‌دهد. بازسازی یا جایگزینی API تا تعیین منشأ نسخهٔ لایهٔ عملیاتی و ثبت نقطهٔ بازگشت متوقف است.

## ادامهٔ Checkpoint و علت خطای API

مبنای گزارش 84d58b1 و HEAD عملیاتی جدا 5fe21e9 بود. دستور docker compose --profile "*" config --services هر هفت سرویس را تأیید کرد. demo-db همچنان healthy بود. API اصلی در وضعیت Exited 78 حفظ شد.

Manifest مکمل ۵ Volume و ۴ مجموعهٔ پایگاه را ثبت کرده و لایهٔ نوشتنی را خارج از پوشش اعلام کرده بود. فراداده و docker diff رمزگذاری شدند. docker commit از کانتینر متوقف‌شده snapshot محلی 6c6a05dcd26a ساخت. خروجی docker save به صورت جریان رمزگذاری‌شده در پوشهٔ امن mac-first-start-api-84d58b1 ذخیره می‌شود. این snapshot و فرادادهٔ خصوصی فقط محلی هستند. تأیید بستهٔ کامل و بازیابی از آرشیو هنوز در جریان است.

آزمون جدا از snapshot با UID 11001 و mountهای فقط‌خواندنی CONFIG_PASS را ثبت کرد. پس از بررسی‌های preflight، import در repository.py:16 برای خواندن packages/contracts/product.v1.schema.json با PermissionError متوقف شد. اصلاح در شاخهٔ محلی ops/mac-first-start با commit 4752c2b ثبت شد. Dockerfile.api دسترسی گروه سرویس را فقط روی درخت‌های کد و قرارداد تنظیم می‌کند. compose.api.yaml مسیر بررسی سلامت را با /run/api-private/api.json همسان می‌کند. کلیدها، اعتبارنامه‌ها و کنترل‌های Startup دست‌نخورده‌اند.

ساخت آفلاین Docker با linux/amd64، --pull=false و --network=none موفق شد. import ماژول API و schema به‌عنوان UID سرویس در مرحلهٔ build اجرا شد. manifest ایمیج اصلاحی 2754f21404d9e88c2b2dd2f8b8850cde049a3d3648e04291d9f5368cf13d5ac6 است. هنوز سرویس اصلی تعویض نشده است. راهنمای فعلی شاخهٔ Gate 3 اجرای retrieval ایزوله با NO_DISPATCH_ONLY را پیش‌بینی کرده است و Generation و Gateway مسیر جدا دارند.

## بازیابی لایهٔ API و شروع نسخهٔ اصلاحی

در بستهٔ محلی mac-first-start-api-84d58b1، آزمون SHA256SUMS برای هر هفت مورد موفق شد. آرشیو پس از احراز HMAC، رمزگشایی و gzip -dc با docker load روی همان daemon بارگذاری شد. شناسهٔ کامل 6c6a05dcd26af99bc406b4e2f9d64fca29f635d894d8daabbada429b8b2dce10 تطبیق داشت. docker run با network none، کاربر 11001، root filesystem فقط‌خواندنی و بدون Volume، ISOLATED_ENTRYPOINT_IMPORT_PASS ثبت کرد. Restore کل پشته همچنان PARTIAL است. دستور دقیق بازیابی در RESTORE_REPORT.md کنار آرشیو آمده است.

پیش از جایگزینی، API اصلاحی با همان تنظیمات و mountهای فقط‌خواندنی و ledger موقت جدا از CONFIG_PASS، PREPARE_PASS و PROTOCOL_PASS گذشت. سپس docker compose up -d --no-deps --no-build --pull never product-api در همان پروژه اجرا شد. کانتینر جدید d98dfeaca7c41 با ایمیج 2754f21404d9e healthy شد. لاگ Uvicorn مبدأ https://127.0.0.1:8443 و healthcheck با خروج ۰ و PRIVATE_STAGING_PREFLIGHT_PASS ثبت کردند. Volumeهای اصلی حفظ شدند.

مسیر بازگشت، اعمال Compose اولیه با API_IMAGE_NAME=rag-finance-f3/api-local-recovery:84d58b1 و up -d --no-deps --no-build --pull never product-api است. در بازگشت، خطای قبلی API نیز بازمی‌گردد. دانستن شناسهٔ snapshot جایگزین بررسی کنترل‌های امنیتی نسخهٔ اجراشده نیست.

ایمیج اولیهٔ Bootstrap نیز فایل entrypoint با مالک root و mode 0600 داشت. ساخت آفلاین نسخهٔ اصلاحی در commit محلی f1a83c4، import با UID 11002 را تأیید کرد. فایل Dockerfile.bootstrap و override محلی در شاخهٔ ops/mac-first-start قرار دارند. شناسهٔ ایمیج جدید 8e5d6a79f945ec928d04d94408dbd0ca7e436dc48fbe70174da1af0a8a03de3f است. آزمون runtime سرویس‌های وابسته در جریان است.

## هفت سرویس شروع شدند و HTTPS محلی پاسخ داد

پایگاه‌های demo-db و idp-db و سرویس web-bff هم‌زمان healthy ثبت شدند. API و auth-bootstrap شنوندهٔ mTLS فعال دارند و BFF با گواهی واقعی هر دو endpoint را در probe داخلی بررسی کرد. این probe امضای درخواست یا نشست کاربر را آزمایش نمی‌کند. وضعیت health هر دو سرویس هنگام بار هم‌زمان unhealthy شد. برای نمونه، healthcheck API از سقف ۴۰ ثانیه عبور کرد، آزمون metadata محیط C018 با مهلت ۶۰ ثانیه موفق شد و ۲۷٫۴۹ ثانیه طول کشید، و preflight مستقل Bootstrap در ۹۳٫۲۲ ثانیه PRIVATE_BOOTSTRAP_PREFLIGHT_PASS داد. هیچ Runner در این بررسی‌ها اجرا نشد.

پس از خطای conflicting options در Compose، extra_hosts تکراری Bootstrap حذف شد (84e474d). getent hosts idp-staging.ragfinance.ir در Bootstrap همچنان 127.0.0.1 برگرداند و مسیر TLS حفظ شد. پس از mount placeholder و خطای chown nginx، گواهی موجود با CA و با کلید خصوصی متناظر تطبیق داده شد. تنظیمات تأییدشده بدون تغییر بایت در Volume محلی mac_ingress_private_v1 با مالک 101:101 و فایل‌های mode 0400 قرار گرفت. منبع bind فقط‌خواندنی بود. nginx بدون root و با همان محدودیت قابلیت‌ها اجرا شد (7ce11c9). nginx -t در کانتینر جدا موفق بود. دستور curl با --cacert و --resolve روی 127.0.0.1 نتیجهٔ HTTP 200 و TLS_VERIFY=0 داد.

Keycloak در ۷۶۱۷۹۷ میلی‌ثانیه Quarkus augmentation را کامل کرد ولی هنوز listener بررسی‌شده در دسترس نبود. درخواست HTTPS به discovery واقعی 502 گرفت. آزمون مرورگر Chrome در تلاش اول ۱۰۰ ثانیه و در تلاش دوم CDP پس از ۳۰ ثانیه timeout شد. گزارش HTTP 200 شاهد مرورگر، ورود OIDC، Attempt، Signed BFF، منابع یا Refresh نیست.

شاخهٔ اجرایی 136bd8f مهلت‌های healthcheck را متناسب با اندازه‌گیری بالا اصلاح کرد. build آفلاین و import غیرریشهٔ ایمیج 438ba61c69ea0518ab43f932c70b5e79caa5fdfc7adbbfe954f0aaead5f2b0cb موفق شد. این اصلاح همهٔ بررسی‌های فایل، SHA موتور، نسخهٔ metadata، TLS، شبکه و نقش‌های مجاز را نگه می‌دارد. نتیجهٔ build از پذیرش runtime جداست.

## پایداری API و مانع واقعی IdP

پس از اصلاح مهلت‌ها، Product API و Bootstrap و سپس BFF با healthcheck واقعی healthy شدند. پروژهٔ موجود هر هفت کانتینر را در حالت Running داشت. پنج healthcheck Docker و پاسخ HTTP 200 HTTPS با TLS_VERIFY=0 تأیید شدند. راه‌اندازی Keycloak روی 8080 و اتصال TCP از کانتینر API موفق بود، اما discovery از ingress به 503 رسید و Keycloak صراحتاً پیام bootstrap و health DOWN ثبت کرد.

شناسه‌های checkpoint نهایی این نوبت: demo-db ceb8cfcc9b1a و idp-db f1ce62cc6476 با ایمیج ff87138949ad، product-api 61ff7a7ce511 با ایمیج 438ba61c69ea، auth-bootstrap 52d6a9967656 با ایمیج 8e5d6a79f945، web-bff aaa462b24e36 با ایمیج ead7afb7f9ec، web-https f5ca6e14ad66 با ایمیج caf4e1e032a2 و IdP اصلی 5b4c6b0af692 با ایمیج 7e66a96e4739. هیچ‌کدام OOM گزارش نکردند.

خروجی پالایش‌شدهٔ jcmd 1 Thread.print -l، bootstrap پایگاه را در مسیر LiquibaseRemoteAnalyticsConfiguration و ساخت سوکت HTTPS نشان داد. نشست تراکنش PostgreSQL در ClientRead منتظر بود و blocking PID نداشت. تنظیم آفلاین LIQUIBASE_ANALYTICS_ENABLED=false در SHA محلی 6a3d426 ثبت و در مدل Compose اعتبارسنجی شد. این تنظیم مربوط به telemetry است و سیاست TLS، OIDC یا نقش پایگاه را تغییر نمی‌دهد.

قبل از جایگزینی Keycloak، pg_dump سفارشی تازهٔ IdP در mac-first-start-idp-preanalytics احراز و رمزگذاری شد. pg_restore --list تعداد ۵۴۷ خط داشت و هر دو SHA-256 تطبیق داشتند. نسخه در PostgreSQL با Volume جدید، network none و pg_restore --exit-on-error --no-owner --no-privileges بازیابی شد و ۱۰۱ جدول عمومی را نشان داد. کانتینر آزمون متوقف شد. globals و مالکیت اولیه در آزمون تازه بازپخش نشدند.

دو مرورگر به‌صورت جداگانه و با نام دامنه و اعتبارسنجی گواهی عادی آزمایش شدند. Chrome در Page.navigate و Firefox در گرفتن تصویر پس از ۱۸۰ ثانیه timeout شدند. HTTP 200 سلامت ingress را نشان می‌دهد؛ مشاهدهٔ واقعی UI تأیید نشده است. شمارش تجمعی در snapshot زندهٔ پایگاه، حساب فعال staging یا master نشان نداد. نشست OIDC، درخواست امضاشده، C018، نمایش منابع و Refresh اجرا نشده‌اند. منبع نسخهٔ API فعال 5fe21e9 است. مسیر نسخه‌دار منابع در شاخهٔ مستقل c2edbbf وجود دارد و در پشتهٔ مک اعتبارسنجی نشده است.

[راهنمای رسمی تنظیم Analytics](https://docs.liquibase.com/secure/reference-guide-5-2/parameters/analytics-enabled)

## اجرای نسخهٔ آفلاین Keycloak و وضعیت ادامه

پس از بازیابی منطقی IdP در محیط جدا، Docker از لایهٔ بهینه‌شدهٔ Keycloak تصویر محلی 338942f0b25e ساخت. یک اجرای network none وجود فایل generated-bytecode.jar را تأیید کرد. Compose در شاخهٔ محلی ops/mac-first-start به SHA 2a5948f رسید. فقط Keycloak با توقف کنترل‌شده و up -d --no-deps --no-build --pull never اجرا شد. کانتینر جدید 39a6d2d1828a با همان mountهای خصوصی و پایگاه اصلی Running شد. نسخهٔ قدیمی و تصویر بازیابی موجودند. بایگانی رمزگذاری‌شدهٔ لایهٔ Keycloak هنگام این مشاهده در جریان بود.

پس از آغاز Keycloak آفلاین، HTTPS دوباره HTTP 200 و TLS_VERIFY=0 داد و discovery در دورهٔ شروع HTTP 502 داد. در مشاهدهٔ بعدی هفت کانتینر Running بودند. سه healthcheck Docker شامل demo-db، idp-db و web-bff موفق بودند. با احتساب پاسخ HTTPS، چهار سرویس شاهد سلامت عملیاتی داشتند. بررسی دوره‌ای API و Bootstrap پس از چند نتیجهٔ موفق، دوباره با خروج ۷۸ یا timeout افت کرد. API همچنان روی HTTPS داخلی گوش می‌دهد. پایداری در ظرفیت فعلی تأیید نشده است.

Docker Desktop در دو بررسی ۲ CPU و حدود ۳٫۸۲ GiB حافظهٔ قابل استفاده گزارش کرد. اختلاف زمان اجرای بررسی‌ها تا چند دقیقه، زمان build اولیهٔ Keycloak، و timeout هر دو مرورگر ثبت شدند. علت هر ۷۸ جدید جدا از نقص مجوز فایل قبلی بررسی می‌شود. قدم بعدی افزایش منابع Docker Desktop به ۳ CPU و ۶ GB RAM برای تکرار readiness است. رابط CLI این نصب فرمان تغییر Resources ندارد. آروان HOLD است. Gate، فریز قبولی و تأیید سرپرست ثبت نشدند.

بازآزمایی مستقیم و فقط‌خواندنی API در همان کانتینر، StagingConfigDenied را در verify_staging_database_authority و شاخهٔ except psycopg.Error در خط ۲۱۲ ثبت کرد. بنابراین خطای دوره‌ای جدید از مسیر ارتباط با PostgreSQL است. از خروجی پالایش‌شدهٔ این آزمون نمی‌توان Timeout اتصال را از دیگر خطاهای psycopg جدا کرد. از تغییر نقش‌ها، pg_hba، مهلت اتصال یا TLS بدون شاهد خودداری شد.

در آخرین بازآزمایی پس از هشت دقیقه اجرای Keycloak بهینه‌شده، HTTPS همچنان HTTP 200 و TLS_VERIFY=0 و discovery HTTP 502 داد. هر هفت کانتینر Running بودند. پنج سرویس دارای healthcheck Docker، از جمله هر دو PostgreSQL، هم‌زمان unhealthy شدند. فقط ingress شاهد سلامت عملیاتی فعلی داشت. بایگانی رمزگذاری‌شدهٔ تصویر Keycloak در حال پیشرفت بود. تنظیم منابع پس از پایان بایگانی تغییر کند.

## ادامهٔ راه‌اندازی پس از افزایش منابع Docker

مبنای گزارش شاخهٔ codex در 50d26aa و مبنای اجرای محلی شاخهٔ ops/mac-first-start در 2a5948f بود. نسخهٔ کاری اصلی در 67ffa71 به‌صورت detached و تمیز مشاهده شد. اعتبار بایگانی Keycloak و SHA-256 از checkpoint تأییدشده به ارث رسید.

فرمان docker info --format با فیلدهای NCPU و MemTotal مقدار ۴ CPU و ۶٬۲۱۲٬۰۳۰٬۴۶۴ بایت حافظه (۵٫۷۹ GiB) را نشان داد. تعداد CPU یک واحد بالاتر از هدف ۳ CPU بود و تنظیمات تغییر نکرد. پس از راه‌اندازی Docker هیچ‌یک از هفت سرویس فعال نبودند. ابتدا دو PostgreSQL و سپس پنج کانتینر وابسته با docker start و نام‌های موجود راه‌اندازی شدند. ایمیج‌ها و اتصال Volumeهای اصلی حفظ شدند.

آزمون پایداری با docker ps و docker inspect روی State.Health.Log در چند نمونه تا دقیقهٔ پنجم انجام شد. demo-db و idp-db هرکدام پنج خروج موفق اخیر داشتند. Product API و Auth Bootstrap پس از یک خطای آغازین، هرکدام سه خروج موفق متوالی داشتند. Web BFF چهار خروج موفق متوالی داشت. شمارندهٔ restart این پنج سرویس صفر بود. Web HTTPS در درخواست loopback با CA محلی HTTP 200 و TLS_VERIFY=0 داد. Keycloak پس از حدود ۸۷ ثانیه روی JVM شروع شد و GET /health/ready روی پورت مدیریتی ۹۰۰۰ HTTP 200 داد. هر هفت سرویس در نمونهٔ نهایی فعال بودند. خرابی هم‌زمان checkpoint قبلی در این پنجره تکرار نشد.

آزمون OIDC با اتصال به 127.0.0.1، SNI میزبان staging و اعتبارسنجی CA محلی انجام شد. discovery در شروع ۵۰۲ و سپس ۵۰۳ داد. بعد از readiness، discovery و JWKS با HTTP 200 پاسخ دادند، issuer و مبدأ سه endpoint با realm پیکربندی‌شده تطبیق کردند و JWKS کلید داشت. GET /login موفق بود. POST /api/auth/login بدون Sec-Fetch-Site با 403 رد شد. با cookie فرم، CSRF، Origin و Sec-Fetch-Site: same-origin همان مسیر واقعی HTTP 303 به Keycloak داد. درخواست اولیهٔ مقصد در ۱۵ ثانیه timeout شد و تکرار با مهلت ۵۵ ثانیه فرم ورود واقعی Keycloak را با HTTP 200 و فیلد گذرواژه دریافت کرد. هیچ اعتبارنامه یا توکنی ثبت نشد.

Chrome در پروفایل موقت ابتدا ERR_CERT_AUTHORITY_INVALID داد. آزمون دوم پس از اعتبارسنجی جداگانهٔ گواهی و استفاده از پین SPKI همان میزبان‌ها در پروفایل موقت، در Page.navigate پس از ۱۵۰ ثانیه timeout شد. شواهد HTTP فرم ورود از آزمونی مستقل به دست آمد. نمایش گفت‌وگو در مرورگر و callback احراز هویت مشاهده نشدند.

در PostgreSQL IdP کوئری تجمیعی SELECT count(*) FILTER برای user_entity.enabled با JOIN realm و تفکیک master از بقیه ۱ و ۰ را نشان داد. مانع ادامه، نبود حساب دعوت‌شدهٔ فعال در realm staging و دسترسی مصوب متناظر برنامه است. ورود با حساب master جایگزین این مسیر نیست. Product API در حالت NO_DISPATCH_ONLY بود. نشست دعوت‌شده، درخواست امضاشدهٔ محصول، اجرای C018، بازگشت نتیجه به UI و Refresh اجرا نشدند. آروان HOLD و پذیرش سرپرست در انتظار است.

## قرارداد دعوت Staging و آزمون واقعی مرورگر

ادامه از گزارش محلی codex در 5d9e8cf و نسخهٔ اجرایی ops/mac-first-start در 2a5948f انجام شد. HEAD شاخهٔ codex روی origin پیش از ارسال 50d26aa بود. شواهد سلامت هفت سرویس و منابع Docker (۴ CPU و ۵٫۷۹ GiB) از checkpoint قبلی استفاده شد.

قرارداد docs/operations/phase3_private_staging_integration_v0.md ورود کاربران واقعاً دعوت‌شده با Keycloak، HTTPS و Authorization Code + PKCE را لازم می‌داند. در src/phase3/auth/bootstrap_oidc.py توکن باید issuer، nonce و subject معتبر و email_verified=true داشته باشد. تابع auth_l1.map_identity در migration 003 بعد از تأیید هویت، نگاشت (issuer, subject) را می‌سازد یا بازیابی می‌کند. سپس Bootstrap نشست موقت را صادر می‌کند و نشست باید مراحل binding و acknowledgement را طی کند. این نگاشت مسیر ساخت کاربر در Keycloak نیست. راهنمای infra/auth-ci/README.md، ثبت‌نام و تأیید از طریق Mailpit را برای CI ایزوله تعریف کرده است.

در کانتینر idp-db با docker exec و psql -X، شمارش تجمیعی SELECT روی user_entity و realm نشان داد هر سه شمارش کاربر فعال، غیرفعال و ایمیل تأییدشده خارج از master صفر و شمار realm فعال خارج از master یک است. خواندن registration_allowed و verify_email از همان realm هر دو false و شمار سطرهای realm_smtp_config صفر بود. بررسی اولیهٔ SMTP به دلیل نام ستون نادرست متوقف شد و با بررسی جدول جداگانه اصلاح شد. در demo-db، پایگاه حاوی auth_l1 با to_regclass کشف شد. identity_links و sessions هر دو صفر بودند و گروه‌بندی initial_login_attempts سه INITIATED و هیچ وضعیت دیگری را نشان داد. query اولیه در پایگاه پیش‌فرض به دلیل نبود schema شکست خورد و در پایگاه دارای schema بازآزمایی شد.

در کد و تنظیمات بررسی‌شده، رویهٔ تأییدشده‌ای برای دعوت و اعتبارسنجی ایمیل در Staging فعلی یافت نشد. ثبت‌نام بسته است و SMTP آماده نیست. حسابی ساخته یا فعال نشد و هیچ سیاست یا ردیف هویتی تغییر نکرد. ادامه به مسیر تأییدشدهٔ دعوت و اثبات کنترل ایمیل برای یک حساب آزمایشی محدود به همین realm وابسته است.

Chrome در پروفایل موقت و با پین فقط برای گواهی‌های loopback اعتبارسنجی‌شده با CA موجود اجرا شد. هدایت با زمان‌بندی ناهمگام location.assign در CDP اجرا شد و DOM جداگانه بررسی شد. مرورگر مبدأ محصول، lang=fa و محتوای DOM صفحهٔ ورود را گزارش کرد. کلیک واقعی روی login-submit انجام شد و سپس DOM در مبدأ Keycloak فیلد گذرواژه را نشان داد. این روش از انتظار مسدودکنندهٔ Page.navigate عبور کرد. علت داخلی timeout قبلی قطعی نشده است. هیچ HTML خام، URL حاوی پارامتر ورود، cookie یا credential ثبت نشد.

فرم مرورگر تأیید شد. دریافت callback و نشست، Signed BFF محصول، اجرای مجاز C018، بازگشت نتیجه به UI و Refresh به‌دلیل نبود حساب دعوت‌شده اجرا نشدند. در این نوبت هیچ اجرای Generation یا Gateway آغاز نشد و شمارندهٔ آزمون انتهابه‌انتها اندازه‌گیری نشد. آروان HOLD است و پذیرش سرپرست ثبت نشده است.

## طرح دعوت محدود به Staging، نسخهٔ ۱

مبنا codex در 0257e19 و ops/mac-first-start در 2a5948f است. این بخش طرح عملیاتی است و سیاست فعال محیط را تغییر نمی‌دهد. سلامت Docker، discovery و مشاهدهٔ فرم مرورگر از checkpoint پیشین به ارث رسیدند.

پیش‌شرط اجرا، یک دعوت آماده برای تحویل به صندوق آزمایشی تحت کنترل دعوت‌شونده از مسیر ایمیل مورد تأیید اپراتور Staging است. تنظیمات موجود شامل صفر ردیف SMTP در realm است و مسیر Mailpit مخزن فقط برای CI ایزوله تعریف شده است. هیچ ارسال ایمیل، تغییر تنظیمات یا ساخت حساب در این checkpoint انجام نشد.

اپراتور مجاز در Admin Console یا Admin REST همان realm غیر master را با issuer پیکربندی‌شده تطبیق می‌دهد و یک حساب بدون نقش مدیریتی، بدون گذرواژهٔ اولیه و با ایمیل تأییدنشده برای همان دعوت ایجاد می‌کند. ثبت‌نام عمومی بسته می‌ماند. اپراتور از قابلیت بومی send-verify-email برای مالکیت صندوق و از execute-actions-email با UPDATE_PASSWORD برای تنظیم گذرواژه توسط کاربر، با مهلت محدود، استفاده می‌کند. کاربر خودش پیام‌ها را در صندوق مجاز باز می‌کند. اگر ارسال ناموفق یا نامعین بود، پیش از تکرار وضعیت همان حساب بررسی می‌شود. حساب تکراری ایجاد نمی‌شود و اپراتور می‌تواند دعوت رهاشده را با غیرفعال‌کردن حساب متوقف کند.

شاهد پذیرش هویت، تغییر وضعیت تأیید پس از اقدام کاربر و ورود تازه از صفحهٔ محصول است. Bootstrap اعتبار ID token و email_verified=true را بررسی می‌کند. نگاشت مالک از issuer و subject انجام می‌شود. Callback صدور موقت، binding و acknowledgement را طی می‌کند. فقط پس از مشاهدهٔ نشست معتبر، درخواست محصول از BFF امضاشده با mTLS آزموده می‌شود. گزارش فقط نتیجهٔ مراحل را نگه می‌دارد تا نشانی ایمیل، پیوند دعوت، کوکی و توکن در Git قرار نگیرند.

در مرحلهٔ بعد، مسیر اجرایی مصوب C018 در حالت NO_DISPATCH_ONLY پس از درخواست تازه باید یک اجرای موتور و نتیجهٔ CONTEXT_READY را نشان دهد. برای پذیرش باید Generation و Gateway هر دو صفر باشند و Refresh با همان شناسه‌های درخواست، فقط GET انجام دهد و شمار اجرای موتور ثابت بماند. هیچ شاهد جدیدی برای این مراحل وجود ندارد. نمایش پاسخ مولد یا نقل‌قول به این آزمون تعلق ندارد. آروان HOLD و پذیرش سرپرست در انتظار است.

[مرجع رسمی مدیریت کاربران و ایمیل Keycloak](https://www.keycloak.org/docs/26.8.0/server_admin/)

[مرجع رسمی Admin REST](https://www.keycloak.org/docs-api/26.8.0/rest-api/index.html)

## آماده‌سازی اجرایی دعوت و مانع تحویل ایمیل

مبنای گزارش codex در 1aa4caf و مبنای اجرای ops/mac-first-start در 2a5948f بود. Docker 28.0.4 با ۴ CPU و ۶٬۲۱۲٬۰۳۰٬۴۶۴ بایت RAM در دسترس بود. هفت کانتینر فعال بودند. پنج healthcheck خود Docker موفق بودند. Keycloak از /health/ready روی پورت مدیریتی ۹۰۰۰ پاسخ ۲۰۰ داد و Nginx با nginx -t -c /run/ingress/nginx.conf و HTTPS محلی با CA موجود، HTTP 200 و TLS_VERIFY=0 را ثبت کرد. آزمون‌های قبلی discovery و ورود مرورگری تکرار نشدند.

شناسه‌های ایمیج‌های زنده در docker inspect به‌ترتیب demo-db و idp-db برابر ff87138949ad، Product API برابر 438ba61c69ea، Auth Bootstrap برابر 8e5d6a79f945، Web BFF برابر ead7afb7f9ec، Web HTTPS برابر caf4e1e032a2 و Keycloak برابر 338942f0b25e بودند. Compose لایهٔ ops در infra/mac-first-start/compose.api.yaml با تنظیم Keycloak از 2a5948f حفظ شد. هیچ جایگزینی کانتینر، ایمیج، Compose یا Volume لازم نشد. بایگانی Keycloak و SHA-256 از checkpoint پیشین تأیید شده‌اند. بازیابی کامل همهٔ اجزا همچنان شاهد ندارد.

issuer از /run/ops/bootstrap.json کانتینر Auth Bootstrap خوانده و فقط نام realm غیر master از مسیر HTTPS از آن استخراج شد. کوئری psql پارامتری و فقط‌خواندنی در idp-db برای همان realm دقیقاً یک سطر Realm، یک Realm فعال، صفر Realm با ثبت‌نام عمومی، صفر ورودی realm_smtp_config و صفر کاربر نشان داد. نتیجهٔ SMTP در همین بررسی زنده مانع عملی ارسال دعوت است. آدرس گیرنده، اعتبارنامه و لینک دعوت وارد گزارش یا Git نشدند.

ابزار نسخه‌دار infra/mac-first-start/staging_invitation_v1.py در SHA محلی b57bf7af40e7f5606cf456b3573dd4f8e721676c روی ops/mac-first-start ثبت شده است. check سپس invite و در مرحله‌ای مستقل password-email اجرا می‌شوند. ورودی غیرمحرمانه شامل issuer دقیق Bootstrap، مسیر CA محلی و میزبان SMTP تأییدشده است. توکن اپراتور Realm و نشانی صندوق با ورودی پنهان ترمینال دریافت می‌شوند. مقصد به loopback با SNI و CA محدود است. ابزار قبل از ساخت حساب SMTP با TLS، بسته بودن ثبت‌نام و نقش‌های پیش‌فرض را بررسی می‌کند. بعد از ایجاد بدون گذرواژه، وضعیت دقیق حساب و نقش‌ها را می‌خواند و سپس از send-verify-email استفاده می‌کند. مرحلهٔ دوم فقط پس از verification ثبت‌شده توسط Keycloak از execute-actions-email برای UPDATE_PASSWORD استفاده می‌کند.

بررسی‌های اجراشده شامل python3 infra/mac-first-start/staging_invitation_v1.py --help، بررسی مرز issuer با runpy و جایگزین‌های محلی HTTP با unittest.mock بودند. سناریوهای SMTP غایب با صفر نوشتن، ساخت و درخواست ایمیل تأیید، درخواست ایمیل تنظیم رمز بعد از تأیید، و رد کردن نقش پیش‌فرض خارج از کلاینت حساب بررسی شدند. این نتایج شاهد آزمایش محلی ابزار هستند. اجرای واقعی Admin REST یا تحویل پیام به دلیل نبود SMTP تأییدشده انجام نشد. بررسی سرویس Docker در تلاش اول با timeout بازبینی مجوز روبه‌رو شد و تلاش محدود بعدی نتیجه داد.

قرارداد C018 در apps/api/PRIVATE_STAGING_ASGI_HANDOFF.md پین 93233bfdf25e40684fd9120b82ec19c217695fdb632ed4a1f7d2bb2a3abcb17d و CONTEXT_READY را مشخص می‌کند. پین مستند شاهد اجرای موتور یا اعتبارسنجی شاخص نیست. به‌دلیل نبود نشست، سؤال تعیین‌شده ارسال نشد و هیچ Attempt تازه، منبع نتیجه، شمارندهٔ تأییدشدهٔ Generation/Gateway یا Refresh ثبت نشد. شاهد زندهٔ Product API محدود به healthcheck است. اقدام بعدی آماده‌کردن مسیر SMTP تأییدشدهٔ Realm برای یک صندوق آزمایشی تحت کنترل دعوت‌شونده است. آروان HOLD و پذیرش سرپرست در انتظار است.

[مرجع رسمی Keycloak Admin REST](https://www.keycloak.org/docs-api/26.8.0/rest-api/index.html)

## بازبینی مسیر SMTP و ورودی لازم برای ادامه

مبنای گزارش codex در ad24281 و نسخهٔ ابزار در شاخهٔ ops/mac-first-start برابر b57bf7a بود. docker version دسترسی زنده به daemon نسخهٔ 28.0.4 را تأیید کرد. آزمون‌های موفق قبلی آمادگی سرویس‌ها، discovery و مرورگر تکرار نشدند.

نام Realm از issuer زندهٔ Bootstrap استخراج و با SELECT پارامتری در IdP تطبیق داده شد. یک Realm فعال منطبق، صفر مورد ثبت‌نام عمومی، صفر سطر تنظیم SMTP و صفر کاربر ثبت شد. docker ps -a هیچ کانتینر با نام یا ایمیج شناخته‌شدهٔ سرویس ایمیل نشان نداد. lsof در محدودهٔ دسترسی جاری شنونده‌ای روی ۲۵، ۴۶۵، ۵۸۷ یا ۱۰۲۵ نشان نداد. در تنظیمات عملیاتی بررسی‌شده پیکربندی تأییدشده‌ای پیدا نشد. Mailpit موجود در سورس، برای CI ایزوله است.

ابزار دعوت نسخهٔ ۱ پیش از ساخت حساب، میزبان SMTP تأییدشده، TLS و سیاست Realm را بررسی می‌کند. گردش ادامه آماده است. اپراتور مشخصات مسیر SMTP تأییدشده و صندوق آزمایشی را از کانال امن فراهم می‌کند و اسرار لازم فقط در رابط امن مدیریت Keycloak یا ورودی پنهان ابزار وارد می‌شوند. بعد از تنظیم، ابزار ابتدا check، سپس invite و بعد از تأیید واقعی صاحب صندوق، password-email را اجرا می‌کند. پیام یا اطلاعات هویتی در این نوبت ارسال یا ثبت نشد.

ورود OIDC، Signed BFF و اجرای C018 به این دعوت وابسته ماندند. سؤال ارسال نشد و نتیجه، منبع یا Refresh تازه‌ای ثبت نشد. هیچ تغییر در ثبت‌نام، Volume، بکاپ یا شاخه‌های محافظت‌شده انجام نشد. آروان HOLD و پذیرش سرپرست در انتظار است.
