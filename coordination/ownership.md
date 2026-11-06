# Phase 3 — مالکیت مسیرها و هماهنگی سه ایجنت

**وضعیت:** پیشنهاد ساختار برای مأموریت‌های اجرایی آینده؛ در این مأموریت هیچ کد/فولدر نمایشی ایجاد نمی‌شود. دستورهای مرجع: `AGENTS.md` و `coordination/phase3_checklist.md`.

| مالک واحد | مسیرها/فایل‌های اختصاصی (future; not all created) | مرز |
|---|---|---|
| Foundation | `README.md`, `AGENTS.md`, `.gitignore`, `.github/**`, تنظیمات/Lockfileهای **ریشه**، `docs/architecture/**`, `docs/adr/**`, `coordination/phase3_checklist.md`, `coordination/ownership.md`, `coordination/open_decisions.md`, `coordination/tasks/AGENT-FOUNDATION-01.md`, `references/phase2/**`, `packages/contracts/**`, `schemas/phase3/**` | **ویرایشگر یگانهٔ چک‌لیست و قراردادهای مشترک**؛ مشورت با API/UI/DB لازم است |
| API | `apps/api/**`, `src/phase3/auth/**`, `src/phase3/conversations/**`, `src/phase3/rag_runtime/**` (adapter فقط پس از Gate), `src/phase3/safety/**`, `tests/phase3/api/**`, `tests/phase3/integration/api/**`, `coordination/tasks/AGENT-API-*.md` | Endpoint، Auth flow، Orchestration، HTTP، Retry/Timeout/Streaming/Cancellation؛ نه PostgreSQL schema |
| UI | `apps/web/**`, `tests/phase3/ui/**`, `tests/phase3/integration/ui/**`, `coordination/tasks/AGENT-UI-01.md` | Frontend RTL، Consent، Chat، Citation UI، Feedback و Privacy؛ نه Backend/API logic |
| DB | `src/phase3/storage/postgres/**`, `infra/postgres/**`, `tests/phase3/database/**`, `tests/phase3/integration/database/**`, `coordination/tasks/AGENT-DB-01.md` | PostgreSQL محصول، Migration/RLS/PK/FK/Transaction و PostgreSQL Restore؛ نه Qdrant/Object Storage |
| Foundation integration (human ops/QA owner **assignment pending**) | `tests/phase3/integration/cross_component/**`, `tests/phase3/system/**`, `docs/operations/**` | Cross-component tests، امنیت، عملیات و Gateهای نهایی؛ تصمیم/پذیرش ناظر جداست |

**قواعد عدم هم‌پوشانی:** هیچ ایجنت مالک کل `tests/` یا `tests/phase3/integration/` نیست. هر ایجنت فقط زیرپوشهٔ تخصصی خود را ویرایش می‌کند؛ قراردادهای مشترک، ریشه و چک‌لیست فقط Foundation. ساختار موازی `apps/`، `src/phase3/` یا `tests/phase3/` ایجاد نمی‌شود. مسیرهای پیشنهادی پیش از کار اجرایی با این جدول تطبیق می‌شوند.

## مرز DB و موتور و دارایی‌های عملیاتی

- **DB:** PostgreSQL محصول؛ schema, constraints, indexes, RLS, app role, transaction context, atomic persistence, duplicate persistence prevention, rollback و local PostgreSQL restore. Atomic DB **exactly-once** اجرای موتور یا Provider نیست.
- **API:** ترتیب درخواست، فراخوانی موتور، retry، timeout، cancel، streaming، identity context. قرارداد مشترک با مالک Foundation: `request_id`, `trace_id`, idempotency scope, identity owner, transaction boundary, commit/abort, error mapping و repeated requests.
- **Qdrant:** خارج از DB؛ پیاده‌سازی Retrieval در قلمرو API/RAG با مأموریت بعدی و Gate؛ مالک عملیاتی نهایی **assignment pending**. **Object Storage:** خارج از DB و API app، مالک عملیاتی نهایی **assignment pending**.
- **بازیابی و Gate کل سامانه:** هماهنگی Foundation، پذیرش رسمی با ناظر؛ backup/restore محلی DB به معنی بازیابی Qdrant یا کل سامانه نیست. امنیت، Integration، Launch و عملیات مالک هماهنگی Foundation دارند و تعیین نیروی عملیاتی نهایی منتظر تصمیم است.

## چک‌لیست، پذیرش و موازی‌سازی

- `coordination/phase3_checklist.md` یک ویرایشگر دارد: **Foundation**. Gateهای `P3M00–P3M25` آنجا ثبت می‌شوند، `P3OPxx` overlay هستند و پیشرفت دوباره شمرده نمی‌شود.
- **UI:** `coordination/tasks/AGENT-UI-01.md`، نسخهٔ مصوب v1.1 و ۱۴ زیرکار. **DB:** `coordination/tasks/AGENT-DB-01.md`، نسخهٔ مصوب v2 و ۱۸ زیرکار. متن ابتدا توسط Foundation طبق دستور ناظر ثبت می‌شود؛ مالک ویرایش بعدی متخصص است. Onboarding پذیرفته‌شده به معنی اجرای پذیرفته‌شده نیست.
- پس از **پذیرش Foundation و مأموریت اجرایی مشخص**، طراحی و آزمون مستقل با Mock/Fixture و قرارداد provisional می‌تواند موازی پیش رود: UI/History/Persistence مستقل به پذیرش NB23 گره نمی‌خورد.
- **همچنان blocked:** اتصال واقعی Runtime، قرارداد سازگاری موتور، پذیرش Module 00، کل Retrieval و Launch. Streaming و Cancellation الزام نقشه‌اند ولی آمادگی موتور ثابت نشده و حذف نمی‌شوند.
- **حذف داده** به تصویب Export وابسته نیست. Auth، Retention، زیرساخت، SLO و هزینه تا تصمیم مصوب بازند.
