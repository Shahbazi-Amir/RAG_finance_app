# FOUNDATION_F3 | چرخهٔ رسمی پیشرفت و اجرا | 2026-11-23

> **اول گزارش → سپس کدنویسی و آزمون → سپس ثبت GitHub → پراگرس‌بار نهایی.** هیچ اجرای پس‌زمینه یا پذیرشِ خودکار انجام نمی‌شود.

## پراگرس‌بار واقعی از CSVهای پیوست

| حوزه | پراگرس بار برای PARTIAL | پوشش جزئی | وضعیت دقیق | تغییر همین نوبت |
|---|---|---:|---|---:|
| Foundation | `███████████░░░░░░░░░░░░░░░░░░░░░` | **33.06%** | 40 PARTIAL, 38 NOT_VERIFIED, 43 NOT_RUN / 121 | **+0.00 pp** |
| کل Phase3 | `██████████████████░░░░░░░░░░░░░░` | **57.63%** | 151 PARTIAL, 68 NOT_VERIFIED, 43 NOT_RUN / 262 | **+0.00 pp** |
| پذیرش واقعی | `░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░` | **0.00%** | 0/262 activity, 0/26 Gates | **+0.00 pp** |

**PARTIAL ≠ DONE.** نسبت 40/121 و 151/262 پوشش فعالیت‌های «شروع‌شده» است، نه میزان تکمیل واقعی. 105 alias عملیاتی غیرشمارشی و 26 Gate مستقل‌اند. کل ماتریس: 262+26+105=393 ردیف.

## کار انجام‌شده در این چرخه

1. خواندن مستقیم چهار CSV کاربر و تطبیق SHA256 هر کدام. ماژول‌های P3M00…P3M25 جداگانه محاسبه شدند.
2. تولید `f3_progress_cycle.py` به همراه گزارش فارسی/JSON و مقایسهٔ درصد با چرخهٔ قبل. **22/22** تست محلی PASS؛ منفی‌ها شامل جعل پذیرش، تغییر شمارش، ID تکراری، فایل دست‌کاری‌شده و شمارش دوبارهٔ alias هستند.
3. بستهٔ کامل *source-only* `FOUNDATION_F3_CYCLE_PROGRESS_REPORTER_20261123.zip`: SHA256 `0a591918d8c38906b019e485033ecb48ce5480ac3de2295b77ded1aafa2f8bd0`. شامل چهار CSV اصلی، کد تولید گزارش، آزمون‌ها، progress.json و SHA256SUMS است. GitHub checkpoint `coordination/f3_execution/progress_cycles/20261123.json` فقط خلاصهٔ قابل‌حسابرسی آن را حمل می‌کند؛ فایل‌های حجیم و تست 22گانه در ZIP هستند.
4. کنترل مستقل شمارش GitHub: `scripts/f3_progress_checkpoint_verify.py` مجموعهٔ 26 ماژول و نسبت‌ها را بررسی می‌کند؛ **اعتبارسنجیِ حسابی جای فایل خام/امضای Ops را نمی‌گیرد**.

آخرین محصول یکپارچه قبل از این چرخه: `ac6aaf616c7e4c630e456316d96185d882de5580`، [CI 45223368556](https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/45223368556) 4/4 PASS. کد محصول در این چرخه تغییر نکرد؛ CI روی SHA جدید فقط پس از اجرا قابل انتساب خواهد بود.

## مانع واقعی و ترتیب ادامه تا 100%

1. **ENGINE/CENTRAL**: Release/NB23 پذیرفته‌شده و اصالت Source/Locator/Author/Editor/Speaker، Lock اصلی Engine و Python3.11.18 wheelhouse/ONNX/Qdrant ABI (Gate00 BLOCKED).
2. **Ops**: Snapshot/Build و نصب تمیز روی پشتهٔ **جدا** در مک، Digest ایمیج واقعی، UID/HOME/PKI/config/mount؛ دمو فریز تغییر نکند.
3. **API/UI/DBA/Ops**: HTTPS/OIDC/mTLS و A/B واقعی با Receipt/Attempt، 202/200/404/401، Refresh فقط GET، RLS واقعی.
4. **ENGINE/Ops**: C018 فقط با مجوز جدا، OS child=1, top_k=10, CONTEXT_READY, dispatch=false, generation_calls=0، Refresh بدون child اضافه.
5. **DBA/Security**: Backup/Restore مستقل، Tombstone/ACL/RLS، اسکن OCI و SBOM، SLO/RPO/RTO و Load واقعی.
6. **CENTRAL/Employer**: 26 پذیرش رسمی، Go/No-Go و در صورت تصویب انتشار/Hypercare.

**Frozen Mac UNTOUCHED · ARVAN HOLD · No Mac/C018/Gateway in this cycle.** هیچ درصد پذیرش به خاطر ایجاد گزارش افزایش داده نشده است.
