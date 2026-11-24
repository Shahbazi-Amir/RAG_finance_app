# Execution log

## 2026-11-23 / CODEX-REPORTING-01

- Recorded the [starting baseline](BASELINE.md) and [sanitized backup assessment](BACKUP_STATUS_FA.md). Historical reports from both existing backup revisions were reviewed. No new restore or runtime test was performed.
- `git status --short --branch`, `git rev-parse HEAD`, `git remote -v` and `git worktree list` identified the clean detached workspace and the Phase 3 destination.
- Sandboxed GitHub access failed. The approved retry with `gh repo view` confirmed the non-fork repository and ADMIN permission. `git ls-remote --heads origin refs/heads/codex` returned no matching branch. A separate worktree was created from the observed starting SHA.
- Added the report index, baseline, log, Persian assessment, recovery plan and current status. Publication is tracked by Git history and verified against the remote branch ref at delivery.
- Roadmap references are P3M22-A06 and P3OP11-R07 for the recovery evidence. No gate or checklist progress is claimed. Supervisor acceptance is pending.
- Historical recovery issues included an unavailable Docker socket, incompatible compression and read-only extraction permissions. The local reports record a successful second Docker capture and successful rechecks of all six base archives after corrections.
- Generated the Persian HTML in the secure backup folder. The renderer checked UTF-8 round-trip and three table rows (header and two data rows). macOS `open` exited successfully.
- Staged only the six report Markdown files and the mission checkpoint. Review used `git diff --cached --check` and `git diff --cached --name-status`.

## Docker_3 / NB23-SESSION-RESUME-09

- بازیابی checkpointهای محلی ۰۱ تا ۰۹ و نتیجهٔ HTTP Callback، آزمون مالک دوم و restore منطقی با خروج ۰. Chrome Stable و Canary در DevTools timeout داشتند.
- مقایسهٔ Python روی ۱۰۲ مشاهدهٔ ONNX و شش مشاهدهٔ مشترک Native نتیجهٔ MatMulInteger شاخهٔ ۱ را محدود کرد. AST هر ۱۶ فایل Python و git diff --check موفق بود. قبلاً بازبینی خودکار با 404 متوقف شد؛ در این نوبت فهرست Docker و فرایندها از مسیر مجاز خوانده شد.
- وضعیت شمارش ۲/۲۰ → ۴/۲۰. [فهرست کد، خطاها، آزمون‌ها و ادامه](MAC_FIRST_START_FA.md#docker_3--بازیابی-پس-از-انتقال-حساب)

## NB23-SESSION-RESUME-10

- Docker exact-attention خروج ۰. عملوند چپ متفاوت، راست و هر دو zero point برابر، ضرب دقیق در هر دو محیط با صفر خطا. probe برای ورودی/خروجی Softmax گسترش یافت. افزایش پیشرفت صفر.

## NB23-SESSION-RESUME-11

- جفت Softmax خروج ۰، دو کنترل logits برقرار، ورودی برابر و خروجی متفاوت. فعالیت ۱۰ تکمیل شد.
- بازیابی DB روی tmpfs، تشخیص مجوز EXECUTE و اجرای سه GRANT محافظت‌شده، Chrome CDP روی صفحهٔ خالی خروج ۰. آزمون Browser E2E هنوز آغاز نشده است.

## NB23-SESSION-RESUME-12

- BFF و Bootstrap جداشده بازسازی شدند و هر دو HTTPS با TLS=0 پاسخ ۲۰۰ دادند. Chrome Page.navigate timeout داد. بازبینی آزمون navigation تغییرکرده HTTP 404 داد.
- Docker Softmax-reference خروج ۰. گزینهٔ نامزد دقت دوگانه برای یک Batch اضافه شد. پیشرفت بدون تغییر.

## NB23-SESSION-RESUME-13

- Native float64 reference خروج ۰، دو کنترل و fingerprintهای قبلی برابر. بازبینی Docker candidate و اولین تلاش انتشار گزارش تکمیلی با HTTP 404 خاتمه یافت. آزمون نامزد Native آغاز شد.

## NB23-SESSION-RESUME-14

- نامزد Native FP64 خروج ۰، کنترل‌ها برقرار، ولی اختلاف جدید logits برابر ۰٫۳۱۳۶۶۴۹۱۳۱۷۷۴۹۰۲۳. نامزد پذیرفته نشد و Golden کامل آغاز نشد. تلاش دوم commit/push در بازبینی خودکار HTTP 404 داد.

## NB23-SESSION-RESUME-15

- بازبینی Docker موفق شد. مسیر Worker آفلاین و API ایزوله پیاده شد. بررسی کد و سه fixture موجود موفق بودند. fixture سوکت sandbox-denied. آماده‌سازی PostgreSQL آغاز شد.

## NB23-SESSION-RESUME-16

- شروع پشته مستقل و HTTPS معتبر پس از گرم‌شدن Keycloak. چهار fixture موفق. Chrome Callback و History موفق؛ SEND_BUTTON_NOT_ENABLED قبل از POST. Harness با readiness و مسیر دو پرسش به‌روز شد.
