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
