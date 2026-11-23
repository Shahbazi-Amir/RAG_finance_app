# F3 app-only isolated Compose — never the signed target

This lab consumes the immutable, exact-SHA API/Web CI image tags and supplies only a two-process **restricted** runtime. It never loads secrets, Engine, Qdrant, PostgreSQL, OAuth, an Auth fixture, or production data. No volume mounts, no old Mac Docker project, no listener mapped for API. Web port `127.0.0.1:3100` is localhost only; the API-only network denies API egress; Web has a separate ingress bridge for localhost port publishing and is not an egress-isolation guarantee. Never insert secrets or production sessions.

## Reproduce with already-built, verified images

```bash
export F3_API_IMAGE=f3-api-l1:<exact-ci-sha>
export F3_WEB_IMAGE=f3-web-l1:<exact-ci-sha>
export F3_WEB_HOST_PORT=3100
docker compose -p f3app-only-ci -f infra/phase3_l1/compose.app_only_isolated.yml config --quiet
docker compose -p f3app-only-ci -f infra/phase3_l1/compose.app_only_isolated.yml up -d --no-build
curl --fail http://127.0.0.1:3100/api/product-capabilities
docker compose -p f3app-only-ci -f infra/phase3_l1/compose.app_only_isolated.yml down --remove-orphans
```

Expected only `DISABLED` Send and false engine/generation. There is no end-to-end History acceptance: readiness still 503 until verified signed IdP+PG. Nonroot UIDs: API 11001; Web 11003; read-only filesystem with bounded tmpfs, cap-drop, no-new-privileges, CPU/RAM/PID limits, local-only web ingress. Container cleanup must only address this unique Compose project. Do **not** run `down -v` against existing deployments.

This lab is not a substitute for the Mac/Ops namespace, TLS SAN/CA and client-cert pinning, signed BFF, real IdP or A/B PG restore witness. CI DockerHub base version tags remain non-approved for release.
