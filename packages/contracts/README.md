# Product contracts and NB23 Draft boundary

Proposed separation only; no API or executable model adapter. Source request/response schemas in `references/phase2/contracts/` are **read-only Draft copies**; the source copies and SHA-256 inventory are recorded in `references/phase2/source_manifest.json`.

`nb23.request.v1` permits exactly `contract_version` and `question`. `conversation_history`, `source_filter`, `authority_filter`, `context` are unsupported. Draft response includes `outcome`, `answer_text`, `claims`, `citations`, `confidence`, `version_trace`, `provenance`, `error`; enumerated states are not yet verified with real producer. Resolved Citation sample details are not official response fields. `confidence: null` means unmeasured.

Product identity/history lives above this adapter; avoid forwarding unsupported extras. Full API, streaming, authority filtering and locator resolver require accepted handoff, contract tests and supervisor decision. No runtime is operational.

## Versioned provisional contract ownership and boundaries

- Foundation is the sole editor of shared `packages/contracts/**` and `schemas/phase3/**`; API, UI and DB agents review proposed changes without creating parallel DTOs. Historical NB23 Draft schemas are immutable source evidence, not editable product schemas.
- After Foundation acceptance and a separate task, UI and DB can test versioned **Mock/Fixture** adapters and independent history/persistence. These do not establish live producer compatibility.
- Streaming and Cancellation **remain required** eventual product contracts; their real event sequence and server stop semantics are pending authoritative API/runtime verification. `speaker` and `speaker_name` mapping requires explicit product-contract decision and evidence.
- Data deletion workflow must not be blocked solely by an unresolved optional Export feature. Product/backend confirmation is required before representing deletion as successful.
