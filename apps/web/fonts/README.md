# Vazirmatn — local font asset provenance

This app bundles **one unmodified variable WOFF2** for Persian/Arabic UI text, served locally by `next/font/local`.

| Field | Verified value |
| --- | --- |
| Original project | https://github.com/rastikerdar/vazirmatn |
| Official release | https://github.com/rastikerdar/vazirmatn/releases/tag/v33.003 |
| Tag | `v33.003` |
| Upstream file | `fonts/webfonts/Vazirmatn[wght].woff2` |
| Bundled file | `Vazirmatn-Variable.woff2` (unchanged bytes; filename normalized) |
| Font format | WOFF2, variable weight axis `wght 100–900` |
| Size | 111,152 bytes |
| SHA-256 | `4e3fa217d38fdafc1fea4414ceb58ca5e662cf0ab5fa735a8c8c20e8b42cad92` |
| Git blob SHA-1 | `a501289a85595158570b0c2badcb4608b042e748` (identical to official tag) |
| License | [SIL Open Font License 1.1](OFL.txt); copyright © 2015 The Vazirmatn Project Authors |
| License file from tag | `OFL.txt`, Git SHA `be66b3824e9772e75141e631695c5256f105fb57` |

**Integrity method:** retrieve the WOFF2 from the upstream `v33.003` tag, decode the base64 transfer, validate the `wOF2` magic, byte length, SHA-256 and original Git blob SHA before copying the exact binary Git blob into the product repository. No release ZIP, CDN, additional font variant, or system-wide installation is included.

The font is applied globally through `apps/web/app/layout.tsx`. A real browser check in `tests/phase3/ui/browser_check.py` verifies font-face readiness and the effective font in ordinary text and composer, with no external font requests. These browser checks must be **executed** on a running UI before counting them as PASS.
