# ADR 0004 — Auth واقعی محصول: مقایسهٔ دو معماری و پیشنهاد مشروط

**Status: PROPOSED / READY_FOR_REVIEW — SELF_HOSTED_AUTH_PLAN; NOT AUTH_IMPLEMENTED, NOT PRODUCTION_READY.**
**Date / official-source check:** 2026-11-08. **Mission:** AGENT-API-AUTH-PLAN-01; **starting main:** `9d5f2f9adc8e4522ec8cf4ffd397ba0a815e8fb7`; branch `prep/auth-decision`.
**Decision owner:** کارفرما/ناظر؛ ترجیح‌های کارفرما در §8 تثبیت شده‌اند، نه انتخاب فنی/پذیرش. این ADR هیچ ارائه‌دهنده، حساب، قرارداد، منطقه، هزینه یا امنیت Production را تصویب نمی‌کند.

## 1. زمینهٔ واقعی و رابطه با ADR 0003

- [ADR 0001](0001-architecture-proposal.md) انتخاب محدود **Next.js + TypeScript / FastAPI / PostgreSQL / Modular Monolith** را ثبت کرده؛ نه Auth و نه استقرار.
- [ADR 0003](0003-history-persistence-proposal.md) زیر «Auth choices for employer» دقیقاً **A = OIDC استاندارد + Authorization Code/PKCE + Backend/BFF session** و **B = first-party credentials + secure server-side sessions** را پیشنهاد کرده و H-DEC-01 را باز گذاشته است. ADR 0004 **متمم تصمیم‌ساز** است؛ گزینهٔ سومی یا تغییر بی‌مجوز به ADR 0003 نیست.
- PR [#9](https://github.com/Shahbazi-Amir/RAG_finance_app/pull/9) صرفاً PostgreSQL 17.11 موقت با هویت مصنوعی/RLS و آزمون‌های مصنوعی، PR [#10](https://github.com/Shahbazi-Amir/RAG_finance_app/pull/10) FastAPI با dependency پیش‌فرض **401** و هویت تزریقی فقط در تست، PR [#11](https://github.com/Shahbazi-Amir/RAG_finance_app/pull/11) اتصال UI/API/DB فقط با Harness ایزوله و Proxy محدود CI را با **پذیرش محدود** ادغام کرده‌اند؛ هیچ‌کدام ورود واقعی، استقرار عمومی، اتصال مدل یا Gate را نمی‌پذیرند. مرز `product.v1` و original-null/idempotency نباید در Auth تغییر کند.
- نقشهٔ دقیق: Module 05 «identity_and_session» فعالیت‌های `P3M05-A01..A10` (روش ورود، hashing مشروط، session rotation، Cookie، CSRF، lockout، خروج/ابطال، انقضا، security event و آزمون منفی سرقت نشست)، Module 06 `P3M06-A01/A02/A03/A07` (RLS و transaction context)، Module 13 `P3M13-A08` (Authorization هر Endpoint)، Module 14 `P3M14-A01` (Login + session UI)، Module 15 `P3M15-A07` (no cross-user data)؛ overlays عملیاتی شمارش پیشرفت جدید نیستند. **همهٔ آزمون‌های Auth واقعی = NOT_RUN.**

## 2. الگوی مشترک امن پیشنهادی؛ مستقل از IdP

```text
Browser (no provider tokens / no owner selection)
    ↕ TLS, same-origin __Host- session cookie + CSRF
Next.js server / BFF  ↔ session store (server-side, revocable, opaque verifier)
    ↕ private authenticated, explicitly trusted server-to-server channel
FastAPI trusted identity dependency → internal stable owner_user_id
    ↕ per-transaction owner scope, non-BYPASSRLS app role
PostgreSQL RLS → existing History repository
OIDC case only: BFF ↔ HTTPS OIDC issuer / discovery, auth code+PKCE, validation
```

این یک **طرح** است، نه مسیر موجود و نه مجوز ایجاد سرویس. مسیر فعلی UI `/api/history` فقط در CI/loopback کار می‌کند؛ جایگزینی آن با BFF واقعی مأموریت جدا می‌خواهد.

قواعد مشترک: Cookies فقط از HTTPS با `Secure; HttpOnly; SameSite=Lax/Strict; Path=/` و بدون `Domain` (ترجیحاً پیشوند `__Host-`)؛ session ID با آنتروپی بالا و سمت سرور قابل ابطال و قابل چرخش، ذخیرهٔ verifier به شکل hash، حدهای **idle/absolute expiry** به تصمیم امنیتی، rotation هنگام login، elevation و recovery. هیچ access/refresh token، اطلاعات خصوصی گفتگو، کلید یا credential در `localStorage`، لاگ عمومی یا Bundle. همهٔ POST/PUT/PATCH/DELETE با token-CSRF + بررسی Origin/Fetch Metadata مناسب؛ `SameSite` به تنهایی مجوز حذف CSRF نیست. Login callback هم `state` و `nonce` و binding به initiator نیاز دارد. تمام درخواست‌های History باید در FastAPI هویت تأییدشدهٔ سروری و وضعیت session/owner را کنترل کنند؛ API هرگز header/body/query/cursor انتخاب owner را نپذیرد. اعتماد BFF↔API باید با شبکهٔ خصوصی و اعتبارنامهٔ خدمت کوتاه‌عمر/کانال هویت‌سنجی‌شده، allowlist و حذف forwarded headers ورودی طراحی و adversarial-test شود؛ header سادهٔ `X-User-Id` کافی نیست.

**نگاشت immutable owner:** جدول نگاشت خصوصی `(issuer, subject) -> internal_owner_user_id` با unique constraint، ایجاد اتمیک با عدم بازانتساب، state کاربر (active/suspended/deletion_requested/deleted) و جداسازی identity/linking از پروفایل. کلید OIDC استاندارد **`(iss,sub)`** است، نه email/phone/username که تغییرپذیرند. حساب‌های ادغام‌شده و انتقال IdP فقط با تأیید هویت دوطرفه و ممیزی؛ هیچ migration ضمنی با matching email. نقش `user/admin/support` توسط سیاست و منابع سرور محصول تعیین و دوباره تأیید شود، نه یک claim درخواست‌شده توسط مرورگر. Admin UI آینده سطح و مسیر جدا، least privilege، reauthentication/MFA و Audit مستقل می‌خواهد؛ دسترسی PostgreSQL RLS کاربر از admin bypass بی‌دلیل به ارث نمی‌رسد.

## 3. دو معماری ADR 0003 و فقط دو نمونهٔ واقعی مسیر A

**A — OIDC استاندارد + نشست سروری BFF (ترجیح مشروط).** Authorization Code + PKCE، validate `iss/aud/exp/nonce/state` و امضای توکن، تبادل Code فقط سرور، عدم ارسال Token به JS یا FastAPI عمومی. IdP گذرواژه/MFA/Account login را مدیریت می‌کند؛ محصول session/CSRF/owner mapping/RLS/role/consent/deletion را همچنان مدیریت می‌کند. OIDC الزاماً اشتراک پولی، اجباری بودن email، SMS یا فروشندهٔ خاص نیست.

1. **Auth0 (managed OIDC، صرفاً نمونهٔ SaaS برای ارزیابی):** IdP کاربر، identifiers، رمز در حالت Auth0 Database Connection، MFA، زمان/رویداد ورود و IP/device metadata را طبق قرارداد خود دریافت و نگهداری می‌کند؛ **متن پرسش مالی و Answer نباید از BFF به IdP منتقل شود.** Public Cloud مناطق US، UK، Europe، Australia، Japan و Canada را فهرست می‌کند؛ انتخاب subregion مشخص به‌صورت دستی در public cloud پشتیبانی نمی‌شود؛ انتقال tenant موجود به منطقهٔ دیگر پشتیبانی نمی‌شود و tenant جدید/انتقال داده لازم است. منطقه و سطح دسترسی مجاز برای کشور کاربر، مالک حساب، کارکنان عملیاتی و استفادهٔ نهایی **تأیید حقوقی/تجاری مستقل می‌خواهد**؛ صرف نام region معادل residency کامل یا تعهد عدم انتقال نیست. Auth0 username login ممکن است، اما مستند رسمی Database Connection در حالت `Requires Username` می‌گوید ثبت‌نام همچنان username **و email** می‌خواهد؛ لذا **بدون ایمیل** را برای این مسیر فرض نکنید. Sms فقط با انتخاب روش phone/passwordless لازم می‌شود، الزامی برای OIDC نیست. هزینه به MAU، B2C/B2B، features/MFA، Organizations، audit/export، custom domains و شرایط قرارداد وابسته است. Snapshot سایت قیمت (2026-11-08) برای **B2C**: Free با سقف اعلامی 25,000 MAU و Essentials *شروع از* USD 35/month برای 500 MAU، Professional *شروع از* USD 240/month برای 500 MAU؛ این‌ها **قیمت قطعی محصول، quote و تضمین سطح سرویس نیستند**؛ قیمت/حدود هنگام تصمیم باید مجدداً تأیید شود. کم‌شدن عملیات هویتی در برابر vendor outage، terms، region، export/delete، lock-in و قیمت متغیر.
2. **Keycloak (open-source OIDC، self-hosted، نمونهٔ مستقل):** خود سازمان در محل **بعداً مصوب** آن را میزبانی و credential/user DB، OTP/WebAuthn، recovery codes، logs، backups، upgrade و HA/TLS/proxy را اداره می‌کند. OAuth/OIDC discovery, auth/token/logout و RP/back-channel logout استاندارد دارد. Realm می‌تواند username را شناسهٔ ورود قرار دهد و تنظیمات user-profile/required email را طبق سیاست تغییر دهد؛ **ورود اولیهٔ بدون SMS و احتمالاً بدون email قابل طراحی است**، ولی مسیر recovery بدون ایمیل باید صریحاً با passkey/recovery codes یا فرایند دستی امن حل و تست شود؛ هیچ recovery پیش‌فرض بدون تماس فرض نمی‌شود. هزینهٔ اشتراک IdP لزوماً ندارد اما **لایسنس رایگان = عملیات رایگان نیست**: hosting/DB/backup/patching/availability/on-call/monitoring و متخصص امنیت لازم است. محل ذخیره با تصمیم hosting مشخص می‌شود، نه با انتخاب واژهٔ self-hosted؛ رعایت محدودیت‌های شبکه، export/legal و دسترسی کاربر همچنان باید بررسی شود. قابلیت انتقال OIDC مساعد است، اما export users/password hash/MFA mappings و session migration بی‌دردسر یا تضمین‌شده نیست.

**B — first-party credentials + server-side sessions:** Product خودش username/password/passkey/recovery/MFA، Argon2id/adaptive password hashes، throttling/lockout، credential rehash، abuse/fraud، security update، incident response، device/session management و deletion را اجرا و پشتیبانی می‌کند. **نیازی ذاتی به IdP SaaS یا شماره/ایمیل نیست**؛ اما اگر هیچ کانال بازیابی انتخاب نشود self-service password reset تأییدپذیر ممکن نیست و باید risk/identity-proofing/recovery policy تعیین شود. Credentials و event metadata در زیرساخت تحت کنترل محصول قرار می‌گیرند؛ خودمیزبانی مخزن داده لزوماً به معنی قرارداشتن داخل یک کشور مشخص نیست. هزینهٔ مستقیم SaaS ممکن است صفر باشد، ولی توسعه، بررسی امنیتی، اپراتور، ایمیل در صورت انتخاب، پشتیبانی، breach handling و تست دائمی معمولاً بیشتر و مسئولیت مستقیم‌تر از A است.

### ماتریس مقایسهٔ تصمیم

| موضوع | A — OIDC + BFF (Auth0 یا Keycloak؛ هیچ‌کدام انتخاب نشده) | B — محصول با Credentials |
|---|---|---|
| انتقال داده و منطقه | حداقل identifier, auth factors/events, IP/device به IdP؛ Auth0 بیرونی و تابع region/contract، Keycloak طبق hosting بعدی؛ محتوای Chat نباید منتقل شود | credential hashes/MFA و رخدادها در زیرساخت انتخابی محصول؛ vendor IdP لازم نیست، اما hosting/backup location باز است |
| ورود اولیه، email/SMS | Auth0 username login ≠ ثبت‌نام بدون email؛ Keycloak username بدون SMS قابل پیکربندی؛ social login اختیاری و انتقال اضافی | username/password بدون email/SMS از نظر فنی ممکن، recovery رسمی هنوز باید طراحی شود |
| هزینه و تیم | Auth0 usage/plan/add-on + BFF؛ Keycloak infra/patch/on-call/HA + BFF؛ بدون فرض MAU/TCO | توسعه و پشتیبانی security/MFA/recovery و ops سنگین‌تر؛ بدون فرض بودجه |
| Session و CSRF | BFF خودش Cookie، store، CSRF و revocation را کنترل می‌کند؛ IdP session مستقل | همان کنترل‌ها و افزون بر آن مدیریت کامل credential lifecycle |
| Expiry/logout/revoke | local revoke فوراً، هماهنگی IdP logout/front/back channel مورد ارزیابی؛ cache/token TTL آزمون | local revoke و credential reset کاملاً داخلی؛ همهٔ دستگاه‌ها و recovery rotation آزمون |
| MFA/recovery | قابلیت IdP وجود دارد ولی Plan/config/device/recovery بررسی شود؛ admin MFA پیشنهاد الزامی | باید مستقلاً توسعه/تست/پشتیبانی شود |
| owner پایدار | مپ `iss+sub` به internal owner، بدون email matching؛ ردیف‌ها با تغییر vendor حفظ شوند | internal ID مستقیم؛ تغییر login identifier بدون تغییر owner |
| مدیر/Support | نقش از سیاست DB سرور؛ admin endpoint/step-up جدا از ادعای IdP | عین همان سیاست؛ IAM/admin security مسئولیت محصول |
| حذف و status بعد از revoke | local revoke + IdP deletion/export policy + نگهداری tombstone مطابق retention؛ status فقط از فرآیند تأییدشدهٔ مستقل، نه 401 bypass | local revoke + credential erasure و حذف/Retention/Backup؛ status پس از revoke باز هم نیازمند سازوکار مستقل |
| Availability / exit | Auth0 external outage/vendor change؛ Keycloak outage/HA ops داخلی؛ portable protocol ≠ credential/actor migration تضمینی | وابستگی کمتر به IdP خارجی، ولی امنیت و uptime کاملاً با تیم محصول؛ export hashed credentials به provider دیگر ممکن است مشکل‌دار باشد |

### مرز حذف حساب و پیگیری درخواست حذف

اول «deletion_requested»/case ثبت‌شده با receipt قابل رهگیری و بدون محتوای خصوصی در خروجی عمومی؛ سپس revoke **همهٔ** BFF sessions و بررسی حذف/غیرفعال‌سازی در IdP، منع replay History و انطباق lifecycle DB/backup طبق Retention مصوب. بعد از revoke، یک cookie قبلی **نباید** به وضعیت خصوصی یا محتوای حذف دسترسی بدهد. پیگیری وضعیت باید با یکی از روش‌های **بعداً تصویب‌شده** (ورود مجدد با identity مجاز و کنترل حساب، یا case-token مستقل کوتاه‌عمر و کم‌دامنه/پشتیبانی با identity verification) انجام شود؛ فعلاً Endpoint، token یا استثنا ایجاد نمی‌شود. Export scope مستقل از deletion است. حل این فرایند به NB23 وابسته نیست؛ به سیاست privacy/employer وابسته است.

## 4. پیشنهاد اولیهٔ تاریخی (پیش از ترجیح جدید کارفرما) — با §8 تکمیل/محدود شده

**پیشنهاد قابل‌تصمیم: A (provider-neutral OIDC Code+PKCE + BFF server session).** دلیل: Next.js server و FastAPI یک مرز صریح برای نگهداری توکن و session دارند؛ PostgreSQL owner/RLS موجود می‌تواند با internal mapping پایدار حفظ شود؛ کاهش سطح نگهداری مستقیم گذرواژه نسبت به ساخت Credential system از صفر. این گزینه **انتخاب Auth0 یا Keycloak، هزینه، کشور/hosting یا مسیر بازیابی را تصویب نمی‌کند**. اگر انتقال داده/دسترسی قانونی سرویس خارجی پذیرفته نشود و تیم عملیات امن واقعاً وجود داشته باشد، Keycloak یکی از دو نمونهٔ مسیر A است، نه تغییر ناگزیر به B. اگر OIDC کلاً رد شود، B به سند threat model و منابع انسانی/امنیتی جدا نیاز دارد.

**تصمیم‌های لازم اکنون (قبل از توسعه):** (1) A یا B؛ (2) آیا ذخیره/پردازش هویت نزد IdP خارجی در منطقه و شرایط قانونی قابل قبول است یا نیاز به میزبانی کنترل‌شده است؛ (3) حداقل identifier و روش recovery/ورود اولیه (email, username, phone, passkey/OTP) و مسئول عملیات/هزینهٔ مرتبط. پیکربندی دقیق TTL، Cookie name، library، provider SDK، schema، UI flow، پیکربندی RLS، threat-model و Test IDs وظیفهٔ تیم فنی پس از تصمیم و پیش از اجرا است، نه کارفرما.

**قابل عقب‌افتادن برای بستهٔ اول (مشروط به اینکه کاربر و مدیر محافظت لازم را داشته باشند):** social login/چند IdP، SMS، نقش‌های پیشرفتهٔ Support، پنل مدیریتی کامل، federation سازمانی، remembered devices، SSO بین اپ‌ها، fancy analytics و مهاجرت‌های bulk. MFA مدیر/مدیریت نقش پایه، logout/revoke، recovery امن و basic privacy/deletion-path **نباید بدون policy/gate به «بعداً» موکول شوند**. وجود self-service recovery ممکن است به email یا روش جایگزین مؤثر نیاز داشته باشد.

**تأیید مستقل هزینه/انتقال:** Auth0 subscription + MFA + region/DPA/subprocessors/availability/legal eligibility، Keycloak هزینهٔ host/on-call/HA/backup/patch و محدودیت جغرافیایی hosting؛ یا برای B هزینهٔ engineering/security support/incident/privacy. هیچ capacity، MAU، budget، country یا SMS dependency در مخزن ثابت نشده است؛ **مطمئن نیستیم** کدام ترکیب برای این کارفرما از نظر هزینه/منطقه مجاز است. **NB23-independent:** owner mapping، session/BFF/CSRF، role checks، RLS/Auth adversarial suite، deletion-request design و User/History access. **NB23-blocked:** عرضهٔ پاسخ واقعی، RAG engine/citations/streaming و Gate Module 00/14/15 end-to-end.

## 5. ماتریس پذیرش بستهٔ آینده — تماماً NOT_RUN

تمام موارد زیر **پیشنهاد آزمون** هستند، نه Test PASS. باید روی server-to-server trust و PostgreSQL RLS با **دو حساب واقعیِ مستقل** و در CI امنیتی جدا از synthetic dependency override اجرا شوند:

| ID | آزمون / رفتار منفی و مثبت | معیار پیشنهادی (NOT_RUN) |
|---|---|---|
| AUTH-P01 | OIDC Code/PKCE, state, nonce, issuer, audience, expiry, signature و callback tampering | فقط login معتبر session بسازد؛ replay/code injection پذیرفته نشود |
| AUTH-P02 | Username/email/phone/passkey شروع ورود طبق policy مصوب | فقط روش‌های تأییدشده پذیرفته شوند؛ هیچ requirement پنهان SMS/email |
| AUTH-P03 | Session invalid, expired, revoked, tampered, stolen-cookie-after-logout | 401 و عدم History/Status leak؛ server-side invalidate واقعی |
| AUTH-P04 | Idle/absolute timeout، refresh و rotation پس از login/elevation/recovery | session قدیم قابل استفاده نباشد؛ session جدید محدود باشد |
| AUTH-P05 | CSRF token/Origin/Fetch Metadata در create/send/delete/logout | درخواست forged cross-site هیچ mutation انجام ندهد |
| AUTH-P06 | جعل owner در Header/Body/Query/Cursor، fake BFF header, direct FastAPI | هر owner spoof بی‌اثر و 401/403/404 غیرقابل‌enumerate |
| AUTH-P07 | دو حساب واقعی، list/message/Answer/status و replay/IDs | بدون leakage؛ هر account فقط owner داخلی خودش |
| AUTH-P08 | DB `SET LOCAL`, transaction rollback/connection reuse, RLS, non-BYPASSRLS | context از session معتبر؛ cross-request owner carry-over صفر |
| AUTH-P09 | User/admin/support authorization و elevation | user هیچ admin route یا RLS bypass ندارد؛ admin step-up/MFA |
| AUTH-P10 | منابع و citation links/locators/private prompts, debug logs | منبع غیرمجاز، token، PII، source URL خصوصی افشا نشود |
| AUTH-P11 | MFA enroll, loss/recovery, reset, account takeover/brute-force | rate limit، backup recovery، invalidate-all و audit مطابق policy |
| AUTH-P12 | Account delete_request → revoke → tombstone/backup retention | عدم resurrection، عدم Content retrieval و عدم دسترسی با session قبلی |
| AUTH-P13 | Post-revocation deletion-status lookup | تنها سازوکار مستقل صریحاً تصویب‌شده؛ عدم ایجاد Auth bypass |
| AUTH-P14 | IdP outage, back-channel logout delay, vendor migration | fail-closed برای mutation، no phantom success؛ owner stable |
| AUTH-P15 | E2E desktop/mobile, accessibility and authorized browser targets | Login→History واقعی با Auth، بدون Mock و بدون fixture actor |
| AUTH-P16 | Security/abuse/threat review and deployment operations | audit/incident/backup/key-rotation and human owner approved |

**Status of every AUTH-P01..P16: NOT_RUN / NOT_ACCEPTED.** Gate های P3M05، P3M06، P3M13، P3M14، P3M15، P3M00 و DB01-02 ناتمام‌اند.

## 6. مواردی که واقعاً به تصمیم کارفرما نیاز دارند (پاسخ‌های قبلی دریافت شده)

**پاسخ داده‌شده در 2026-11-08:** کاربران هدف فعلی ایران؛ ترجیح نگهداری دادهٔ محصول و IdP در زیرساخت تحت کنترل سازمان؛ ورود اولیه با **ایمیل + رمز، تأیید ایمیل و بازیابی امن**؛ معماری قابل توسعه به username/phone/OTP در آینده **بدون اجرای آن‌ها اکنون**؛ و مدیر با دسترسی محدود، نه superuser. سؤال‌های قدیمی دربارهٔ نوع شناسه و اینکه «خودمیزبانی ترجیح دارد یا نه» دوباره مطرح نمی‌شوند.

**حداقل تصمیم‌های باز پیش از یک بستهٔ CI ایزوله:** پذیرش ناظر برای ارزیابی *Keycloak به‌عنوان نامزد آزمایشی و نه انتخاب نهایی* و تعیین مالک اجرای آزمون/تأمین زیرساخت آزمایشی. اگر مأموریت CI جدا با ابزار و دسترسی محدود صادر شود، انتخاب محل سرور عمومی، خرید سخت‌افزار، قرارداد ارسال ایمیل، بودجهٔ Production و تعداد کاربران **پیش‌نیاز CI محلی نیستند**. پیش از هر خدمت واقعی به کاربران ایران، مالک عملیات و امنیت، میزبان/محدودهٔ حقوقی داده، سرویس قابل‌اتکای SMTP و دسترسی/تحویل ایمیل از شبکه‌های هدف باید به تأیید برسند.

**پرسش‌های ضروری باقی‌مانده:** ۱. مسئول سازمانی عملیات/امنیت و هزینهٔ زیرساخت/ایمیل چه کسی است؟ ۲. چه کسی مجوز بررسی حقوقی میزبانی و پردازش داده/ارسال ایمیل برای کاربران ایران را صادر می‌کند؟ انتخاب vendor، تنظیمات فنی، Token policy، نقش‌ها و Test Harness وظیفهٔ تیم فنی در مأموریت بعدی‌اند.

## 7. منابع رسمی بررسی‌شده در 2026-11-08

اطلاعات خدمات، قیمت و منطقه در زمان تصمیم نهایی باید دوباره بررسی شود. موارد زیر فقط **منابع رسمی منتشرشده/در دسترس** هستند، نه تضمین قرارداد یا دسترسی جغرافیایی برای کارفرما.

| Source | What supports / limitations | URL |
|---|---|---|
| OpenID Connect Core §5.7 | stable subject unique by `iss+sub`, email/phone mutable | https://openid.net/specs/openid-connect-core-1_0.html#ClaimStability |
| Keycloak OIDC endpoints | discovery/auth/token/logout and provider-neutral OIDC | https://www.keycloak.org/securing-apps/oidc-layers |
| Keycloak admin guide | realm username/email policies, OTP/WebAuthn/recovery codes | https://www.keycloak.org/docs/latest/server_admin/ |
| Keycloak production guide | TLS, reverse proxy, DB/HA/monitoring operational burden | https://www.keycloak.org/server/configuration-production |
| Auth0 official pricing (B2C snapshot) | MAU/tier/features; Free and B2C Essentials/Professional starting prices, not TCO | https://auth0.com/pricing |
| Auth0 Database Connections | username login and signup email requirements for Requires Username | https://dev.auth0.com/docs/connections/database |
| Auth0 Cloud Deployment | standard public-cloud and private cloud region scope | https://auth0.com/platform/cloud-deployment |
| Auth0 support region/subregion (updated 2025-09-10) | public cloud subregion not manually selectable | https://support.auth0.com/center/s/article/Tenant-Creation-in-a-Specific-Sub-region |
| Auth0 support tenant relocation (updated 2025-09-10) | existing tenant cannot be moved between regions; migrate to new tenant | https://support.auth0.com/center/s/article/Change-the-Location-of-Existing-Tenant |
| OWASP Session Management | server sessions, token handling, secure cookies, expiry/revoke | https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html |
| OWASP CSRF Prevention | synchronizer tokens, Origin/Fetch Metadata, SameSite as defense | https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html |
| OWASP Password Storage / MFA | Argon2id, MFA and recovery risks | https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html and https://cheatsheetseries.owasp.org/cheatsheets/Multifactor_Authentication_Cheat_Sheet.html |

**Final decision:** NONE. No account/tenant/secret/service, migration, workflow, code, public deployment, Auth acceptance or runtime tests performed.


## 8. ترجیح‌های تثبیت‌شدهٔ کارفرما و مسیر خودمیزبانی — 2026-11-08 (AUTH-PLAN-01-G)

این بخش **تصمیم‌های کارفرما** را از **گزینه‌های فنی پیشنهادی** جدا می‌کند و بخش‌های 3، 4 و 6 تاریخی این ADR را در صورت اختلاف محدود می‌سازد. **READY_FOR_REVIEW — SELF_HOSTED_AUTH_PLAN**، نه انتخاب نهایی Keycloak، پیاده‌سازی، خرید یا Production.

### 8.1 دامنهٔ تصمیم، و غیرتصمیم‌ها

| موضوع | ثبت تصمیم فعلی | چیزی که هنوز تصویب نشده |
|---|---|---|
| بازار نسخهٔ نخست | کاربران هدف فعلی **ایران** هستند | تضمین دسترسی اینترنتی، ایمیلی یا قانونی؛ مکان میزبانی و شرکت تأمین‌کننده |
| کنترل داده | **ترجیح** نگهداری داده‌های محصول و IdP در زیرساخت تحت کنترل سازمان | الزام به خرید سخت‌افزار/ادارهٔ شخصی، محل سرور، قرارداد، region یا پذیرش Production |
| ورود v1 | **ایمیل + رمز عبور**، اجبار به تأیید مالکیت ایمیل پیش از دسترسی عادی، **بازیابی امن رمز** | انتخاب موتور IdP/SMTP، TTLها، متن ایمیل، سرویس پرداختنی، دسترسی عمومی |
| توسعهٔ آینده | حفظ قابلیت افزودن نام کاربری، شماره‌تلفن و OTP با قرارداد/owner پایدار | ثبت/ارسال SMS، فیلدهای phone، Login با username، OTP کاربران، Endpoint یا UI این قابلیت‌ها در بستهٔ اول |
| Admin/analytics | دسترسی مدیریتی آینده **حداقلی، قابل ممیزی و scoped**؛ «admin» به معنی دسترسی نامحدود به همهٔ داده‌ها نیست | پنل مدیریت/مالی، Roleهای گسترده، دسترسی تحلیلی به PII یا bypass RLS |
| اطلاعات مالی احتمالی | صرفاً **نیاز آینده به بررسی دامنه، سیاست داده و حریم خصوصی** | هیچ بانک/حساب/تراکنش/فیلد یا جدول مالی، اتصال بانک، مجوز تحلیل دادهٔ مالی، رمز یا OTP بانکی |

**نکتهٔ مهم:** تصمیم کارفرما «ساخت سیستم نگهداری گذرواژه از صفر» نیست؛ گزینهٔ B به‌عنوان مقایسه باقی می‌ماند ولی مسیر منتخب برای *بررسی*، OIDC با IdP قابل خودمیزبانی و BFF است. ADR 0003 و H-DEC-01 در سطح انتخاب فناوری/Auth هنوز OPEN می‌مانند.

### 8.2 چرا Keycloak نامزد مناسبی برای ارزیابی فنی است، نه انتخاب قطعی

مستند رسمی Keycloak تأیید می‌کند که:
- سرویس OIDC، endpointهای discovery/auth/token/logout و سیاست‌های هویت و Session دارد؛ فرم password-based با **Email as username**، **Verify Email** و جریان **Forgot Password / Reset Credentials** با سیاست زمان‌دار قابل پیکربندی است. Realm برای ارسال verification/reset email به **SMTP تنظیم‌شده** نیاز دارد. استفاده از login «email+password» لزوماً email-provider، صندوق یا DNS/SMTP رایگان/آماده ایجاد نمی‌کند.
- سیاست password را باید عمداً تنظیم کرد؛ **Realm تازه به‌خودی‌خود Password Policy سخت‌گیرانه ندارد**. مستند جدید استفاده از Argon2 را در حالت non-FIPS بیان می‌کند. Brute force detection باید فعال/تنظیم شود؛ default امن فرض نشود. MFA با TOTP/WebAuthn و Recovery Codes پشتیبانی می‌شود؛ **MFA مدیر باید الزام و قابل بازیابی باشد**، نه صرفاً یک گزینه که در صورت نبود credential دور زده شود.
- Keycloak می‌تواند با PostgreSQL سازگار کار کند؛ برای آینده، دیتابیس Identity با credential/Realm/Admin/Security Events باید از History محصول **از نظر role/schema/backup/access جدا** طراحی شود؛ اشتراک موتور PostgreSQL خودبه‌خود مرز دسترسی ایمن نمی‌سازد.
- Production مستلزم hostname ثابت، TLS، reverse proxy امن، database، backup/restore آزموده، مراقبت از updateها، health/metrics بدون انتشار عمومی و برنامهٔ قطعی مالک عملیات و رخدادهاست. مستند Keycloak توصیه می‌کند مسیرهای administration از سطح login عمومی جدا باشند. **خودمیزبانی صرفاً کنترل زیرساخت را افزایش می‌دهد، نه تضمین دسترس‌پذیری یا رایگان بودن.**

**منابع رسمی بررسی‌شده 2026-11-08:** [Keycloak Server Admin — Realm Email/SMTP, Verify Email, Forgot Password, Password Policy/Brute Force, MFA/Recovery Codes](https://www.keycloak.org/docs/latest/server_admin/)، [Keycloak OIDC layers](https://www.keycloak.org/securing-apps/oidc-layers)، [Keycloak production configuration](https://www.keycloak.org/server/configuration-production)، [Keycloak production database](https://www.keycloak.org/server/db)، [Keycloak reverse proxy](https://www.keycloak.org/server/reverseproxy)، [Keycloak hostname validation](https://www.keycloak.org/server/hostname). نسخهٔ دقیق موتور، حمایت از نسخهٔ PostgreSQL و تغییر رفتار Config در زمان اجرای بسته باید با مستند نسخهٔ pinشده بازسنجی شوند؛ انتخاب نسخه هنوز انجام نشده است.

**پیشنهاد فنی قابل بازبینی:** برای بستهٔ تست اول Keycloak را فقط به‌عنوان **نامزد خودمیزبان مبتنی بر OIDC** ارزیابی کنید؛ با BFF نشستی Next.js + FastAPI trusted identity و owner داخلی مستقل از IdP. انتخاب نهایی Keycloak، روش استقرار، پشتیبانی و محل داده به پذیرش معماری، تست و مجوزهای جدا نیاز دارد. استاندارد بودن OIDC خروج از فروشنده را آسان‌تر می‌کند، ولی migration اعتبارنامه‌ها/MFA و هویت‌ها خودکار نیست.

### 8.3 Email verification و Reset — مسیر پیشنهادی بستهٔ v1

1. در جریان ثبت‌نام/دعوت (سیاست ثبت‌نام عمومی یا دعوتی هنوز تصویب نشده)، کاربر آدرس ایمیل و گذرواژهٔ آزمایشی وارد می‌کند؛ سرویس IdP سیاست رمز، hash، ضد brute force، پیام عمومی عدم افشای وجود حساب و rate limit را اعمال می‌کند. **تا قبل از تأیید ایمیل دسترسی به History فعال نمی‌شود.**
2. IdP فقط لینک/توکن تأیید **کوتاه‌عمر، یک‌بارمصرف، audience/realm/flow محدود** با پایه URL ثابت و معتبر ایجاد می‌کند. ارسال از پیکربندی SMTP سروری انجام می‌شود؛ Mail service دریافت‌کننده باید با سیاست‌های حریم خصوصی سازگار باشد. Token در Log، URL analytics، referrer خارجی یا browser storage نگه‌داری نشود؛ replay/expiry/invalid-link مستقل آزموده شود.
3. Forgot Password باید پاسخ عمومی و غیرقابل enumerate بدهد، درخواست را با rate limit کنترل کند و لینک Reset زمان‌دار ارسال کند؛ پس از تعویض رمز، sessionهای BFF و در صورت امکان IdP sessions/tokenهای قبلی باید طبق سیاست به‌صورت آزمودنی باطل شوند. **کیفیت revoke میان IdP و BFF نیازمند آزمون end-to-end است**؛ صرف reset کردن رمز تضمین invalidate شدن همه نشست‌ها نیست.
4. در **CI ایزوله** به‌جای اینترنت/SMTP واقعی، یک **SMTP catcher محلیِ فاقد ارسال بیرونی** با mailbox مصنوعی و آدرس‌های دامنهٔ نمونهٔ رزروشده (مانند `first@example.test` و `second@example.test`) پیشنهاد می‌شود. Test از پیام ضبط‌شده token را استخراج و در loopback link دنبال می‌کند؛ no outside delivery/no actual mailbox/no PII. ارسال هر نوع ایمیل واقعی یا راه‌اندازی سرویس در **این مأموریت ممنوع** است.
5. در محصول واقعی سرویس SMTP/ارسال ایمیل لازم است؛ می‌تواند در زیرساخت مورد تأیید سازمان یا از ارائه‌دهندهٔ مجاز با قرارداد باشد. مسئول deliverability، دامنه و SPF/DKIM/DMARC، مدیریت برگشتی‌ها، abuse rate و ظرفیت باید تعیین شود. هیچ شرکت، دامنه، mailbox یا قرارداد انتخاب نشده است.

**محدودیت ویژهٔ کاربران هدف ایران:** مستند Keycloak به‌تنهایی نه دسترس‌پذیری سرور/دامنه/HTTPS از شبکه‌های داخل ایران را تضمین می‌کند نه رسیدن ایمیل‌های تأیید/بازیابی به صندوق‌های مخاطب. پیش از انتخاب میزبان/SMTP و انتشار باید به‌شکل مجاز دسترس‌پذیری DNS/TLS/redirect و callback، تحویل ایمیل و لینک‌های Reset برای شبکه‌ها و providerهای ایمیل مورد استفادهٔ مخاطب، شرایط حقوقی/قراردادی، سیاست انتقال داده و محدودیت سرویس‌دهنده را با تست عملی و تأیید مسئول مربوط بررسی کرد. **هیچ نتیجهٔ موفق یا ناممکن بودن برای ایران ادعا نشده است.**

### 8.4 مرز هویت، مدیر، Analytics و داده

- **Browser → BFF:** OIDC Authorization Code + PKCE + state/nonce؛ session opaque server-side، Cookie `HttpOnly/Secure/SameSite`، CSRF/Origin کنترل‌شده، login fixation/rotation و expiration/revoke. Tokenهای IdP به JS، localStorage یا logs ارسال نشوند؛ public API/Proxy فعلی CI-only باقی می‌ماند تا مأموریت جدا.
- **BFF → FastAPI:** اعتماد سرور-به-سرور با احراز هویت خدماتی/شبکهٔ محدود و allowlisted identity claims، نه header `owner` دلخواه از درخواست. FastAPI هویت و وضعیت تأیید ایمیل/نشست را اعتبارسنجی و به یک `internal_owner_user_id` **پایدار** وصل کند، بر اساس `(iss,sub)`؛ email صرفاً شناسهٔ ورود/تماس قابل تغییر است، نه کلید owner یا مجوز. تبدیل سشن به Transaction Context و RLS محصول با کاربر DB فاقد BYPASSRLS انجام شود؛ endpointها/Status و Cursor نیز باید کنترل شوند.
- **Admin:** roleهای پایهٔ `user` و `admin` فقط به حداقل مسئولیت مشخص دسترسی می‌دهند؛ admin نیازمند **MFA الزامی/step-up** برای عملیات حساس، لاگ ممیزی redacted و revocation جداست. Role `admin` نه مجوز خواندن تاریخچهٔ همهٔ کاربران است نه `BYPASSRLS`. Console Keycloak و Admin UI آینده جدا از Browser کاربر، محدود به مسئول عملیاتی مجاز؛ پنل مدیر و مالی فاز ۴ ساخته نمی‌شود.
- **Analytics:** برای آینده فقط policy design و دسته‌بندی سطح داده در نظر گرفته شود؛ دسترسی aggregate/minimized/consent-aware و scope شده، بدون اتصال مستقیم کاربر analytics به جداول private History. هیچ API، schema، جدول، export یا score/financial field جدیدی در این مأموریت یا بستهٔ Auth اول تصویب نمی‌شود.
- **حذف و وضعیت پس از ابطال:** درخواست حذف، revoke نشست/IdP، جلوگیری از مشاهدهٔ پیام و مسیر پیگیری حذف بعد از revoke مستقل از جلسهٔ باطل‌شده نیازمند policy و آزمون است؛ مشخصات Retention/Backup و مسیر status هنوز OPEN.

### 8.5 بستهٔ اجرایی نخست پیشنهادی (FUTURE, AUTH-P01..P16 همگی NOT_RUN)

**پیش‌شرط شروع کدنویسی:** مأموریت اجرایی و مرز مالکیت جدا + تأیید ناظر برای **ارزیابی** Keycloak آزمایشی، نه تصمیم نهایی/Production؛ انتخاب نسخهٔ پشتیبانی‌شده در آن زمان؛ ایزوله بودن CI؛ مالک هماهنگ‌کنندهٔ امنیت/عملیات؛ بدون رمز/ایمیل واقعی. از مسیرهای زیر **در این PR هیچ فایلی تغییر نمی‌کند**:

| گام آتی و مالک/مسیر پیشنهادی | وابستگی و خروجی مورد انتظار | شاهد پذیرش پیشنهادی |
|---|---|---|
| 0. Boundary & contract review — Foundation: `docs/architecture/**`, `docs/adr/**`, `packages/contracts/**` فقط اگر ضرورتِ تأییدشده و با مالک | فریز محدود Trust Boundary، realm/client، callback allowlist، CSRF/role/session/recovery policy، mapping owner؛ `product.v1` و History immutable/idempotency حفظ شوند | Threat checklist و review مشترک؛ نه ساخت DTO/endpoint فرضی |
| 1. IdP test harness — Foundation/ops با مالکیت مصوب در `tests/phase3/integration/cross_component/**` و Workflow **بعداً مجازشده** | یک Keycloak CI-only آزمایشی + دیتابیس/realm مجزا + SMTP catcher loopback با outbound=DENY، دو کاربر مصنوعی A/B و یک بازیگر مدیر تست؛ ورود با ایمیل، Verify/Reset واقعی داخل Sandbox | Realm fresh startup/shutdown، credential defaults reviewed، email delivery فقط catcher، test isolation و no real outbound |
| 2. Product boundary — API `src/phase3/auth/**`, `apps/api/**`, `tests/phase3/api/**`; UI `apps/web/**`, `tests/phase3/ui/**` | Next.js BFF OIDC callback و session store server-side، Login/Logout/Verification/Reset UI، FastAPI trusted identity replacement در API بدون public actor selector؛ original `product.v1` request semantics ثابت | Positive/negative code/PKCE/state/nonce, 401 default, verified email enforcement, no token in browser bundle |
| 3. Owner/RLS & integration — DB `src/phase3/storage/postgres/**`, `infra/postgres/**`, `tests/phase3/database/**`; Foundation cross-component CI | بعد از design review: `(iss,sub)`→ immutable owner mapping و role; PostgreSQL RLS مستقل، migrationهای جدید صرفاً با مجوز مجزا، session revoke/delete boundary | Two real CI users cannot read other History via API/DB/cursor, no admin superaccess, DB context cleared per transaction |
| 4. Acceptance and handoff — assigned QA/security/ops, Foundation Gate owner | ترکیب در یک runner ایزوله، logs redacted، report exact SHAs، CI artifacts، failures; no public host | کامل‌شدن ماتریس زیر در CI جدا با ناظر؛ Production access و Gate همچنان تصمیم مستقل |

**حداقل Scope بسته:** ایمیل+رمز، Verify Email و Reset با SMTP catcher، Login/Logout و session revocation/CSRF، guard verified-owner، ۲ کاربر مستقل (نه dependency override)، نقش `user`/ `admin` با MFA اجباری مدیر، جداسازی History تحت RLS. Username/Phone/OTP/SMS کاربران عادی، real SMTP، analytics، پنل مالی/مدیریتی، اتصال بانکی، RAG/NB23 و deploy **خارج** هستند. OTP مخصوص MFA مدیر در این بسته **آزمون سیاست امنیتی مدیریت** است؛ نه راه‌اندازی ورود OTP عمومی.

**تست‌های پذیرش CI پیشنهادی، همه NOT_RUN:**

| Test | حالت‌های مثبت و منفی، شرط رد |
|---|---|
| AUTH-CI-01 | Signup/login ایمیل+رمز A/B؛ بی‌تأییدایمیل، user disabled، رمز اشتباه و تکرار تلاش → 401/deny و هیچ session محصول |
| AUTH-CI-02 | دو پیام SMTP محلی Verify/Reset با لینک scoped/یک‌بارمصرف و انقضا؛ هیچ SMTP خارجی، PII، Token log یا takeover |
| AUTH-CI-03 | Reset معتبر و reset-replay/expired/foreign-account؛ revoke sessionهای قبلی و الزام reauthentication با رمز جدید |
| AUTH-CI-04 | OIDC code+PKCE/state/nonce، tamper callback/redirect/issuer/audience/expiry/replay؛ login فقط از issuer مجاز |
| AUTH-CI-05 | BFF cookie `HttpOnly/Secure/SameSite`، fixation/rotation، idle/absolute timeout، logout-all/revoke؛ session قبلی 401 |
| AUTH-CI-06 | Forged CSRF/cross-site Origin/Fetch Metadata on POST/logout; no owner or send mutation |
| AUTH-CI-07 | Forged owner via header/body/query/cursor و direct FastAPI/public endpoint؛ missing/foreign ID indistinguishable 404 |
| AUTH-CI-08 | Two synthetic but **real OIDC-logged-in CI identities** (not API dependency overrides): independent History create/list/send/status, pagination/retry; no cross-user leak or duplicate |
| AUTH-CI-09 | Role user vs admin: admin TOTP/WebAuthn mandatory as configured, recovery secure, user forbidden admin actions; admin **cannot** read unrelated History or bypass RLS |
| AUTH-CI-10 | PostgreSQL transaction context/connection reuse and role grants non-BYPASSRLS: never carry owner between users/requests |
| AUTH-CI-11 | Unverified/deleted/suspended/revoked identity: no Conversation, Answer, account info or delete-status bypass; post-revoke deletion receipt policy explicitly still OPEN |
| AUTH-CI-12 | CI fixed ports/loopback, no outbound email/Internet model/payment, clean teardown; Browser desktop/mobile accessibility/login errors and no JS/localStorage token leakage |

هر Test: **NOT_RUN, NOT_ACCEPTED**. آزمون‌ها طرح‌اند و لاگ/آرتیفکت واقعی ندارند. Gate P3M05، P3M06، P3M13، P3M14، P3M15 و DB01-02 با گذراندن CI به‌تنهایی خودکار پذیرفته نمی‌شوند.

### 8.6 واقعاً چه پاسخ‌هایی پیش از بستهٔ CI لازم است؟

- **پاسخ‌های داده‌شده، دیگر سؤال نیستند:** ایران، ترجیح کنترل زیرساخت، ایمیل/رمز+Verify/Reset، توسعهٔ آیندهٔ identifier، محدودبودن Admin.
- **برای CI ایزوله:** مجوز مشخص ناظر برای مأموریت اجرا و استفاده از نامزد Keycloak به‌صورت **nonbinding**، مالک اجرایی آزمون و محدودهٔ دسترسی/هزینهٔ CI (بدون سرویس پرداختی/خارجی). جزئیات نسخه، realm، session TTL و ابزار SMTP catcher را تیم فنی در طرح بسته تعیین و به ناظر ارائه می‌کند، نه کارفرما.
- **پیش از آزمون واقعی کاربران/Production، جدا و بعداً:** مسئول عملیات/امنیت/Backup و تأیید هزینه؛ محل میزبانی و ضوابط پردازش داده و دسترسی کاربران ایران؛ SMTP واقعی، دامنه، sender و deliverability، قرارداد/محدودیت و پاسخ‌گویی به رخداد؛ Retention/Deletion و panel/analytics privacy policy.

**تعریف پایان این نوبت:** فقط مستندسازی تصمیم و مسیر اجرایی پیشنهادی؛ هیچ IdP/SMTP، حساب، credential، container، service، migration، role، dependency، UI، schema، Workflow، آزمون Auth واقعی، ارسال ایمیل، خرید یا استقرار ایجاد نشده است. **READY_FOR_REVIEW — SELF_HOSTED_AUTH_PLAN.**
