# FOUNDATION F3 app-only API listener — restricted CI scope

On 2026-11-24 the Foundation candidate imports source blobs from specialist UI #65, DB #59 and API #76 without file conflict, and adds a **real** isolated API process to replace the previous import-only Docker CMD.

## Exact boundary
- `apps.api.app_only_asgi` is the intentionally restricted listener; it **does not** import/execute engine Runner, Qdrant, model, Gateway or the signed/DB-backed Product handlers.
- `GET /health/live` is process liveness (HTTP 200). `GET /health/ready` is always 503 until full signed IdP+PG+Product wiring is installed in a separately verified entrypoint. No fake readiness.
- `GET /v1/capabilities` returns `ui.runtime_capabilities.v1` with disabled Send and unavailable engine/generation.
- `POST /v1/messages` always returns 503 `ENGINE_NOT_AVAILABLE` without consuming the request body or making durable T1/T2 reservations. History/status reads are 503 `SIGNED_PRODUCT_API_NOT_WIRED` rather than fixture data or false 401. No raw prompts or PII in logs.
- Docker runs as UID 11001; `HEALTHCHECK` proves process liveness only. CI-only DockerHub BASE override remains **not** an approved ECR release digest.
- No public port mapping is authorized. This is a disposable CI smoke listener, not a production-ready replacement for signed API/Bootstrap.

## Reproduction
`python -m unittest tests.phase3.api.test_app_only_asgi -v` in the locked Python 3.13 environment; then run `.github/workflows/f3-m18-m19-real-image-http.yml` on the exact source commit. The CI tests docker image, GET live/ready/capabilities, POST Send deny, zero-body-read handler and unchanged in-container no-engine API suite.

## Still open
Full Web→BFF→signed API/Bootstrap→PG with two real identities, service TLS trust, app readiness, install/backup/restore, CVE scan and approved base digest, Mac isolated Ops witness, consumer contract tests and CENTRAL acceptance. The gateway, engine, server and any production deploy remain disabled. An isolated listener success **is not** a Gate PASS.
