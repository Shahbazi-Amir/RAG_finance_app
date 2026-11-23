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
