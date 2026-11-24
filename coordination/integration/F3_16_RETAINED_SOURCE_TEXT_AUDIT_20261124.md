# F3 — 16 retained three-way files: source-line reconciliation (non-acceptance)

**Source:** exact candidate parent SHA `c6705614255ff09b840e5e34395bc5dc11908e58`; inputs unchanged from `coordination/integration/FOUR_PR_58_PATH_THREE_WAY_AUDIT_20261124.json`: UI PR #65, API #76 and DB #59 heads. This is an audit, not a change to P0-1 integration decisions.

Method: fetch actual candidate and each owner-source file at its pinned Git SHA. Normalize nonempty source lines with whitespace trim and count source-only line occurrences absent anywhere in the candidate. Textual inclusion is **not** proof of equivalent behavior, line order, flow, safety or signed owner acceptance.

| Retained file | Source owner(s) | Source-only nonempty lines | Owner follow-up |
|---|---|---:|---|
| .github/workflows/foundation-integration-staging-candidate.yml | UI,API | 16 | Engine/C018 branch and SHA witness require separate authorization; no auto-import |
| apps/api/product_session_api.py | UI | 1 | Review changed exception boundary against verified mTLS and negative tests |
| apps/web/app/history/page.tsx | DB | 333 | Old client page vs current re-export; review history behavior and routing |
| apps/web/app/layout.tsx | DB | 2 | Resolve product text/title and origin attribution |
| apps/web/app/page.tsx | DB | 480 | Old client home page vs current re-export; preserve authenticated app-only UI |
| apps/web/README.md | UI,API,DB | 0 | Verify docs ordering and accurate release assertions |
| apps/web/src/history/client.ts | DB | 5 | Candidate has richer T2 trace/attempt correlation; do not downgrade |
| coordination/open_decisions.md | DB | 0 | Await decision owners; text presence is not approval |
| coordination/phase3_checklist.md | UI,API,DB | 0 | Preserve 262 activities +26 Gates +105 noncounting mappings |
| coordination/tasks/AGENT-API-AUTH-BOUNDARY-01.md | DB | 0 | Do not equate task documentation with acceptance |
| coordination/tasks/AGENT-FOUNDATION-01.md | DB | 0 | Confirm independent Gate owner/witness |
| coordination/tasks/AGENT-UI-01.md | DB | 0 | Review target auth/mobile criteria |
| src/phase3/rag_runtime/retrieved_sources.py | UI | 0 | Never execute/import Engine outside explicit mission |
| tests/phase3/api/test_retrieved_sources_gate3.py | UI | 1 | Review pinned chunk/receipt import; keep producer integrity assertions |
| tests/phase3/ui/product-chat-client.test.mjs | API | 1 | Compare strict isVerifiedLiveAnswer assertion with candidate's current gate |
| tests/phase3/ui/README.md | DB | 0 | Reconcile scope/CI/target evidence |

**Result:** 16/16 mechanically inspected, 8 with no source-only lines, 8 with one or more. **16/16 still pending owners.** No source file was force-replaced or blindly merged; this audit cannot promote any of P0-1, 262 primary activities, 26 Gates, or 105 crosswalks.
