# Recovery plan

1. Select the backup revision and review its local manifest, checksum list and restore report. Confirm authorization and use isolated storage.
2. Check the encrypted artifacts against the manifest and verify authentication using the existing local key procedure. Extract into temporary storage and check the Git bundle, expected commit, file modes and SQLite integrity against the documented baseline.
3. For a separately authorized Docker drill, use a separate daemon and fresh volumes with the documented PostgreSQL major version. Review private Compose paths before starting anything. Test image loading, role restoration, physical and logical database recovery, and compare restored schemas and data to the expected baseline.
4. Run isolated service health and end-to-end checks for the authorized scope. Record commands, outcomes and limitations in the local evidence and publish a sanitized summary.
5. Obtain supervisor acceptance before treating the result as a recovery point. Preserve source volumes and originals during the drill.

The historical reports document component checks. Full recovery remains open. Container writable layers and Docker.raw are outside the documented backup coverage.

## Docker_3 — isolated logical restore

The disposable session database passed a custom dump and restore into a separate database. Conversation, message, Attempt and session-state counts and FORCE RLS and test-definer policy counts matched. Full rollback, physical recovery and immutable baseline restoration remain pending. Before restarting the isolated product stack, account for loss of tmpfs provisioning. [Commands and historical evidence](MAC_FIRST_START_FA.md#docker_3--بازیابی-پس-از-انتقال-حساب)

### NB23-SESSION-RESUME-11

A tmpfs restart replay exposed stale generated role setup. The three required grants now live in the guarded staging SQL used by the provisioning path. Apply it only to the verified disposable clone after restarting its PostgreSQL. Full frozen-stack recovery remains pending.

### NB23-SESSION-RESUME-12

If isolated API restarts and BFF cannot see its loopback listener, recreate only the disposable BFF and Bootstrap to attach to the current API network namespace, then restart the isolated edge. Verify both HTTPS routes before Chrome. This recovery was observed with status 200 and TLS verification 0.

### NB23-SESSION-RESUME-15

Keep the frozen C018 rollback intact. Stop only the independent nb23-session-product-local project and its dedicated temporary PostgreSQL when ending the local V4 test. Preserve the V4 ledger volume and pinned image. The full isolated start/stop drill remains pending.

### NB23-SESSION-RESUME-19

Version B keeps its running PostgreSQL while stopping or recreating isolated API, BFF and Worker services. The named SQLite volume retains retrieval outcomes. The operator procedure lives in the execution worktree at infra/nb23-v4/STAGING_RETRIEVAL.md. Full restore and accepted Freeze remain pending.

### NB23-SESSION-RESUME-22

The isolated API now starts independently of Worker warmup. Before an owner Send, confirm the WORKER_READY marker. Replaying an existing FAILED receipt was observed to leave the PostgreSQL deadline, Attempt count and isolated outcome unchanged.

### NB23-SESSION-RESUME-27

For a stopped Version B, restore its isolated PostgreSQL, start Keycloak first and wait for its private 8443 listener, then start the remaining project services. This order was exercised with one verified real retrieval. Preserve both stacks and existing volumes. Formal Freeze remains pending.

### NB23-SESSION-RESUME-28

Use the experimental-local-v4-product-fixes BFF tag for Version B. For this rollout only Bootstrap and BFF were recreated. Preserve the live Keycloak, PostgreSQL, API and Worker. Existing Chrome tabs require one sign-in after replacement so the new cookie and owner-bound correlation can be recovered.

### NB23-SESSION-RESUME-29

The thread-fixes BFF image was activated independently while the existing store was transferred in memory. The Version B title overlay is guarded to nb23_session_local and changes only the existing title data. Keep the original BFF image available and preserve API/Worker/IdP/PG on a UI-only rollback.

### NB23-SESSION-RESUME-30

Use the independent local artifacts/nb23-v4-recovery-cp30 package for execution rollback. Verify SHA256SUMS and local dependencies; restore into a separate sibling directory and validate the pinned Compose plan before activation. This package excludes live data, credentials and image layers. No live restore drill was run.

### NB23-SESSION-RESUME-32

نسخه بازیابی checkpoint 30 محفوظ است. پل خصوصی Context همان Attempt و ذخیره و نمایش پاسخ Mock در Worktree پیاده‌سازی شد. آزمون کانتینری ۱/۱، آزمون مصرف‌کننده Web ۱/۱ و بررسی TypeScript موفق بودند. امضای واقعی BFF، PostgreSQL، Chrome و Gateway در این آزمون اجرا نشدند. نسخه B و Worker روشن دست‌نخورده ماندند. درخواست خارجی صفر. آمادگی آزمون زنده هنوز احراز نشده است. مسیر ادامه و محدودیت‌های آزمون در MAC_FIRST_START_FA.md ثبت شده است.


### NB23-SESSION-RESUME-33

آداپتر HTTPS آزمون آفلاین ۳/۳ را گذراند و پشته Chrome ساختگی ساخته شد. PostgreSQL، API و Worker سبک آماده شدند. آزمون Chrome در مهلت بعدی آمادگی Keycloak ادامه دارد. درخواست خارجی صفر. برای مسیر ادامه، گزارش اجرای همین checkpoint را ببینید.


### NB23-SESSION-RESUME-34

آزمون یکپارچه Chrome، Keycloak، BFF، API، PostgreSQL و Generation Mock موفق شد. پاسخ زیر سؤال و حفظ همان Attempt در Refresh و History، با دقیقاً یک dispatch تأیید شد. آداپتر HTTPS غیرفعال است. درخواست خارجی صفر. برای مسیر ادامه، گزارش اجرای همین checkpoint را ببینید.


### NB23-SESSION-RESUME-35

کنترل بسته زنده و دستور smoke آماده شد و آزمون آفلاین ۴/۴ موفق بود. تعرفه همان Gateway و بازیابی کامل حساب و تاریخچه نسخه B احراز نشد. درخواست خارجی صفر و نسخه B دست‌نخورده است. برای مسیر ادامه، گزارش اجرای همین checkpoint را ببینید.


### NB23-SESSION-RESUME-36

Smoke واقعی ساختگی موفق شد و گزارش آن پس از اعتبارسنجی آفلاین یک پاسخ ثبت شد. Volumeها و PostgreSQL پایدار مستقل برقرارند و Chrome هنوز در مرحله آزمون است. برای مسیر ادامه، گزارش اجرای همین checkpoint را ببینید.


### NB23-SESSION-RESUME-37

مسیر واقعی ساختگی از BFF و API تا DeepSeek و History موفق شد. مالکیت حساب دوم با ۴۰۴ و رد وضعیت تأیید شد. دو درخواست از سه درخواست استفاده شده‌اند و بازآزمایی ماندگاری در حال اجرا است. برای مسیر ادامه، گزارش اجرای همین checkpoint را ببینید.


### NB23-SESSION-RESUME-38

READY FOR HUMAN LIVE GENERATION TEST — SYNTHETIC CONTEXT ONLY. ماندگاری پس از توقف و راه‌اندازی، ورود مجدد، خواندن پاسخ موجود و باز شدن پنجره مالک تأیید شد. دو درخواست استفاده شده‌اند و یک درخواست باقی است. برای مسیر ادامه، گزارش اجرای همین checkpoint را ببینید.


### NB23-SESSION-RESUME-39

پنجره Chrome مالک دوباره باز شد و ورود و پاسخ ذخیره‌شده از HTTPS تأیید شدند. نمونه مالی ساختگی فعال است. اشتراک شبکه BFF پس از Restart API بازیابی شد و سهم یک درخواست مالک محفوظ است. برای مسیر ادامه، گزارش اجرای همین checkpoint را ببینید.


### NB23-SESSION-RESUME-40

توقف Chrome در بارگذاری کلید کوکی تشخیص داده شد. پنجره خصوصی با ورود واقعی و UI قابل استفاده تأیید شد. پاسخ مالی در Chrome دیده شد. سقف بسته ۳/۳ است و عامل هیچ درخواست DeepSeek ارسال نکرد. برای مسیر ادامه، گزارش اجرای همین checkpoint را ببینید.


### NB23-SESSION-RESUME-41

پاسخ گل و مالی از سرور زیر Message مربوط بازیابی شدند. Chrome خروج، ۴۰۱، ورود مجدد و History را گذراند. بسته ۳/۳ بسته است؛ شمار Gateway ثابت. نقطه بازیابی CP41 و نقشه اتصال RAG ثبت شدند. برای مسیر ادامه، گزارش اجرای همین checkpoint را ببینید.


### NB23-SESSION-RESUME-42

پروفایل Worker واقعی و محصور روی پشته پایدار فعال شد. دو سؤال بدون Gateway پذیرفته شدند اما به مهلت محلی رسیدند. بستهٔ ۳/۳ ثابت و CP41 معتبر است. آزمون تشخیصی یک سؤال تازه در جریان است. برای مسیر ادامه، گزارش اجرای همین checkpoint را ببینید.


### NB23-SESSION-RESUME-43

REAL RAG INTEGRATION VALIDATED — EXTERNAL EGRESS BLOCKED. یک آزمون واقعی کامل با ۱۰ شاهد و receipt ماندگار موفق شد. دو UNKNOWN قبل تکرار نشدند. بسته Gateway روی ۳/۳ ثابت است. برای مسیر ادامه، گزارش اجرای همین checkpoint را ببینید.


### NB23-SESSION-RESUME-44

REAL RAG INTEGRATION PRESERVED. OWNER BROWSER READY. PERFORMANCE DIAGNOSTICS DOCUMENTED. EXTERNAL EGRESS BLOCKED. Snapshot و Backup خصوصی CP43 با Checksum ثبت شده‌اند و آزمون Retrieval تکرار نشد. برای مسیر ادامه، گزارش اجرای همین checkpoint را ببینید.


### NB23-SESSION-RESUME-45

اصلاحات محلی Chat و History، Cache و حافظه محدود؛ Worker جاری آماده نیست برای مسیر ادامه، گزارش اجرای همین checkpoint را ببینید.
