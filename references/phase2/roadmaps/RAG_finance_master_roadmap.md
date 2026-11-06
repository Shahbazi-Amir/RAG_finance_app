<div dir="rtl" align="right">

# نقشه کلان چهار فاز RAG_finance

**از Demo تا RAG حرفه‌ای، لانچ چندکاربره و مربی شخصی سواد مالی**

| <span dir="ltr">Repository</span> | <span dir="ltr">Shahbazi-Amir/RAG_finance</span> |
| ---: | ---: |
| Branch مبنا | <span dir="ltr">rag-phase2</span> |
| Commit ممیزی | <span dir="ltr">96c0f0c7d09f4bff107ed71664a0c57ed09f3214</span> |
| تاریخ نسخه | ۲۱ اوت ۲۰۲۶ |
| دامنه | فازهای ۱ تا ۴ و قرارداد تحویل بین آن‌ها |

## ۱. تعریف محصول نهایی

محصول نهایی سه کار متفاوت را با مرز روشن انجام می‌دهد:

- دانش معتبر: پاسخ به پرسش‌های سواد مالی فقط با شواهد Corpus اختصاصی.
- آموزش هدفمند: تشخیص سطح، شکاف دانشی و پیشنهاد محتوای مناسب.
- مربیگری عملی: تبدیل آموزش به هدف، اقدام کوچک، پیگیری و ارزیابی مجدد.
محصول در نسخه پایه «مشاور خریدوفروش دارایی» نیست. توصیه سرمایه‌گذاری شخصی، پیش‌بینی بازار و تصمیم مالی پرریسک باید خارج از Policy باشد یا به انسان/مرجع مجاز ارجاع شود.

## ۲. چرا کاربر باید این محصول را به AI عمومی ترجیح دهد؟

| مزیت | رفتار قابل مشاهده در محصول |
| ---: | ---: |
| اعتبار صاحب دانش | هر پاسخ به مقاله، کتاب یا دقیقه مشخص از محتوای مؤلف متصل است |
| پاسخ قابل دفاع | هر ادعای واقعی Claim-level Citation و Evidence دارد |
| تشخیص نبود پاسخ | سیستم در نبود شاهد، سؤال روشن‌کننده می‌پرسد یا Abstain می‌کند |
| روش آموزشی منسجم | Taxonomy و مسیر یادگیری از روش و محتوای مؤلف ساخته می‌شود |
| کاربرد شخصی ایمن | قواعد و ماشین‌حساب‌های نسخه‌دار از داده ساخت‌یافته استفاده می‌کنند |
| رشد قابل اندازه‌گیری | آزمون قبل/بعد، اقدام‌ها، Check-in و تغییر امتیاز ثبت می‌شود |
| شفافیت | کاربر می‌بیند پاسخ از کجا آمده، چه داده‌ای استفاده شده و محدودیت چیست |

## ۳. معماری کلان قابلیت‌ها

مالکیت و منابع دانش             ↓     فاز ۲: Knowledge & RAG Core             ↓     فاز ۳: Web Platform & Production Launch             ↓     فاز ۴: Assessment + Learning + Planning + Admin             ↓     نتیجه: رشد قابل سنجش سواد و سلامت مالی

در سطح محصول، چهار موتور مستقل اما هماهنگ وجود دارد:

1. RAG Engine: پاسخ مستند از منابع اختصاصی.
2. Assessment Engine: آزمون و امتیازدهی قطعی و نسخه‌دار.
3. Planning Engine: قواعد، ماشین‌حساب‌ها و برنامه اقدام.
4. Conversation Engine: گفت‌وگو، توضیح و هدایت کاربر بدون تغییر خودسرانه محاسبات.
## ۴. نقشه چهار فاز

| فاز | هدف | خروجی نهایی | وضعیت بر اساس فایل‌های پروژه |
| ---: | ---: | ---: | ---: |
| فاز ۱ | اثبات امکان RAG | Demo کامل Website → Qdrant → Answer → Streamlit | انجام‌شده؛ Baseline |
| فاز ۲ | مهندسی دانش و RAG حرفه‌ای | RAG Core سه‌منبعی، نسخه‌دار، قابل استناد و Benchmark | فاز اجرایی جاری |
| فاز ۳ | دیپلوی و لانچ روی سایت | Web/PWA چندکاربره با DB، امنیت، عملیات و چت عمومی | پس از Gate فاز ۲ |
| فاز ۴ | مشاور/مربی مالی و پنل گسترده | Assessment، پروفایل، مسیر، اقدام، پیشرفت و Admin | پس از پایداری فاز ۳ |

## ۵. فاز ۱ - Baseline و میراث قابل استفاده

دارایی‌های اثبات‌شده فاز ۱:

- ۷۶ مقاله نویسنده، ۱۶۸ Chunk و Embeddingهای ۳۰۷۲بعدی.
- Qdrant Local، Dense Retrieval و Qwen3-30B-A3B.
- Cache، Streamlit، تاریخچه JSON/SQLite و Evaluation ده‌سؤالی.
- ساختار ماژولار اولیه در src.
فاز ۱ نباید توسعه پیدا کند؛ باید Tag، Baseline و به‌عنوان مرجع مقایسه فریز شود. محدودیت‌های Dense-only، Character Chunking، Evaluation کوچک و Citation سطح Source باید در گزارش Baseline ثبت شوند.

## ۶. فاز ۲ - Knowledge & RAG Core

### هدف

تبدیل سه خانواده منبع به Dataset قابل ردیابی و ساخت موتور پاسخ مستند، ایمن و قابل ارزیابی.

### سه خانواده منبع

- Website: مقاله‌های مستقیم مؤلف و مقاله‌های تولیدشده زیر نظر سردبیری او.
- Books: کتاب، مقاله بلند و نوشته‌های تألیفی مؤلف؛ با تفکیک Work/Edition.
- Video/Audio: تدریس، آموزش، مصاحبه و برنامه تلویزیونی تبدیل‌شده به Transcript.
### خروجی

- Registry حقوق و منشأ محتوا.
- Pipeline مستقل و تکرارپذیر برای هر منبع.
- Common Schema، Stable IDs، Lineage، Dataset/Index releases.
- Source-aware Chunking، Hybrid Retrieval و Reranker فقط در صورت اثبات.
- Context Builder، Claim-level Citation، Answerability و Safety.
- Golden Dataset، Benchmark، Regression و System/Dataset/Model cards.
### Gate

پاسخ هر سؤال از Dataset و Index نسخه‌دار تا Claim، Chunk، Document و Raw source قابل ردیابی باشد و نتیجه Benchmark از محیط تمیز تکرار شود.

## ۷. فاز ۳ - Platform & Launch

### هدف

عرضه واقعی RAG فاز ۲ روی سایت برای کاربران ثبت‌شده، با ذخیره امن گفت‌وگو و امکان عملیات پایدار.

### خروجی

- Web/PWA واکنش‌گرا، FastAPI و PostgreSQL.
- Auth/session، consent، tenant/user isolation و RLS.
- Conversation، message، citation، retrieval/model run و feedback.
- Qdrant پایدار برای دانش عمومی؛ Redis و Object Storage.
- Dockerized deployment، reverse proxy، TLS، backup/restore و CI/CD.
- Staging، Production، observability، rate limit، cost guard و incident runbook.
### Gate

کاربر واقعی بتواند وارد شود، چت کند، Citation را باز کند، تاریخچه خود را ببیند و هیچ داده‌ای بین کاربران نشت نکند؛ Release و rollback و restore آزمایش شده باشد.

## ۸. فاز ۴ - مربی سواد مالی و پنل مدیریت

### هدف

عبور از «پرسش‌وپاسخ» به چرخه رشد:

Assess → Explain → Plan → Act → Check-in → Reassess

### خروجی کاربر

- Onboarding و رضایت داده.
- آزمون سواد و سلامت مالی، سطح‌بندی و نمایش شکاف‌ها.
- پروفایل اختیاری درآمد، هزینه، بدهی، پس‌انداز و هدف.
- مسیر یادگیری و محتوای منتخب از سه منبع.
- برنامه اقدام دوره‌ای با قواعد شفاف.
- Check-in، یادآوری، بازآزمون و نمودار پیشرفت.
- توضیح منبع، Confidence components و ارجاع موارد حساس.
### خروجی پنل مدیریت

- مدیریت Taxonomy، محتوا، Release و Rights.
- مدیریت سؤال/آزمون/Scoring version.
- مدیریت قواعد، Policy، Prompt و Feature flag.
- مشاهده کیفیت Retrieval/Citation/Safety و صف بازبینی.
- پشتیبانی کاربر با دسترسی محدود و Audit‌شده.
- گزارش رشد آموزشی و سلامت سرویس.
### Gate

در پایلوت کنترل‌شده، مسیر کامل از Assessment تا Reassessment کار کند و اثر با KPIهای رفتاری و آموزشی سنجیده شود؛ خروجی عددی حساس فقط از Rules/Calculators نسخه‌دار تولید شود.

## ۹. قرارداد تحویل بین فازها

| تحویل | اجزای الزامی |
| ---: | ---: |
| فاز ۱ → ۲ | Tag، Baseline، Dataset/Model/Prompt config و Known limitations |
| فاز ۲ → ۳ | RAG API contract، Dataset/Index IDs، Citation schema، Policy و Eval report |
| فاز ۳ → ۴ | Auth/consent، user isolation، event model، conversation API و operational SLOs |
| فاز ۴ → بهره‌برداری | Assessment/Rules versions، pilot report، safety review و product KPI dashboard |

## ۱۰. مسیر دانش فنی و دانش‌بنیان

پرونده فنی باید در طول کار ساخته شود، نه در پایان:

| محور دفاع | شواهد لازم |
| ---: | ---: |
| مهندسی داده اختصاصی | سه Pipeline، Schema، Lineage، Rights و Quality reports |
| مهندسی بازیابی | Baseline، Hybrid/Reranker experiments و Ablation |
| اعتماد و استناد | Claim citation، verifier، answerability و conflict handling |
| فارسی و حوزه مالی | Normalizer، Taxonomy، آزمون و Policy تخصصی |
| محصول هوشمند | Assessment/Planning engines و جداسازی منطق قطعی از LLM |
| اثر | Golden tests، pilot، pre/post assessment و action completion |
| بازتولیدپذیری | ADR، experiment registry، CI، releases و runbooks |

طبق آیین‌نامه، تعیین حوزه‌ها و معیارهای تشخیص مصادیق در اختیار کارگروه مربوط است و معیارها می‌توانند تغییر کنند؛ بنابراین این نقشه تضمین تأیید رسمی نیست. مرجع حقوقی: <span dir="ltr">https://qavanin.ir/Law/TreeText/?IDS=7646595681372737421</span>

## ۱۱. قواعد مشترک اجرای پروژه

- هر Task باید Code، Test، Acceptance، Documentation و Commit مشخص داشته باشد.
- Notebook برای Exploration است؛ مسیر اصلی باید Package/CLI/API باشد.
- Raw data تغییرناپذیر و هر Release دارای Hash باشد.
- هیچ تصمیم معماری بدون ADR و هیچ انتخاب مدل بدون Benchmark نباشد.
- هیچ Secret، PII یا Test set محرمانه وارد Git نشود.
- هر Claim پاسخ باید Citation معتبر یا دلیل Abstention داشته باشد.
- اطلاعات شخصی کاربر در PostgreSQL باقی بماند و بدون نیاز روشن وارد Vector DB نشود.
- تغییرات Dataset، Index، Prompt، Policy و Rules باید Versioned و قابل Rollback باشند.
## ۱۲. شاخص نهایی موفقیت

معیار موفقیت، تعداد پیام نیست:

- کیفیت Citation و Grounded answer.
- تشخیص صحیح سؤال بی‌پاسخ و پرریسک.
- تکمیل آزمون و مسیر یادگیری.
- انجام اقدام پیشنهادشده.
- بهبود آزمون مجدد و شاخص‌های تعریف‌شده.
- حفظ حریم خصوصی و نبود نشت بین کاربران.
- هزینه و پایداری قابل کنترل.
## ۱۳. تصمیم نهایی

مسیر چهارمرحله‌ای درست است، به شرط آنکه:

1. فاز ۲ با RAG Core واقعی و Benchmark بسته شود.
2. فاز ۳ فقط Demo آنلاین نباشد و الزامات محصول چندکاربره را پاس کند.
3. فاز ۴ چت را به Assessment، Rules، Action و Outcome متصل کند.
4. مستندات دانش فنی در هر Gate هم‌زمان تولید شوند.

با این مرزبندی، پروژه دلیل روشنی برای انتخاب شدن به‌جای AI عمومی دارد و از نظر فنی قابلیت تبدیل شدن به محصول قابل دفاع را خواهد داشت.

</div>
