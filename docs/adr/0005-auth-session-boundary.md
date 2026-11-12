# ADR 0005 — مرز نشست، ابطال و اتصال هویت OIDC به محصول

**Status 2026-11-13:** DECIDED_INITIAL_LOGIN_OPTION_B / DOCUMENT_ONLY / NEW_TESTS_NOT_RUN / NO_MODULE_GATE. بخش ۹ **تصمیم جدید ناظر** است و در مرز ورود اولیه بر پیشنهاد قدیمی 2026-11-09 در بخش‌های ۱–۸ اولویت دارد؛ سیاست Cookie/CSRF، Session TTL و Production grants هنوز بازند. نه Auth محصول و نه Production/Gate پذیرفته نشده‌اند.

**Mission:** AGENT-API-AUTH-BOUNDARY-01؛ **Starting main:** 97293558bc80953bd88e98e81166a8da745a2207؛ **branch:** prep/auth-session-boundary؛ **Date:** 2026-11-09؛ **Decision owner:** ناظر «مغز فاز سوم». این سند ADR 0004 را برای مرز اجرایی تکمیل می‌کند؛ انتخاب نهایی IdP، منطقهٔ میزبانی و قرارداد عملیاتی نیست.

## 1. مبنا و حدود اعتبار

- [ADR 0004](0004-auth-options.md) الگوی استاندارد OIDC Authorization Code + PKCE و نشست سروری Next.js BFF را مشروطاً ترجیح داده؛ مقایسهٔ ارائه‌دهندگان تکرار نمی‌شود. هدف نخست ایمیل+رمز با verify/reset است؛ افزودن شناسه یا OTP عمومی به آینده موکول است.
- [PR #13](https://github.com/Shahbazi-Amir/RAG_finance_app/pull/13) در merge 97293558bc80953bd88e98e81166a8da745a2207 با HEAD پذیرفته‌شدهٔ 975062681e8124e65f72cda3338cf4cfa4a3c782 ادغام شد. CI محدود: [Run 42617144329](https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/42617144329)، کد آزموده‌شده 835bd417ede49184caa93f36bbfcc8d7bac12a3a، Keycloak 26.8.2، PostgreSQL هویت 17.11، Mailpit 1.32.0، Chromium مصنوعی. این‌ها **IdP ایزوله** هستند، نه Auth محصول.
- **اندازه‌گیری مهم:** پس از Reset رمز در این پیکربندی، مرورگر قدیمی با prompt=none موفق به گرفتن Code جدید شد، Refresh Token قبلی HTTP 200، UserInfo با Access Token قبلی HTTP 200 و امضای JWT پیش از انقضا معتبر ماند. پس از **Logout مدیریتیِ جداگانه**، Refresh HTTP 400 و UserInfo HTTP 401 شدند، ولی امضای محلی JWT تا پیش از exp همچنان معتبر بود. هیچ کدام ابطال Cookie محصول را اثبات نمی‌کنند.
- وابستگی نقشه: Module 05 فعالیت‌های **P3M05-A03/A04/A05/A07/A08/A09/A10**، همچنین A06 سیاست Brute Force؛ Module 03 تعریف Error/Request/Trace/Contract و تفکیک Domain؛ Module 06 RLS و user context هر Transaction، cross-user/ID enumeration؛ Module 13 Authorization هر Endpoint و نسخه‌بندی API. ماژول‌های 00، 03، 05، 06 و 13 هیچ Gate تازه‌ای PASS نمی‌گیرند.
- محدودیت قرارداد NB23 همچنان ورودی Draft فقط contract_version و question است؛ هیچ History/owner/context بی‌اجازه به موتور تزریق نمی‌شود.

## 2. انتخاب پیشنهادی مشخص و مرز مالکیت

**تصمیم Option B برای ورود اولیه:** Next.js **BFF** مالک آغاز Login، Callback مرورگر، initiator binding، shared alias store و Cookie است. **API/FastAPI مالک انحصاری Authorization Code exchange با PKCE S256، اعتبارسنجی IdP JWKS/claims، mapping معتبر issuer+subject و صدور مشروط Product Session** است. پیش از ایجاد نخستین نشست، BFF→API نیازمند احراز خدمت مستقل است. صدور با Registry یکتا و نشست PENDING_BINDING آغاز می‌شود؛ فعال‌سازی اتمیک بعد از ACK ثبت پایدار Alias در BFF و **قبل از ارسال Cookie** انجام می‌شود. PostgreSQL محصول با RLS منبع حقیقت می‌ماند؛ Keycloak انتخاب Production محسوب نمی‌شود. بخش ۹ معیار حاکم بر پیاده‌سازی آینده است.

| مسئول / دامنه | مسیر دقیق **پیشنهادی برای بستهٔ بعدی** | مرز |
|---|---|---|
| UI (مالک Next.js server/BFF و صفحهٔ ورود) | apps/web/app/api/auth/login/route.ts، apps/web/app/api/auth/callback/route.ts، apps/web/app/api/auth/logout/route.ts، apps/web/app/api/auth/logout-all/route.ts، apps/web/src/auth/server/**، apps/web/app/login/page.tsx | OIDC، Cookie، CSRF، Session bootstrap، redirect allowlist و رندر؛ هیچ JWT به Client JS |
| API (مالک اعتماد سمت FastAPI) | apps/api/history_api.py با تغییر محدودِ مأموریت آینده و src/phase3/auth/** برای dependency تأیید BFF | پذیرش identity assertion فقط از خدمت معتبر؛ مجوز هر Endpoint و lookup session/owner؛ نه جایگزینی Schema عمومی |
| DB (مالک Schema و Session persistence) | src/phase3/storage/postgres/** و infra/postgres/migrations/** با شمارهٔ Migration بعد از بررسی زنجیرهٔ موجود | issuer+sub unique mapping، session rows، epoch/tombstone/nonce/replay، تراکنش و RLS؛ **نه** پوشهٔ موازی جدید |
| Foundation / Integration | tests/phase3/integration/cross_component/** و بستهٔ قرارداد مستقل پس از مجوز؛ coordination/phase3_checklist.md فقط Foundation | integration واقعی، adversarial security، reconciliation و Gate، نه کار مشترک بی‌مالکیت |

این مسیرها **تعهد پیاده‌سازی فعلی نیستند**؛ مالک UI کد BFF را می‌نویسد، API صرفاً قرارداد/بازبینی مرز را هماهنگ می‌کند، DB مالک SQL می‌ماند. هیچ مسیر یا فایل پیشنهادی در این PR ایجاد نشده است.

### معماری جریان درخواست

1. مرورگر تنها به Origin محصول با HTTPS دسترسی دارد؛ Login یک initiation record سمت سرور شامل state تصادفی تک‌مصرف، nonce، PKCE verifier رمزگذاری‌شده، redirect مقصد ثابت/allowlist، زمان انقضا و binding به Cookie موقتِ HttpOnly دارد. **Authorization Code فقط به callback سروری** برمی‌گردد.
2. Next BFF Callback فقط state/Code یکتا، initiator Cookie واقعی، سن Challenge و issuer بازگشتی را نسبت به رکورد مشترک بررسی می‌کند؛ سپس Code/State و initiator digest را با **bootstrap service proof مستقل** به API می‌فرستد. API حق claim یکتای Code exchange را از Registry می‌گیرد، خودش با PKCE S256 token exchange انجام داده و nonce، iss/aud/iat/exp/sub، signature/JWKS و policy email_verified را بررسی می‌کند. تکرار/خطا → بدون Session. جزئیات در بخش ۹.
3. نگاشت **(iss,sub)** معتبر به internal_owner_user_id در DB تراکنشی upsert می‌شود؛ email/phone/username فقط contact هستند، **هرگز primary linking key**. unique(issuer,subject)، immutable internal owner، collision → fail closed، حذف/تعلیق در وضعیت کاربر مستقل بررسی شود.
4. API فقط یک Product verifier خام را پس از Commit نشست PENDING_BINDING از کانال خصوصی احراز‌شده به BFF می‌رساند. BFF یک Browser handle تصادفی مجزا حداقل 256-bit با alias→encrypted verifier در **Shared BFF Store** و وضعیت NOT_SERVE ثبت پایدار می‌کند؛ پس از ACK و Commit فعال‌سازی اتمیک در API/DB، **و نه پیش از آن** Cookie/303 صادر می‌شود. هیچ IdP Token/Code یا raw Product verifier در JS، localStorage، URL، Error یا لاگ مرورگر قرار نمی‌گیرد.
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

**تبصرهٔ 2026-11-13:** جدول زیر سابقهٔ برنامهٔ 2026-11-09 است. وابستگی BND-IDP-02 و C2 برای بازگشایی *پس از Reset* باقی است و **شرط ورود معمولی نیست**. توالی جدید initial login در بخش ۹: Migration 009 → API private/bootstrap → UI Callback/ACK/Cookie، سپس آزمون مشترک.

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


## 9. تصمیم ناظر — Option B: one-issue Registry و ACK-before-Cookie (2026-11-13)

**Stable ID:** FND-ADR0005-OPTIONB-01. این تصمیم مالکیت و قرارداد ورود اولیه را تعیین می‌کند، **نه اجرای پذیرفته‌شده**. ارجاع به شناسه‌های موجود P3M05-A01/A03/A04/A05/A07/A08/A10، P3M06-A03/A05/A07، P3M13-A03/A07/A08 و P3M14-A01 است؛ ردیف یا Gate تازه ایجاد نمی‌شود. IMPLEMENTED=DOCUMENTATION_ONLY، NEW_SQL/API/UI/CI=NOT_RUN، ACCEPTED_GATE=NO.

### 9.1. شواهد مبنا و مرز تصمیم

- [API Draft #40](https://github.com/Shahbazi-Amir/RAG_finance_app/pull/40) در HEAD `ddc2f2f4424f548df50047ce7eb7209584d6bdb7`، سند API-AUTH-NEXT-PRIVATE-CONTRACT-01؛ [Run #43318211274](https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/43318211274) روی SHA آزموده‌شده `59a1ae76c71337cbddbe6759f93a1a7402334b7c`، 108/108 PASS با Keycloak 26.8.2 و PostgreSQL 17.11 ایزوله: INIT01–04، واقعی Code+S256/JWKS، nonce/state، دو مالک ثابت و صدور اولیهٔ Session. این آزمون **HTTP bootstrap، Registry بادوام، ACK یا مرورگر واقعی را اثبات نمی‌کند**.
- [UI Draft #41](https://github.com/Shahbazi-Amir/RAG_finance_app/pull/41) در `babdcfcdef4cf274a2a555a9a2e0bab0ac5cbdc5`، UI-AUTH-BFF-PLAN-01، صرفاً طراحی Next Login/Callback/Logout، Cookie و ۱۶ تست آینده UI-AUTH-P01..P16، **NOT_RUN**. هرجا طرح قبلی Next را سازندهٔ PKCE/nonce می‌خواند، با این تصمیم API آن دو را تولید/نگهداری می‌کند و Next فقط binding به Initiator را برقرار می‌سازد.
- [DB Draft #42](https://github.com/Shahbazi-Amir/RAG_finance_app/pull/42) در `4bc1ac42b68996bdabbf94ab942ba367ddfd927c`، DB-AUTH-BOOTSTRAP-REVIEW-01، ۱۶ آزمون پیشنهادی DBL01..DBL16 و توصیهٔ PENDING_BINDING، **DESIGN_ONLY/NOT_RUN**. SQL کنونی 003 فقط active/rotated/revoked و revoke_one برای active دارد؛ 004 فقط active را می‌پذیرد و 005 ضد Replay JTI سرویس است، نه Registry صدور Login.
- [H1 #39](https://github.com/Shahbazi-Amir/RAG_finance_app/pull/39)، [Run #43315447479](https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/43315447479) آزمون مشترک محدود GET /v1/conversations با امضاکنندهٔ موقت، PostgreSQL revoke و 401 واقعی بود؛ **نه اثبات OIDC، دیگر History endpoints یا Gate**.
- **رفع تعارض ADR:** در ورود اولیه، Next.js BFF مالک front-channel Callback و Cookie است ولی **API تنها مالک Authorization Code redemption و cryptographic IdP validation** است. عبارات قدیمی بخش ۲ و جدول تاریخی بخش ۶ در این نقطه superseded هستند. Reset/C2 مستقل و NOT_PROVEN؛ شاهد امنیتی منفی #33 با SECURITY_BYPASS_REPRODUCED محفوظ است.

### 9.2. مالکیت، اعتماد اولیه و قرارداد PRIVATE

| مالک | مسئولیت معتبر | منع صریح |
|---|---|---|
| **Next.js BFF / UI** | POST آغاز Login با anti-login-CSRF، Origin و Cookie آغازگر Host-only/HttpOnly، shared Initiator→Attempt binding، GET Callback با یک Code/State و issuer مجاز، server-to-server call به API، durable shared encrypted Alias، ACK و سپس Cookie/303، Logout | نمی‌تواند Token/JWKS IdP را دوباره اعتبارسنجی یا از Browser owner/issuer/redirect آزاد/PKCE verifier بگیرد؛ Product verifier خام هرگز Browser Cookie نیست |
| **API / Auth** | ساخت server-held state، nonce، PKCE verifier/S256 و allowlisted IdP metadata؛ Registry، unique claim Code، IdP token exchange و JWKS/signed claims validation؛ verified issuer+subject→immutable owner؛ issue Pending و ACK/ABORT | Code/IdP token به Next/Browser یا Secret به log نمی‌دهد؛ InitialChallenge.used حافظهٔ یک Worker جای Registry مشترک نیست |
| **DB / PostgreSQL** | Registry با UNIQUE attempt/receipt/digest، Session PENDING_BINDING، Owner epoch/gate CAS، atomic ACK/ABORT، cleanup/roles | Registry-only کنار Session از ابتدا Active بدون guard مشترک با 003/004 مجاز نیست؛ تغییر 003–008 در این مأموریت ممنوع |
| **Foundation/QA** | نسخه‌بندی مرز خصوصی، cross-component negative tests و ثبت Evidence | بدون تغییر public product.v1، هیچ Gate یا اسکن تولیدی به‌صرف این ADR پاس نمی‌شود |

**Pre-session BFF service authentication جدا است:** هیچ Product session_ref/owner_id/epoch هنوز وجود ندارد؛ BFFServiceVerifier و TrustedSession قدیمی که session-bound هستند را با identity جعلی استفاده نکنید. Next→API فقط کانال داخلی HTTPS + **mTLS با client certificate identity معتبر** همراه RS256 bootstrap assertion مستقل با purpose=initial_oidc_bootstrap، allowlisted iss/aud/kid و key rotation، unique JTI، iat/nbf/exp کوتاه (حد بالای 30 ثانیه صرفاً پیشنهاد)، method، exact raw path/query/body hash+length، BFF principal و initiator binding دارد. API قبل از Registry mutation TLS principal/signature/purpose/replay را مستقل verify می‌کند؛ نامعتبر → 401. اگر 005 برای JTI استفاده شود، namespace و role مجزا و تأییدشده می‌خواهد و جای احراز خدمت یا one-attempt uniqueness نیست. Browser حق فراخوانی این private RPC، انتخاب Owner یا ارسال Session proof از خودش ندارد.

**Private contract namespace:** `private.auth.bootstrap.v1` با مسیرهای پیشنهادی `POST /internal/auth/oidc/v1/start`، `/complete`، `/status`، `/ack` و `/abort`؛ فقط قرارداد سرور↔سرور، هنوز Route موجود نیست. Strict JSON/request validation، no redirects، no-store، size/deadline bounds، redacted generic errors، trace/request ID. Public `product.v1` و `packages/contracts/product.v1.schema.json` **دست‌نخورده و byte-identical** می‌مانند.

| RPC خصوصی | ورودی و تعهد پیشنهادی |
|---|---|
| **START** | signed BFF principal، bff_attempt_id و caller-scoped start_idempotency_key، HMAC initiator-binding digest، return/provider allowlist alias؛ API یک login_attempt_id/state و server-held nonce/PKCE + challenge S256 در Registry پایدار می‌سازد، تنها safe authorize URL/State/Attempt/expiry به BFF برمی‌گردد؛ retry با payload fingerprint یکسان یک نتیجه، conflict=409 |
| **COMPLETE** | یک Code+State، attempt/initiator و original signed BFF principal؛ Next Callback قبل از ارسال strict state/initiator/callback iss را چک می‌کند؛ API unique exchange claim و S256/JWKS/iss/aud/exp/iat/nonce/sub و policy email_verified را verify می‌کند و pending Session با **حداکثر یک receipt/Session در هر Attempt** Commit می‌کند. یک پاسخ private نخست شامل receipt، ISSUED_PENDING_BINDING، owner/epoch/generation و **Product verifier خام فقط به BFF authenticated** است؛ retry نه second exchange و نه second issue |
| **STATUS** | همان BFF principal، original initiator/attempt/operation binding؛ فقط state داخلی INITIATED/EXCHANGE_STARTED/ISSUED_PENDING_BINDING/ACTIVE/FAILED/UNKNOWN_RECONCILIATION_REQUIRED/EXPIRED/ABORTED و metadata محدود همان caller. **هرگز raw Product verifier، Code، nonce، PKCE verifier، IdP token یا Browser handle را برنمی‌گرداند**؛ هیچ status عمومی یا credential recovery بدون escrow مصوب |
| **ACK** | فقط بعد از **durable Commit** Alias به shared BFF store، handle_digest→encrypted همان verifier با وضعیت NOT_SERVE؛ signed original receipt/attempt و keyed alias confirmation digest، BFF principal و expected epoch. DB در یک TX Owner→Registry→Session CAS هر دو Registry ISSUED_PENDING_BINDING→ACTIVE و Session PENDING_BINDING→active را Commit می‌کند؛ **تنها پس از ACK قطعی و قبل از Set-Cookie، فعال‌سازی تأیید شود**. ACK اثبات Cookie delivery نیست |
| **ABORT** | قبل از فعال‌سازی و در alias-write failure/withdrawal: 009 abort_pending اختصاصی با Owner-first lock، pending Session→revoked و Registry→ABORTED، tombstone و receipt invalidation، بدون Cookie. 003 revoke_one فقط نشست Active را revoke می‌کند و جای این تابع نیست. اگر ACK اول ACTIVE شده باشد ABORT conflict؛ مسیر عادی Logout/revoke_one جدا لازم است |

Response mapping پیشنهادی (freeze آینده): 201 first transition، 200 safe exact duplicate/receipt، 202 فقط UNKNOWN با وضعیت durable و no Cookie، 400/422 malformed، 401 invalid bootstrap proof، 403 forbidden principal، 409 duplicate conflict/stale epoch/terminal mismatch، 410 expired، 503 dependency unavailable. Callback Browser فقط generic error و 303 به مسیر allowlisted؛ no raw IdP errors.

### 9.3. Registry و پایان‌های نامعلوم / همزمانی

**Migration 009 پیشنهادی آینده:** `009_initial_login_attempt_binding.up.sql` + `.down.sql`؛ جدول `auth_l1.initial_login_attempts` با UUID PK غیرقابل‌حدس، UNIQUE روی جفت BFF principal/attempt و principal/idempotency، payload fingerprint، unique state digest، unique receipt و session_digest با FK، issuer/client/redirect pinned، encrypted nonce/PKCE، expected owner/epoch تنها پس از IdP verification، monotonic state version و timestamps/expiry/tombstones. **هیچ raw Product verifier، Code، IdP token، Cookie یا Email در Registry.** فقط یک Session digest/receipt به هر Login Attempt وصل می‌شود. تغییر CHECK status جدول Sessions برای **PENDING_BINDING در خود Session** در 009؛ Registry تنها بدون کنترل همهٔ inspect/touch/rotate/004 امن نیست. 003/004 فقط active را قبول می‌کنند، ولی این رفتار بعد 009 باید با PG17 واقعی اثبات شود. مهاجرت‌های 003–008 و product.v1 فعلاً تغییر نکنند.

**State machine Registry:** INITIATED → EXCHANGE_STARTED → ISSUED_PENDING_BINDING → ACTIVE؛ terminal/failed/expiry: FAILED، EXPIRED، ABORTED، UNKNOWN_RECONCILIATION_REQUIRED. **Session:** absent → PENDING_BINDING → active، یا Pending → revoked با ABORT/cleanup. EXCHANGE_STARTED و Pending دو مرحلهٔ جدا هستند؛ هیچ status terminal به Active برنمی‌گردد.

1. **T0 START:** mTLS/Bootstrap proof و replay validation، Registry durable UNIQUE/idempotency و TTL در DB TX کوتاه.
2. **T1 Claim:** Registry FOR UPDATE و state/version CAS، INITIATED→EXCHANGE_STARTED؛ **COMMIT قبل از IdP HTTP**. دو Worker فقط یک exchange owner دارند. Lease expiry یا Code timeout حق replay Code دوم نمی‌دهد.
3. **T2 IdP:** فقط Worker برنده با server-held PKCE به IdP می‌رود؛ **هیچ PG transaction یا Owner lock حین HTTP باز نیست**. Token+claims معتبر یا FAILED؛ نتیجهٔ نامعلوم شبکه/Crash = UNKNOWN_RECONCILIATION_REQUIRED و no automatic Code retry یا issue.
4. **T3 Issue:** verified issuer/sub را با role محدود map_identity می‌کند؛ حتی اگر map در TX جدا باشد، Issue باید **Owner FOR UPDATE ابتدا**، gate=open، active Owner، matching epoch و immutable mapping را recheck کند؛ سپس Registry FOR UPDATE، Session INSERT(status=PENDING_BINDING) و unique receipt/session_digest در **همان TX** Commit شود. Constraint/CAS مانع issuance دوم پس از lost response می‌شود.
5. **T4 BFF Alias/ACK:** BFF shared encrypted alias را **durably commits** در NOT_SERVE؛ signed ACK ثابت و receipt-bound به API؛ در TX با Owner→Registry→Session، Epoch/Gate CAS و Registry+Session را اتمیک ACTIVE می‌کند. بدون ACK قطعی **no successful Cookie/303**.
6. **T5 Cookie:** پس از ACK، Set-Cookie مستقل از Product verifier صادر می‌شود؛ delivery به Browser با Product DB/BFF store اتمیک نیست. ACK فقط اعلان authenticated BFF از durable alias write است، نه تضمین رسیدن Cookie. Alias فعال اما unclaimed با TTL/heartbeat و revoke واقعی Product cleanup شود.

**قفل سراسری:** T0/T1 فقط Registry و TX کوتاه؛ در مراحل دارای Owner ترتیب یکتا **Owner→Registry→Session** (Owner FOR UPDATE) برای Issue/ACK/ABORT/Sweeper؛ با 003 revoke و 004 Owner/Session fences سازگار، ولی نبود Deadlock و race با دو Connection و pg_blocking_pids باید واقعاً آزموده شود. Registry را در یک TX قفل نکنید و بعد منتظر Owner در همان TX بمانید.

**Timeout/Restart/Repeat:** مبهم‌شدن Code redemption یا crash پس از token endpoint یعنی UNKNOWN؛ **Code یا Session دوم برای همان Attempt صادر نشود**، login تازه فقط پس از disposition بستهٔ قبلی. گم‌شدن پاسخ Issue پس از Commit یعنی pending باقی، STATUS فقط state/receipt بدون Secret؛ digest verifier خام را بازیابی نمی‌کند؛ escrow در طرح حداقلی **وجود ندارد** و هر one-time encrypted escrow نیاز به تصویب مستقل امنیتی دارد. Pending تا ABORT/cleanup قابل History admission نیست. گم‌شدن ACK response یعنی retry ACK با **JTI تازه ولی receipt/principal/alias برابر** فقط برای reconciliation؛ تا نتیجهٔ قطعی no Cookie. عدم قطعیت ABORT نیز no Cookie + bounded reconciliation/cleanup.

**Idempotency terminal:** ACK همان receipt/alias بعد از ACTIVE پاسخ ثابت بدون mutation؛ ACK با alias دیگر، epoch/gate کهنه، پس از ABORTED/FAILED/UNKNOWN یا Session revoked=409/deny، نه revive. ABORT همان receipt بعد از ABORTED ثابت؛ ABORT برنده → ACK ممنوع؛ ACK برنده → ABORT conflict و برای logout باید ACTIVE revoke_one انجام شود. 003 revoke_one نشست Pending را نمی‌تواند ABORT کند. Revoke_all/Reset اگر epoch را پیش از Issue/ACK bump کند، pending هرگز Active نمی‌شود؛ sweeper با قفل Owner-first آن را terminal می‌کند. اگر ACK زودتر Commit شود، revoke_one/revoke_all بعدی با Lock واقعی Active را revoke می‌کند؛ 004 admission تازه پس از revoke commit را رد می‌کند، نه الزاماً SQL پذیرفته‌شدهٔ قبل از Commit را.

**Cleanup:** Registry و Pending abandoned/expired با function-only sweeper، terminal tombstone، TTL/retention و audit بدون Secret؛ UNKNOWN هیچ وقت به blind reissue تبدیل نشود. Pending expired پیش از ACK status revoked و late ACK denied؛ ACTIVE orphan ناشی از Cookie گمشده باید با Product revoke واقعی پاک شود. 009.down در DB دارای attempt/receipt/session evidence **fail closed** کند، نه حذف خاموش داده.

### 9.4. سیاست‌ها و Production permissionهای هنوز باز

| موضوع | تصمیم/شاهد جداگانهٔ لازم |
|---|---|
| **Session policy** | idle/absolute/refresh/rotation/step-up/clock/alias TTL و disabled account؛ اعداد قدیمی idle=30m، absolute=12h و step-up=5m صرفاً PROPOSED/NOT_APPROVED. سیاست verified-email از claim معتبر و account linking با تصویب مستقل |
| **Cookie/CSRF** | نام پیشنهادی `__Host-session` با Secure/HttpOnly/Path=/بدون Domain و SameSite=Lax، initiation cookie، Origin/Fetch Metadata/synchronizer، callback top-level GET، stale Cookie/multitab/lost-303. Cookie/CSRF واقعی در #41 آزموده نشده و صرفاً طرح است |
| **IdP/bootstrap** | Production issuer/client/redirect/JWKS allowlist، trust roots/mTLS/certificate rotation، purpose-bound proof/JTI expiry، policy email_verified، secret custody و hosting/ops. #40 CIِ ایزوله انتخاب Production را ثابت نمی‌کند |
| **DB permissions** | Roles جدا برای map، pre-session bootstrap، restricted pending issue/ack/abort، cleanup، active revoke و History replay/fence؛ NOSUPERUSER/NOBYPASSRLS/NOINHERIT، EXECUTE فقط functionهای مشخص SECURITY DEFINER با fixed search_path و PUBLIC revoked، بدون direct table grants؛ role-matrix negative tests و backup/retention. grants موقت CI #36–#39 **Production permission نیستند** |
| **Reset/C2** | C2=NOT_PROVEN و #33 SECURITY_BYPASS_REPRODUCED؛ only post-Reset fresh-auth/reopen مستلزم C2، نه ordinary initial Login، ordinary Logout یا isolated History. هیچ C2/Gate به‌واسطهٔ این تصمیم پذیرفته نمی‌شود |

### 9.5. سه مرحلهٔ اجرا و معیار پایان (همه آینده/NOT_RUN)

| ترتیب و مالک | پیش‌نیاز | Done لازم با شواهد |
|---|---|---|
| **1) DB — Migration 009** | قرارداد Option B، Registry/epoch/Role semantics مصوب، owner DB و مأموریت مستقل | `009_initial_login_attempt_binding.up/down.sql` با unique attempt/receipt/digest، Session PENDING_BINDING، Owner→Registry→Session CAS، atomic ACK/ABORT و cleanup، 004 pending-denial، least-privilege، rollback امن؛ **DBL01..DBL16** شامل multi-worker/PG17/pg_blocking_pids و Run/Job/SHA واقعی green |
| **2) API — private OIDC Bootstrap** | 009 tested، service identity/mTLS و issuer/verified-email policy مشخص، #40 تنها reuse اولیه | private START/COMPLETE/STATUS/ACK/ABORT versioned، API-only Code+S256/JWKS و verified issuer/sub، unique attempt، unknown/idempotent/epoch negatives، no raw verifier in STATUS/log، browser-actor injection denied؛ real concurrent API/PG CI و SHA/Run/Job |
| **3) UI — Next Callback/Binding/Cookie** | API contract green، shared alias/CSRF/Cookie policy مصوب و stored alias durable | strict browser initiator/state/callback، encrypted NOT_SERVE alias → ACK قطعی → Cookie/303، logout/revoke و 401 privacy، rejected stolen/old handle، lost response/orphan cleanup، دو مالک و Chromium desktop/mobile **UI-AUTH-P01..P16** با CI API/PG و SHA/Run/Job |

Foundation پس از این مراحل آزمون مشترک واقعی را جدا بررسی می‌کند؛ #39 فقط GET فهرست است و اثبات همهٔ مسیرهای History یا Product Login نیست. ورود اولیه به C2 و NB23 runtime وابسته نیست؛ Release/NB23/Gate00 مسیر جدا برای RAG/stream/citation است. **هیچ SQL، Route، UI، Workflow، public product.v1، canonical checklist، Gate، Merge یا Deploy در این Draft مستندی تغییر نمی‌کند.**
