# گزارش اجرای SPEC-01 — تکمیل نسخهٔ ۱۰۰ نفره و دیپلوی تکرارپذیر آروان

- **مخزن:** `RAG_finance_app`
- **شاخه:** `deploy/arvan-100users-candidate`
- **کامیت مبنا:** `36fa742`

## ۱. خلاصهٔ تغییرات (۵ تسک SPEC-01)

1. **پاک‌سازی کوکی‌های سشن Keycloak در `/api/auth/logout`:**
   - افزودن `apps/web/app/api/auth/logout/keycloak-cookies.ts` برای صدور هدرهای `Set-Cookie` انقضا (`Max-Age=0; Expires=Thu, 01 Jan 1970 00:00:00 GMT; HttpOnly; Secure`) برای `KEYCLOAK_IDENTITY`، `KEYCLOAK_SESSION` و نسخه‌های `_LEGACY` آن‌ها روی مسیر `/realms/finance-staging/` (و معادل بدون اسلش انتهایی)، قابل تنظیم از `AUTH_KEYCLOAK_REALM_COOKIE_PATH` با اعتبارسنجی ضدتزریق هدر.
   - اتصال به `apps/web/app/api/auth/logout/route.ts` با حفظ کامل ابطال سروری، `redirectLocal('/login?reason=logged_out')` و حفاظت CSRF.
2. **خروج تک‌کلیکی از سایدبار چت (با حفظ CSRF):**
   - تولید سرور-ساید `logoutCsrf` در `apps/web/app/history/page.tsx` (و بازصادرات در `apps/web/app/page.tsx`) و انتقال آن به `apps/web/src/ui/product-chat.tsx`.
   - تبدیل لینک خروج سایدبار به فرم `POST /api/auth/logout` با فیلد مخفی `csrf` (`data-testid="sidebar-logout"`) و به‌روزرسانی تست‌های Playwright (`tests/phase3/integration/ui/sidebar_logout_browser.mjs` و `tests/phase3/integration/ui/phase3_auth_demo.py`).
3. **اصلاح ظاهری تم `moshaver-mali`:**
   - حذف خط آبی دوبل ارث‌رسیده از `keycloak.v2` (`border-top: 0` روی `.pf-v5-c-login__main-header` و `--keycloak-card-top-color: transparent !important`).
   - پنهان کردن `.pf-v5-c-form-control__utilities` برای جلوگیری از هم‌پوشانی آیکون قرمز روی فیلد نام کاربری با حفظ نمایش متن خطا.
   - اصلاح آیکون نمودار سه‌میله‌ای صعودی `.mm-badge` با CSS `linear-gradient` روی `direction: ltr` و `left 9px/15px/21px bottom 8px` بدون تگ `<i>` اضافی در پیام‌های `messages_fa.properties` و `messages_en.properties`.
   - یکدست‌سازی سربرگ کارت ورود با پالت جدید.
4. **پالت آبی/زرد لایت‌تر + `direction: ltr` روی `.advisor-mark`:**
   - روشن‌تر و هماهنگ‌تر کردن رنگ‌های آبی (`#f3f8ff`, `#dbeafe`, `#bfdbfe`, `#164173`, `#12355c`) و زرد (`#fff8d9`, `#ead58d`) در `apps/web/app/history/history.css`، `apps/web/app/login/route.ts` و تم `moshaver-mali`.
   - افزودن `direction: ltr` روی `.advisor-mark` (و `.brand-mark` در `/login`) جهت نمایش صعودی چپ-به‌-راست میله‌ها در رابط RTL.
5. **اسکریپت دیپلوی تکرارپذیر آروان و قالب‌های غیرمحرمانه:**
   - ایجاد `infra/arvan-staging/deploy-arvan.sh` (`set -euo pipefail`، `flock`، پشتیبانی از `--dry-run`، Preflight فایل‌های `0600` بدون چاپ، بیلد آفلاین، نصب ۴ unit سرویس `systemd`، همگام‌سازی تم Keycloak، اجرای `realm-sync.sh`، تست `nginx -t` با rollback خودکار، ری‌استارت سرویس‌ها و Post-Deploy Smoke Gate شامل بررسی قفل‌های #143 و mTLS).
   - ایجاد قالب‌های غیرمحرمانه در `infra/arvan-staging/templates/`: `ragfinance.ir.conf`، `idp-staging.ragfinance.ir.conf`، `realm-sync.sh`، `protected-profile-check.py` و `.env.example`.

## ۲. فهرست فایل‌های تغییریافته و جدید

### فایل‌های ویرایش‌شده (۱۰ فایل)
- `apps/web/app/api/auth/logout/route.ts`
- `apps/web/app/history/history.css`
- `apps/web/app/history/page.tsx`
- `apps/web/app/login/route.ts`
- `apps/web/app/page.tsx`
- `apps/web/src/ui/product-chat.tsx`
- `infra/arvan-staging/themes/moshaver-mali/login/messages/messages_en.properties`
- `infra/arvan-staging/themes/moshaver-mali/login/messages/messages_fa.properties`
- `infra/arvan-staging/themes/moshaver-mali/login/resources/css/moshaver.css`
- `tests/phase3/integration/ui/phase3_auth_demo.py`

### فایل‌های جدید (۱۰ فایل)
- `apps/web/app/api/auth/logout/keycloak-cookies.ts`
- `infra/arvan-staging/deploy-arvan.sh`
- `infra/arvan-staging/templates/.env.example`
- `infra/arvan-staging/templates/idp-staging.ragfinance.ir.conf`
- `infra/arvan-staging/templates/protected-profile-check.py`
- `infra/arvan-staging/templates/ragfinance.ir.conf`
- `infra/arvan-staging/templates/realm-sync.sh`
- `tests/phase3/integration/ui/sidebar_logout_browser.mjs`
- `tests/phase3/ui/keycloak-logout-cookies.test.mjs`
- `docs/reports/SPEC-01-arvan-100users.md`

## ۳. نتایج تست و ممیزی (Verification Gate)
- `cd apps/web && npm run lint`: **PASS** (بدون خطا)
- `cd apps/web && npm run typecheck`: **PASS** (`tsc --noEmit`)
- `cd apps/web && TMPDIR=/tmp npm test`: **PASS** (تمام ۱۴۳ تست واحد از جمله `keycloak-logout-cookies.test.mjs`)
- `cd apps/web && npm run build`: **PASS** (بیلد کامل Next.js)
- `node tests/phase3/integration/ui/sidebar_logout_browser.mjs` (با Playwright/Chrome): **PASS**
  - `desktop /: CSRF 403, logout POST 303, cookies removed`
  - `mobile /history: CSRF 403, logout POST 303, cookies removed`
  - `mobile theme CSS: inherited border removed, ascending bars, error text visible`
- `bash -n infra/arvan-staging/deploy-arvan.sh` و `realm-sync.sh`: **PASS**
- `python3 -m py_compile infra/arvan-staging/templates/protected-profile-check.py`: **PASS**
- `infra/arvan-staging/deploy-arvan.sh --dry-run`: **PASS**

## ۴. چک‌لیست امنیتی #143 و بهداشت مخزن
- [x] **mTLS:** حفظ بررسی اجباری گواهی کلاینت روی پورت‌های `18443` و `18444` در `protected-profile-check.py --smoke-mtls`.
- [x] **RS256:** تأیید `defaultSignatureAlgorithm == "RS256"` در `realm-sync.sh` و discovery چک در `deploy-arvan.sh`.
- [x] **PKCE (S256):** تأیید `pkce.code.challenge.method == "S256"` و `S256` در discovery چک `deploy-arvan.sh`.
- [x] **404 مسیرهای حساس:** قفل و اسموک‌تست `404` روی `/internal/`، `/admin/`، `/realms/master/`، `/auth/` و کل ویرچوال‌هاست `idp-staging.ragfinance.ir`.
- [x] **بدون Secret یا فایل `0600`:** هیچ کلید/رمز واقعی در ریپو یا گزارش ثبت نشده است.
- [x] **`docs/codex_execution/`، `docs/PROJECT_STATE.md` و مخزن `RAG_finance`:** دست‌نخورده و خارج از استیج.

## ۵. کارهای باقی‌مانده (اجرای استیجینگ آروان)
1. همگام‌سازی شاخهٔ `deploy/arvan-100users-candidate` به `/opt/rag-finance-staging/phase3/arvan-candidate` روی سرور آروان و برقراری سشن معتبر `kcadm` روی کانتینر Keycloak.
2. اجرای تک‌دستوری دیپلوی به‌عنوان `root`:
   ```bash
   sudo /opt/rag-finance-staging/phase3/arvan-candidate/infra/arvan-staging/deploy-arvan.sh
