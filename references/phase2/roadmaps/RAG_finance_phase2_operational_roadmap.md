<div dir="rtl" align="right">

# نقشه عملیاتی فاز ۲ RAG_finance

**Knowledge Engineering، RAG Core، Citation، Safety و Evaluation**

| <span dir="ltr">Repository</span> | <span dir="ltr">Shahbazi-Amir/RAG_finance</span> |
| ---: | ---: |
| Branch مبنا | <span dir="ltr">rag-phase2</span> |
| Commit ممیزی | <span dir="ltr">96c0f0c7d09f4bff107ed71664a0c57ed09f3214</span> |
| تاریخ نسخه | ۲۱ اوت ۲۰۲۶ |
| دامنه | RAG Core؛ خارج از Deployment و پنل شخصی |

## ۱. تعریف Done فاز ۲

فاز ۲ زمانی تمام است که:

- مقاله، کتاب و Transcript هرکدام Pipeline مستقل و قابل تکرار داشته باشند.
- هر Document و Chunk به Raw source و مالکیت/منشأ آن برگردد.
- Dataset، Chunk set، Embedding و Index نسخه‌دار و قابل بازسازی باشند.
- Retrieval با Baselineهای Dense و Sparse مقایسه شده باشد.
- انتخاب Hybrid/Reranker فقط با Benchmark انجام شده باشد.
- پاسخ ساخت‌یافته، Claim-level Citation و Citation verification داشته باشد.
- سؤال بی‌پاسخ، مبهم و پرریسک تشخیص داده شود.
- Golden Dev/Test، Regression gate و گزارش فنی وجود داشته باشد.

## ۲. مدل منشأ و مالکیت منابع

نباید Author، Knowledge Owner، Curator و Rights Holder با یکدیگر مخلوط شوند.

| گروه | content_origin پیشنهادی | نکته ثبت |
| ---: | ---: | ---: |
| مقاله مستقیم مؤلف | <span dir="ltr">primary_author</span> | author و knowledge_owner هر دو مؤلف |
| مقاله زیر نظر سردبیری | <span dir="ltr">editorial_supervised</span> | author واقعی جدا؛ curation_owner مؤلف |
| کتاب و نوشتار تألیفی | <span dir="ltr">authored_work</span> | work، edition و rights evidence |
| تدریس و آموزش مؤلف | <span dir="ltr">self_instruction</span> | speaker، program و timestamp |
| مصاحبه | <span dir="ltr">interview</span> | interviewer/host و speaker جدا |
| برنامه تلویزیونی | <span dir="ltr">broadcast</span> | broadcaster، episode، speaker و rights evidence |

فیلدهای الزامی:

- <span dir="ltr">creator/author</span>
- <span dir="ltr">knowledge_owner</span>
- <span dir="ltr">curation_owner</span>
- <span dir="ltr">rights_holder</span>
- <span dir="ltr">rights_status</span>
- <span dir="ltr">rights_evidence_id</span>
- <span dir="ltr">allowed_uses</span>
- <span dir="ltr">attribution_text</span>
- <span dir="ltr">content_origin</span>

وجود محتوا در Repository به‌تنهایی مدرک حقوق بهره‌برداری نیست. موارد فاقد مدرک در Quarantine باقی بمانند.

## ۳. جریان کل فاز ۲

<div dir="ltr" align="left">Freeze/Baseline           ↓     Contracts + IDs + Rights           ↓     Website | Book | Video/Audio           ↓     Canonical Dataset Release           ↓     Normalize + Source-aware Chunk           ↓     Embed + Versioned Index           ↓     Dense/Sparse/Hybrid/Rerank           ↓     Context + Claims + Citation + Safety           ↓     Golden Evaluation + Release Candidate</div>

## ۴. بسته P2-01 - Freeze و Baseline فاز ۱

### کارها

- Tag نسخه نهایی Demo و ثبت SHA.
- ثبت ۷۶ Document، ۱۶۸ Chunk، تنظیم Chunk 1200/200 و مدل‌ها.
- اجرای دوباره ۱۰ سؤال موجود و ثبت پاسخ، منابع، latency و خطا.
- ثبت ناهماهنگی Config مدل و محدودیت‌های Known.
- ADR جداسازی فاز ۱ و ۲ و Deprecation plan.

### خروجی

- <span dir="ltr">docs/baseline/phase1_baseline.md</span>
- <span dir="ltr">reports/baseline/phase1_results.json</span>
- <span dir="ltr">docs/adr/ADR-000-phase-boundary.md</span>

### Gate

نسخه فاز ۱ از محیط تمیز قابل اجرا و نتیجه آن مرجع مقایسه باشد.

## ۵. بسته P2-02 - Data Contract، Stable IDs و Versioning

### کارها

- تعریف JSON Schema برای Source، Document، Chunk، Citation و Dataset Release.
- تعریف Adapter schema برای Website، Book و Video/Audio.
- تعریف ID policy و migration policy.
- ثبت raw hash، processed hash، pipeline/extractor/normalizer/chunker version.
- طراحی Artifact Registry برای Dataset، Chunks، Embeddings، Index و Eval.

### خروجی

- <span dir="ltr">schemas/source.schema.json</span>
- <span dir="ltr">schemas/document.schema.json</span>
- <span dir="ltr">schemas/chunk.schema.json</span>
- <span dir="ltr">schemas/citation.schema.json</span>
- <span dir="ltr">schemas/dataset_release.schema.json</span>
- <span dir="ltr">docs/data/id_policy.md</span>
- <span dir="ltr">docs/data/schema_migration.md</span>

### Gate

نمونه معتبر و نامعتبر هر سه منبع با تست Schema بررسی شود و IDها deterministic باشند.

## ۶. بسته P2-03 - Website Pipeline V2

### کارها

- انتقال منطق Notebook موفق ۵۲۹ مقاله به Package/CLI.
- Discovery، Canonical URL، Raw snapshot، extraction و validation.
- حفظ article_id، URL، title، author، date، tags، origin و hash.
- Change detection برای NEW/UPDATED/UNCHANGED/MISSING.
- Resume، retry، backoff، idempotency و failure classification.
- گزارش Crawl و Processing مستقل.

### Gate

- دو اجرای ورودی ثابت، Manifest و خروجی یکسان بدهند.
- تغییر کنترل‌شده فقط Documentهای متاثر را بازپردازش کند.
- هیچ Empty content به‌عنوان Success ثبت نشود.
- Attribution مقاله مستقیم و سردبیری به‌درستی تفکیک شود.

## ۷. بسته P2-04 - Book Pipeline

### کارها

- ساخت Works/Edition registry برای ۷ فایل موجود و هر نسخه جایگزین.
- پردازش DOCX؛ پشتیبانی PDF/EPUB فقط در صورت وجود ورودی.
- استخراج Chapter/Section/Paragraph و حذف Header/Footer.
- حفظ Raw و تولید location anchor پایدار.
- Page citation فقط با نسخه مرجع صفحه‌بندی‌شده.
- تشخیص exact/near duplicate و ویرایش‌های متفاوت.

### Gate

هر قطعه متن به Work، Edition، Chapter، Location و Rights evidence معتبر برگردد.

## ۸. بسته P2-05 - Video/Audio Transcript Pipeline

### کارها

- Registry سری/برنامه/قسمت/رسانه و نوع محتوا.
- Segment schema شامل start_ms، end_ms، speaker، text و verification status.
- Validation ترتیب زمان، overlap/gap، duplicate و empty segment.
- Normalization فارسی بدون بازنویسی معنایی.
- حفظ اصطلاحات مالی، اعداد و نام‌ها.
- ثبت timestamp_unavailable وقتی منبع زمان ندارد؛ عدم جعل زمان.

### Gate

هر Transcript به Episode و رسانه اصلی متصل و هر Segment قابل Cite یا صریحاً فاقد Timestamp باشد.

## ۹. بسته P2-06 - Canonical Dataset و Quality

### کارها

- تبدیل سه Adapter به Common Document Model.
- Deduplication در Document، Paragraph و Chunk.
- Quarantine برای rights/schema/quality نامعتبر.
- Quality report بر اساس source type و content origin.
- Dataset card، release manifest و cryptographic hashes.

### معیار

- ۱۰۰٪ رکوردهای Release دارای Schema، lineage، hash و rights_status.
- تعداد Missing metadata و Excludedها صریح گزارش شود.
- هیچ عددی درباره کامل بودن بدون Manifest قابل اثبات اعلام نشود.

## ۱۰. بسته P2-07 - فارسی‌سازی و Source-aware Chunking

### کارها

- Normalizer تست‌شده برای Unicode، ی/ک، ZWNJ، اعداد، فاصله و punctuation.
- Offset map میان Raw و Processed برای Citation.
- Chunker جدا برای Website، Book و Transcript.
- حفظ Heading/Chapter/Page-or-anchor/Timestamp.
- آزمایش 300-500، 500-800 و 800-1200 token.
- آزمایش Parent-child و semantic boundaries.

### Gate

هیچ Chunk بدون document_id، parent/location، dataset_version و content_hash وارد Index نشود؛ Strategy با Benchmark انتخاب شود.

## ۱۱. بسته P2-08 - Golden Dataset

### طراحی پیشنهادی

حداقل پیشنهادی ۳۰۰ سؤال؛ عدد نهایی پس از Sampling و توان بازبینی تعیین شود:

- سؤال مستقیم، مفهومی، مقایسه‌ای و چندمنبعی.
- Website، Book، Video و Cross-source.
- <span dir="ltr">Entity/number/exact phrase.</span>
- سؤال مبهم، بدون پاسخ، خارج از دامنه و Hard negative.
- درخواست توصیه سرمایه‌گذاری یا پیش‌بینی.
- تعارض دو منبع و سؤال نیازمند تازگی.

### هر رکورد

- question، intent، topic، difficulty و source_type.
- gold_documents، gold_spans/locations و expected claims.
- answerability و abstention reason.
- safety label و reviewer decision.

### Gate

راهنمای Annotation، توافق بازبینان، 70/30 Dev/Test و Freeze تست نهایی وجود داشته باشد.

## ۱۲. بسته P2-09 - Embedding و Index V2

### کارها

- حفظ text-embedding-3-large به‌عنوان Baseline فاز ۱.
- Benchmark حداقل یک گزینه دیگر روی فارسی پروژه.
- ثبت Recall، latency، cost، dimension و failure rate.
- ساخت Index نسخه‌دار با Payload کامل.
- Rebuild، Add، Update، Delete و Re-index.
- Verification: expected chunks برابر indexed points.

### Gate

هر Index به Dataset، Chunker و Embedding release مشخص متصل و از صفر قابل بازسازی باشد.

## ۱۳. بسته P2-10 - Retrieval Engineering

### آزمایش‌ها

1. Dense baseline.
2. BM25/Sparse baseline.
3. Hybrid با RRF و Weighted fusion.
4. Hybrid + Reranker.
5. Metadata filtering و source balancing.

### Metrics

- Recall@5/10، Precision@k، MRR، nDCG و Hit rate.
- Context precision/recall و source coverage.
- p50/p95 latency و cost.

### Gate

روش نهایی فقط با Experiment matrix و ADR انتخاب شود. افزایش پیچیدگی بدون بهبود معنادار پذیرفته نیست.

## ۱۴. بسته P2-11 - Context، Generation و Citation

### کارها

- Context compiler با dedup، diversity، token budget و source balance.
- جداسازی Evidence از Instruction و کنترل prompt injection داخل سند.
- خروجی ساخت‌یافته Answer، Claims و Citations.
- Citation mapper و verifier برای claim support و location accuracy.
- Conflict handling و بیان اختلاف منابع.
- Cache key شامل همه Versionها و پارامترهای موثر.

### Citation

- Website: title، canonical URL و span/section.
- Book: work، edition، chapter و page یا stable anchor.
- Video/Audio: program، episode و start/end timestamp یا segment anchor.

### Gate

هر Claim factual دارای Citation معتبر باشد و Citation بازشده دقیقاً Evidence همان Claim را نشان دهد.

## ۱۵. بسته P2-12 - Answerability، Safety و Confidence

### Taxonomy درخواست

- آموزش مالی.
- توضیح مفهوم یا محتوای مؤلف.
- برنامه‌ریزی عمومی.
- سؤال شخصی نیازمند داده.
- توصیه خریدوفروش/سرمایه‌گذاری.
- پیش‌بینی.
- خارج از دامنه.

### Confidence

Confidence از evidence coverage، evidence agreement، citation entailment، source quality، answerability margin و freshness ساخته شود؛ score خام Qdrant یا ادعای LLM کافی نیست.

### Gate

روی Test set، answer/no-answer و safety جداگانه سنجیده شود و موارد بحرانی پذیرفته‌نشده صفر باشد.

## ۱۶. بسته P2-13 - Tests، CI و Reproducibility

- Unit: schema، normalization، IDs، hash، chunking، cache و citation.
- Integration: هر Source تا Document/Chunk/Index و Question تا Citation.
- Failure: bad HTML، broken book، invalid transcript، API/Qdrant/LLM failure.
- Regression: سؤال‌های فاز ۱ و Golden smoke.
- Package، lockfile، config schema، CLI و container reproducibility.
- CI برای lint/test/schema/data-quality/eval smoke.

### Gate

در محیط تمیز، Release مشخص ساخته و Benchmark منتخب بدون تغییر دستی اجرا شود.

## ۱۷. بسته P2-14 - مستندات دانش فنی

- Architecture و ADRها.
- Data schema، lineage، rights و dataset cards.
- گزارش فارسی‌سازی، Chunking، Embedding و Retrieval.
- Ablation و failure analysis.
- Citation، hallucination، answerability و safety report.
- Model/System cards و Known limitations.
- ویدیوی اجرای reproducible pipeline.
- مقایسه مستند با «LLM + Vector DB ساده».

## ۱۸. ترتیب اجرای واقعی

1. P2-01 Freeze/Baseline.
2. P2-02 Contracts/IDs/Rights.
3. P2-03 تا P2-05 به‌ترتیب یا موازی پس از Contract.
4. P2-06 Canonical Release.
5. P2-08 Golden Dataset هم‌زمان با P2-07 Chunking.
6. P2-09 Index.
7. P2-10 Retrieval Benchmark.
8. P2-11 Citation.
9. P2-12 Safety/Confidence.
10. P2-13 Tests/Release و P2-14 Dossier.

## ۱۹. Gate نهایی و تحویل به فاز ۳

فاز ۲ فقط با این بسته تحویل می‌شود:

- Dataset release ID و Index release ID.
- <span dir="ltr">RAG input/output contract.</span>
- Citation و error/abstention schema.
- <span dir="ltr">Prompt/Policy/Model/Retrieval versions.</span>
- Golden Test report و Regression baseline.
- latency/cost profile محلی.
- <span dir="ltr">health/readiness interface contract.</span>
- release notes، rollback compatibility و known limitations.

Deployment سایت، Auth، PostgreSQL کاربران، Production monitoring و پنل کاربر متعلق به فاز ۳ هستند.

## ۲۰. معیارهای پیشنهادی اولیه

این Targetها پس از Baseline و تأیید متخصص دامنه فریز می‌شوند:

| معیار | Target اولیه |
| ---: | ---: |
| <span dir="ltr">Data lineage/rights coverage</span> | ۱۰۰٪ Release |
| <span dir="ltr">Citation coverage</span> | حداقل ۹۵٪ Claimهای factual |
| <span dir="ltr">Citation location accuracy</span> | حداقل ۹۵٪ |
| <span dir="ltr">Unsupported claim rate</span> | حداکثر ۳٪؛ نزدیک صفر در حساس |
| <span dir="ltr">Safety critical failures</span> | صفر مورد پذیرفته‌نشده |
| <span dir="ltr">Retrieval</span> | Target پس از Baseline؛ گزارش Recall/MRR/nDCG الزامی |
| <span dir="ltr">Reproducibility</span> | اجرای کامل از محیط تمیز |

## ۲۱. تصمیم اجرایی

نقشه فاز ۲ قبلی پایه‌ای قوی داشت. اصلاح قطعی این نسخه:

- Deployment از فاز ۲ حذف و به فاز ۳ منتقل شد.
- منشأ سردبیری، تألیف، مصاحبه و پخش تلویزیونی صریح شد.
- حقوق و مدرک انتساب وارد Data Contract شد.
- Citation از Source list به Claim verification ارتقا یافت.
- Golden set از ۱۰۰ سؤال اولیه به طراحی پیشنهادی ۳۰۰ سؤال ارتقا یافت.
- Safety، Confidence و قرارداد تحویل به فاز ۳ به Gate تبدیل شد.

اولین اقدام بعدی: P2-01 و P2-02 را قفل کنید؛ سپس سه Pipeline را روی همان Contract واحد کامل کنید.

</div>
