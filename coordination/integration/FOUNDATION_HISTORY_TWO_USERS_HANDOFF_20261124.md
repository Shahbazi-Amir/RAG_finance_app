# FOUNDATION_F3 shared candidate — First two-user History journey

**Candidate root**: PR #84 HEAD `0fd1066945ef91a3913e040ab4c350bb645ea502` (fresh isolated branch `integration/f3-foundation-history-two-users-20261124`). Owner transfer is exact Git blobs from PR #80 `cc04bef906d827c20dcdf5da49897246c7f2a7dd`, **not** a copy of #80's default API Dockerfile or CI identity claim.

Imported private signed ASGI entrypoint, mTLS socket liveness probe, strict config sample, 2 source/transport test suites, #80 runbook and a separate signed API Dockerfile. Original `apps/api/app_only_asgi.py` and original `Dockerfile.api` remain unchanged; the regular APP_ONLY Send deny and History 503 remain fail-closed until the real private BFF, Postgres, Bootstrap and IdP are wired.

**Run the imported L1 tests**:
```bash
python -m unittest discover -s tests/phase3/api -p test_app_only_no_engine.py -v
python -m unittest discover -s tests/phase3/integration/api -p test_app_only_mtls_network.py -v
```
The imported HTTPS/mTLS test uses an in-memory inner ASGI app and a patched DB readiness verifier: it is **not** proof of a real Browser→SQL History journey. Do not promote the five user-specified journey steps until witnessed in a single namespace with authenticated A/B and restored DB.

**Verified source witness before any execution**: #84 report `SIGNED_HISTORY_NOT_CONFIGURED` at GET /v1/conversations and 503 readiness, no token accepted from browser header. No Mac demo/011/Qdrant/Engine/server deployment allowed. The signed API path must be explicitly Ops-configured, with strict 0600 private file and real mTLS BFF fingerprint, RS256 issuer/audience and restricted PG roles. The #80 runtime deliberately refuses `CI=true` and `GITHUB_ACTIONS=true` environment flags; a real lab profile requires separate correctly bounded changes, not disabling trust checks.

**Next barriers**: assemble genuine standard OIDC IdP two subjects → signed BFF → real API/Bootstrap → TLS PG17.11 001–010 History with A/B RLS; replay after fresh-volume restore. Evidence must include SHA, HTTP/SQL IDs, screenshot/browser trace, migration ledger digest and strict negative Send/revoke/peer probes. Until then Gate 0/26; 0/5 full journey steps independently passed.