# Foundation F3 — 16 bounded owner evidence rows (2026-11-23)
**Primary integration code-tested SHA:** `eff01f8fca2808ee0d44f54cbaf8ca22d15d2a5a` (as of CI [45211590431](https://github.com/Shahbazi-Amir/RAG_finance_app/actions/runs/45211590431), 4/4 SUCCESS). The owner/runtime pins are API #61 `c02ba7896edb78febd2042f7afb1243f2a6aca34`, UI #65 latest tested `f5321d4d647a355313907255a69f35d0d291b02f` and DB tested `996dfc9b66cf8cbd4b37b7a267d08cc5acd5deba`. API #63 is documentation-only.
**Rule:** evidence scope is synthetic Chromium / source scanner / isolated PostgreSQL17.11; this is not Mac E2E, not Phase2 Release/NB23 and not a module Gate pass. All 16 rows remain NOT_ACCEPTED; no original checkbox is marked and no 262/26/105 count changes. 151 PARTIAL, 68 NOT_VERIFIED,43 NOT_RUN baseline unchanged.

| Canonical ID | Evidence owner | Bounded criterion | Exact witness | Environment | Acceptance | Remaining blocker |
|---|---|---|---|---|---|---|
| P3M02-A05 | Foundation/Security | source tracked high-confidence secret scanner + prod npm advisory | GitHub source supply-chain 45211590431; 316 files; High/Critical 0 | SOURCE/CI_OR_ISOLATED_ONLY | NOT_ACCEPTED | Engine/OCI/target security scan remains open |
| P3M02-A07 | Foundation/Security | CycloneDX source lock SBOM API+Web | source supply-chain 45211590431; 28 Python+407 npm | SOURCE/CI_OR_ISOLATED_ONLY | NOT_ACCEPTED | installed Engine/OCI dependency inventory missing |
| P3M04-A06 | DB/DBA | 003 intent ledger no replay with physical schema checks | DB996@996dfc...; CI 45202743968 + integrated 45211590431 | SOURCE/CI_OR_ISOLATED_ONLY | NOT_ACCEPTED | independent Mac DB admission/migration authority missing |
| P3M04-A07 | DB/DBA | pre009 populated upgrade+restore / fault-injected negative / index plan | DB scripts15/16/17; CI 45211590431 | SOURCE/CI_OR_ISOLATED_ONLY | NOT_ACCEPTED | real target data, rollback & capacity not accepted |
| P3M06-A03 | DB/API | strict tenant/owner context with negative RLS | DB996 isolated PG17.11 and tested OwnerFence UI fixture | SOURCE/CI_OR_ISOLATED_ONLY | NOT_ACCEPTED | real Mac signed owner A/B and nine role receipt missing |
| P3M06-A05 | DB/API/UI | cross-user negative / UI late OwnerFence | UI65@f5321... CI 45210742242 + integrated 45211590431 | SOURCE/CI_OR_ISOLATED_ONLY | NOT_ACCEPTED | real signed browser L2 not run |
| P3M14-A01 | UI/API | login session expiry/revoke visible fail closed | UI65 synthetic Chromium 45210742242 | SOURCE/CI_OR_ISOLATED_ONLY | NOT_ACCEPTED | real IdP and signed Mac session missing |
| P3M14-A03 | UI | responsive chat context and owner switching | UI65 1280x800,390x844 synthetic CI 45211590431 | SOURCE/CI_OR_ISOLATED_ONLY | NOT_ACCEPTED | real browsers and signed backend missing |
| P3M14-A09 | UI/API | same-T2 status and double-send one POST, late result never resurrects | UI65 ListEpoch 121 Node + synthetic browser 45210742242; integrated Node126 | SOURCE/CI_OR_ISOLATED_ONLY | NOT_ACCEPTED | real OS single C018 child/Refresh witness missing |
| P3M14-A10 | UI | keyboard Escape/focus and mobile navigation | UI65 synthetic Chromium 45210742242 | SOURCE/CI_OR_ISOLATED_ONLY | NOT_ACCEPTED | real target browsers/accessibility UAT missing |
| P3M14-A11 | UI | desktop and mobile viewport UI regression | synthetic Chromium 1280x800 and390x844 45211590431 | SOURCE/CI_OR_ISOLATED_ONLY | NOT_ACCEPTED | non-synthetic Mac L2 missing |
| P3M19-A01 | Foundation | combined lint typecheck unit build | CI45211590431 API134 Contracts38 Node126 Next build | SOURCE/CI_OR_ISOLATED_ONLY | NOT_ACCEPTED | Mac image build not run |
| P3M19-A03 | Foundation/DB | 001-010 migration idempotence and populated restore | DB996 installer03 blob9cc9458; scripts15-17, CI45211590431 | SOURCE/CI_OR_ISOLATED_ONLY | NOT_ACCEPTED | DBA target receipt/RPO-RTO missing |
| P3M19-A04 | Foundation/Security | negative auth source tests and source supply-chain scan | CI45211590431 full 4 jobs, npm prod high0/critical0 | SOURCE/CI_OR_ISOLATED_ONLY | NOT_ACCEPTED | Engine OCI security and Mac signed L2 missing |
| P3M21-A06 | Foundation/Security | dependency/supply chain source evidence | CI45211590431 Web/API CycloneDX and npm audit only | SOURCE/CI_OR_ISOLATED_ONLY | NOT_ACCEPTED | critical/full image scan pending approved build |
| P3M22-A06 | DB/DBA | independent PostgreSQL synthetic restore with populated data | DB996 isolated CI45202743968 + integrated45211590431 | SOURCE/CI_OR_ISOLATED_ONLY | NOT_ACCEPTED | encrypted full Mac PG+Qdrant restore/RPO-RTO pending |

## Decision boundaries and external ownership
- **Ops/DBA:** approved separate SHA/worktree from source only, no alterations to frozen Mac; independent project/network/ports/volume; DB installer03 exact blob `9cc9458c55b82f03811b346259ccf2ae3dce318d`, 15-17 tests, 001-010 only, full signed HTTPS/IdP/two-owner L2, later separate signed C018 zero-dispatch once authorized.
- **ENGINE/Phase2:** accepted Release/NB23 for Gate00, exact original Engine requirements lock and wheelhouse ABI Python3.11.18/ONNX/qdrant1.18.0, Qdrant coherent copy with physical+logical SHA, typed Author/Editor/Speaker/Locator, C018 OS child receipt.
- **API/UI/DB/Product/CENTRAL:** Consent/Feedback/Delete/Retention/Streaming/Citation T3 contracts require explicit approval; UI65 v0.1 proposal is fixture-only. No migration 011 in first private-no-dispatch install. No Guess SLO/RPO/RTO.
- **Security/Ops:** source scanner is not OCI critical vulnerability or target secret attestation; provide real image digests, scan/SBOM signed receipt, encrypted backup and restore, incident alerts/rollback.
- **CENTRAL:** Gate decisions = 0/26 accepted. No merge/deploy, Gateway/Arvan HOLD.

GitHub [Draft #67](https://github.com/Shahbazi-Amir/RAG_finance_app/pull/67) remains source-only; updated matrix CSV in separate source handoff ZIP mirrors these 16 bounded receipts, without inventing target acceptance.
