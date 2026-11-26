# App-only residual security review and capacity evidence (NOT_APPROVED)

Exact known green image scan: ffdbf03a91870eced8ecdbb80659ff2cc324fee9, run 45652033205, artifact 15040217938, sha256 0807c6d4283ac3124b4751dcca7079b6434aeb816eac019e8611620f4daa6f9a independently verified. Findings are per scanner package/version/CVE entry, not confirmed exploitability; unique IDs per image are not additive.

| Role | HIGH+CRITICAL findings | Unique IDs | Fixed-version field present | No fixed-version field |
|---|---:|---:|---:|---:|
| API | 86 | 48 | 40 | 46 |
| Web | 49 | 21 | 10 | 39 |
| PG | 140 | 66 | 26 | 114 |
| IdP | 6 | 6 | 1 | 5 |
| Browser lab | 192 | 99 | 40 | 152 |

API/Browser fixable entries concentrate in libssl3 (9), openssl (9), perl-base (8), libgnutls30 (5), libpcre2-8-0 (4), and 5 other packages (one each). cfc9fe7321604f8168ce3904fac45bc31d293659 run 45654410384 confirmed minimum package versions installed and built; signed PG run 45654410286 passed. Browser source 48/48 distinct IDs and all ordinary source assertions passed, but trace witness failed and restore/scan did not run. Do not claim additional CVE reduction until complete new scan.

Web fixable entries are npm transitive/global packages (brace-expansion 5, pacote 2, picomatch 1, sigstore 1, ip-address 1); identify installed layer before changing lock or base. PG 26 fixable entries report stdlib; DB owner must identify runtime and candidate digest, keep PG 17.11 and migration pins until reviewed. IdP 1 fixable Guava entry; owner review pinned Keycloak image and supported update; no independent auth policy change. Browser-only findings never become a release image. Entries without fixed version still require applicability/exposure review; no blanket exceptions. Security owner disposition pending for every residual group. No Production promotion.

## Capacity and environment matrix (proposals, no target SLO)
Source CI on 36ae868f7c1f445c25c597319e7baec8da741b1d: A-list p50/p95/p99 32.607/35.988/35.988 ms; restore 32.867/40.015/40.015 ms. Bounded workload 48 sequential + 53 bounded + 8 simultaneous requests per stage on later real green run. Parallel A/B 16 intersecting request pairs each stage; not server saturation/stress/soak. Actual runtime limits CPU/memory: API 1/512MiB, Web 1/768MiB, Bootstrap 1/512MiB, ingress 0.5/256MiB, IdP 2/1536MiB; these are lab settings, not production sizing. 0eec4413 restore+replay 16008 ms, zero lost synthetic rows; not target RPO/RTO.

Local: developer checkout/worktree, no credentials committed. Test: isolated CI actual Web/API/Bootstrap/IdP/PG; exact SHA and digest, synthetic identities only; engine disconnected. Staging/production: NOT_AUTHORIZED; Ops target topology, location, TLS, privacy, capacity, backup, smoke and rollback must be approved separately. No Mac/main/011/engine/paid traffic.

P3M01-A04 / A06 / A07: environment distinctions, lab timing and restore evidence supplied; employer target numeric bounds and authorization missing. P3M21-A10: residual dispositions pending, no signed acceptance. P3M23-A09: bounded capacity baseline; actual resource observation, stress and tuning approval needed. P3M24-A08 / P3M25-A03: error/latency read monitoring, model cost/citation/safety absent in APP_ONLY; not production monitoring or hypercare. No numeric thresholds invented.
