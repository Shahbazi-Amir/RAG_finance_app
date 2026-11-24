# تحویل پروژه RAG_finance_app برای انتقال حساب Codex

تاریخ مشاهدهٔ مک ۲۴ نوامبر ۲۰۲۶. این سند حاصل خواندن Git، Docker و شواهد ثبت‌شده است. در نوبت تحویل هیچ آزمون برنامه، Build، استقرار، تغییر داده یا اجرای موتور انجام نشد. وضعیت جاری کانتینرها را از نتیجهٔ تاریخی آزمون‌هایشان جدا بخوانید. هیچ Gate یا پذیرش سرپرست برای این تحویل ثبت نشده است.

## هدف محصول و مرز کار

کاربر باید در UI فارسی با OIDC واقعی وارد شود، پرسش را یک بار ارسال کند، وضعیت بازیابی NB23 V4 را ببیند و با Refresh همان حساب، گفت‌وگو و Attempt را از History بازیابی کند. مسیر هدف `Chrome → HTTPS → Keycloak → Bootstrap/BFF امضاشده → Product API → PostgreSQL → یک Worker پایدار NB23 V4 → CONTEXT_READY + Top-10 → UI` است. خروجی فعلی بازیابی Context است. عملکرد Generator و Gateway باید غیرفعال بماند. وضعیت Source Permission برای انتشار متن، Locator و استناد `BLOCKED` است. تا احراز مجوز، UI فقط وضعیت پردازش و اطلاعات فنی غیرحساس مجاز را نشان دهد. Arvan در `HOLD` است و DNS و Production خارج از محدوده‌اند.

## Git و نقطهٔ ادامه

| محل | شاخه و مبنای مشاهده‌شده | ادامه |
| --- | --- | --- |
| `Shahbazi-Amir/RAG_finance_app`، ریشهٔ مک `/Users/macbookpro/AMIR_DATA/00_WORKS/01_PROJECTS/AI-Agent-projects/RAG_finance_app` | `detached HEAD` در `67ffa71`. پیش از ایجاد این سند تمیز بود. | محل فایل تحویل و Artifactهای نادیده‌گرفته‌شدهٔ Git. |
| Worktree اجرایی `artifacts/nb23-v4-worktree` نسبت به ریشهٔ مک | `ops/nb23-v4-staging`، `af57f26eaac0b20b32a53f0b934f0a5f3d1c814c`. `git status --short --branch` تمیز بود. | همهٔ ادامهٔ اجرایی در همین Worktree. Push کد به شاخه‌های مشترک خارج از محدوده است. |
| Worktree گزارش `/private/tmp/rag-reboot-report` | پیش از تحویل `detached HEAD` در `88702f547b86d8e44d8d58efa0fc05a50d3da974`. همان SHA ابتدا روی `origin/codex` با `git ls-remote` تأیید شد. | SHA گزارش جدید را از `git ls-remote origin refs/heads/codex` بخوانید. `/private/tmp` را محل پایدار Artifact ندانید. |
| `Shahbazi-Amir/RAG_finance` | `rag-phase2` در `1e43edcab922f143e2314f171f641f6235330e6a`. شاخهٔ محلی نسبت به tracking ref یک Commit جلو بود. | فقط‌خواندنی؛ فایل، Index، Golden، Checkout، Commit یا Push تغییر نکند. |

پیشینهٔ اجرایی محلی به ترتیب از `b03d54a` برای writable کردن کپی خصوصی dense، `121addd` برای mountهای فقط‌خواندنی، `8367cf6` برای پروفایل ONNX، `5ee8a25` برای readiness مجوز dense و `c90cfa7` برای ممیزی پین و تنظیم non-spinning می‌گذرد. `5fe21e922b5e6570e319cf528fc481a96a4c8e9e` مبنای نمونه‌های فایل‌های نسخهٔ فریز‌شده بود. ۹ نمونه با Git تطبیق داشتند؛ منشأ تمامی لایه‌های پایه و Web کامپایل‌شده `UNKNOWN` است. ساخت و اتصال کد توسعهٔ موازی در اجرای گزارش‌شده شاهد ندارد.

| Commit اجرایی | پیشرفت |
| --- | --- |
| `d6b659d` | بستهٔ پین‌شدهٔ V4، Dockerfile، Worker مستقل و آزمونگر خروجی. |
| `3bf155a` / `7fef2d8` | Trace مرز بازیابی و توقف هدفمند پس از Hybrid. |
| `78c350b` | حفظ Conversation و Attempt در Reload بر اساس History مالک و تفکیک خطای نشست، alias و خرابی store. |
| `2682060` | مقایسهٔ DEMO08 و V4 با مجموعهٔ مشترک امتیاز برای حذف اثر رتبه‌بندی از فرضیهٔ اصلی. |
| `a80b66d` | تمدید Idle فقط در Staging و ثبت Q2. |
| `6bbb8fd` | بازیابی رسید Q2 و آزمون Fixture انتقال به Worker پایدار. |
| `cec1efc` | بررسی حساسیت Graph Optimizer در نخستین Batch و ثبت مرز اختلاف عددی. |
| `a3430c7` | آزمون مسیر امضاشدهٔ تمدید و گزینهٔ `x64quantprecision`. |
| `af57f26` | PostgreSQL مستقل با Migrationهای پین‌شده، آماده‌سازی Keycloak و آزمون واقعی Authorization Code + PKCE در namespace کانتینر. |

زنجیرهٔ گزارش‌های قبلی به‌ترتیب شامل `bc90f7fae6ca26430d3c3667d23ef8d5f06f6007`، `7ec4685049a852910b93259bedb66b2bd84d08ac` و `88702f547b86d8e44d8d58efa0fc05a50d3da974` است. شواهد تفصیلی و تصمیم‌ها در [گزارش فارسی](MAC_FIRST_START_FA.md)، [HTML](MAC_FIRST_START_FA.html)، [وضعیت](CURRENT_STATUS.md)، [برنامهٔ بازیابی](RECOVERY_PLAN.md) و [دفتر مأموریت](../../coordination/tasks/AGENT-CODEX-REPORTING-01.md) هستند. برای نگه‌داشتن Worktree موجود می‌توان این سند را از مسیر مک خواند؛ تغییر حساب ChatGPT به‌خودی‌خود فایل‌های مک یا دسترسی GitHub را منتقل نمی‌کند.

چهار جریان موازی Foundation، UI، API و DB جدا هستند. آخرین مشاهدهٔ تاریخی ثبت‌شدهٔ PRهای مشترک `#84` در `0fd1066945ef91a3913e040ab4c350bb645ea502`، `#88` در `5969a2e2d8f3550f0386d8f486761ad8a07a110f` و `#92` در `4d951bb427992fd297c17399c87671965718435d` بود. این‌ها در تحویل دوباره خوانده نشدند و مبنای اجرایی نیستند. هرگونه انتخاب نامزد یکپارچهٔ فاز سوم پس از پذیرش V4 در مأموریت مستقل انجام می‌شود. هیچ Pull، Merge، Rebase یا Cherry-pick موازی در Worktree اجرایی انجام نشود.

## Docker مک، داده‌ها و Rollback

Daemon در زمان تحویل پاسخ داد. ظرفیت تاریخی Docker Desktop چهار CPU و حدود ۵٫۷۹ GiB RAM است. `docker ps -a` و `docker inspect` محدود به هویت ایمیج و نام Volume نشان دادند هر هفت کانتینر تاریخی پروژهٔ `rag-f3-db-rotate-local` اکنون متوقف‌اند. آخرین PASS هفت سرویس مربوط به مشاهدهٔ قبلی است. شناسه‌های مقایسهٔ تکرارپذیر در جدول، شناسهٔ کوتاه Container و Image ID محلی هستند.

| سرویس | Container فعلی | Image ID فعلی | Volume نام‌دار | وضعیت مشاهده‌شده |
| --- | --- | --- | --- | --- |
| `demo-db` | `ceb8cfcc9b1a` | `ff87138949ad` | `rag_finance_f3_demo_pg17_20261121` | Exited 0 |
| `idp-db` | `f1ce62cc6476` | `ff87138949ad` | `rag-f3-db-rotate-local_idp_pgdata` | Exited 0 |
| `idp-keycloak` | `39a6d2d1828a` | `338942f0b25e` | mountهای محلی در Freeze Manifest | Exited 143 |
| `product-api` | `6de520400fe5` | `0dc53deefb28` | `rag-f3-db-rotate-local_api_config_private_v1` | Exited 143 |
| `auth-bootstrap` | `fd381291cbdc` | `8e5d6a79f945` | namespace مشترک API | Exited 143 |
| `web-bff` | `95a0741c2270` | `ead7afb7f9ec` | namespace مشترک API | Exited 143 |
| `web-https` | `9ba5554c252b` | `caf4e1e032a2` | `rag-f3-db-rotate-local_mac_ingress_private_v1` | Exited 0 |

API اولیهٔ Freeze `438ba61c69ea` بود. API تاریخی فعلی به‌دلیل اصلاح dense مشتق محلی `sha256:0dc53deefb28fb903ef4deea07a45a09cede78cf4bfa0e85db723a5ded7d9ead` است. اصل Qdrant با mode `0555` و mount فقط‌خواندنی باقی ماند. ورودی dense مستقل stage با بایت‌های برابر و mode `0755` برای تولید کپی Scratch خصوصی writable استفاده شد. lock در Scratch و اعتبارسنجی ۳٬۴۸۸ بردار PASS شد. نتیجهٔ زندهٔ قبلی پنج healthcheck و ۷ سرویس قابل دسترسی داشت. بودجهٔ Runner C018 هنوز ۱۸۰ ثانیه است. Attempt تاریخی `FAILED` بود و در این تحویل دست‌نخورده ماند. یک اجرای ایزولهٔ موفق خروج صفر، ده نتیجه، `CONTEXT_READY`، ۱۹۳٫۰۲ ثانیه زمان کل و Generation صفر داشت؛ اجرای مستقل محدود ۱۸۰ ثانیه به‌طور تکرارپذیر پذیرفته نشد. آزمایش تک‌موردی ۳۰۰ ثانیه با خروج ۱۲۴ و wall حدود ۳۰۵ ثانیه پایان یافت. این مسیر در Resume هدف آزمایش دوباره نیست.

Freeze Manifest خصوصی `rag-finance-mac-freeze.v1` و نسخه‌های before/after با mode `0600` در ریشهٔ امن مک قرار دارند؛ برای محل دقیق و اتصال mountها [گزارش Freeze](MAC_FIRST_START_FA.md) را ببینید. یازده pin Runtime و ۶۰ هش بکاپ در سه مجموعهٔ ۱۵، ۴۰ و ۵ مورد قبلاً تطبیق داشتند. شاهد بازیابی منطقی ایزوله وجود دارد؛ بازیابی سرتاسری، replay Globals و بارگذاری آرشیو ایمیج در daemon مستقل `PARTIAL` هستند. Compose، overrideها و `cutover-checkpoint.txt` در `artifacts/mac-first-start` موجودند. بازگشت API به مبنای قدیم فقط برای خود عملیات Rollback با شرایط و مجوز همان عملیات است. دستور ثبت‌شده و dry-run موفق تاریخی بود:

```sh
/bin/zsh artifacts/mac-first-start/base.zsh up -d --no-deps --no-build --pull never --force-recreate product-api auth-bootstrap web-bff web-https
```

هیچ Rollback زنده در این نوبت انجام نشد. تعویض API در محیط قدیمی به‌دلیل وابستگی namespace مشترک با Bootstrap/BFF/HTTPS یک تغییر چهار سرویسی است. Resume آزمایشی از Staging مستقل آغاز شود؛ سرویس‌های تاریخی را برای حل مشکل Staging روشن یا بازسازی نکنید. `down -v`، prune، reinitialize و حذف Image، Volume، Backup یا Snapshot ممنوع‌اند.

## Session، BFF، History و Staging مستقل

باگ گزارش‌شدهٔ مالک، خروج غیرمنتظره پس از Refresh و خرابی بازخوانی گفت‌وگو بود. `78c350b` در `apps/web/src/auth/server/initial-store.ts`، `apps/web/src/history/proxy.ts` و `apps/web/src/ui/{attempt-checkpoints.ts,product-chat.tsx}` میان alias ناموجود یا نشست نامعتبر و خطای سرویس تمایز می‌گذارد و انتخاب گفت‌وگو و Attempt را پس از Reload از فهرست همان مالک بازیابی می‌کند. آزمون Docker BFF ایزوله با fixture برای صفحهٔ اصلی ۲۰۰، alias ناموجود ۴۰۱ و alias خراب ۵۰۳ داد. ۳۰ آزمون واحد در checkpoint کد BFF ثبت شد. در checkpoint بعدی ۱۴ تست ASGI/mTLS و ۱۴ تست Node برای Bootstrap، BFF و chat موفق بودند. این شواهد مستقل و تاریخی هستند. تنها Reload تاریخی پس از انقضای نشست ۴۰۱ گرفت و سطر ledger اضافه نشد؛ Refresh با نشست معتبر هنوز اثبات نشده است.

تمدید Idle در `apps/api/product_session_api.py` و `src/phase3/auth/transactional_admission.py` با `STAGING_RENEW_IDLE_ON_SEND=1` فقط در مسیر Send مجاز است. Signed BFF، mTLS، بررسی Path و Body، مصرف JTI، Origin و Sec-Fetch-Site حفظ می‌شوند. `infra/nb23-v4/staging_idle_renewal.sql` تابع `admit_and_renew_staging_session` را فقط برای پایگاه آزمایشی اضافه می‌کند. آن تابع هویت مالک، epoch و generation را می‌سنجد و اول مالک، بعد نشست را قفل می‌کند. تمدید با همان تراکنش Send می‌ماند و با شکست action rollback می‌شود. مجوز مستقیم تغییر جدول یا `touch_session` به `history_app` افزوده نشد. Idle برابر ۱۲۰ ثانیه و Absolute برابر ۵۰۰ ثانیه است. GET، Poll و Browser Reload هیچ‌کدام Idle را تمدید نمی‌کنند. مرور بدون Send معتبر پس از ۱۲۰ ثانیه انقضای طبیعی دارد. توکن‌های حساس باید فقط سمت سرور بمانند.

`infra/nb23-v4/test_staging_idle_renewal.sh` با PostgreSQL واقعی موقت، فعالیت ثانیهٔ ۹۰، cap، انقضای idle و absolute، مالک/نسل ناسازگار، revoke، rollback و permissions را PASS کرد. در Race، تمدید منتظر قفل ماند و پس از Commit ابطال رد شد. `test_signed_idle_db.sh` و `check_signed_idle.py` با RSA fixture و verifier برنامه روی PostgreSQL واقعی نشان دادند Send معتبر تمدید می‌کند و GET زمان‌ها را ثابت نگه می‌دارد؛ replay، اثبات نامعتبر، مالک دیگر و opt-in تمدید با GET رد شدند. DB و تنظیم تاریخی تغییر نکردند. Logout در مرورگر، دوام نشست پس از Restart، شمارش Attempt هنگام Refresh و E2E کامل هنوز بازند.

ایمیج مشتق API `sha256:d8d93260a4d41cf26242b3744065f8958a0db1388d55a532d05c021b29995691` با `--pull=false --network=none` قبلاً ساخته و آزمون import شد. ایمیج BFF نامزد `0ee86f3333ec` در آزمون ایزولهٔ HTTP با fixture استفاده شد. ایمیج API محلی `psycopg`، `PyJWT` و `httpx` دارد. ایمیج Web بررسی‌شده Next و React دارد ولی Playwright/Puppeteer ندارد. Chrome روی مک نصب است. `Playwright 1.64.1` پین harness قبلی است؛ ماژول‌های `initial_oidc_harness` و `test_bootstrap_oidc_010` در Worktree فعلی یافت نشدند. مسیر اصلی برای مرورگر، Chrome موجود یا harness محلی معتبر است. نصب سراسری یا Download در این نوبت انجام نشد.

### وضعیت فعلی شبکه و کانتینر آزمایشی

| جزء | شاهد مشاهده‌شده | وضعیت |
| --- | --- | --- |
| شبکهٔ `nb23-session-e2e` | bridge داخلی، شناسهٔ کوتاه `141ae40e` | موجود. انتشار پورت `19443` روی میزبان در این شبکه در checkpoint قبلی برقرار نشد. |
| `rag-nb23-session-e2e-pg` | `1616d842dacb`، `ff87138949ad` | Running، روی tmpfs، Migrationهای 001 تا 010 و SQL تمدید اعمال شده‌اند. `psql` قبلاً دو تابع `issue_initial_login_pending` و `admit_and_renew_staging_session` را تأیید کرد. |
| `rag-nb23-session-e2e-keycloak` | `aa6baa2144de`، `7e66a96e4739` | Running، روی tmpfs، Realm و حساب fixture. `check_session_oidc.py` قبلاً HTTPS discovery، فرم واقعی و تبادل Authorization Code با PKCE را در namespace کانتینر PASS کرد. |
| `rag-nb23-session-e2e-db` | `4226a4a1fb7a` | تلاش قبلی متوقف با exit 126 و جدا از PostgreSQL فعلی. |
| Bootstrap/BFF/API/HTTPS مستقل | ایمیج‌ها موجود؛ اتصال کامل در Staging انجام نشده | `BLOCKED` برای Browser E2E؛ URL محصول حاضر وجود ندارد. |

در تاریخچهٔ `af57f26`، ناسازگاری `openssl -addext` با فایل CNF رفع شد. قلاب initdb روی mount قابل اجرا نبود و نسخهٔ `0644` در نمونهٔ تازه خوانده شد. اولین درخواست OIDC حین گرم‌شدن JVM timeout شد و بررسی بعدی خروج ۰ داد. کدهای مرتبط `prepare_session_oidc.py`، `init_session_e2e_db.sh` و `check_session_oidc.py` هستند. tmpfs با توقف از بین می‌رود. پیش از اتکا در حساب جدید وضعیت همان دو کانتینر را بخوانید و لاگ حساس، محیط کامل، Credential یا material خصوصی را چاپ یا export نکنید. در فهرست Docker تحویل، Worker سنگین فعال نبود؛ از فایل‌های پایان Q2 استفاده شود و پیش از آزمایش بعدی وضعیت فرایند بومی هم بررسی شود.

آخرین کار باز، سیم‌کشی Bootstrap/BFF/Product API به IdP و PostgreSQL ایزوله، مبدأ ثابت `https://ragfinance.ir` در پروفایل برنامه و callback همسان، نقش‌های Login جداگانه و صدور mTLS تازه برای همین مرز داخلی است. نگاشت محلی Chrome برای `ragfinance.ir → 127.0.0.1` در گذشته استفاده شد؛ آدرس قدیمی را URL آماده یا اینترنتی فرض نکنید. TLS/Hostname verification را حفظ کنید و ابتدا راه دسترسی مرورگر و نام میزبان را بدون بازکردن پورت IdP/Worker به اینترنت حل کنید.

## NB23 V4، Parity و Adapter

نامزد `NB23.PERF_CACHE01_TRIGRAM_PRIVATE_V4` از NB23، ایمیج مستقل `sha256:f49f536f4d8294ff1453665e99b87a85158200d0d16368b57a38f7274d320781` و پایهٔ محلی `c90cfa73de7c8f7a264f59f5dedbfaec4dd3693c` است. Worker هنگام شروع E5، Tokenizer، ONNX و cache trigram را برای ۳٬۴۸۸ قطعه آماده می‌کند. cache قبلاً با استخراج مرجع SHA-verified DEMO08 مقایسه شد. نقص تاریخی گزارش نوت‌بوک (C192، `NameError: PART` و ثبت‌نشدن `results.json` اصلی) با harness مستقل دور زده شد و شواهد اصلی بازنویسی نشد. Native Cleanup مستقل، restart نظارت‌شده و اتصال به محصول پذیرفته نشده‌اند. یک بار خروج clean و رویداد `closed` مشاهده شد. هر بار فقط یک Worker سنگین فعال شود.

| بررسی | نتیجهٔ تاریخی یا مشاهده‌شده |
| --- | --- |
| NB23 گرم تاریخی | شش اجرای Context حدود ۱۵٫۶۲۵ تا ۲۲٫۴۲۱ ثانیه، میانهٔ ۱۹٫۰۸۴. |
| Docker V4 واقعی آفلاین | Q2 سرد ۴۱٫۸۱۰، Q3 گرم ۳۷٫۴۰۰ و WARM ۴۴٫۶۳۲ ثانیه. startup Worker برابر ۲۴٫۳۳۸ ثانیه. اوج RSS فرایند `1817328 KiB`، حدود ۱٫۷۳ GiB. نمونهٔ Docker ۱٫۷۸۴ GiB و ۴۰۱٫۱۲٪ CPU. سه Context ساخته شدند. Generation صفر و شبکه و Gateway قطع بودند. |
| مرجع | Golden تاریخی DEMO07 با زنجیرهٔ V4 و SHA سؤال تطبیق داشت. DEMO08 و V4 با همان ۱۰۰ امتیاز Q2 در Linux، ترتیب، Top-10 و Context برابر تولید کردند. هر دو با Golden متفاوت بودند. |
| Q2 | Hybrid100 برابر. Top-10 مرتب Docker فقط ۸/۱۰ تطبیق موقعیتی داشت و Context متفاوت بود. Native Mac بازیافته Top-10 و Context برابر Golden داشت. |
| Q3 | Hybrid100 برابر. اجرای مستقل Docker Top-10 فقط ۳/۱۰ تطبیق موقعیتی و Context متفاوت داشت. Trace تفصیلی بعدی در ONNX با ۲۴۰ ثانیه و خروج ۱۲۴ پایان یافت. Parity کامل بومی Q3 ثبت نشده است. |
| WARM | Top-10 و Context در اجرای Docker اولیه با Golden متفاوت بودند. |
| جفت Native و Docker Q2 | بازیابی Native Q2 پس از `Path.open(opener=...)` موفق شد. هر دو اجرای ثبت‌شده با خروج ۰ تمام شدند. ۲۵/۲۵ هش ورودی Tensor برابر. نخستین اختلاف در logits مربوط به Batch 1، بیشینهٔ قدر مطلق اختلاف کل ۰٫۷۷۴۵۰۷۵۲۲۶. |

SHA مدل ONNX در دو محیط یکسان و فایل external tensor صفر است. مدل ۹۸ `DynamicQuantizeLinear` و ۹۸ `MatMulInteger` دارد. خروجی `float` با شکل `[batch_size,1]` است. ORT هر دو 1.16.3 و Provider هر دو `CPUExecutionProvider` است. SHA باینری Mach-O مک `499a5ad6bcacff32285e67929c3cef8047d6eb125e0d8cf2500c3f49cb333b4b` و ELF Linux `22d666c3c24b9efb4d98c8d4d810960014fab055a6deba77f5dda74e3334845c` است. مک x86_64 دارای AVX2/FMA بود؛ Docker AVX/FMA و SSE4.2 نشان داد و AVX2 گزارش نشد. نشست مرجع چهار intra-op، یک inter-op، sequential و `ENABLE_ALL` بود. Graph Optimizer خاموش به‌تنهایی Batch 1 را با Native برابر نکرد (`max_abs_delta≈0.241923` در برابر تنظیم مرجع `≈0.542899`). `session.x64quantprecision=1` همان امتیازهای Docker را داد و ترکیب آن با optimizer خاموش با timeout ۱۲۰ بدون خروجی پایان یافت. این تفاوت‌ها فرضیهٔ build/ABI/Kernel/ISA می‌سازند. نخستین عملگر متفاوت و علت قطعی `UNKNOWN` است. تفاوت Torch مک 2.2.2 و Docker 2.6.0+cpu و sentence-transformers 5.0.0 و 4.1.0 به‌تنهایی علت اختلاف اجرای Tensor ثابت را ثابت نمی‌کند.

`src/phase3/rag_runtime/persistent_v4_pipe.py` سه `FIXTURE_TEST` موفق ثبت کرد: استفاده از همان فرایند برای دو درخواست، رد Attempt ناسازگار و timeout همراه با بستن فرایند بدون replay. Adapter به Product API وصل یا به‌صورت واقعی dispatch نشده است. همچنان قرارداد نسخه‌دار و SHA، readiness پس از بارگذاری کامل، queue محدود، Owner و Attempt binding، ledger و idempotency، timeout/cancel، Recovery، Restart و Native Cleanup بازند. Worker بومی Mac صرفاً گزینهٔ احتمالی Staging محلی است؛ Q3 بومی و مرز امن احراز هویت و شبکه پیش‌نیازند. برچسب جداگانهٔ `NATIVE_MAC_STAGING` در صورت اجرای مصوب لازم است.

## Artifactهای خصوصی و هویت ورودی

مسیرها نسبت به ریشهٔ اصلی مک‌اند؛ این فایل‌ها را با Git منتقل نکنید. در حساب جدید با همان Workspace و مجوزهای محلی کار کنید. Manifest کامل، pinهای tokenizer، قرارداد، snapshotهای cache و مسیر هر ورودی در `artifacts/nb23-v4-bundle/manifest.json` و `artifacts/nb23-v4-bundle/contract.json` ثبت شده‌اند. پوشهٔ ورودی `artifacts/nb23-v4-bundle/inputs` مشتق خواندنی از مبنا است. اصل نوت‌بوک `RAG_finance/notebooks/phase2/23_phase3_handoff.ipynb` و خروجی محلی اصلی `_RAG_finance_NB23_speed_quality_outputs/NB23_PERF_CACHE01_TRIGRAM_PRIVATE_V4/` فاز دوم دست‌نخورده بمانند.

| هویت | SHA-256 یا revision ثبت‌شده |
| --- | --- |
| V4 `engine.py` | `91a1a34628f221f7f8bc892a0fb6a917328817dae1328856d84aad7f880f406e` |
| رسید تاریخی `postrun_recovery_receipt_v4.json` | `4fb6a89cdd2cd07df44b7798fe7740f97e6b4412d5b7e95073f0313c389584c2` |
| C018 `rag_engine.py` | `93233bfdf25e40684fd9120b82ec19c217695fdb632ed4a1f7d2bb2a3abcb17d` |
| `C011.population_boundary` | `a3ffce372eab24e210bedae9b2b6087dc2493e45805c4c27836d223a6578fe80` |
| CHUNKS `baseline_phase1_char_safe_v1.jsonl` | `3891c4ecad9332ba753cd605bbccd99da9d063f64934a30ee39e495349cffb50` |
| Dense `storage.sqlite` | `2835c3de93140865af5ef25a0b4310d63d573864cb804bec8853a0159ef29125` |
| Dense `meta.json` | `ef0d4006d923b18237685698834b888b67d8e2f68e36249d35c782f7189b8380` |
| Dense logical | `2fc5e50ebbd1e1e66d59c703eb48f1367b2d3deadfed62efb9d5a5e6959f7ef4` |
| Sparse config | `f0b6becdb096493ccfe491c04acec649216238f1e13a6124427994c23c9fd670` |
| Sparse documents | `104c1fb0aade4456bfd6ec7ce4466e3c09f95d916c079bf1a91f4767d1250d9f` |
| Sparse postings | `d2b1ceed5a62f9f0048ede8fa73ccde5299b4d85b4f3f164aefaa82d939257d0` |
| E5 `intfloat/multilingual-e5-small` | revision `614241f622f53c4eeff9890bdc4f31cfecc418b3` |
| ONNX `cross-encoder/mmarco-mMiniLMv2-L12-H384-v1` | revision `1427fd652930e4ba29e8149678df786c240d8825` و مدل `6c2513767fb63d008a4377bef7a7a3555433d9436342bb53e35a3a72ffc52d4b` |
| قرارداد بسته | `b565fc60fc313feeeb0ff5ffc1cfb2836babbf9852bb63c4ae5201ed74f95595` |
| Worker بسته | `f05f820f6141686c6571706760bedece532fd227be2bc4034cadbeb5c98f2a2b` |

- شواهد Q2 در `artifacts/nb23-v4-bundle/` شامل `q2-recovery.checkpoint`، `q2-quantprecision.checkpoint`، `q2-native-recovery.jsonl`، `q2-native-recovery.log`، `q2-docker.log`، `q2-native-private.json`، `q2-docker-private.json`، `first-batch-private.json`، `onnx-options.log` و `onnx-quantprecision.log` است. از نام‌های `private` فقط در محیط مجاز استفاده کنید و Tensor خام، متن پرسش خصوصی و scoreها را منتشر نکنید.
- `trial.log`، `hybrid-trace.log`، `parity-trace.log` و `shared-scores.log` شواهد آزمون‌های قبلی‌اند. `run-trial.zsh`، `run-trace.zsh`، `run-hybrid.zsh` و `run-score-docker.zsh` روش ثبت را حفظ می‌کنند. خواندن Checkpoint جای اجرای دوباره را می‌گیرد.
- `artifacts/nb23-session-build/` شامل Dockerfileها، `api-renewal/`، `report-renewal.py`، `report.py`، `smoke.mjs` و کپی‌های کار BFF است. این پوشهٔ محلی، تغییر ثبت‌نشدهٔ Git در شاخهٔ اجرایی محسوب نمی‌شود. تغییر گزارش‌ساز پیش از HTTP 404 در همین محل بود.
- فایل‌های اصلی کد Worker در `infra/nb23-v4/{Dockerfile,.dockerignore,worker.py,verify_trial.py,trace_parity.py,compare_tail.py,score_fingerprint.py,probe_onnx_options.py}`، آزمایش pipe در `tests/phase3/api/test_persistent_v4_pipe.py` و آزمون‌های Refresh/Bootstrap در `tests/phase3/ui/{attempt-checkpoints.test.mjs,auth_bootstrap_010.test.mjs}` است. `git diff --name-only c90cfa7..af57f26` فهرست کامل ۲۶ مسیر اجرایی را می‌دهد. Worktree اجرایی بدون تغییر ثبت‌نشده بود؛ تنها فایل جدید در ریشهٔ تحویل همین Markdown است.

## Terra، Sol و بازیابی قطع ارتباط

بکاپ‌های محلی زیر `AMIR_DATA/_SAFE_BACKUPS/RAG_finance_phase3` قرار دارند. برای هر مجموعه، `SHA256SUMS` و `RESTORE_REPORT.md` همان مجموعه مبنای خواندن‌اند. حساب جدید برای دسترسی به این داده‌ها باید همان محیط مک و مجوزهای محلی را داشته باشد.

طبق خلاصهٔ مالک، Terra در بررسی وابستگی‌ها به HTTP 404 مسیر ارتباطی Codex رسید؛ تصویر مرورگر یا URL قابل تحویل به مالک ثبت نشد. از بررسی Terra وجود psycopg/PyJWT در ایمیج محلی و نبود Playwright/Puppeteer در ایمیج Web به‌عنوان سرنخ استفاده شد. Sol خروج موفق بررسی وابستگی‌ها را بازیابی کرد و در `af57f26` از ایمیج‌های موجود، PostgreSQL و Keycloak مستقل و PKCE واقعی در namespace را تأیید کرد. بنابراین dependency برای اجزای آزموده‌شده رفع شده و اتصال مرورگر به پشته باز است. `404` FAIL موتور یا Docker نیست. خروج ۱ شناخته‌شدهٔ Q2 بومی از serialization رسید بود و اجرای journalدار و جفت Docker تکمیل شده‌اند. در قطع ارتباط بعدی قبل از اجرای تازه PID، Timestamp، خروجی، trace و exit code را بخوانید.

## وضعیت پذیرش و موانع

در بررسی میزبان با `ps -axo pid=,stat=,comm=` و فیلتر نام اجرا، فرایند بومی منتسب به Q2 یا Worker دیده نشد. این مشاهده را پیش از هر آزمون سنگین دوباره بررسی کنید. شناسهٔ کامل شبکهٔ مستقل `141ae40e28a8cf492f1718e18bb581557e0a038f9a9cd0d34666347444949ef3` است.

| مرحله | وضعیت و شاهد |
| --- | --- |
| Docker تاریخی و Rollback | حفظ شده، اکنون ۰ از ۷ Running. دستور بازگشت dry-run قبلی PASS. Restore کامل PARTIAL. |
| Qdrant تاریخی | PASS در اجرای پیشین، mode فقط‌خواندنی اصل و قفل Scratch اثبات شدند. |
| Session BFF و انتخاب History | آزمون‌های HTTP/Node و fixture PASS؛ Browser E2E باز. |
| Idle/Race/Revoke/Replay/Cross-owner | PostgreSQL واقعی ایزوله و Signed Send PASS؛ logout/revoke مرورگر باز. |
| Issuer و Code+PKCE | PASS فقط در namespace کانتینر Keycloak؛ Login محصول در مرورگر NOT RUN. |
| Staging برنامه | PARTIAL. PG و IdP بالا؛ TLS/mTLS، Bootstrap/BFF/API، نقش Login و مرورگر باز. |
| Hybrid100 و ورودی ONNX Q2 | PASS. Hybrid Q2/Q3 برابر و ۲۵/۲۵ Tensor Q2 برابر. |
| Docker ONNX/Top-10/Context | FAIL. مرز قطعی logits در Batch 1؛ نخستین عملگر و علت UNKNOWN. Native Q2 PASS؛ Native Q3 باز. |
| Worker و Adapter | Worker آفلاین واقعی Context ساخت؛ lifecycle PARTIAL؛ Adapter فقط FIXTURE_TEST PASS. |
| محصول V4 و Refresh | BLOCKED بر Parity و اتصال Staging. Attempt واقعی تازه، Session E2E و Refresh با همان Attempt NOT RUN. |
| انتشار منبع | BLOCKED؛ شواهد مجوز انتشار و Locator لازم است. |
| Human UI و Freeze | NOT READY؛ پذیرش انسانی و سرپرست در انتظار. |

## ترتیب ادامه و معیار پذیرش

1. **ابتدا Staging نشست.** در همان مک و Worktree اجرایی `af57f26`، سلامت `rag-nb23-session-e2e-pg` و `rag-nb23-session-e2e-keycloak` را با بررسی کوتاه بخوانید. Bootstrap، BFF و API نامزد را به همین IdP/DB وصل کنید. roleهای Login جدا، mTLS داخلی و HTTPS محلی با hostname/callback صحیح بسازید. سرویس حساس را عمومی نکنید و هفت کانتینر قدیمی را خاموش نگه دارید. Health، TLS و Signed BFF از ورودی واقعی و DB مستقل باید قبل از آزمون مرورگر شاهد داشته باشند.
2. **Browser E2E مستقل از Parity.** با Chrome و حساب fixture مجاز، Login واقعی → History → Refresh نشست معتبر → Send مجاز با dispatch موتور غیرفعال طبق قرارداد آزمون → تمدید Idle اثبات‌شده در SQL → Refresh همان Conversation/Attempt → Logout و رد نشست باطل‌شده. در زمان آزمون با Trace HTTP و ledger اثبات کنید Refresh فقط GET است، Send یا Attempt تازه و dispatch ایجاد نمی‌شود، و polling ساعت Idle را جابه‌جا نمی‌کند. انقضای طبیعی ۱۲۰/۵۰۰، ۴۰۱ معتبر، ۵۰۳ مجزا و منع دسترسی مالک دوم هم بررسی شوند. اگر نیاز به ورود انسانی بود، فقط بعد از اعتبارسنجی URL و TLS از مالک همان اقدام را بخواهید. هیچ Cookie، Token یا هویت حقیقی در شواهد منتشر نشود.
3. **ONNX با یک Batch ثابت و یک Worker.** از Q2 بازیافته، مدل پین‌شده و همان ورودی Batch 1 استفاده کنید. روی کپی خصوصی مدل فقط خروجی‌های میانی نخستین `DynamicQuantizeLinear`، scale، zero-point، نخستین `MatMulInteger` و float بعدی را بیرون بگیرید. logits کپی را با اصل در همان محیط کنترل کنید تا اثر instrumentation بر optimizer و execution plan معلوم باشد. فقط نخستین اختلاف معتبر را گزارش کنید و اصلاح وابسته به شاهد را در کپی مستقل اعمال کنید. با موفقیت Batch 1، ۲۵ batch Q2، سپس Q2 و Q3 و WARM را با Golden بدون تغییر بسنجید. در صورت عدم حل، بررسی native محلی فقط با Q2/Q3 معتبر و مجوز مرز شبکه، بدون ادعای Docker parity، مطرح است.
4. **Worker و محصول.** قرارداد lifecycle و پاسخ نسخه‌دار و SHA، مالک/Attempt، idempotency، cancel، Recovery و Cleanup را روی محیط مستقل ببندید. آزمون fixture را جدا برچسب بزنید. پس از Parity واقعی و Ready بودن Worker، یک Attempt مرورگری واقعی با OIDC/BFF و ledger ثبت کنید. `CONTEXT_READY`، Top-10، زمان Worker، شمارهٔ Attempt، شمار dispatch و Refresh با همان Attempt را بدون خروجی غیرمجاز ثبت کنید. اگر Attempt شکست خورد علت همان یکی را بیابید. پس از موفقیت واقعی، `READY FOR HUMAN UI TEST` با URL دقیق Chrome، روش ورود، سؤال مجاز، نتیجهٔ قابل انتظار و مراحل Refresh اعلام شود. Candidate Freeze با manifest، Image ID، rollback، شواهد Parity و Session و با پذیرش انسانی و سرپرست باز ثبت شود.

تکرار ممنوع در Resume بدون فرضیه یا تغییر مرتبط: Benchmark C018 با سقف ۱۸۰/۳۰۰، Build نامزدهای موجود، Import آزموده‌شده، SQL/Race/Signed Send/PKCE موفق، ۲۵ هش ورودی Q2، Hybrid موفق، رتبه‌بندی با امتیاز مشترک، probe تکراری optimizer و `x64quantprecision`، سه Fixture pipe بی‌تغییر، و Q2/Q3 کامل پیش از اصلاح هدفمند. Golden، مدل، Index، CHUNKS، وزن، امتیاز و معیار پذیرش را برای PASS تغییر ندهید.

## PROMPT FOR NEW CODEX ACCOUNT

> این فایل تحویل را کامل بخوان. روی همان مک و مخزن `Shahbazi-Amir/RAG_finance_app`، Worktree `artifacts/nb23-v4-worktree`، شاخه `ops/nb23-v4-staging` و checkpoint تأییدشده `af57f26eaac0b20b32a53f0b934f0a5f3d1c814c` ادامه بده. ابتدا HEAD، Git status، فرایند سنگین و دو کانتینر Staging را خواندنی بررسی کن. بعد از HTTP 404 هیچ آزمایش تکمیل‌شده را دوباره آغاز نکن. Artifactها در Workspace اصلی‌اند. کد موازی GitHub، مخزن فاز دوم، کانتینرها، Volumeها، دیتابیس، Golden، مدل و Backup تاریخی را حفظ کن. بدون Download، عملیات مخرب، Force Push، تغییر Production یا افشای اسرار کار کن. Generation/Gateway غیرفعال، Source Permission مسدود و Arvan HOLD بمانند.
>
> اولین کار اجرایی، پیوند Bootstrap، BFF و API مشتق به PostgreSQL/Keycloak مستقل موجود از طریق HTTPS محلی و mTLS داخلی است. پس از Health روی مرورگر واقعی Login، History، Refresh با همان نشست/Attempt، Send معتبر، تمدید SQL، Logout و Revoke را کامل کن. Idle=120 و Absolute=500، GET/Poll بدون تمدید، منع cross-owner و بدون duplicate POST/Attempt/dispatch الزام‌اند. اگر ورود دستی لازم شد، بعد از آماده‌بودن URL فقط ورود را درخواست کن. این مسیر را منتظر ONNX نگذار.
>
> در مسیر دوم از trace کامل Q2 موجود استفاده کن. نخستین اختلاف اثبات‌شده logits Batch 1 است؛ با instrumentation روی کپی خصوصی و کنترل execution plan، نخستین عملگر متفاوت را ثابت کن. حداکثر یک Worker سنگین؛ Q2/Q3 کامل پس از اصلاح مؤثر. تنها پس از PASS Parity و کنترل‌های Worker، V4 را به API آزمایشی وصل کن و یک Attempt واقعی، CONTEXT_READY، Top-10، Refresh بدون redispatch و Logout را با شواهد پالایش‌شده ثبت کن. هیچ Fixture را E2E ننام. مقصد نهایی READY FOR HUMAN UI TEST و Candidate Freeze با Rollback، URL Chrome و دستور کوتاه تست برای مالک است. پس از هر پیشرفت معنادار در شاخهٔ اجرایی checkpoint محلی و در صورت Push طبق AGENTS.md همان دفتر مأموریت گزارش را به‌روز کن. پذیرش سرپرست و انسانی را جدا ثبت کن.
