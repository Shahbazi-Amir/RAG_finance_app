# LOCAL_DOCKER_UI_FIXES

این فهرست برای بازبینی انتخابی اصلاحات نسخهٔ آزمایشی B است. مبنای اجرایی `ops/nb23-v4-staging` در `af57f26` با تغییرات محلی همان مأموریت است. هیچ کد، Schema یا migration از جریان‌های موازی وارد پشته نشد. وضعیت پذیرش رسمی و Golden جداست.

| پرونده و نگاشت | تغییر محلی و علت | آزمون و انتقال انتخابی آینده |
| --- | --- | --- |
| `LOCAL-UI-01` / UI-05, UI-06 / P3M14-A02/A03, P3M15-A01/A03 | `apps/web/src/ui/product-chat.tsx` کارت را بعد از پیام کاربر با شناسهٔ Message حاصل از پاسخ امضاشده قرار می‌دهد. شناسه و Trace مربوط به Attempt در Status و Engine Status باید برابر باشند. علت، نمایش دو فهرست جدا بود. | آزمون fixture مرورگر، همسایگی DOM را با Message و Attempt امضاشده می‌سنجد. متخصص UI فقط منطق گروه‌بندی و اعتبارسنجی را با DTO و ترتیب صفحه‌بندی مقصد تطبیق دهد. |
| `LOCAL-UI-02` / UI-05 / P3M14-A02, P3M15-A02/A07 | `infra/nb23-v4/session_conversation_titles.sql` عنوان خالی را با ۴۸ نویسه یا کمتر از نخستین پرسش هم‌مالک پر می‌کند و عنوان دستی را حفظ می‌کند. Trigger محلی و backfill روی ستون موجودند. `provision_session_postgres.py` این overlay را فقط برای DB آزمایشی اعمال می‌کند. | dry-run با نقش history_app و rollback، عنوان نخست، حفظ عنوان دستی و محدودیت طول را آزمود. backfill شمار رکوردها را ثابت نگه داشت. متخصص Database روش عنوان‌گذاری و rollout خود را بازبینی کند. Trigger محلی یا SQL مشترک از این شاخه منتقل نشود. |
| `LOCAL-UI-03` / UI-03, UI-05 / P3M14-A01/A02, P3M15-A07 | `product-chat.tsx` مسیر هم‌بستگی owner-bound و draft مستقل را حفظ می‌کند. جایگزینی BFF فقط در نسخهٔ B با انتقال در حافظهٔ store موجود انجام می‌شود. سیاست ۳۰ دقیقه/۸ ساعت از checkpoint پیشین است. | سیاست و revocation از طریق `--http-session-policy` قابل بازآزمایی است. متخصص UI فقط رفتار Refresh/History را در مدل نشست مقصد بررسی کند. مهلت آزمایشی و دستور Docker برای انتشار عملیاتی منتقل نشوند. |
| `LOCAL-UI-04` / UI-05, UI-06, UI-10 / P3M14-A02/A03/A09, P3M15-A03/A10 | `product-chat.tsx` History را دوره‌ای و هنگام بازگشت به تب می‌خواند، حالت completed مستقل را نشان می‌دهد، متن تکراری کارت را حذف می‌کند و گزینهٔ وضعیت فقط هنگام شکست بازیابی ظاهر می‌شود. مسیر دکمه فقط GET است. | fixture وضعیت تکمیل، غیبت دکمه‌های حالت سالم و عدم POST را می‌سنجد. متخصص UI این منطق را با polling یا lifecycle پذیرفتهٔ مقصد تطبیق دهد. این آزمون شاهد Streaming یا Cancel نیست. |
| `LOCAL-UI-05` / UI-06, UI-11 / P3M14-A03/A10/A11 | `apps/web/app/history/history.css` اسکرول پیام را از composer جدا می‌کند. `product-chat.tsx` آخرین نتیجه را هنگام حضور نزدیک انتهای فهرست دنبال می‌کند. `infra/nb23-v4/Dockerfile.session-v4-web` CSS محلی را در مشتق UI می‌سازد. | fixture هندسهٔ composer و پیام‌ها و قابلیت اسکرول را می‌سنجد. متخصص UI اصلاح overflow و composer را با layout مقصد بازسازد و دسکتاپ/موبایل را بررسی کند. فایل‌های محلی جایگزین کامل فایل‌های فاز سوم نمی‌شوند. |

روش انتقال آینده بر اساس نیاز و پس از بررسی متخصص و ناظر است. نتیجهٔ عملی هر آزمون در checkpoint ۲۹ گزارش تجمعی ثبت می‌شود. هیچ Checkbox رسمی یا Gate از این فهرست تغییر نمی‌کند.

در checkpoint ۲۹، Build و TypeScript، dry-run/backfill عنوان، HTTPS/GET/Logout و حفظ نشست/Worker شاهد واقعی گرفتند. آزمون DOM در navigation متوقف شد. انتظارهای fixture دربارهٔ ترتیب، دکمه‌ها و هندسه برای بازآزمون ثبت‌اند.


### تأیید انسانی checkpoint ۳۰

مالک Refresh، عنوان فارسی، اتصال سؤال/نتیجه، حذف دکمه‌های اضافی، اسکرول و انتخاب History را روی Build checkpoint ۲۹ موفق اعلام کرد. این شاهد دستی جدا از نتیجهٔ ابزار پیشین و از انتقال به فاز سوم است.

### Checkpoint 41 — saved synthetic Generation and closed package

- UI-03/UI-05/UI-06, Module 14 and 15. The saved card is now read through a signed owner-scoped History projection keyed to Message, Attempt and Trace. Existing client-only correlators no longer determine whether a saved response is visible. Both legacy flower and financial answers survived refresh and sign-in in Chrome.
- UI-10/UI-11, Module 14 and P3M10. The synthetic profile labels stored Generation and its initial latency, shows a persisted failure when applicable and stops new submissions after the package cap. The signed API also refuses before T1/T2. No Gateway request was made in the regression checks.
- Local paths: `apps/api/product_session_api.py`, `apps/web/src/history/client.ts`, `apps/web/src/ui/product-chat.tsx`, and the dedicated Chrome scripts under `infra/nb23-v4/`. For a future specialist handoff, move only the owner-bound read projection or UX change after API/UI review. Keep the synthetic cap policy and temporary test profile local. [Evidence](MAC_FIRST_START_FA.md).

### Checkpoint 43 — real retrieval and disabled Generation boundary

- P3M14-A09/A11 and P3M15-A07. The local real-context Web profile displays the blocked external Generation state under the matching historical Message and accepts the measured real Worker duration. It retains archived synthetic results independently of the real retrieval state.
- Paths: `apps/web/src/history/client.ts`, `apps/web/src/ui/product-chat.tsx` and the signed projection in `apps/api/product_session_api.py`. Offline Next/TypeScript and signed BFF-to-Worker-to-History tests passed for the completed real Attempt. Two earlier timeouts were left UNKNOWN.
- A specialist handoff should review the reusable owner/Trace projection and accessible status copy. The 600-second diagnostic deadline and archive-only provider mode remain local. [Evidence](MAC_FIRST_START_FA.md).

### Checkpoint 44 — measured retrieval duration in saved History

- P3M14-A09/A11 and P3M15-A07. The signed History projection attaches the saved Worker duration only to the owner-matched blocked Attempt. The Web client validates the field and displays it together with the blocked explanation, including after a new sign-in.
- Paths: `apps/api/product_session_api.py`, `apps/web/src/history/client.ts`, `apps/web/src/ui/product-chat.tsx` and `infra/nb23-v4/check_owner_saved_chrome.py`. Offline build and Chrome verification passed without a new Send. Keep the performance and timeout settings outside future UI cherry-picks. [Evidence](MAC_FIRST_START_FA.md).
