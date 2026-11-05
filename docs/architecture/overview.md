# Proposed Phase 3 architecture overview

Status: **proposed, not implemented or accepted**. Pinned source: `7c74783c3dcda897b010ba9ea358d113f172ed1f`.

- UI: responsive RTL, consent/chat/history/source drawer/privacy and safe offline/retry views, without inventing full NB23 Citation/streaming.
- API: product-owned identity/authorization/error/idempotency/trace envelope, adapter to Phase 2 **only after** accepted release and Module 00 checks.
- Database: per-user users/consent/sessions/conversations/messages/citations/feedback/audit/deletion records with strict isolation; schema and RLS tests later.
- RAG boundary: Draft NB23 request only `contract_version` and `question`; no history/context/filter inputs. Outcome enums only candidate consumer vocabulary. Synthetic Citation IDs not production source resolver.
- Security and operations: shared foundation coordination, human final operations owner pending, least privilege, no logs with PII, source-use controls, backup/restore, load and incidents untested.

Modular monolith and technology examples from source maps are **proposals**, not frozen Stack. Do not select provider/model/hosting/auth/retention/scale/SLO/budget. Phase 4 functions remain explicitly excluded. Parallel UI/DB design and foundation docs do not unblock NB23/Module 00.
