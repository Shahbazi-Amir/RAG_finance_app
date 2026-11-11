# ADR 0006 — پروتکل اجرایی Reset کنترل‌شده و فنس ابطال نشست محصول

**Status:** PROPOSED / READY_FOR_REVIEW — CONTROLLED_RESET_EXECUTION_PLAN. **Implemented:** DOCUMENTATION_ONLY؛ **Tests:** تمام آزمون‌های این ADR `NOT_RUN`؛ **Accepted:** NONE / SUPERVISOR_PENDING. هیچ Product Session revocation، Reset API، Migration یا Gate جدیدی پیاده‌سازی/پذیرفته نشده است.

**Mission:** `CONTROLLED-RESET-PLAN-01`؛ **Repository:** `Shahbazi-Amir/RAG_finance_app`؛ **baseline main:** `6d7ad5320267e4a10a0bf458f954023f89a25d8c`؛ **branch:** `prep/controlled-reset`. این ADR، [ADR 0005](0005-auth-session-boundary.md) را برای ترتیب دقیق اجرا تکمیل می‌کند؛ آن را جایگزین یا به یک تصمیم production تبدیل نمی‌کند. در فهرست main تا ADR 0005 موجود بود و شمارهٔ آزاد 0006 انتخاب شد.

## 1. تصمیم قطعی ناظر، شواهد و دامنهٔ تضمین

**تنها مبنای مجاز برای بستهٔ بعدی:** Realm مصنوعی/آینده‌ای که تنظیمات نهایی منع self-service credential change، Account Console و Required Action و مجوزهای FGAP **قبل از ایجاد اولین نشست/جریان/لینک Reset** روی آن برقرار و readback شده‌اند. **انتقال Realm قدیمی با جریان‌های از پیش باز پشتیبانی نمی‌شود.** migration/retroactive cancellation، fallback خودخدمتی یا تضمین صفر برای هر مسیر ناشناخته ممنوع است.

**واقعیت ادغام‌شدهٔ PR #23:** همان head آزمون‌شده `0ca98d70defc7ef6cc250686b08f62dc57441571` و head مستندی نهایی `8546e4dcfcf7d2f38e02379a513f976923cd4caa`، پس از merge در `main 6d7ad5320267e4a10a0bf458f954023f89a25d8c`. [Run مستقل PR #42923509560](https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/42923509560): `clean-bootstrap-idp` **SUCCESS**، [artifact 13811749362](https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/42923509560/artifacts/13811749362)؛ `isolated-idp` **FAILURE**، [artifact 13812198795](https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/42923509560/artifacts/13812198795)، با واقعیِ `inflight-form` و `inflight-form-after-logout-all`. کل workflow **FAILURE**. Clean فقط روی یک حساب هدف و حساب‌های خارج از دامنه، User→AuthZ Resource `_id`→Permission→Scope `reset-password`→Policy خدمت را اثبات کرد، نه اتوماسیون permission برای کاربران بعدی یا Product Sessions. `CLEAN_BOOTSTRAP_CONTROLLED_RESET=PROVEN` تنها به همین آزمون مصنوعی محدود است؛ `TRANSITION_WITH_PREEXISTING_FLOWS=NOT_PROVEN`.

**منبع حقیقت محصول** PostgreSQL محصول است، نه PostgreSQL Keycloak؛ تأیید Authentication در IdP به‌تنهایی مجوز ساخت Session محصول نیست. این سند مدل طراحی قابل‌واگذاری است، نه تضمین cross-database atomicity، تحقق event/outbox، استقرار، یا قابلیت Auth واقعی.

## 2. موجودی رابط واقعی و شکاف‌ها (بدون بازتعریف قرارداد)

| شواهد موجود در main | توان واقعی | چیزی که هنوز وجود ندارد |
|---|---|---|
| Migration 003 و `auth_session.revoke_all(conn,owner_id,expected_epoch)` | در transaction یک owner-epoch را CAS افزایشی کرده، `reset_gate=pending_reauth` و نشست‌های فعال را revoked می‌کند؛ privilege `auth_revoker` | عملیات شناسه‌دار Reset، یک‌بارمصرفی Recovery، مقایسهٔ نتیجه IdP، fresh-auth product |
| Migration 004 و `admit_session_fenced` | Lock به ترتیب Owner `FOR SHARE` سپس Session `FOR SHARE`، بررسی epoch/generation/status/gate/expiry **بعد از locks**؛ فقط در همان outer PostgreSQL TX | فنس شبکه/IdP یا cancel خودکار درخواست قبلاً admitted |
| Migration 005 و `PostgresDurableReplayStore.consume` | درج SHA256(verified service issuer + NUL + JTI)، replay assertion BFF→FastAPI داخل همان TX، pre/post-lock clock guard | idempotency عملیات Reset یا استفادهٔ دوباره از recovery proof؛ JTI هر network attempt جداست |
| `transactional_admission.protected_operation` | RSA-verification→JTI→session-aware fence→final DB-clock→protected SQL در یک TX؛ CI synthetic | اتصال واقعی به History API/BFF و cross-DB orchestration |
| `finish_simulated_reauth` و role `auth_reauth` | صرفاً Fixture/SQL بازکردن Gate با epoch، **بدون اعتبارسنجی IdP** | هیچ مسیر عملیاتی معتبری برای بازکردن Gate وجود ندارد |

**نتیجه:** DB مالک extension در Migration آینده و policy access است؛ API مالک coordinator و IdP delegation؛ UI مالک BFF/Recovery/Cookie و تجربهٔ کاربر. **هیچ کدام در این مأموریت نوشته نشده‌اند.**

## 3. اثبات مجوز؛ دو ورودی مستقل

### 3.1. بدون نشست: `RECOVERY`

1. `POST recovery/request` با **ایمیل تنها** همواره پاسخ عمومی یکسان/بدون افشای حساب می‌دهد (و abuse control می‌خواهد). **هیچ session_epoch، reset_gate، session row یا IdP password عوض نمی‌شود.** ایمیل، اثبات مالکیت نیست؛ timing/status/user enumeration باید آزموده شود.
2. سرویس بازیابیِ آینده، challenge تصادفی پرآنتروپیِ تک‌مصرف را فقط به **کانال تأییدشدهٔ متعلق به (issuer,sub) نگاشت‌شده** می‌رساند؛ قابلیت فعلی/ارسال ایمیل در این مأموریت وجود ندارد. مالکیت (issuer,sub) از lookup معتبر DB به دست می‌آید؛ lookup ایمیل هرگز owner selection مبتنی بر درخواست عمومی نیست. هنگام mismatch, disabled, suspended یا ambiguity: **deny/fail closed**. اطمینان تحویل، نحوهٔ اعتبارسنجی mailbox، تعویض ایمیل و recovery compromise تصمیم عملیاتی باز هستند.
3. فقط **redeem سروری token اصلی** با اثبات nonce/challenge معتبر، single-use، audience/purpose/owner/realm binding و server-clock expiry *که مقدارش هنوز تصمیم نشده*، حق ورود به مرحلهٔ Commit را دارد. نشانی ایمیل، `request_id`، Link-view، دریافت SMTP یا OIDC Callback به‌تنهایی authorization نیست.
4. در همان transaction اصلی DB، ردیف credential authorization lock و **CAS از ISSUED→CONSUMED** هم‌زمان با ثبت reset operation و commit revocation انجام می‌شود. در crash پیش از Commit، مصرف/ابطال هیچ‌کدام نباید نیمه‌ثبت شوند. پس از Commit، همان recovery token **هیچ بار دیگر** مجوز reset یا epoch bump نیست.
5. بعد از قطع ارتباط، ادامهٔ کار فقط از طریق **اثبات تازهٔ بازیابی با linkage به همان operation_id و owner** (و در صورت لزوم continuation capability جدید با اعتبارسنجی مستقل و محدود) ممکن است؛ `operation_id` به تنهایی bearer authorization نیست و recovery token مصرف‌شده revive نمی‌شود. صدور/کنترل continuation خود یک تصمیم امنیتی پیش از کدنویسی است. در نبود مسیر امن: **operator-reconciled / reverify، Gate بسته**.

### 3.2. با نشست معتبر: `AUTHENTICATED_PASSWORD_CHANGE`

- BFF session opaque فعلی، owner/epoch/generation، CSRF+Origin و **step-up یا fresh-password proof واقعی طبق سیاستی که باید تصویب و آزموده شود** شرط هستند. یک Session معتبرِ معمولی اگر assurance موردنیاز تغییر credential را ندارد، به‌تنهایی کافی نیست.
- اثبات به Session و `(issuer,sub)` و owner و intended operation متصل می‌شود؛ owner از ایمیل/body انتخاب نمی‌شود. در همان DB TX، `admit_session_fenced` برای session مرجع و authorization step-up و CAS session/epoch پیش از revoke بررسی می‌شود. عملیات DB write تحت lock order Owner→Session؛ قبل از Commit نشست مجاز بوده ولی بعد از Commit همان نشست revoke می‌شود.
- بازیابی بدون نشست و تغییر رمزِ نشست‌دار **نوع، راه اثبات، challenge lifecycle و policy audit مستقل** دارند؛ هیچ راه سومی از `kc_action`، Account Console یا admin service غیرمجاز، بدون ثبت Product operation وارد این مسیر نمی‌شود.

## 4. State machine و خطوط Commit

**Stateها طراحی آینده‌اند؛ هنوز جدول/Service ندارند.** هر operation با `operation_id` پایدارِ تولید سرور، `issuer+subject` نگاشت‌شده به `owner_id`، `authorization_kind`، `authz_consumption_ref` غیرقابل بازسازی، `expected_epoch`, `revoked_epoch`, `attempt_seq`, `status`, `policy_version`, `created_at`, `updated_at` و evidence/status digestهای غیرمحرمانه تعریف شود. `operation_id` تصادفی و پایدار است، ولی **credential نیست** و idempotency برای درخواست‌های فاقد مجوز نمی‌آورد.

```text
REQUESTED (public; no owner mutation)
    ├─ no verified authorization → DENIED/GENERIC (no epoch bump)
    └─ verified recovery redemption OR session+step-up
         → AUTHORIZED_UNCOMMITTED [transaction local; not externally visible]
         → COMMIT C1 [single product PostgreSQL transaction:
             owner FOR UPDATE; authz single-use CAS;
             per-owner active-operation constraint;
             revoke_all(expected_epoch) ⇒ new epoch;
             session invalidation + Gate pending_reauth;
             durable operation row = REVOKED_PENDING_IDP;
             principal/policy references + scrubbed audit]
         → REVOKED_PENDING_IDP
             ├─ claim authorized attempt with CAS → IDP_IN_FLIGHT
             │     ├─ definitively verified success → IDP_CONFIRMED
             │     ├─ definite documented no-change error → IDP_FAILED_GATE_CLOSED
             │     └─ crash/timeout/unverifiable or 5xx → IDP_UNKNOWN_GATE_CLOSED
             ├─ no caller secret / abandoned → AWAITING_VERIFIED_RESTART
             └─ concurrent operation → CONFLICT / same opaque status (never new epoch)
         → IDP_CONFIRMED
             └─ independently verified NEW credential authentication
                with flow_id/state/issuer/sub/operation_id/epoch/attempt_seq
                and fresh assurance (old SSO denied)
                  → COMMIT C2 [product PG transaction under owner FOR UPDATE:
                     current operation + epoch + attempt_seq match;
                     consume fresh-auth proof; Gate open and issue/rotate
                     new product Session under same fencing semantics]
                  → COMPLETED
    Any uncertainty/policy drift/recovery replay/lost evidence
         → PENDING_REAUTH / QUARANTINED (never auto-open).
```

**C1 خط linearization اصلی است.** IdP `PUT /users/{id}/reset-password` یا معادل فقط **بعد از commit قابل‌خواندن C1** فراخوانی می‌شود. تغییر Password **قبل از ابطال Session ممنوع است**. این توالی اتمیک **فقط در PostgreSQL محصول** است؛ هیچ distributed ACID یا exactly-once Keycloak درخواست نمی‌شود. پاسخ C1 به caller به‌معنی تغییر رمز نیست. IdP outage حتی اگر طولانی شود، owner gate باید بسته بماند.

**C2 از C1 جداست.** Callback، `prompt=login`، `max_age=0`، `auth_time`، `sid` یا Code+PKCE موفق به‌تنهایی ثابت نمی‌کند رمز جدید دوباره وارد شده است؛ باید evidence ایزولهٔ Flow واقعی با **fresh password challenge** مورد تأیید ناظر در IdP نسخهٔ pinned وجود داشته باشد که به `operation_id` و epoch/attempt فعلی bind می‌شود. BFF OIDC server callback را verify می‌کند ولی فقط REST/Code receipt را به عنوان proof قبول نمی‌کند. تا انتخاب/آزمون روش assurance، **C2 BLOCKED** است؛ `finish_simulated_reauth` فقط CI fixture باقی می‌ماند. Issue Session جدید صرفاً **در همان C2 با lock و epoch-current**؛ callback/refresh قدیمی یا هم‌زمان پس از C1 reject.

**دروازهٔ دسترسی:** BFF و FastAPI باید Owner/Session/Gate را در **primary Product PG با همان outer TX** و Migration 004 fencing کنترل کنند. stale positive cache، IdP JWT، client-side cookie و `fence_owner` مستقل کافی نیستند. از لحظهٔ commit C1، **هر admission جدیدِ درست فنس‌شده** رد می‌شود؛ تراکنش SQL از پیش admitted می‌تواند پیش از C1 قفل را نگه دارد و C1 منتظر آن شود. Remote HTTP/stream که پس از رهاشدن lock ادامه می‌یابد، خارج از این تضمین است و سیاست توقف/compensation و تست جدا می‌خواهد.

## 5. شکست میان دو DB، Retry و رقابت

### 5.1. قانون retry با secret-only RAM

- Recovery credential و password جدید **تنها در جریان امن درخواست معتبر و حافظهٔ کوتاه‌عمر سرور**؛ **نه** متن، رمزنگاری قابل بازگشت، hash-password، request body، Ledger، JTI idempotency، DB، صف، cache پایدار، analytics، log، tracing، error، crash dump یا artifact. حتی ذخیرهٔ payload رمزگذاری‌شده برای «retry خودکار» ممنوع است. اگر crash رخ داد، مقدار رمز دوباره از **ورودی تازه و مجاز** گرفته می‌شود.
- Operation ID پایدار + per-owner exclusive active-operation UNIQUE (یا equivalent serialized lock) + `expected_epoch` + `attempt_seq` CAS. Status/read API فقط پس از احراز هویت/continuation معتبر، حداقل افشای لازم و identity binding. Caller-supplied idempotency key اگر وجود داشته باشد **هرگز جایگزین authority** نیست؛ برای scope `(owner,kind,operation)` و رکورد سروری scrubbed استفاده شود.
- Claim کردن `IDP_IN_FLIGHT` فقط برای یک worker با **اثبات جاری مجوز ادامه** و CAS؛ به IdP `operation_id` قابل‌اعتمادِ dedup منتقل نمی‌شود مگر API استاندارد واقعاً پشتیبانی کند (در PR #23 اثبات نشده است). در پاسخ دیررس فقط worker/attempt که status+epoch+attempt_seq هنوز برابر دارد می‌تواند `IDP_CONFIRMED` ثبت کند. **هیچ response قدیمی قادر به بازکردن Gate نیست.**
- اگر تماس IdP از دید محصول `UNKNOWN` باشد، **کاهش lock یا بازکردن امکان تماس دوم، ممکن است دو write رمز را خارج از ترتیب اعمال کند**. بدون proof of remote quiescence/fencing، هیچ attempt هم‌زمان یا بازپخش خودکار مجاز نیست؛ حالت `IDP_UNKNOWN_GATE_CLOSED` نیازمند reconciliation معتبر و سپس retry تحت authorization تازه/تأیید operator است. حتی پاسخ 204 دیررسِ attempt قدیمی، Gate را باز نمی‌کند، مگر state/evidence وابسته به همان attempt و آخرین epoch معتبر باشد. اگر IdP هیچ correlation/ordered-ack رسمی ندهد، توقف دستی و تکرار چالش با قاعدهٔ پذیرفته‌شده لازم است؛ **هیچ TTL فرضی برای منتظر ماندن remote call وجود ندارد**.
- دو Reset هم‌زمان برای یک owner: تراکنش C1 اول برندهٔ owner lock/CAS می‌شود؛ دوم یا همان operation و status را برای actor مجاز بازمی‌خواند **بدون مصرف دوباره** یا `CONFLICT`/رد؛ هرگز revoke_all دوم و IdP write موازی. در دو owner مستقل تا حد نقش/قید DB مجزا اجرا می‌شوند. Reset صاحب موجودِ UNKNOWN، Reset جدید را نیز تا reconciliation مسدود می‌کند.
- **متمایزکردن JTI:** هر BFF→API attempt باید assertion JTI تازه داشته باشد؛ Migration 005 replay فقط request proof را مصرف می‌کند، نه `reset_operation_id` را. دو idempotency namespace مستقل‌اند. ناتمام‌ماندن عملیات Reset اجازهٔ replay assertion مصرف‌شده نمی‌دهد.

### 5.2. ماتریس لحظهٔ شکست

| نقطهٔ توقف/حمله | وضعیت معتبر باقی‌مانده | رفتار صحیح |
|---|---|---|
| public email request / SMTP send failure پیش از proof | هیچ owner mutation و Gate بازمانده | generic response؛ retry only invitation نه revoke |
| validation ردشده / expired یا reused recovery token | هیچ C1؛ epoch ثابت | deny، no IdP write و audit بدون secret |
| PG outage یا crash **پیش از** C1 | rollback همهٔ authz CAS+revoke+ledger | هیچ IdP call؛ retry با proof معتبر/تازه |
| crash **بعد از** C1 و **قبل از** IdP | epoch بالا، sessions revoked، Gate pending، op persisted | بدون password store، retry نیازمند authorization تازه؛ no auto-open |
| IdP 204 با ثبت موفق CAS | IDP_CONFIRMED، Gate pending | فقط آغاز fresh-auth evidence، نه صدور Session |
| HTTP timeout/connection drop/5xx یا crash هنگام IdP | `IDP_UNKNOWN_GATE_CLOSED` | هیچ replay کور، releaseِ remote fence یا Gate open؛ reconcile |
| IdP definite 4xx بدون credential mutation (با semantic معتبر) | `IDP_FAILED_GATE_CLOSED` | هیچ rollback C1؛ retry پس از fresh authorization |
| response 204 دیررس بعد از superseding attempt/epoch | stale attempt | ignore for state/C2، record nonsecret audit |
| دو C1 هم‌زمان | یک lock winner؛ epoch فقط یک بار برای operation | دوم reject/same-status، never dual IdP mutation |
| callback/SSO/refresh قبلی از قبل C1 | epoch/gate old | commit بعد از C1 رد؛ signed proof replay denied |
| C2 proof تکراری یا owner/epoch/op متفاوت | Gate pending | no Session, CAS reject |
| policy drift, FGAP missing, IdP unavailable, DB unavailable | fail closed/realm quarantine | admissions مجاز نیستند؛ alert و manual adjudication |
| admitted protected SQL پیش از C1 | lock تا پایان outer TX | C1 تا پایان TX صبر می‌کند؛ remote streaming پوشش جدا |

## 6. FGAP برای کاربران جدید و مرز privilege

**آزمایش PR #23 فقط یک حساب هدف بود.** هر کاربر جدید با lifecycle مستقل `UNPROVISIONED → PROVISIONING → VERIFIED → ELIGIBLE`: identity `(issuer,sub)` verify و owner link immutable؛ موجودی Authorization Resources با `_id` داخلی واقعی و User entity UUID جداگانه؛ Permission دقیق `Users/reset-password` فقط برای همان هدف و policy principal محدود؛ readback کامل **paginated** User→Resource→Permission→Scope/Policy و direct target/other-user/profile adversarial cases. `GET /permission?resourceType=Users&resource=<user-id>&scope=reset-password` و سایر scopeها، association reverse و direct permission role/composite بررسی شوند. count/name/POST status/hidden UI کافی نیست؛ خروجی raw UUID/secret export نمی‌شود.

**Runtime Reset service** فقط capability دقیق reset-password همان owner را دارد، نه `manage-users` یا `realm-admin`. **Permission Provisioner** (دارای privilege بالاتر برای ساخت/حذف policy/resource و realm adminPermissions) یک خدمت **جداگانه** با هویت، credential، network boundary، approval، audit و دسترسی محدود به lifecycle است؛ endpoint عمومی یا BFF حق فراخوانی ad-hoc آن را در درخواست Reset ندارد. Provisioner با service reset principal یکسان نیست و حق اجرای reset-password runtime به‌عنوان مجوز عملیاتی ندارد. مدیر اضطراری Keycloak/master و operator تنظیمات Realm خارج از trust boundary «تنها مسیر Reset» هستند و به‌طور فنی قادر به دورزدن policy‌اند؛ نیاز به break-glass دو‌نفره/ثبت/بازبینی و **تعلیق فوری پذیرش Product access** در صورت دخالت یا تغییر غیرمجاز دارند. این کنترل‌های انسانی/عملیاتی هنوز پیاده‌سازی یا اثبات نشده‌اند.

اگر Permission هر user آماده/fully readback نشده، profile دستکاری شده، adminPermissions، UPDATE_PASSWORD، Reset/Forgot/Account Console/registration یا Realm flags از baseline Clean Bootstrap منحرف شده، یا audit/policy attestation معتبر در مسیر admission موجود نیست: **Reset جدید و issue/session admission برای دامنهٔ متأثر fail-closed**؛ owner/realm quarantine و گزارش امنیتی. Monitor دوره‌ای بدون bounded admission check **تضمین توقف فوری نمی‌دهد**؛ تصمیم دربارهٔ نحوهٔ attestation معتبرِ هم‌زمان با admission پیش از محصول باز است. هیچ claim برای retroactive cancel فرم‌های Realm قدیمی یا trusted break-glass مطرح نیست.

## 7. ماتریس آزمون قابل‌واگذاری (همه `NOT_RUN`)

| ID | owner آزمون | مثبت / منفی / Crash / race | شاهد پذیرش آینده |
|---|---|---|---|
| CR-T01 | UI/API | عمومی فقط ایمیل (شناخته/ناشناخته، spam, enumeration) | epoch و Gate **بدون تغییر**؛ پاسخ غیرقابل تشخیص |
| CR-T02 | UI/API/DB | recovery valid، expired، replay، stolen/wrong-owner، race دو redeem | یک مصرف CAS؛ no stale authz/owner crossover |
| CR-T03 | UI/API | session change با CSRF/Origin و fresh step-up؛ stolen session بدون step-up | موفق فقط با assurance واقعی؛ old Cookie پس از C1 reject |
| CR-T04 | DB | authz proof+ledger+revoke_all+Gate در C1، crash هر گام، concurrent owner | یک commit کامل یا صفر؛ lock order و monotonic epoch |
| CR-T05 | API/IdP | reset service target vs other user vs profile; non-provisioned user | 204/403/403 با credential check مستقل؛ FGAP account lifecycle |
| CR-T06 | API/DB | crash before C1 / after C1 / before IdP / after IdP before ACK | Gate closed در همهٔ نامعلوم‌ها، no IdP call before C1 |
| CR-T07 | API/DB | IdP timeout, 5xx, delayed 204, duplicate retry, second reset race | no second remote mutation while unknown؛ CAS ignores late result |
| CR-T08 | UI/API/DB | old SSO cookie، `prompt=login`/callback، stale refresh و `finish_simulated_reauth` | هیچ‌کدام Gate را باز نکند؛ فقط verified fresh challenge |
| CR-T09 | UI/API/DB | درستِ fresh auth پس از IdP ack، wrong op/epoch/attempt/owner یا double consume | C2 atomic Gate-open+new session only current proof |
| CR-T10 | API/DB | BFF JTI replay، mismatched body/method، reset op_id replay، revoke admission race | separate replay namespaces؛ SQL transaction fencing |
| CR-T11 | Foundation/Integration | IdP/PG outage، policy drift، emergency admin override | realm quarantine/fail-closed؛ no claimed grace TTL |
| CR-T12 | Security/QA | secret canaries در ledger, idempotency, logs, traces, exceptions, artifacts | هیچ password/recovery link/token قابل بازیابی نیست |
| CR-T13 | DB/API | multi-user FGAP auto-provision/update/remove/reconcile، scope pagination و role composite | per-user identity→resource→scope/policy exact, no broad permission |
| CR-T14 | Foundation/Integration | streaming/remote side effects before/after C1; last protected SQL lock interleaving | SQL admission after C1 denied؛ remote boundary gap separately documented |

**معیار عدم پذیرش:** آزمایش مصنوعی Clean Bootstrap PR23 آزمون‌های CR-T01..T14 را اجرا نکرده است؛ همه `NOT_RUN`. هیچ Gate تا پوشش interleaving واقعی Product PG + OIDC + BFF + API و شواهد معتبر C2 PASS نمی‌شود.

## 8. کمینهٔ بسته‌های اجرایی بعدی و ترتیب مالکیت

| ترتیب | بسته / مالک واحد | مرز تحویل و وابستگی |
|---|---|---|
| **CR-00 — پیش‌شرط امنیتی** | **Foundation/ناظر + IdP operations owner (هنوز تعیین نشده)** | تأیید فقط Clean Bootstrap، مستندسازی و کنترل Admin break-glass/realm flag baseline، policy attestation و انتخاب معتبر fresh-auth proof، approvals policy/TTL/abuse؛ تا حل نشدن **block runtime** |
| **CR-DB-01 — schema و C1/C2** | **DB**: `src/phase3/storage/postgres/**`, `infra/postgres/migrations/**`, `tests/phase3/database/**` | migration شمارهٔ بعد از بررسی زنجیره؛ reset_operations + recovery authorization digest/consume CAS + per-owner one-active constraint + fresh-proof consume; reuse 003/004/005 با role separation و lock order؛ no production scripts پیش از مأموریت |
| **CR-IDP-02 — FGAP lifecycle & proof** | **API/Auth + IdP operator مستقل**: `src/phase3/auth/**` و CI ایزوله با مأموریت جدا | per-user provisioner جدا از reset worker؛ readback and least privilege؛ definite/unknown response classification؛ fresh-auth challenge binding evidence؛ بدون SPI/outbox مگر تصمیم جدید |
| **CR-API-03 — orchestration** | **API**: `src/phase3/auth/**`, `apps/api/**`, `tests/phase3/api/**` | C1→IdP، durable op_id، per-attempt CAS، unknown/manual reconciliation، status auth، service trust/replay from existing; no storage of secret |
| **CR-UI-04 — BFF & UX** | **UI**: `apps/web/src/auth/server/**`, future scoped `apps/web/app/api/auth/**`, `tests/phase3/ui/**` | separate anonymous verified recovery vs session+step-up; CSRF, cookies, memory-only secret, proof-bound C2, generic error/timeout |
| **CR-X-05 — cross-component acceptance** | **Foundation integration/security**: `tests/phase3/integration/cross_component/**`, `tests/phase3/system/**` | CR-T01..T14 across real disposable Product PG + pinned clean IdP + BFF/API; failure injection, audit, security signoff; **no Gate automatic** |

**وابستگی:** CR-00 policy/fresh-auth/provisioner decisions → CR-DB-01 و CR-IDP-02 با هماهنگی → CR-API-03 و CR-UI-04 پس از تثبیت رابط‌های داخلی → CR-X-05 و تصمیم ناظر. موازی‌سازی صرفاً پس از قرارداد داخلی مصوب و مالک‌گذاری؛ هیچ DTO عمومی در این ADR تغییر نمی‌کند.

**Traceability:** P3M05-A03/A04/A05/A07/A08/A09/A10؛ P3M06-A03/A05/A07؛ P3M13-A03/A07/A08/A09/A10؛ operational P3OP03 فقط overlay است و **هیچ فعالیت/Gate مجدداً شمرده نمی‌شود**.

## 9. تصمیم‌های واقعاً باز، بدون TTL یا ضمانت ساختگی

1. **CR-D01** — تعریف اثبات recovery واقعی، کانال تحویل/compromise/abuse و سیاست اعتبار/انقضا و continuation پس از مصرف؛ ایمیل تنها هرگز revoke نمی‌کند.
2. **CR-D02** — IdP Fresh Credential Proof که بتواند password challenge جدید را مستقل از SSO ثابت و با `op_id/epoch/attempt` bind کند. تا شاهد نسخهٔ pinned موجود نباشد C2 ممنوع.
3. **CR-D03** — سازوکار reconciliation نتیجهٔ `UNKNOWN`، remote quiescence/ordering یا تصمیم عملیات دستی. بدون correlation استاندارد، retry کور ممنوع؛ عدم تعیین timeout ثابت.
4. **CR-D04** — multi-user FGAP provisioner privilege, role custody, break-glass two-person process, policy drift/attestation per-admission, new-user lifecycle.
5. **CR-D05** — قواعد lock/commit برای protected DB SQL vs streaming/remote side effect، مالک Product API integration، dependency NB23؛ هیچ تضمین blanket after-revoke برای کارهای قبلی.
6. **CR-D06** — زمان‌های recovery challenge, continuation, step-up و session TTL، نگهداریِ بدون secret، audit/legal/operations، ارسال ایمیل واقعی، deployment policy؛ هیچ مقدار جدید اینجا اختراع نمی‌شود.

**Disposition:** **READY_FOR_REVIEW — CONTROLLED_RESET_EXECUTION_PLAN**؛ documentation only، design tests `NOT_RUN`، no product auth guarantee، no migration/contracts/workflow/SPI/outbox/deploy/merge.
