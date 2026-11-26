# F3 App-only: common delivery witness and next operations (2026-11-25)

This is a bounded CI candidate receipt, NOT a release approval, Mac run, or CENTRAL acceptance. Source #84 base `0fd1066945ef91a3913e040ab4c350bb645ea502`. Candidate Draft [#143](https://github.com/Shahbazi-Amir/RAG_finance_app/pull/143). Owner source PRs #80/#79/#85 remain separate and untouched.

## Exact successful checkpoint

Tested SHA `4694c7d32cd0608a5b3be5fdd6c76c7a611db0bd`. [Browser + clean DB run 45548913509](https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/45548913509), [signed PG 45548913536](https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/45548913536), [listener 45548913662](https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/45548913662) all SUCCESS, 4/4 jobs. Sanitized DB receipt artifact [14992348884](https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/45548913509/artifacts/14992348884), archive SHA256 `4df1218e9176fce5e4517a2dee8867a4fe404a98fe9604549601819550c36aba`.

| Actual local image in browser job | Image ID (not a target registry digest) |
|---|---|
| API | sha256:e692343946fe1166e80069f4df12a8ae886b04a5abfff464805aad870b15eb07 |
| Web | sha256:64e9ad751a66aa951488ed8e12ad29d24e0d56df807f1ac28a09ff9adcdccb47 |
| Browser witness | sha256:c1be12196ba56e6eb31dc2f8a253c59cb2ff12f3664d9f7f7ce2b71a007122a4 |
| Keycloak | sha256:4938c322f47d3736c580fc57bb335d35c784489bc7e6d8fbbd52dbdd1b27e72e |

PG17.11 registry pin: sha256:73bedc9eaa0121b92b9b26bb52e5141b3f6f37479c7ef913c0160455763ca80a. IdP registry pin: sha256:7e66a96e4739239070aeaf72e4c5decf0f7f682cfc725b9f7ea2b336eaba38b3.

| Delivery step | Observed log marker(s) | Relevant IDs |
|---|---|---|
| 1 startup | STACK_REAL_BOOTSTRAP_TLS_AND_PRODUCT_PG_READY_PASS; private CI topology | P3M18-A03/A04/A09, P3M19-A02 |
| 2 OIDC | BROWSER_BOOTSTRAP_START_303, CALLBACK_303, SESSION_AND_SIGNED_HISTORY_200; two independent subjects and revoke | P3M05-A01/A03/A04/A07, P3M14-A01 |
| 3 History | BROWSER_SOURCE_OIDC_DOM_SQL_IDS_PAGINATION_REFRESH_AB_REVOKE_SEND_PASS | P3M06-A03/A05, P3M13-A04, P3M15-A03/A07 |
| 4 repetition and faults | SAME_STACK_TLS_HOST_IDP_INVALID_PROOF_NO_CERT_DIRECT_WEB_PASS; BROWSER_APP_ONLY_REPEAT_VALID_SEND_DENIED_PASS; BROWSER_REAL_CSRF_DENY_SESSION_REMAINS_ACTIVE_PASS; SAME_STACK_PG_OUTAGE_503_PASS | P3M05-A05, P3M13-A03/A06, P3M14-A09, P3M20-A10, P3M21-A02/A04/A05 |
| 5 restore | RESTORE_INDEPENDENT_CLUSTER=PASS; BROWSER_RESTORE_OIDC_DOM_SQL_IDS_PAGINATION_REFRESH_AB_REVOKE_SEND_PASS; BROWSER_SQL_LINEAGE_COUNTS_REVOKE_RESTORE=PASS | P3M22-A01/A06/A09/A10, P3M20-A06 |

Source marker 04:47:31.593617 UTC; PG outage marker 04:47:32.219072 UTC; independent restore marker 04:47:39.297603 UTC; completed restored browser+SQL marker 04:47:45.223558 UTC. These are observed timestamps, not an approved RTO/RPO measurement. Later lab probe records monotonic elapsed time separately. The CI job has 16 sanitized DB receipts, 10-down/10-up clean rollback, schema SHA256 equality, 14 FORCE RLS tables, 72 denied direct SELECTs, corrupted backup 2/2 rejection and actual PG SIGKILL/WAL recovery. DB M10 concurrency and lost-ACK simulated replay pass, positive HTTP Send persistence remains NOT_RUN.

| Role | Before → after | Transfer/commit or witness | Remaining |
|---|---|---|---|
| Foundation | isolated jobs → same-job private browser/PG journey 5/5 | #143 and exact green SHA | actual tested-image scan, target installation, owner decisions |
| API | History 503 → signed History 200, foreign 404, revoke 401, Send 503 | six #80 blobs + same-SHA signed/listener runs | positive authorized durable HTTP admission is not part of APP_ONLY; engine unavailable |
| DB | isolated read checks → source+restore actual PG ownership, ledger and crash recovery | #79-derived scripts; artifact 14992348884 | authorized target volume, approved retention/encryption, target RTO/RPO |
| UI | synthetic intercepted History → actual OIDC/History desktop+320px, keyboard and CSRF denial | #143 browser job | other browsers, approved policy and engine-only UI |

## Next reproducible steps (CI only)

- Checkout exact candidate in a disposable isolated runner; run its three workflows with exact SHA. Browser workflow builds API/Web/browser, creates random private project and TLS material, performs ordinary OIDC, and restores a fresh PG volume. Only the explicit isolated CI scripts may write synthetic fixture rows.
- Post-journey DB job makes its own empty lab, uses pinned 001–010, runs scripts 00–06, 09/10, 12–17, 19–25 and 11 sanitized export as ordered by workflow. Do not run 011. No existing volume may be deleted.
- New historical replay test uses separate fixture phase after zero-write checks. Repository T1/T2 creates synthetic historical rows in the disposable restored lab, then signed HTTP GET checks stable IDs and denies same POST, foreign access and revoked session. No actual HTTP Send admission or generation. Latest new test must be green before claiming this witness. First test failed import; fix `effe0a8f1b66b39cb96f2131c23ee46da80e9cf9`.
- Actual image supply chain script saves only built image archives, invokes scanner without Docker socket or runtime secret mounts, collects CycloneDX and redacted advisory summaries. Scanner tag must be verified by real pull and recorded ID/digest; missing DB, pull failure or incomplete results means NOT_VERIFIED. Source scan and image scan verdict separate from journey. Findings require review; no vulnerability threshold approval is invented.

## Ops-only target handoff (instructions, not executed)

Before any destination work, Ops must provide approved isolated project/volume names, snapshot/rollback owner, free Docker VM capacity, actual target image digests and architecture, TLS/IdP and private role-only credentials, and approved RPO/RTO/retention. Never reuse or stop existing Mac demo. Keep `APP_ONLY`, no 011 or engine. Verify snapshot and backup restoration feasibility before start, verify candidate SHA and image manifest/scan, then install pinned migration 001–010 on a new volume, inspect grants/DB55/TLS, start private Bootstrap/API/Web/IdP through reviewed target wiring, run two-account E2E plus failure cases, restore into another fresh volume and repeat E2E. If a step fails, stop only the new project; retain existing snapshot, diagnose first assertion, rollback only by authorized operator. Do not reuse ephemeral CI credentials or alias store on target. CI scripts explicitly fail outside GitHub Actions and are not a Mac deployment script. Target topology/secret provisioning and approval still required.

## Decision inputs (no implicit approvals)

- CENTRAL/Product: decide durable Send/no-dispatch contract (P3M10-A10, P3M13-A06, P3M15-A10); preserve default denial until reviewed. Consent/withdrawal/delete/export/feedback policy: exact approved data categories, retention and authorization matrix; no mutation policy inferred.
- Ops: provide exact isolated target and rollback authorization, approved image digests and security finding dispositions, browser/SLO/RPO/RTO bounds. Verify via target-specific receipts, not CI.
- Engine/Release: Issue #78 original engine lock, wheelhouse ABI, approved Release/NB23, Runner/Qdrant assets; no activation requested. Gate00 and all engine-dependent assertions remain open.
- Owner review: 16 proposed keep decisions in existing 58-path audit; no owner approval yet. Sign actual reviewed SHA and conflict disposition before promotion.

Registry acceptance and 26 gates remain unchanged. This receipt is evidence of the five-step CI journey, not a new canonical activity or official release.
