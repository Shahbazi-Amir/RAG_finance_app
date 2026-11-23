# DB_F3 / APP-ONLY — بیشترین کار قابل اجرا در محیط ایزوله | تحویل یکپارچه 2026-11-23

> **وضعیت:** CI VERIFIED در آزمایشگاه، **NOT TARGET VERIFIED**، **NOT ACCEPTED** برای محصول و Gate. این فایل مجوز merge، استقرار، Mac، فعال‌سازی موتور یا تغییر سیاست نیست.

## 1. هویت دقیق و مبنای منبع

- مخزن: `Shahbazi-Amir/RAG_finance_app`.
- کاندیدای مستقل: [Draft PR #79](https://github.com/Shahbazi-Amir/RAG_finance_app/pull/79)، شاخهٔ `agent/db-f3-unified-app-only-20261123`؛ مبنا Foundation [PR #77](https://github.com/Shahbazi-Amir/RAG_finance_app/pull/77) در `b7c8928e596001de83c5f8dbd1b86284f46a57a9`. به هیچ شاخهٔ فعال یا main merge نشده است.
- **SHA اجرایی نهایی آزموده:** `0094971b9c21f155e1ac394cfa4018ecfd967036`.
- API owner #76 `865adb26fefbdbddf7da173d7680255c4a3b19c2`؛ UI owner #65 `48107fcd5c2c0a68d4b69e6be5ae7c2f9141c4b4`; DB owner #59 code `b3505f545054a7d5eaa745785195403191ad72c8` و مستندات `44421600269d0b9cfa59cea340f337ef1bc997c4`.
- Manifest candidate: `integration/F3_COMPLETION_SOURCE_PINS.json`، blob `18eba3ad2b63dc526da00e12e0036b01eb5ed7de`، **120 source-path pins**. Original pinned SQL 001–010 and installer03 unchanged; optional 011 isolated/skipped; 012+ policy HOLD.
- این شاخه هیچ فایل شخصی/Secret، دیتابیس Mac، volume پذیرفته‌شده، Qdrant، Provider/Gateway یا انتشار عمومی را دست‌کاری نکرده است.

## 2. نتیجه‌های واقعی روی همان SHA

| آزمون | CI / Artifacts | نتیجه | دامنه و محدودیت |
|---|---|---|---|
| یکپارچهٔ API/DB/UI و Security/Supply chain | [45262444733](https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/45262444733)، source/Web SBOM artifact `14861322616` | **4/4 jobs SUCCESS** | app-contracts، Typecheck/Lint/Build، Chromium synthetic، all isolated DB، scan؛ بدون مقصد/موتور |
| PostgreSQL17.11 / DB55 / RLS / Restore | همان [45262444733](https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/45262444733)، 16-file DB artifact `14860852079` | **SUCCESS** | دومین کلاستر و volume کاملاً مستقل؛ 001–010، 9 نقش، 14 FORCE RLS، 10 Ledger، Source/Restore parity |
| واقعی Docker imageهای API و Web + HTTP | [45262444483](https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/45262444483)، artifact `14861356714` | **SUCCESS** | image IDs و اجرای اصل Docker در GitHub ubuntu-24.04، CI-only bases و نه digest مصوب Mac |
| API بدون موتور، CI-only localhost | CI `45262444483` | **LIVE=200, READY=503, SEND=503** | `/health/live` آمادهٔ liveness، `/health/ready` فاقد IdP/PG واقعی، capability retrieval/generation unavailable، عدم خواندن یا ثبت Send |
| داخل کانتینر Python API | CI `45262444483` | **208 PASS، 2 engine filesystem BLOCKED** | حد تست‌ها داینامیک، هیچ C018/API Gateway اجرا نشد |
| Browser/UI owner navigation, RTL, A11y | [45260973922](https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/45260973922) و job UI [45262444733](https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/45262444733) | **PASS** | fixtures با برچسب synthetic؛ نه مرورگر واقعی Login/IdP→SQL |
| DB crash/RTO-bounded lab evidence | Standalone [45260469796](https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/45260469796) و integrated 45262444733 | **PASS در scope محدود** | Postgres restore SIGKILL، WAL restart، committed preserved / uncommitted absent، RLS/DB55؛ نه خرابی ماشین، PITR و SLA مصوب |

## 3. تغییرهای کد و علت رفع ناسازگاری

- Source DB scripts **22–25** از PR #59 وارد کاندیدای Foundation شدند و 16 فایل sanitize شده در هر CI الزامی است. `25_pg_crash_recovery_probe.sh` blob `53e921ce3bfcd907867d663cd61a465dcc6dd7ee`، exporter11 `592fdeeb454dbce78a42b864a9e1d7460c9800ab`؛ installer03 blob `9cc9458c55b82f03811b346259ccf2ae3dce318d`، manifest SQL20 blob `f67f5e985c45ae9b6a6c68417ebc54ba05ec7fdf` / SHA256 `9ff95a59570f5f6c6188479d9c37cf684ef836c599e89d9faa2bb0e17a4946f7`.
- API `no_dispatch_handler.py` blob `62d1b8019b2ffb9a22f66c9a3457674748baef6d`: product_request_id به full T2 Attempt identity متصل شد؛ negative regression `test_full_binding_fence.py`.
- UI #65: RTL/320px، keyboard/focus/skip/inert/resize browser checks؛ `product-validation.ts` با **if/then/else** و نگه‌داشتن `conformsToPinnedSchema` به خاطر سازگاری مصرف‌کنندهٔ پیشین؛ blob `5adada8e18bbd705339118dd3d9c04d9d17c1ce4`. بدون این وصله، PENDING می‌توانست Answer نامعتبر بپذیرد و Typecheck fail می‌شد.
- API Dockerfile: import smoke تبدیل به CMD listener واقعی `apps/api/app_only_asgi.py` blob `42c7c62754265e44acf22ab4af63552a523498f2` شد، ولی فقط وقتی `CI=true`، `GITHUB_ACTIONS=true`، `APP_ONLY_PROFILE=ISOLATED_CI_NO_ENGINE` و `APP_ONLY_PORT=18880` هم‌زمان باشند؛ localhost-only و Host Guard؛ startup غیرمجاز با 78. Unit tests (7) `tests/phase3/api/test_app_only_no_engine_listener.py` blob `aaa6109804a7ff158085aa2ce8f3fda176b8b7f3`. This cannot be the production connected API listener without Ops IdP/DB authority.
- Original API image smoke retained as separate explicit `python -c` test; now all **208** non-engine API tests run inside image. Updated pin registry and full candidate CI to reject regression on exact blob.
- Prior failed CI runs for schema compatibility, fixed test counts, and default TestClient host were retained as failures and corrected by subsequent green exact SHA; none counted as pass.

## 4. شمارش واقعی (بدون تورم)

- **۵۷ DB specialist IDs:** **۵ DONE محدود DB/CI، ۲۸ OPEN، ۲۴ BLOCKED**. ۵/۵۷ = **8.77%** narrow tested DB/CI only, 52/57 = 91.23% not narrowly DONE. `P3M04-A07` DONE DB_CI_ONLY; `P3M10-A10` OPEN pending genuine signed API retry/crash; `P3M22-A09` OPEN pending full machine/Qdrant/IdP encrypted disaster and signed RPO/RTO.
- **262 canonical main IDs** در `coordination/phase3_checklist.md` و `PHASE3_262_ACTIVITY_DB_SCOPE_RECONCILIATION_20261123.csv`: **262/262 unique**, zero difference between source and CSV. **26 module Gates**: 26/26 registered, **0 accepted**. **105 P3OP crosswalk**: 105/105 unique and present, **0 witnessed/accepted operationally**. 393 total registered and no duplicate/missing ID by set comparison; **coverage ≠ acceptance**. Canonical approval for main activities remains Foundation/CENTRAL, not specialist tally. This report does **not** mark any main activity accepted.
- در نبود لیست نسخه‌دار و تصویب‌شدهٔ `app_only_slice` denominator، **درصد app-only** ادعا نشده است. شواهد قابل اجرای app-only (DB, CI browser fixtures, localhost CI listener) از آزمون امنیتی/عملیاتی جدا هستند.
- **موتور و Gate محصول**: `NOT_RUN` و `NOT_ACCEPTED`.

## 5. دقیقاً چه چیزی مانده و مالک/اولین آزمون لازم

| محدودیت | مالک ورودی | اولین آزمون بعد از ارائهٔ ورودی | اثر بر بسته‌شدن |
|---|---|---|---|
| Full genuine Web→BFF→mTLS API/Bootstrap→IdP→PG17, two distinct valid actors, no-engine actual app-only readiness | Foundation + API + UI + Ops | startup from separate authorized candidate, signed OIDC A/B Login, History create/list/detail, 404 cross-owner, revoke 401 and DB/HTTP correlators **same transaction** | P0-2/3/4، M05/M06/M13/M14/M15 |
| Actual durable API retry after lost ACK / process crash | API + DB | same `product_request_id` via signed HTTP, kill/restart API, assert exactly one committed Send/Attempt, no engine spawn | P3M10-A10 (still OPEN) |
| Consent/Withdrawal, Answer-linked Feedback, Delete/Tombstone/Export/Retention owner-approved policy | Product + API + Security + DB | approve versioned contract+FK/RLS/legal retention, then 012+ clone migration up/down and cross-owner restore negatives | P3M04/15/21, 012+ remains HOLD |
| Off-host encrypted backup, key custody, deletion non-resurrection, real RPO/RTO and PITR/topology | Ops + Security + employer | authorized independent destination volume backup/restore, full app/IdP/Qdrant E2E replay, timed failure drill vs numeric signed thresholds | P3M22-A04/05/07/08/09/10, Gate22 |
| Canonical integrated product decision and signed Mac receipts | Foundation/CENTRAL | compare ancestor/pins and merge only to another **isolated** candidate, record image/source SHA and actual UAT; no live deployment | P0-1/5/6 final acceptance |
| Engine knowledge Release/C018/C011 genuine evidence | Phase2/Engine (future explicit task) | inspect accepted NB23 Release/manifest/hash/provenance; run retrieval after separate user instruction | Gate00/engine-dependent ID only, **excluded now** |

## 6. بازتولید بدون تغییر مقصد

```bash
git fetch origin agent/db-f3-unified-app-only-20261123
git checkout --detach 0094971b9c21f155e1ac394cfa4018ecfd967036
python3 -m pip install --require-hashes --only-binary=:all: -r locks/requirements-api.lock
python3 -m unittest discover -s tests/phase3/api -p 'test_*.py' -v
python3 -m unittest discover -s tests/phase3/contracts -p 'test_*.py' -v
npm ci --prefix apps/web --no-audit --no-fund
npm --prefix apps/web run typecheck
npm --prefix apps/web run lint
npm --prefix apps/web run test
npm --prefix apps/web run build
```

For isolated real Docker PG & independent restore, execute `.github/workflows/f3-db-isolated-fresh-install.yml` on this **exact branch/SHA** in GitHub Actions; that workflow safely prepares a newly generated `LAB_ROOT`, Docker project, network and volumes and executes pinned `00,01,02,03,03,04,05,09,06,10,22,13,12,14,15,23,24,16,17,19,20,25,21,11` in sequence. Do **not** reuse Mac demo volumes. Image test: `.github/workflows/f3-m18-m19-real-image-http.yml`. Same-SHA unified CI: `.github/workflows/f3-completion-exact-source.yml`.

**Disposition:** `CI_VERIFIED_ISOLATED_CANDIDATE`, `TARGET_VERIFIED=NO`, `ACCEPTED=NO`. Product engine and server are separate future missions, no accidental activation. Human Ops authorization and product policies remain required. This is **بیشترین کار قابل اجرا روی این محیط**، نه «تکمیل کل فاز سه».
