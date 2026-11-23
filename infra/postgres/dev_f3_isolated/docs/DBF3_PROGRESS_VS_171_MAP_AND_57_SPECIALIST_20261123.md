# DATABASE_F3 — نقشهٔ اجرایی، پیشرفت شمارش‌شده و مانده‌ها
**تاریخ:** 2026-11-23 | **وضعیت:** Source-only and isolated PostgreSQL CI PASS; module Gate and real Mac acceptance NOT_GRANTED. **PR:** https://github.com/Shahbazi-Amir/RAG_finance_app/pull/59 (Draft)

## ۱. مخرج و درصد
طبق نقشهٔ کامل ارسالی `02_DATABASE_F3_ROADMAP_CHECKLIST_DONE_REMAINING_FA(1).md`، مجموع وابستگی‌های مستقیم و مشترک **۱۷۱ ID در ۱۷ ماژول** است؛ همان فایل Snapshot خود را `108 PARTIAL + 43 NOT_RUN + 20 NOT_VERIFIED` ثبت می‌کند. این سه برچسب **وضعیت پذیرش/Done نیستند**. سهم تخصصی دقیق DBA با ممیزی شاهدی ردیف‌به‌ردیف **۵۷ ID یکتا** است و این IDها در ۱۷۱ مورد تکرارشماری نمی‌شوند.

**DONE محدود DB/CI = ۴/۵۷ = ۷٫۰۲٪؛ باقی = ۵۳/۵۷ = ۹۲٫۹۸٪ (۲۹ OPEN و ۲۴ BLOCKED).** هیچ عددی بابت PASS تست، مستندسازی یا دریافت Artifact به صورت خودکار به DONE افزوده نشده است. Gateهای ۲۶گانه مستقل و در اختیار CENTRAL/Foundation هستند.

| ماژول تخصصی | DONE محدود | OPEN | BLOCKED | درصد محدود |
|---|---:|---:|---:|---:|
| M03 contracts مشترک | 0 | 8 | 1 | 0٪ |
| M04 schema/migrations | 2 | 4 | 3 | 22.2٪ |
| M06 tenant/RLS | 0 | 7 | 2 | 0٪ |
| M10 orchestration مشترک | 0 | 3 | 7 | 0٪ |
| M15 history/feedback مشترک | 0 | 5 | 5 | 0٪ |
| M22 backup/DR | 2 | 2 | 6 | 20٪ |
| **جمع** | **۴** | **۲۹** | **۲۴** | **۷٫۰۲٪** |

**هر ۵۷ ID و شرط باقی‌مانده:** `docs/PHASE3_57_ROW_DATABASE_AUDIT_20261123.md` و `docs/PHASE3_57_ROW_INDEPENDENT_RE_REVIEW_20261123.csv`; هر ۵۷ مورد با تست بعدی مشخص از پیش بررسی شده است. رجیستر رسمی `coordination/phase3_checklist.md` را DATABASE_F3 به جای مالک آن ویرایش نکرد.

## ۲. آخرین SHAها و Diff اجرایی واقعی

- Baseline قدیمی DB: `0e301a26096cb9f8c2b8e3fde3e20e9a1add48a5`.
- DB base اجرایی با Ledger hardening: `996dfc9b66cf8cbd4b37b7a267d08cc5acd5deba`; [CI 45202743968](https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/45202743968) **SUCCESS**.
- **CURRENT tested executable DB**: **`76822ac273c3f5defbb7e5cd77d497f8d3305852`** — [CI 45218702399 SUCCESS](https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/45218702399), [12-file sanitized artifact 14839553522](https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/45218702399/artifacts/14839553522). New script 21 uses actual History Repository keyset anchors and two-owner PG insert race, with zero cross-owner rows.
- Prior tested executable DB: **`6d2339bc45ce52b4f60a50ced0bb04b588ba3748`**; [CI 45216830775](https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/45216830775) **SUCCESS**, [sanitized artifact 14839885728](https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/45216830775/artifacts/14839885728).
- HEAD of PR #59 includes additional docs-only commits after tested SHA; consult GitHub PR exact HEAD separately. Source-tested should NOT be silently replaced with docs HEAD.
- New DB code blobs: `scripts/19_history_rls_negative_matrix.sh@5d26843eaa129c923c4275e558c60627c15018c9`; `scripts/20_backup_integrity_corruption_probe.sh@d7e5e1cb4bb0b04cf86e87e3eb8a232da78fc391`; `scripts/11_export_sanitized_receipt.sh@f3542ec51b7a5c7bea84bccb42e7eb894f804a55`; workflow `.github/workflows/f3-db-isolated-fresh-install.yml` retested with this exact SHA. Installer 03 `9cc9458c55b82f03811b346259ccf2ae3dce318d` and all original 20 001–010 SQL, manifest `9ff95a59570f5f6c6188479d9c37cf684ef836c599e89d9faa2bb0e17a4946f7` and PG image unchanged.
- On tested old/new DB 0e301a and 996dfc9, [CI 45209570132 PASS](https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/45209570132): two separate actual install + independent restore/source cluster pairs on one isolated runner, four PG system IDs. No real Mac/HTTP.
- **Currently observed integration** `integration/f3-ui65-db996-phase3-20261123@c488837b378d67ddde624dcd2a185e62fccbc30f`: old 001–010/03 pins present, but scripts 19/20 **absent**, 11 is **old blob** `9f0908fef1f93dd66856fde6285ea5a60031aab2`, `integration/F3_SOURCE_PINS.json` says stale tested `57b5d007...` and head `db14943d...`. For latest specialty subtree source tested 6d2339 **38/51 blobs identical, 13 different/missing** (includes documents). **Foundation repin REQUIRED**, no Mac deployed SHA attested.

## ۳. کارهای اجرایی اضافه‌شده و آزمون واقعی
1. **19, M04/M06/M15:** ۲ Owner synthetic، ۶ جدول History all FORCE RLS، هر Actor فقط یک ردیف خود، بدون Owner صفر، تغییر Title مالک مجاز و مالک دیگر ۰؛ هفت مورد منفیِ جاعل Owner، FK نادرست، تغییر متن/Answer بدون GRANT، DELETE ممنوع و duplicate send **۷/۷ PASS** در PostgreSQL 17.11 واقعی CI. کپی دورریختنی پاک شد. در همان Test ثابت شد اگر یک کلاینت مستقیم **خود credential نقش history_app** را داشته باشد، می‌تواند GUC `app.owner_id` را SET کند؛ بنابراین **signed BFF/IdP same-transaction session actor fence هنوز NOT_PROVEN**. این آزمایش جایگزین L2 نمی‌شود.
2. **20, M22-A09:** روی Backup اصلی CI که قبلاً مستقل Restore شده، تغییر یک بایت و قطع فایل هر دو SHA-256 ورودی را **۲/۲ FAIL-CLOSED قبل از Restore** کردند. نسخهٔ سالم و دو Cluster اصلی تغییری نکردند. هیچ خراب‌داده‌ای به PG Restore داده نشد؛ **تمام‌خرابی/DR/PITR/کلید رمزگذاری/RPO/RTO و anti-resurrection هنوز بازند**.
3. **21, M15-A03/M06-A09**: Cursor DESC مکالمه و ASC پیام در SQL واقعی PostgreSQL دقیقاً مطابق `src/phase3/storage/postgres/repository.py@14f97dd680425b74f8e12fa1696d423a20bf7d76`، با INSERT بین صفحات، anchor ثابت، ۲ مالک و صفر نشت؛ CI 45218702399 PASS. **Cursor API HMAC/HTTP و SLO واقعی هنوز NOT_RUN**.
4. صادرکنندهٔ 11 اکنون از 19/20/21 نیز JSON معتبر می‌خواهد؛ **۱۲ فایل sanitized** صادر شد. ترتیب کامل: `00→01→02→03→03(no replay)→04→05→09→06→10→13→12→14→15→16→17→19→20→21→11`. دستور و شروط فایل `contracts/DBF3_EXACT_PINS_SCRIPT11_PREREQUISITES_20261123.md`.
5. شواهد ردیف‌های مرتبط در `docs/PHASE3_57_ROW_DATABASE_AUDIT_20261123.md` افزایش یافت؛ **هیچ ردیف به‌صورت بی‌مدرک ACCEPTED نشده است**.

## ۴. مسیر ادامهٔ ردیف‌های باز تا Gate
| ترتیب | تصمیم/کار مانده | مالک | آزمون پذیرش لازم |
|---|---|---|---|
| P0 | یکسان‌سازی integrated/source pins و نصب candidate مستقل | Foundation/Ops | 19/20 و 11 در همان immutable source؛ TLS CA/SAN، ۹ نقش Product+Bootstrap از Process اصلی، Ledger و independent Restore در Mac candidate |
| P0 | ثبت Owner هویت‌سنجی‌شده/epoch/revoke در همان SQL transaction و deny GUC/worker abuse | API+Security+DB | signed BFF/IdP واقعی دو حساب، same-TX A/B + 404/401 و revoked/hostile owner context منفی |
| P0 | Consent/withdraw، Feedback روی committed Answer، Audit و Export مستقل | API+Owner+Security+DB | نسخهٔ مصوب قرارداد، SQL 012+ جدا، FK/RLS/grants/negative tests، سپس real HTTP |
| P0 | Citation/Attribution و Knowledge/Model/Policy/T3 lineage | ENGINE+API+DB | Release/NB23 پذیرفته، Locator verifiable، عدم جعل source ID و مصرف end-to-end |
| P0 | ضدبازگشت حذف داده از Restore قدیمی | Owner+Security+Ops+DB | policy signed tombstone outside backup، predelete dump→delete→restore quarantine→negative A/B |
| P0 | Backup عملیاتی و Qdrant/PITR/RPO/RTO | Ops+Security+Owner | رمزگذاری و custody تأییدشده، retention، Qdrant no-write snapshot، اندازه/بار و RPO/RTO عددی، DR کامل |
| P0 | L2 No-dispatch and Gate | Foundation+Ops+API+CENTRAL | HTTPS OIDC واقعی؛ POST 202 / T1-T2 / CONTEXT_READY / exactly one permitted C018 OS spawn, GET-only Refresh, 404/401، سپس قبول مستقل |
| P1 | بار و performance نماینده | Owner+Ops+DB | workload frozen, p50/p95/p99, PG pool, index plan under approved data scale and SLO |

**محدودیت صریح:** accepted Mac demo DB `rag_finance_f3_demo` و Volume `rag_finance_f3_demo_pg17_20261121` نباید تغییر کنند؛ 011 Claim راه جدا، no-dispatch همچنان حاکم؛ هیچ Gateway paid/Arvan/Production/Source rewrite مجاز نشده. DB-only CI کد و شاهد تولید می‌کند، **مجوز اجرای مک/مهاجرت واقعی یا Gate نهایی صادر نمی‌کند**.

---
## چرخهٔ اجرایی تازه DATABASE_F3 — پذیرش فنی محدود 2026-11-23

**مرجع شروع:** SHA آزموده 76822ac273c3f5defbb7e5cd77d497f8d3305852 (CI 45218702399 PASS)، HEAD مستندات 23095db370247b12a8c31c70ed6db5de09f1ca57 (فقط سه فایل مستندات جلوتر، طبق Git compare). **نسخهٔ اجرایی جدید آزموده و موفق:** 24b4def0efd16f33d3a8391a479978c0846490aa، [CI 45226799736 — SUCCESS](https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/45226799736)، [۱۳ رسید پاک‌سازی‌شده، Artifact 14842991989](https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/45226799736/artifacts/14842991989). هر دو job: isolated-pg17 SUCCESS، optional-post010-011 SKIPPED. محیط: GitHub Actions Ubuntu 24.04، Docker PostgreSQL 17.11، دو کلاستر/Volume کاملاً ایزوله و یک کپی صرفاً آزمایشی در کلاستر Restore؛ بدون مک، HTTP، Gateway، C018، هزینه و دسترسی به DB/Volume قدیمی.

**تغییر واقعی:** script 22_restore_catalog_parity_probe.sh افزوده شد؛ اثرانگشت ساختار، ستون‌ها، constraint/FK، index، RLS policies، function definitions، مالک و مؤلفه‌های ACL، پرچم ۹ نقش و مجوزهای مؤثر SELECT/INSERT/UPDATE/DELETE و EXECUTE را بین کلاستر source و restore می‌سنجد. NULL بودن relacl در pg_restore با owner-default واقعی PostgreSQL (acldefault) مقایسه می‌شود، نه با bytes خام غیریکسان. ساختار منبع و Restore برابر و آزمون‌های تشخیص NO FORCE RLS و DISABLE RLS روی یک کپی جدید هر دو PASS شدند. کپی آزمایشی حذف شد، source و restore تغییر نکردند. صادرکنندهٔ 11 سخت‌گیرانه اعتبارسنجی می‌کند و سیزدهمین JSON sanitize شده را اضافه می‌کند؛ workflow 22 را بلافاصله بعد از restored preflight اجرا می‌کند.

**یافتهٔ فنی:** در ابتدا هشت جدول auth_l1 در مبدأ relacl صریح owner-only و در Restore مقدار NULL/owner-default داشتند؛ چون PostgreSQL رفتار پیش‌فرض ACL را می‌پذیرد، raw text هرگز معیار درستی برای برابری مجوز مؤثر نبود. پس از canonicalization، ۱۴ جدول فعال و مجوزهای بررسی‌شده برابر شدند. این آزمون صحت سیاست امنیتی کامل API یا تمام نقش‌های آینده را اثبات نمی‌کند. شکست‌های CI در اجرای اولیه برای marker خالی، cast نوع داخلی char و ACL خام در [45224252235](https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/45224252235)، [45224616716](https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/45224616716)، [45225014547](https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/45225014547)، [45225516482](https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/45225516482)، [45226055071](https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/45226055071) و [45226501541](https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/45226501541) ثبت شدند؛ نتیجهٔ نهایی فقط CI 45226799736 است. شواهد ناموفق حذف یا PASS نامیده نشده‌اند.

| ID | وضعیت قبلی → جدید | تغییر کد و تست | SHA آزموده | محیط/رسید | مانده و مالک/ورودی |
|---|---|---|---|---|---|
| P3M04-A02 | OPEN → OPEN؛ شواهد ارتقا یافت | source/restore constraints/index fingerprint؛ بدون اندازه‌گیری SLO | 24b4def0 | PG17.11 isolated؛ CI 45226799736 | DB+Foundation: بار و threshold مصوب و query plan نماینده |
| P3M06-A01 | OPEN → OPEN؛ شواهد ارتقا یافت | 14 جدول FORCE RLS، دو drift منفی تشخیص داده شد | 24b4def0 | 2/2 negative in disposable clone؛ CI 45226799736 | API+Ops: signed same-TX owner/session واقعی، A/B 404/401 |
| P3M06-A02 | OPEN → OPEN؛ شواهد ارتقا یافت | ACL canonical با PostgreSQL owner-default، ۹ نقش effective grants و policies | 24b4def0 | source/restore parity PASS، CI 45226799736 | API+DB: role/worker/caller adversarial live authorization suite |
| P3M22-A06 | DONE محدود DB/CI → DONE محدود DB/CI؛ شاهد تقویت شد | restored independent schema/ACL/function parity و negative drift؛ نه full DR | 24b4def0 | 13-file artifact 14842991989 | SERVER/Ops: Mac مستقل مجاز، داده و محل حقیقی، RPO/RTO امضاشده |
| P3M22-A09 | OPEN → OPEN؛ شواهد ارتقا یافت | catalog-only injected RLS drift detected؛ سناریوی بحران واقعی نیست | 24b4def0 | 2/2 drift detection، CI 45226799736 | Ops/Security: failure drill و Recovery، PITR در صورت مصوبه |

**منابع پین‌شده:** installer 03 Git blob 9cc9458c55b82f03811b346259ccf2ae3dce318d، manifest 20 SQL Git blob f67f5e985c45ae9b6a6c68417ebc54ba05ec7fdf، SHA256 کل manifest 9ff95a59570f5f6c6188479d9c37cf684ef836c599e89d9faa2bb0e17a4946f7 بدون تغییر. Script 19 blob 5d26843eaa129c923c4275e558c60627c15018c9، 20 blob d7e5e1cb4bb0b04cf86e87e3eb8a232da78fc391، 21 blob 8732a4788cb3ecf821c15d811119f8cacc3eedd1، 22 blob 5869b15413d058acb2424199d8fcaa9d274f822c، صادرکننده 11 blob 5872c2554c7704bda0eab97c6230b9a77c1c28eb، workflow blob ca1dbca48727f2b5786e90663e98289106773215.

**Foundation integrated comparison:** آخرین snapshot بررسی‌شدهٔ Foundation f7d738aa763179eba28c7847e6225640bb88b176 هنوز 03 و manifest منطبق دارد ولی script 11 قدیمی با Git blob 9f0908fef1f93dd66856fde6285ea5a60031aab2 و scriptهای 19/20/21/22 غایب‌اند. پس یکسان بودن تعدادی از blobهای تاریخی 001–010 به معنای repin کامل یا admission نیست؛ Foundation باید برای همان integrated SHA و pipeline مستقل نسخهٔ واقعی را ثبت و CI تازه بگیرد. integration/F3_SOURCE_PINS.json نسخهٔ مشاهده‌شده نیز metadata قدیمی DB دارد؛ بدون بازبینی owner تغییر نده.

**شمارش پس از چرخه:** ۴ DONE محدود / ۲۹ OPEN / ۲۴ BLOCKED، یعنی **۴/۵۷ = ۷٫۰۲٪** و **۵۳/۵۷ = ۹۲٫۹۸٪ مانده**. از ۱۷۱ ردیف مشترک دوباره‌شماری نشده است؛ Gate/ACCEPTED جدیدی ثبت نشده. برنامهٔ بعدی: (۱) Foundation/Ops repin+isolated Mac candidate source-bound، (۲) API/Security signed owner/epoch/revoke same-TX و قرارداد consent/feedback/hard-delete، (۳) Ops سیاست Backup رمزگذاری‌شده، retention و RPO/RTO مصوب، (۴) Engine Release/NB23 و provenance؛ تا رسیدن ورودی، مسیر 011، 012+ و هر dispatch بیرونی مستقل و HOLD هستند.


---
## جدیدترین چرخهٔ پذیرش محدود DB/CI — P3M04-A07 بسته شد

**Before:** 4/57 = 7.02% (29 OPEN, 24 BLOCKED). **After successful exact-SHA CI 45233599373:** **5/57 = 8.77% (28 OPEN, 24 BLOCKED)**. Net **+1 DONE / +1.75 percentage points**, only in 57 specialist DB/CI tasks; **module/product Gate remains NOT_ACCEPTED**. Not 5/171, no acceptance in official Foundation-owned register.

| ID | قبلی → جدید | شرط محقق‌شده | کد واقعی | SHA / آزمون | مانده و مالک |
|---|---|---|---|---|---|
| P3M04-A07 | OPEN → **DONE محدود DB_CI_ONLY** | empty 10x DOWN/UP roundtrip canonical schema SHA equal; new Ledger 10, 14 FORCE RLS/DB55; separate populated owner A/B sessions 009–010 upgrade/restore in independent PG | script 23 + workflow + exporter 14th receipt; SQL 001–010 untouched | [CI 45233599373 PASS](https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/45233599373) executable `48110525aa9ac118b6b3749c956930c61cec11fe`, artifact `14848595915` | Foundation/Ops/CENTRAL: Mac L2, approved production data-bearing rollback, full Phase3 migration, signed Gate **still open** |

The 14th sanitized receipt is `m04_migration_full_cycle_receipt.json`. Full destructive reversal was restricted to EMPTY disposable clone; real populated 001/003 down prohibited. Prior failed CI runs are preserved in Actions and not treated as passing. **Executable pins**: script 23 `a547a58ac1555795dd73c18415973bbc955177d8`, script 11 `b9dff8a9f736d36af3916900995afb798826b3e5`, workflow `dadd5ec47d8f312b7de35533241c275961195821`, 03 unchanged `9cc9458c55b82f03811b346259ccf2ae3dce318d`, 20-SQL manifest unchanged `f67f5e985c45ae9b6a6c68417ebc54ba05ec7fdf` / SHA256 `9ff95a59570f5f6c6188479d9c37cf684ef836c599e89d9faa2bb0e17a4946f7`.

**Next executable candidate:** P3M10-A10 concurrent duplicate/replay boundary and P3M04-A02 representative constraint/query plan. Do NOT label DONE without actual version-bound CI and API/owner acceptance required by their row; migration 012+ and Consent/Feedback/deletion remain on policy HOLD. Prioritized [29 original OPEN IDs](DBF3_M04_A07_CLOSURE_AND_NEXT_29_OPEN_QUEUE_20261123.md) (one now closed).


---
## Subsequent executable run after closing M04-A07: M10-A10 still OPEN

[CI 45234862871 PASS](https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/45234862871) on exact executable `f302fbf0f4a00ae4fe80d914452906fe88029078`, 15-file sanitized artifact `14849265819`. Script 24: two concurrent client DB transactions, one winner/one unique denial, simulated lost-ACK duplicate denied, exact same key accepted under separate owner, RLS each sees one, second attempt per Send denied; **real signed API HTTP retry, process crash and IdP actor boundary NOT_RUN**. M04-A07 passes again in this newer run. Keep **P3M10-A10 OPEN→OPEN**. Progress remains **5 DONE limited / 28 OPEN /24 BLOCKED =8.77%**; prior 4/57=7.02%, net +1/57=1.75 percentage points (ONLY M04-A07). Product/Mac Gate still NOT_ACCEPTED. Latest pins script24 `395078707143c85de2d8f58c0b365445176bbf6a`, exporter11 `8ac7ea78dee35bcd90d3fff066a56cc8f06bae23`, workflow `4701c68b3159557b290a2bb96315ae7928cc5a36`, script23 `a547a58ac1555795dd73c18415973bbc955177d8`.
