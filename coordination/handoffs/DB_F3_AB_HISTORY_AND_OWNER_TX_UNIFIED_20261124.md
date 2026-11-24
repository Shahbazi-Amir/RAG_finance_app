# فاز سه / تحویل DB به Foundation — History دو مالک، Restore و مرز امن تراکنش

**دامنه:** `APP_ONLY`، بدون Engine/مدل، بدون Migration 011، بدون تغییر روی Mac، دیتابیس دمو یا `main`.
**مبنای نامتغیر کاندیدا:** [PR #84](https://github.com/Shahbazi-Amir/RAG_finance_app/pull/84) SHA `0fd1066945ef91a3913e040ab4c350bb645ea502`.
**شاخهٔ DB:** `agent/db-f3-ab-history-restore-20261124`، [PR #86](https://github.com/Shahbazi-Amir/RAG_finance_app/pull/86) Draft.
**SHA واحد آزمودهٔ اجرایی:** `f0331f1ba76921c8d0582c1d59ea00965a934ae5`.
**CI قطعی:** [45291109728](https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/45291109728) / `SUCCESS` / یک job.
**رسید تمیز:** Artifact `f3-db-unified-ab-history-restore-owner-tx`، شناسهٔ `14873303344` (فقط JSON امن و ساختارمند).

## تغییر واقعی

۱. `infra/postgres/dev_f3_isolated/scripts/26_two_owner_history_sql_restore.sh`:
کپی جداگانهٔ PG17.11، دادهٔ مصنوعی متمایز برای A (۵ گفتگو، ۴ پیام) و B (۳ گفتگو، ۲ پیام)، اتصال LOGIN محدود واقعی `history_app` از مسیر TCP/SCRAM/TLS `verify-full` با CA/SAN، ۱۸ assertion دربارهٔ list/detail، صفحه‌های keyset، جلوگیری از B→A و A→B، context بدون owner و صفر Send/Attempt/Answer. Backup با SHA256 روی کلاستر PostgreSQL مستقل و Volume مستقل restore می‌شود؛ همان ۱۸ assertion تکرار و خروجی خصوصی SQL با `cmp` مقایسه می‌شود. کپی‌های probe پس از موفقیت حذف می‌شوند.

۲. `infra/postgres/dev_f3_isolated/scripts/27_history_actor_transaction_pool_fence.sh`:
از یک *physical connection* در `history_app` مسیر A → بدون مالک → B → بدون مالک را آزمایش می‌کند. `SET LOCAL` پس از commit پاک می‌شود؛ اما `SET app.owner_id` غیرمحلی می‌تواند در session pool باقی بماند. جعل GUC توسط کلاینت SQL نقش `history_app` عمداً بازتولید شده است، و **نشانهٔ خطر/NOT_ACCEPTED است، نه تأیید امنیت**؛ فقط BFF با mTLS و امضا، اعتبار IdP/Session و Binding داخل همان transaction می‌تواند History واقعی را فعال کند.

۳. `.github/workflows/f3-db-owner-tx-fence.yml`:
یک job روی یک SHA، از نصب پین‌شدهٔ `001–010` و Ledger/DB55/۹ role TLS تا Restore مستقل و **پنج probe** `26`، `27`، `19` (شش جدول History RLS + neg matrix)، `21` (cursor با insert concurrent)، `24` (دو اتصال رقابتی Idempotency) را اجرا می‌کند. قراردادهای پنج رسید assert می‌شوند و سه JSON sanitizeشده بدون داده، سرّ، DSN یا private dump صادر می‌شوند.

## نتایج قابل استناد در لاگ دقیق همین SHA

- `F3_LAB_MIGRATIONS_001_010_APPLIED=PASS`
- `AB_HISTORY_BEFORE=18_SQL_ASSERTIONS_PASS` و `AB_HISTORY_AFTER=18_SQL_ASSERTIONS_PASS`
- `AB_HISTORY_INDEPENDENT_RESTORE_EXACT_PARITY=PASS`
- `ACTOR_GUC_TRANSACTION_LOCAL_A_B_UNSET_NO_LEAK=PASS`
- `ACTOR_GUC_IMPERSONATION_RISK=CONFIRMED_REQUIRES_SIGNED_API`
- `ACTOR_PERSISTENT_SET_POOL_LEAK=CONFIRMED_REQUIRES_CHECKOUT_RESET`
- `HISTORY_CONVERSATIONS_DESC_ANCHORED_KEYSET=PASS`
- `M10_A10_TWO_CLIENT_UNCOMMITTED_UNIQUE_RACE=1_WIN_1_DENIED`
- `M10_A10_REAL_SIGNED_HTTP_CRASH_REPLAY=NOT_RUN`
- `DB_F3_UNIFIED_FIVE_SQL_PROBES_ONE_REAL_PG_SHA=PASS`

**سیاست نتیجه:** صفر acceptance جدید؛ هیچ ادعای اجرای واقعی مرورگر، IdP، BFF/PG با امضای معتبر، session revoke، پروسه API crash یا دیتابیس Mac وجود ندارد.

## ردیف‌های canonical متاثر و موانع اصلی

| ID | شاهد افزوده | هنوز باز |
|---|---|---|
| `P3M06-A03` | SET LOCAL و نشت SET روی یک اتصال PostgreSQL واقعی | Same-TX امضاشدهٔ IdP→BFF→API→PG + تضمین پاک‌سازی connection checkout |
| `P3M06-A05/A07/A09` | Negative SQL Owner A/B/no-owner؛ RLS و FK | منفی HTTP واقعی برای تمام endpoints، direct Repository با actor امضاشده |
| `P3M10-A10` | رقابت واقعی دو client SQL؛ ۱ commit، ۱ duplicate denied | Retry واقعی HTTP با ACK-loss، سقوط فرایند API و signed session epoch |
| `P3M15-A03/A07` | Cursor و Detail/List با ۲ مالک در SQL | Browser واقعی با دو حساب OIDC و pagination/refresh/revoke |
| `P3M22-A09` | Restore مستقل، SHA256 و برابری History | DR تمام ماشین و IdP/Qdrant، offsite encryption، RPO/RTO مصوب |

شاخص تخصصی همان **۵ DONE محدود از ۵۷ (۸٫۷۷٪)** است؛ ۲۸ OPEN و ۲۴ BLOCKED. نقشهٔ اصلی: ۲۶۲ فعالیت و ۲۶ Gate؛ از این تحویل هیچ پذیرش رسمی ایجاد نمی‌شود. پوشش اولیهٔ گزارش‌شدهٔ دیگر چت‌ها (۱۵۱/۲۶۲) را به‌عنوان پذیرش حساب نکنید. اجرای مسیر مشترک پنج‌مرحله‌ای مرورگر→SQL هنوز `0/5 fully verified` است.

## دستور لازم برای Foundation / API / UI

- مبنای PR #84 را بخوانید و تنها سه فایل مشخص DB در #86 را با `merge-base` و SHA واقعی انتقال دهید؛ SQL `001–010`، 011، نقش‌های سرویس، mac/demo را تغییر ندهید.
- تست DB: روی checkout تمیز با ENV آزمایشگاهی جدید (`SOURCE_REPO=$GITHUB_WORKSPACE`، `LAB_ROOT=$RUNNER_TEMP/f3-db-unique-...`)، workflow بالا را اجرا کنید. در مسیر فایل `26` فقط **بعد از** اجرای `06_backup_restore_independent.sh` اجرا می‌شود؛ `27` نیازمند PG17/DB55 آماده است.
- API: `apps/api/private_app_only_asgi.py` از PR #80 را روی PR #84 با diff بررسی و در یک Runner واقعی تست کنید. `history_app` به‌تنهایی هویت IdP را اثبات نمی‌کند؛ تا mTLS cert+RS256 assertion+004/005 session+epoch+same-TX BFF owner binding عملی نشده، History و readiness 503 باقی بمانند.
- Foundation: همهٔ Web/BFF/API/Bootstrap/IdP/PG در یک شبکه خصوصی ماندگار؛ دو حساب **واقعی و متفاوت** OIDC؛ همان IDs از SQL تا DOM؛ دسترسی B به A باید منفی، refresh بدون duplicate، revoke 401، direct Send بدون موتور بدون durable اثر، و همان Journey پس از Restore مستقل پاس شود.
- معیار باقی‌مانده برای پذیرش این مسیر: شواهد پنج گام، SHA نهاییِ یکسان، image digests، RunID، صورت‌جلسهٔ Ops و ردیف‌های canonical. هیچ پیش‌فرض هزینه/Privacy/RPO/RTO امضا نشده است.

**حد اختیار:** PR آزمایشی، GitHub Actions مجاز؛ هیچ اقدام روی مقصد و هیچ تشخیص خودکار رسمی `ACCEPTED` انجام نشده است.


## تکمیل اجرایی افزوده‌شدهٔ ۲۴ نوامبر — آزمایش HTTP واقعی، نه مرورگر یا IdP مقصد

**منبع:** انتقال بدون ویرایش فایل `apps/api/private_app_only_asgi.py` از PR #80، Git blob `96a72b5167d473c88aeb3ddb5a67a284c105d4dd`؛ این فایل در مبنای PR #84 موجود نبود. پیکربندی موتور فعال نشده و مسیر پیش‌فرض عمومیِ کاندیدای #84 عوض نشده است.

**آخرین SHA اجرایی دقیق:** `afbd07e3f6d0f4d3feb850f8df3e9f9f3b37de4c`.

**CI قطعی روی همان SHA:** [Run 45300381508](https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/45300381508) / `SUCCESS` / یک job با PostgreSQL17.11، نصب کامل 001–010، DB55، TLS نقش‌ها و دو کلاستر جدا. **رسید JSON پاک‌سازی‌شده**: Artifact ID `14877269748`، فایل `ci_receipts/app_only_https_pg_ab_restore.json`. از API Docker image واقعی non-root و listener Uvicorn 0.48.0/H11 در یک namespace خصوصی، TLS1.3/mTLS با CA/SAN و گواهی آزمایشگاهی موقت، RSA/RS256 و جلسات PG 004/005 استفاده شد؛ نه mock ASGI، نه TestClient، نه تزریق route browser. کلیدها، رمز نقش‌ها و pg_dump خصوصی منتشر نشده‌اند.

**تست‌های موفق قابل‌ردیابی در لاگ CI:**
- دو **subject مصنوعی و تأییدنشدهٔ IdP** به دو `owner_id` متفاوت از `auth_l1.map_identity` در PostgreSQL نگاشت، opaque session با همان DB صادر شد؛ دادهٔ مصنوعی A=۵ مکالمه/۴ پیام و B=۳ مکالمه/۲ پیام.
- `/internal/ready` با PG سالم روی همان HTTPS/mTLS برابر `200` است ولی `bootstrap_idp=not_probed`؛ این **readiness واقعی API History/PG در آزمایشگاه** است، نه readiness کل Web+BFF+Bootstrap+IdP.
- `GET /v1/conversations` با اثبات BFF RS256 و 004/005 در DB، لیست، صفحات و شناسه‌های A/B را می‌دهد؛ detail پیام‌ها درست است، B→A و A→B با 404 رد می‌شوند.
- replay همان JTI به 401 می‌خورد؛ اختلاف raw query با JWT و تزریق `X-Owner-Id` به 401؛ cursor امضاشدهٔ A برای B به 404؛ بدون گواهی یا با گواهی leaf اشتباه، ارتباط تأییدشده شکل نمی‌گیرد.
- `POST /v1/messages` در app-only با 503 قبل از ایجاد Send/Attempt/Answer، اثر durable صفر؛ پس از backup/hash و restore به مستقل‌ترین کلاستر، کل History و negative HTTP تکرار شدند.
- Revoke نشست A روی دیتابیس restore با role `auth_revoker`، همان HTTP A=401 و B=200 را داد.
- در **همان listener فعال‌شده**: PG restore سالم `ready=200`، توقف موقت و بی‌تخریب فقط restore-db این آزمایش `ready=503`، راه‌اندازی مجدد همان PostgreSQL `ready=200`؛ هیچ volume موجود و demo لمس نشده است.

**فایل‌های افزوده:** `tests/phase3/integration/api/f3_app_only_https_pg_ab_lab.py`، `infra/postgres/dev_f3_isolated/scripts/28_signed_history_https_pg_lab.sh`، `.github/workflows/f3-app-only-https-pg-ab-lab.yml`، و listener پین‌شدهٔ PR #80. آزمون‌های SQL مستقل 26/27/19/21/24 همچنان در [Run 45291109728](https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/45291109728) روی SHA `f0331f1ba76921c8d0582c1d59ea00965a934ae5` سبز و بدون تغییر در سورس این اسکریپت‌ها باقی‌اند.

**مرزهای بازِ واقعی:** هیچ IdP استاندارد OIDC با دو حساب واقعاً login نشده؛ هیچ callback/کوکی/Next BFF عادی یا Chromium/Safari تا PG اجرا نشده؛ تست signing از کلید **آزمایشگاهی** و نگاشت synthetic است؛ readiness کل محصول، نصب Mac/Arvan، SLO/DR امضاشده، rollback محصول، API lost-ACK/process-crash و RPO/RTO هنوز نیاز به شواهد مستقل دارند. **P0-1…P0-6 به‌طور کامل پذیرفته نشده، DB 5/57 DONE محدود و 0/26 Gates پذیرفته باقی می‌ماند.**

**تحویل نقش‌ها:** Foundation باید SHA کاندیدای #84 را با PR #86 مقایسه و فایل‌های مرتبط را بدون overwrite اعتبارسنجی‌شده روی همان شاخهٔ مشترک منتقل و E2E تک‌Runner Web/BFF/API/Bootstrap/IdP/PG را اجرا کند؛ API باید واقعی‌بودن OIDC و session/epoch در همان تراکنش و خطای 401/404/503 را حفظ کند؛ UI باید دو browser context مستقل و DOM/cookie/revoke را با data IDهای PostgreSQL مرتبط کند؛ DB فقط رسید SQL/mTLS lab و restore ارائه داده است. **هیچ Merge/Release/Deployed/ACCEPTED اعلام نشده است.**
