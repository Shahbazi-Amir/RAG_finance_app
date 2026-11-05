# Product contracts and NB23 Draft boundary

Proposed separation only; no API or executable model adapter. Source request/response schemas in `references/phase2/contracts/` are **read-only Draft copies**; the source copies and SHA-256 inventory are recorded in `references/phase2/source_manifest.json`.

`nb23.request.v1` permits exactly `contract_version` and `question`. `conversation_history`, `source_filter`, `authority_filter`, `context` are unsupported. Draft response includes `outcome`, `answer_text`, `claims`, `citations`, `confidence`, `version_trace`, `provenance`, `error`; enumerated states are not yet verified with real producer. Resolved Citation sample details are not official response fields. `confidence: null` means unmeasured.

Product identity/history lives above this adapter; avoid forwarding unsupported extras. Full API, streaming, authority filtering and locator resolver require accepted handoff, contract tests and supervisor decision. No runtime is operational.
