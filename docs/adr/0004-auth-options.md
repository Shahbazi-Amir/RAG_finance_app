# ADR 0004 — Auth واقعی محصول: مقایسهٔ دو معماری و پیشنهاد مشروط

**Status: PROPOSED / READY_FOR_DECISION — NOT_APPROVED, NOT_IMPLEMENTED.**
**Date / official-source check:** 2026-11-08. **Mission:** AGENT-API-AUTH-PLAN-01; **starting main:** `9d5f2f9adc8e4522ec8cf4ffd397ba0a815e8fb7`; branch `prep/auth-decision`.
**Decision owner:** کارفرما/ناظر؛ این ADR هیچ ارائه‌دهنده، حساب، قرارداد، منطقه، هزینه یا امنیت Production را تصویب نمی‌کند.

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

## 4. پیشنهاد، تصمیم‌های فوری و قابل‌تعویق

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

## 6. فقط سه پرسش برای تصمیم کارفرما

1. **از نظر سیاست سازمان، ورود با سرویس هویت استاندارد بیرونی (در صورت تأیید قرارداد/محل داده) مجاز است، یا هویت باید در میزبانی تحت کنترل سازمان بماند؟**
2. **ورود اولیه باید با چه شناسه‌ای باشد: نام کاربری، ایمیل یا شماره تلفن؟ و آیا ایمیل/شماره برای بازیابی حساب مجاز است، یا روش بدون تماس لازم است؟**
3. **برای هزینهٔ اشتراک احتمالی IdP یا نگهداری سرویس هویت خودمیزبان، چه واحد/مسئولی باید بودجه و تعهد عملیات/امنیت را تأیید کند؟**

این سؤال‌ها دربارهٔ سیاست/منابع‌اند؛ تصمیم‌های اجرایی و فنی با تیم پیاده‌سازی پس از تصویب جداگانه است.

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
