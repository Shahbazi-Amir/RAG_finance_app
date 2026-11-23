# وضعیت فعلی راه‌اندازی روی مک

| بخش | وضعیت واقعی |
| --- | --- |
| Docker | PASS. نسخهٔ 28.0.4، چهار CPU و حدود ۵٫۷۹ GiB حافظه. |
| هفت سرویس | ۷ از ۷. پنج healthcheck، آمادگی Keycloak و HTTPS معتبر ingress. |
| پشتیبان و بازیابی | PARTIAL. SHA-256 بایگانی Keycloak تأیید شده و بازیابی کامل همهٔ اجزا در انتظار است. |
| دعوت Staging | BLOCKED. اتصال Gmail STARTTLS از Keycloak تأیید شد. مسیر موقت مدیریت محدود به localhost راه‌اندازی و مرز TLS و ۴۰۱ بررسی شد. ورود اپراتور موجود در پنجرهٔ Chrome تأیید شد. SMTP AUTH و تأیید دریافت پیام در انتظار است. ابزار دعوت روی شاخهٔ اجرایی آماده است. |
| تأیید ایمیل، نشست و Signed BFF | BLOCKED. ورود مرورگری تا فرم Keycloak در checkpoint قبلی مشاهده شد. |
| Product API | PARTIAL. Healthcheck موفق است و درخواست محصول با نشست معتبر در انتظار است. |
| C018 و UI | BLOCKED. هش موتور و متادیتای runtime بررسی شدند. اجرای Retrieval، نمایش منابع، شمارنده‌ها و Refresh آزموده نشده‌اند. |
| آروان | HOLD |
| پذیرش سرپرست | در انتظار |

قدم بعدی، واردکردن App Password توسط صاحب حساب در Email → Authentication → Password، سپس Test connection و تأیید دریافت ایمیل آزمایشی است.

[گزارش فارسی](MAC_FIRST_START_FA.md) · [گزارش HTML](MAC_FIRST_START_FA.html) · [برنامهٔ بازیابی](RECOVERY_PLAN.md)
