# F3 — آزمایش ایزولهٔ Export/Import imageهای واقعی Web/API

این یک آزمایش **CI-only** در شاخهٔ مستقل است و هیچ دسترسی یا تغییر به
Mac، پشتهٔ موجود، PostgreSQL واقعی، IdP، Qdrant، Runner، Engine یا SQL011 نمی‌دهد.

دقیقاً همان دو image ساخته‌شده از SHA checkout با docker save به آرشیو محلی
می‌روند؛ tagهای محلی runner حذف و با docker load برمی‌گردند. Docker image
ID هر دو باید بایت‌به‌بایت ثابت بماند. سپس هر دو سرویس واقعاً با کاربر
غیر-root، mount فقط‌خواندنی، شبکهٔ none و بدون پورت عمومی اجرا می‌شوند:
API live 200، API ready 503، API Send 503، Next capability غیرفعال و
Next Send 503 حتی با بدنهٔ JSON معیوب. SBOM از همین imageهای بازگردانده‌شده
گرفته می‌شود و SHA/ID تطبیق داده می‌شود.

فایل‌های اجرا:
- .github/workflows/f3-oci-airgap-disposable-ci.yml
- scripts/phase3/verify_f3_oci_airgap_rehydrate_ci.sh
- scripts/phase3/check_f3_oci_airgap_receipt.py
- tests/phase3/foundation/test_f3_oci_airgap_receipt.py

**محدودیت‌ها:** SHA256 آرشیو docker save **registry manifest digest نیست**؛
این آزمایش به معنای rollback دیتابیس یا مقصد نیست. زمان آن SLO/RPO/RTO
مصوب نیست. هیچ policy امنیتی، release، Gate، فعالیت canonical یا پذیرش
CENTRAL را خودکار تغییر نمی‌دهد. تمام این موارد HOLD باقی می‌مانند.
