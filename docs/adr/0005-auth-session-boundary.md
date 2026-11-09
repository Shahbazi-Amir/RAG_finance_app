# ADR 0005 — مرز نشست، ابطال و اتصال هویت OIDC به محصول

**Status:** PROPOSED / READY_FOR_REVIEW — AUTH_SESSION_BOUNDARY. این متن طراحی است؛ IMPLEMENTED=DOCUMENT_ONLY، TESTED=NOT_RUN، ACCEPTED=SUPERVISOR_PENDING. نه Auth محصول و نه Production/Gate پذیرفته نشده‌اند.

**Mission:** AGENT-API-AUTH-BOUNDARY-01؛ **Starting main:** 97293558bc80953bd88e98e81166a8da745a2207؛ **branch:** prep/auth-session-boundary؛ **Date:** 2026-11-09؛ **Decision owner:** ناظر «مغز فاز سوم». این سند ADR 0004 را برای مرز اجرایی تکمیل می‌کند؛ انتخاب نهایی IdP، منطقهٔ میزبانی و قرارداد عملیاتی نیست.

## 1. مبنا و حدود اعتبار

- [ADR 0004](0004-auth-options.md) الگوی استاندارد OIDC Authorization Code + PKCE و نشست سروری Next.js BFF را مشروطاً ترجیح داده؛ مقایسهٔ ارائه‌دهندگان تکرار نمی‌شود. هدف نخست ایمیل+رمز با verify/reset است؛ افزودن شناسه یا OTP عمومی به آینده موکول است.
- [PR #13](https://github.com/Shahbazi-Amir/RAG_finance_app/pull/13) در merge 97293558bc80953bd88e98e81166a8da745a2207 با HEAD پذیرفته‌شدهٔ 975062681e8124e65f72cda3338cf4cfa4a3c782 ادغام شد. CI محدود: [Run 42617144329](https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/42617144329)، کد آزموده‌شده 835bd417ede49184caa93f36bbfcc8d7bac12a3a، Keycloak 26.8.2، PostgreSQL هویت 17.11، Mailpit 1.32.0، Chromium مصنوعی. این‌ها **IdP ایزوله** هستند، نه Auth محصول.
- **اندازه‌گیری مهم:** پس از Reset رمز در این پیکربندی، مرورگر قدیمی با prompt=none موفق به گرفتن Code جدید شد، Refresh Token قبلی HTTP 200، UserInfo با Access Token قبلی HTTP 200 و امضای JWT پیش از انقضا معتبر ماند. پس از **Logout مدیریتیِ جداگانه**، Refresh HTTP 400 و UserInfo HTTP 401 شدند، ولی امضای محلی JWT تا پیش از exp همچنان معتبر بود. هیچ کدام ابطال Cookie محصول را اثبات نمی‌کنند.
- وابستگی نقشه: Module 05 فعالیت‌های **P3M05-A03/A04/A05/A07/A08/A09/A10**، همچنین A06 سیاست Brute Force؛ Module 03 تعریف Error/Request/Trace/Contract و تفکیک Domain؛ Module 06 RLS و user context هر Transaction، cross-user/ID enumeration؛ Module 13 Authorization هر Endpoint و نسخه‌بندی API. ماژول‌های 00، 03، 05، 06 و 13 هیچ Gate تازه‌ای PASS نمی‌گیرند.
- محدودیت قرارداد NB23 همچنان ورودی Draft فقط contract_version و question است؛ هیچ History/owner/context بی‌اجازه به موتور تزریق نمی‌شود.

## 2. انتخاب پیشنهادی مشخص و مرز مالکیت

**پیشنهاد برای تصمیم ناظر:** OIDC server-side Code+PKCE با provider-neutral interface؛ Next.js **BFF** مالک OIDC callback، token exchange و Cookie محصول؛ **opaque revocable product session** در PostgreSQL محصول (نه PostgreSQL هویت Keycloak)؛ FastAPI تنها درخواست دارای اثبات خدمت BFF را بعد از **اعتبارسنجی زندهٔ session و internal owner** می‌پذیرد؛ DB با RLS و تراکنش owner-scoped دفاع دوم است. نام Keycloak صرفاً پیاده‌سازی آزمایشی Adapter هویت در بستهٔ جداست.

| مسئول / دامنه | مسیر دقیق **پیشنهادی برای بستهٔ بعدی** | مرز |
|---|---|---|
| UI (مالک Next.js server/BFF و صفحهٔ ورود) | apps/web/app/api/auth/login/route.ts، apps/web/app/api/auth/callback/route.ts، apps/web/app/api/auth/logout/route.ts، apps/web/app/api/auth/logout-all/route.ts، apps/web/src/auth/server/**، apps/web/app/login/page.tsx | OIDC، Cookie، CSRF، Session bootstrap، redirect allowlist و رندر؛ هیچ JWT به Client JS |
| API (مالک اعتماد سمت FastAPI) | apps/api/history_api.py با تغییر محدودِ مأموریت آینده و src/phase3/auth/** برای dependency تأیید BFF | پذیرش identity assertion فقط از خدمت معتبر؛ مجوز هر Endpoint و lookup session/owner؛ نه جایگزینی Schema عمومی |
| DB (مالک Schema و Session persistence) | src/phase3/storage/postgres/** و infra/postgres/migrations/** با شمارهٔ Migration بعد از بررسی زنجیرهٔ موجود | issuer+sub unique mapping، session rows، epoch/tombstone/nonce/replay، تراکنش و RLS؛ **نه** پوشهٔ موازی جدید |
| Foundation / Integration | tests/phase3/integration/cross_component/** و بستهٔ قرارداد مستقل پس از مجوز؛ coordination/phase3_checklist.md فقط Foundation | integration واقعی، adversarial security، reconciliation و Gate، نه کار مشترک بی‌مالکیت |

این مسیرها **تعهد پیاده‌سازی فعلی نیستند**؛ مالک UI کد BFF را می‌نویسد، API صرفاً قرارداد/بازبینی مرز را هماهنگ می‌کند، DB مالک SQL می‌ماند. هیچ مسیر یا فایل پیشنهادی در این PR ایجاد نشده است.

### معماری جریان درخواست

1. مرورگر تنها به Origin محصول با HTTPS دسترسی دارد؛ Login یک initiation record سمت سرور شامل state تصادفی تک‌مصرف، nonce، PKCE verifier رمزگذاری‌شده، redirect مقصد ثابت/allowlist، زمان انقضا و binding به Cookie موقتِ HttpOnly دارد. **Authorization Code فقط به callback سروری** برمی‌گردد.
2. BFF callback باید state، initiator binding، age، nonce، issuer، audience/client_id، exp، signature/JWKS، code one-time، PKCE S256 و email_verified را تأیید کند؛ خطا → هیچ session. جلوگیری از login-CSRF و code mix-up با issuer-bound flow. هر Code قبلی یا state تکراری reject.
3. نگاشت **(iss,sub)** معتبر به internal_owner_user_id در DB تراکنشی upsert می‌شود؛ email/phone/username فقط contact هستند، **هرگز primary linking key**. unique(issuer,subject)، immutable internal owner، collision → fail closed، حذف/تعلیق در وضعیت کاربر مستقل بررسی شود.
4. BFF به‌جای توکن IdP، Cookie یک Session ID تصادفی opaque حداقل 256-bit صادر می‌کند و فقط HMAC/Hash شناسه را در Session Store نگه می‌دارد. اطلاعات توکن IdP در حافظه/ذخیره‌سازی امن **سروری** با encryption-at-rest و rotation keys؛ به JS، localStorage، Query، Error و لاگ نمی‌رسند.
5. برای History، BFF assertion کوتاه‌عمر امضاشده با aud=FastAPI، iss=شناسهٔ سرویس BFF، jti یک‌بارمصرف، exp≤30s، method/path/body-hash و **session_id reference، session_epoch، owner داخلی** می‌فرستد. این Assertion جای IdP JWT نیست. اتصال شبکهٔ خصوصی + احراز خدمت (mTLS یا روش معادل پذیرفته‌شده) و اعتبارسنجی کلید در API لازم است؛ Header سادهٔ انتخاب owner از مرورگر یا X-User-Id هرگز اعتماد نمی‌شود.
6. FastAPI پیش از هر کار session/owner/epoch فعلی و وضعیت active را از Store معتبر می‌خواند، jti replay را reject می‌کند و برای هر Endpoint authorization را اجرا می‌کند. سپس DB app role **non-BYPASSRLS** با SET LOCAL owner در همان Transaction و بدون نشت به Connection Pool به History دسترسی می‌یابد. Foreign/deleted/inaccessible → 404 عمومی مطابق قرارداد فعلی؛ بدون owner واقعی → 401/403. Direct request و spoofed forwarded headers رد می‌شوند.
7. هیچ status polling یا idempotent retry حق دورزدن session gate ندارد. Create/Send scope و requested_conversation_id=null بدون تغییر؛ موتور/History خودکار به NB23 وصل نمی‌شوند.

## 3. Session policy پیشنهادی (برای تصویب، نه Config اجراشده)

| موضوع | سیاست پیشنهادی مشخص | پذیرش آینده |
|---|---|---|
| Cookie | __Host-session، Secure، HttpOnly، Path=/، بدون Domain، SameSite=Lax برای OIDC redirect کنترل‌شده؛ HTTPS/HSTS؛ Cache-Control: no-store در Auth response | Attribute و subdomain/cookie tossing tests |
| Cookie CSRF | Token synchronizer وابسته به server session برای تمام عملیات تغییردهنده، جدا از Cookie، همراه Origin دقیق و Fetch Metadata؛ تنها مبدأ مجاز HTTPS؛ هیچ permissive CORS؛ SameSite تنها دفاع کافی نیست | negative CSRF/form/cross-site fetch |
| Idle/absolute | **پیشنهادی:** idle 30 دقیقه، absolute 12 ساعت، رفرش/تمدید idle با فعالیت معتبر و سقف absolute ثابت؛ admin elevation حداکثر 5 دقیقه و نیازمند step-up. ساعت مرجع DB server UTC؛ drift/clock rollback fail closed | boundary-clock/replay/expired tests |
| Rotation | شناسهٔ session جدید بعد از Login، تغییر سطح دسترسی، recovery و reauthentication؛ old ID اتمیک revoke، ممنوعیت reuse و fixation؛ CAS برای دو Refresh هم‌زمان | concurrent rotation و stolen cookie |
| IdP token handling | Refresh token صرفاً سرور؛ rotation مطابق IdP و atomic compare-and-swap + encrypted storage؛ هیچ refresh در مرورگر؛ Access token **به‌تنهایی** مجوز History نیست | double refresh، reuse detection |
| Revocation | جدول جلسه با status و owner.session_epoch؛ هر درخواست و refresh باید در Transaction جاری آن را تأیید کند؛ cache مثبت authorization ممنوع تا زمان تأیید latency/epoch barrier | deny-after-commit + in-flight race |
| Log/audit | فقط event_type، request_id/trace_id، owner pseudonym/restricted ID، session reference hash truncated، outcome، policy_version و timestamp؛ هرگز token/code/cookie/password/MFA seed/email link/History text | schema redaction + secret canary |

اعداد TTL و استراتژی trust در بالا **PROPOSED/NOT_APPROVED** هستند و باید قبل از ساخت Session در بستهٔ مشترک تصویب و با CI واقعی اندازه‌گیری شوند.

## 4. Logout و logout-all: منبع حقیقت محصول

- **Logout همان نشست:** BFF پس از CSRF/Origin، در DB با CAS فقط همان session را revoked و Cookie را منقضی می‌کند؛ پاسخ تنها پس از commit معتبر است. پاک‌کردن Cookie به‌تنهایی ابطال نیست. درخواست In-flight باید epoch/status را پیش از عملیات حساس دوباره بررسی کند؛ streaming/async work پس از revoke باید قطع/deny شود (در بستهٔ مستقل؛ فعلاً موتور مسدود).
- **Logout-all:** با Lock ردیف owner، افزایش monotonic session_epoch و revoke همه session rows + refresh handles در یک transaction؛ هر session با epoch قدیمی در BFF و FastAPI رد می‌شود. برای IdP نیز مسیر استاندارد End Session/RP-initiated یا Admin REST user logout به‌عنوان *پیگیری جدا* پیشنهاد می‌شود، نه جایگزین ابطال محلی. failures در IdP ثبت و retry امن/محدود؛ Product revocation حتی هنگام IdP outage باقی می‌ماند.
- **جلوگیری از silent re-creation:** Login endpoint فقط پس از آغاز صریح جدید با state/initiator و **assurance معتبر reauthentication** session جدید می‌سازد. پس از logout-all یا credential-change یک reset_gate روی Owner باز می‌شود که صدور Session جدید را تا دریافت شاهد معتبر reauth پس از epoch مسدود می‌کند. prompt=login، max_age=0 یا auth_time به‌تنهایی proof of re-entered fresh credentials نیستند؛ رفتار Authentication Flow/ACR/AMR و sid باید در Keycloak واقعی adversarial-test شود. بدون چنین تضمینی **fail-closed**، نه استناد به کوکی SSO قدیمی.
- **Keycloak admin با product admin متفاوت:** حداقل نقش‌های realm-management فقط برای operator هویت، و نقش user/admin/support محصول از جدول Authorization مستقل و MFA/step-up است. Realm admin حق خواندن همه History یا BYPASSRLS ندارد.

## 5. مشکل حیاتی Reset — طراحی قابل آزمون و مرز تضمین

### 5.1. واقعیت نسخهٔ 26.8.2 و فقدان تضمین آماده

در مستندات رسمی دقیق Keycloak 26.8.2:
- Server Administration Guide بخش Auditing user events، انواع **Update Credential** (تغییر Password/OTP) و legacy/deprecated Update Password و Admin events را تشریح می‌کند. Event Listener داخلی وجود دارد اما listener پیام webhook تضمین‌شدهٔ آماده برای revoke Product نیست؛ event storage/log پیش‌فرض نیز durable delivery به BFF نیست.
- Server Developer Guide بخش **Event Listener SPI** آن را **internal SPI با امکان تغییر ناسازگار در نسخه‌های بعدی** می‌نامد. نوشتن extension اختصاصی و آزمودن سازگاری upgrade ضروری است.
- Admin REST به‌صراحت **POST /admin/realms/{realm}/users/{user-id}/logout** را برای حذف نشست‌های کاربر معرفی می‌کند؛ این API یک **عمل مستقل** است، نه سند اینکه Reset به‌صورت خودکار آن را اجرا می‌کند.
- OIDC logout و back-channel logout قابلیت جداگانه‌اند؛ صحت listener، پوشش همهٔ Reset pathها، تأخیر انتشار و at-least-once delivery از اسناد بالا **اثبات نشده‌اند**.

**منابع رسمیِ بررسی‌شده 2026-11-09:** [Keycloak 26.8.2 Server Admin](https://www.keycloak.org/docs/26.8.2/server_admin/)، [Server Developer/Event Listener SPI](https://www.keycloak.org/docs/26.8.2/server_development/)، [26.8.2 Admin REST](https://www.keycloak.org/docs-api/26.8.2/rest-api/index.html)، [OIDC layers](https://www.keycloak.org/securing-apps/oidc-layers). API/extension کارکردهٔ credential-revision یا webhook با تضمین end-to-end در مخزن **وجود/آزمون تأییدشده ندارد**. هر ادعای فوریت یا bound فعلاً ممنوع.

### 5.2. مسیر Product-initiated Reset — پیشنهاد کنترل‌شده

1. پیش از ارسال ایمیل/redirect Reset، BFF با Session/CSRF (یا recovery token محدود و مستقل) intentِ reset را روی owner معتبر ثبت و در Transaction با Lock ردیف owner: session_epoch را افزایش می‌دهد، همهٔ Product Sessions و refresh handles را invalid می‌کند، reset_gate را به PENDING_REAUTH تغییر می‌دهد؛ commit باید **قبل از ارسال لینک** ثبت شده باشد. در قطعی DB هیچ لینک جدیدی از محصول آغاز نشود؛ بدون پذیرش عملیات anonymous spam.
2. Keycloak در محیط کنترل‌شده ایمیل تأییدشده را ارسال و credential را تغییر می‌دهد؛ اقدام واقعی باید از شاهد trusted credential-change مشخص شود، نه فقط کلیک روی لینک، ایمیل دریافت‌شده یا callback بازگشته. Tokenهای IdP قدیمی هنوز ممکن است زنده باشند؛ revoke محصول پیش‌دستانه مانع دسترسی به History می‌شود.
3. رفع reset_gate و صدور session جدید تنها پس از تطبیق epoch و شاهد **fresh credential authentication** مرتبط با تغییر جدید مجاز است. SSO cookie قدیمی حتی با Code+PKCE معتبر نباید gate را دور بزند؛ در صورت نامعلوم بودن ACR/AMR/auth_time یا معنی آن در Flow انتخابی، gate بسته می‌ماند و بازگشایی از طریق مسیر بررسی‌شدهٔ reauthentication/step-up انجام می‌شود.
4. Commit صدور session، epoch و active status باید زیر قفل/شرط CAS همان owner باشد. Callback یا Refresh شروع‌شده پیش از Reset اگر پس از bump commit کند باید 401/409 بدون session جدید برگردد؛ پاسخ/History in-flight نیز سیاست fencing مشخص و آزمون‌پذیر می‌خواهد.

**محدودهٔ فوریِ قابل طراحی:** پس از Commit ابطال در PostgreSQL محصول، هر درخواست جدیدی که **بعد از همان Commit** از session/epoch gate عبور کند باید رد شود (هدف منطقی 0 پنجرهٔ admission بعد از commit؛ **NOT_TESTED**). درخواست در حال اجرای پیش از commit، streaming و عملیات DB هم‌زمان نیازمند locking/linearization test است؛ صفرنشت تضمین‌شده هنوز اثبات نشده. این فقط Reset آغازشده از *محصول* را پوشش می‌دهد.

### 5.3. Reset خارج از محصول / admin / Account Console — راه‌حل مشروط و شکاف

**پیشنهاد وابسته به مجوز مستقل:** extension داخلی Keycloak 26.8.2 که در همان transaction تغییر credential، یک **monotonic credential_epoch per (issuer,subject)** و durable outbox با event_id پایدار، نوع/منبع تغییر و commit marker تولید کند. Consumer معتبر، private+mTLS/authenticated و idempotent، ترتیب را با epoch (نه ساعت رخداد) کنترل و در PostgreSQL محصول با atomic CAS افزایش revision + revoke تمام session rows + reset_gate ثبت کند. Duplicate با unique(event_id,issuer,subject,epoch) بی‌اثر؛ reorder فقط epoch بزرگ‌تر را اعمال کند؛ gap در توالی، شناسهٔ نامعتبر و clock conflict → fail closed، alert و reconciliation. Event شامل رمز، token، email body یا claims خصوصی نباشد.

**قرارداد لازم، نه قابلیت اثبات‌شدهٔ حاضر:** آیا Keycloak 26.8.2 روی *تمام* user-initiated Forgot/Reset، Account Console password change، UPDATE_PASSWORD required action، admin REST reset-password، و مسیر user federation/update credential همواره event و epoch اتمیک/قابل بازیابی صادر می‌کند؟ این در PR #13 و اسناد موجود ثابت نشده است. Extension/outbox/mapping جداگانه باید در محیط ایزوله حتی crash-before/after-commit، restart، lost/reordered/duplicated events، admin reset، failure of listener و upgrade اجرا شود. صرف event listener → محصول قابلیت تحویل تضمین‌شده نیست.

**برای جلوگیری از gap در Event:** Consumer heartbeat تنها health آن را نشان می‌دهد، نه گم‌نشدن یک رخداد خاص. لازم است authoritative persisted epoch در IdP به‌صورت authenticated / linearizable یا روش معادل **در نقطهٔ admission** قابل بررسی باشد؛ هنگام عدم دسترسی، stale/gap یا عدم قطعیت سری نسخه‌ها، BFF و FastAPI دسترسی و callback/refresh را fail closed کنند. اگر قفل/نسخهٔ معتبر در transaction تغییر credential و مقایسهٔ اتمیک در Product فراهم نشد، تعارض زمانی Cross-DB حل‌شده فرض نمی‌شود.

**حد تأخیر صریح:**
- از commit محلی Product revocation تا request admission جدید: **هدف نظری 0 ثانیه** فقط برای درخواست پس از commit با خواندن DB معتبر، هنوز NOT_TESTED.
- مسیر بیرون محصول با ابزار فعلی: **هیچ حد بالای تضمین‌شده‌ای وجود ندارد (worst-case نامحدود)**. حتی heartbeat پنج‌ثانیه‌ای، TTL کوتاه JWT، UserInfo، prompt=login، back-channel logout یا delivery هدف 30 ثانیه‌ای، فقدان کامل event را پوشش نمی‌دهد. **Proposed engineering SLO ≤30s** برای انتقال event *پس از تأیید outbox و reconciliation*، هرگز ضمانت فعلی نیست.
- **Production go/no-go:** تا زمانی که پوشش reset خارج از محصول، authoritative epoch، admission fencing، replay/SSO denial و failure behavior در Run واقعی آزموده نشده‌اند، مسیرهای Reset بیرونی باید رسماً غیرفعال/محدود با کنترل عملیاتی اثبات‌پذیر شوند؛ در غیر این صورت Auth product/Production **BLOCKED**. حتی مسیر Admin به‌عنوان bypass عملیاتی مستقل باید تحت همان پوشش قرار گیرد. اگر خاموش‌کردن تمام مسیرها قابل تضمین نباشد، هیچ تعهد زمانی و هیچ Gate احراز نشده است.

### 5.4. جدول وضعیت و خطا

| وضعیت | BFF/History/Callback/Refresh | عملیات |
|---|---|---|
| ACTIVE, session_epoch برابر، store healthy | فقط پس از کنترل کامل پاسخ | owner/RLS مجاز |
| REVOKED/RESET_PENDING/SUSPENDED/deleted یا session epoch قدیمی | 401/403، callback بدون session، refresh ممنوع | عدم اجرای History/Status یا replay |
| IdP outage در login/refresh یا نامعلوم بودن credential epoch | login/refresh fail closed؛ session موجود نیز اگر epoch reference لازم نامطمئن باشد 503/deny | بدون fallback به JWT یا fixed actor |
| Session store/database outage یا cache stale | 503 با no-store؛ نه 200 از cache و نه anonymous downgrade | نیاز به monitoring و retry محدود |
| listener lag/duplicate/reorder/gap | conservative revocation / PENDING_REAUTH و alert؛ replay با idempotency | عدم بازکردن reset_gate خودکار |
| concurrent callback-refresh-reset | DB lock/epoch CAS؛ Reset باید در ترتیب linearization غالب شود؛ old worker نمی‌تواند session تازه commit کند | آزمون interleaving الزامی |

## 6. بسته‌های اجرایی واگذارشونده (همه NOT_RUN)

| ترتیب / بسته | مالک و مسیر | وابستگی | پذیرش منفی/مثبت آینده |
|---|---|---|---|
| **BND-DB-01** owner/session foundation | **DB:** src/phase3/storage/postgres/**؛ infra/postgres/migrations/**؛ tests/phase3/integration/database/** | تصمیم immutable mapping، epoch و retention، شمارهٔ Migration، role non-BYPASSRLS | atomic unique issuer+sub، collision/reassignment reject؛ opaque hash session + rotation/CAS، deny-after-revoke، no epoch rollback و concurrent reset, RLS |
| **BND-IDP-02** credential change event proof | **API/Auth + IdP integration با مجوز جدید:** src/phase3/auth/** (قرارداد adapter)؛ infra/auth-ci/** فقط برای ارزیابی ایزولهٔ بعدی | نسخه Keycloak ثابت، owner/ops IdP، extension transaction/outbox و سطح دسترسی، تصمیم دسترسی Admin/Account reset | self-service/admin change event completeness, durable gap/replay/reorder/crash test, authoritative epoch, absence of stale SSO re-entry؛ بدون آن **BLOCKED** |
| **BND-API-BFF-03** trust / session / revoke | **UI مالک Server BFF:** apps/web/app/api/auth/** و apps/web/src/auth/server/**؛ **API مالک FastAPI:** apps/api/**، src/phase3/auth/**، tests/phase3/integration/api/** | DB01، event trust/reauth gate از IDP02، policy idle/absolute/CSRF/signed assertion | actual callback+PKCE issuer/state/nonce, no token in JS, secure Cookie+CSRF, mTLS/service proof and replay denial, reset/logout-all CAS, no direct API/owner spoof, fail closed |
| **BND-UI-04** UI integration | **UI:** apps/web/app/login/**، apps/web/app/history/**، apps/web/src/history/**، tests/phase3/integration/ui/** | BFF03، API History L1 existing contracts and DB01 | login/error/logout UX، mobile/RTL، expired session handling، no token in client, history identity routing |
| **BND-X-05** real OIDC integrated acceptance | **Foundation/Integration:** tests/phase3/integration/cross_component/**، tests/phase3/system/** | DB01+IDP02+BFF03+UI04، supervisor security sign-off | دو حساب OIDC واقعی ولی مصنوعی؛ separate subject→owner→RLS، history/Status leakage 0، reset concurrent callback/refresh, stolen cookie, CSRF, replay, wrong issuer/audience, admin privilege denial, chaos IdP/store; no false Gate PASS |

**قانون ترتیب:** DB01 برای توسعهٔ session و mapping؛ IDP02 برای پوشش تغییر اعتبارنامه؛ سپس BFF/API03 و UI04 با قرارداد ثابت؛ در آخر Integration05 و تأیید ناظر. می‌توان پژوهش محدود موازی داشت اما Integration و Gate پیش از پیش‌شرط‌ها ممنوع. برآورد عملکرد، حریم خصوصی، retention و ops در مأموریت جدا تصمیم می‌خواهند.

## 7. ماتریس آزمون‌های آینده و حدود پذیرش

| Test ID جدید (noncanonical؛ NOT_RUN) | ورودی/حمله | انتظار پذیرش |
|---|---|---|
| BND-T01 | دو مرورگر/دو کاربر واقعی OIDC مصنوعی، History cross-user، IDs و Cursor | owner درست با iss+sub؛ foreign 404، RLS zero leak |
| BND-T02 | State/Nonce/Code/PKCE replay، callback بدون initiator، invalid issuer/aud | همه reject؛ no session |
| BND-T03 | forged owner header/body/query، direct FastAPI، signed assertion jti replay، wrong body/method | no trusted actor و no data |
| BND-T04 | CSRF cross-origin/Fetch Metadata، cookie fixation/theft، disabled Secure/SameSite | mutating request deny؛ old rotated cookie reject |
| BND-T05 | logout one/all و concurrent in-flight transaction/refresh | بعد از linearization هیچ session epoch قدیمی اجازهٔ History نگیرد |
| BND-T06 | Reset product-initiated و external/admin؛ old SSO, old Access/Refresh/ID Token, new silent callback | همه نشست‌های محصول revoke و no silent recreate؛ هر رخداد گمشده/نامعلوم deny |
| BND-T07 | event replay/duplicates/reorder/drop/crash, queue lag >SLO, IdP/store outage | monotonic epoch، durable reconciliation یا fail-closed؛ هیچ stale session بی‌پروایی |
| BND-T08 | JWT امضاشده تا exp پس از logout/reset و UserInfo پاسخ مثبت | دسترسی History **صرفاً** با product session/epoch؛ denied even if JWT valid |
| BND-T09 | admin role forgery, Keycloak operator role vs product admin, MFA bypass | no blanket history/role bypass; step-up evidence checked |
| BND-T10 | access via status/read-only endpoints بعد از revoke و deletion pending | no information leak, no unauthenticated status bypass |

**ALL NEW BND-T01..T10 = NOT_RUN.** این ADR هیچ Schema، API، Code، SQL، IdP Extension یا Migration ایجاد نکرده و هیچ Product Auth، real-user operation، email واقعی، مدل یا production deploy انجام نداده است.

## 8. موارد لازم برای تصمیم ناظر

1. تصویب provider-neutral OIDC + Next.js BFF و session store مستقل محصول؛ تعیین اینکه extension داخلی Keycloak برای authoritative reset epoch مجاز/قابل نگهداری است یا مسیر دیگری باید آزمایش شود؛ تا آن زمان خارج از محصول Reset یک **BLOCKER** است.
2. تعیین امنیت/عملیات IdP، policy کنترل Admin/Account Console، پوشش تمامی password-change pathها، حضور support/owner و مجوز کار تخصصی مشترک DB/API/UI/Integration.
3. تصویب اعداد idle/absolute/step-up، max window Reset و نحوهٔ برخورد با fail-closed در خرابی‌ها با تست واقعی؛ SLO فرضی 30 ثانیه **قبولی نیست**.
4. تعیین retention/audit/privacy، Key rotation، TLS/host/SMTP deliverability و شرایط دسترسی کاربران ایران؛ هیچ انتخاب/هزینه/میزبانی قطعی وجود ندارد.

**Final design disposition:** READY_FOR_REVIEW — AUTH_SESSION_BOUNDARY؛ implemented=documentation, tested=new security/integration NOT_RUN, accepted=supervisor pending؛ بدون Merge مستقل یا تغییر Gate.
