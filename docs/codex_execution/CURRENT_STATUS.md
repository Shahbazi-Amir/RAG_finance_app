# وضعیت فعلی راه‌اندازی روی مک

| بخش | وضعیت واقعی |
| --- | --- |
| Docker | PASS. نسخهٔ 28.0.4، چهار CPU و حدود ۵٫۷۹ GiB حافظه. |
| هفت سرویس | ۷ از ۷. پنج healthcheck، آمادگی Keycloak و HTTPS معتبر ingress. |
| پشتیبان و بازیابی | PARTIAL. SHA-256 بایگانی Keycloak تأیید شده و بازیابی کامل همهٔ اجزا در انتظار است. |
| دعوت Staging | BLOCKED. اتصال Gmail STARTTLS از Keycloak تأیید شد. تنظیم و ارسال ایمیل به مسیر مدیریت خصوصی تأییدشده و اپراتور مجاز نیاز دارد. ابزار دعوت روی شاخهٔ اجرایی آماده است. |
| تأیید ایمیل، نشست و Signed BFF | BLOCKED. ورود مرورگری تا فرم Keycloak در checkpoint قبلی مشاهده شد. |
| Product API | PARTIAL. Healthcheck موفق است و درخواست محصول با نشست معتبر در انتظار است. |
| C018 و UI | BLOCKED. اجرای Retrieval، نمایش منابع، شمارنده‌ها و Refresh آزموده نشده‌اند. |
| آروان | HOLD |
| پذیرش سرپرست | در انتظار |

قدم بعدی، مجوز صریح مسیر TLS موقت محدود به localhost و معرفی اپراتور دارای دسترسی فعلی Realm است.

[گزارش فارسی](MAC_FIRST_START_FA.md) · [گزارش HTML](MAC_FIRST_START_FA.html) · [برنامهٔ بازیابی](RECOVERY_PLAN.md)
