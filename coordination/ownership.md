# Ownership and no-double-count protocol

| Role | Responsibility | Editable task evidence |
|---|---|---|
| foundation | Sole canonical checklist editor, shared docs/contracts, integration, security, operations and Gates coordination; human operational owner assignment pending | `coordination/tasks/AGENT-FOUNDATION-01.md` |
| API | Product API-specific preparation and future implementation (not live model adapter yet) | `coordination/tasks/AGENT-API-*.md` |
| UI | RTL/chat/source/consent flows and future UI scope | `coordination/tasks/AGENT-UI-*.md` |
| database | Conceptual data/isolation/privacy and future migrations after permission | `coordination/tasks/AGENT-DATABASE-*.md` |

Only **foundation** edits `coordination/phase3_checklist.md`. Specialist task files cite `P3Mxx` IDs and evidence, **never count completion again**. `P3OPxx` are operational overlays mapped to modules. Supervisor approval separately recorded. Existing source copies are inventoried in `references/phase2/source_manifest.json`. The transfer issue is closed; preserve original source bytes. Subsequent version changes require supervisor review.

Parallel foundation docs/UI sketch/DB design/API contract planning allowed; live NB23 adapter, true Citation/streaming, Module 00 acceptance, migrations, provider/deploy blocked. Any missing security/operations human owner remains assignment-pending with foundation accountable for coordination.

## Mission onboarding and handoff (three specialist areas)

- **API agent:** inspect AGENTS/architecture/contract README, select canonical P3M03/P3M09–13/P3M17 as relevant, and open its own API task record. Draft API envelopes and negative/compatibility cases without assuming NB23 history, filters, streaming or accepted runtime; report concrete evidence and blockers to foundation. Do not edit canonical checklist.
- **Database agent:** inspect P3M04–06/P3M15/P3M22 and P3OP02/03/07, maintain its own database task record, propose user isolation, consent/data classification, deletion/retention and schema boundaries. No production migration, unapproved auth or retention decision. Report evidence locators to foundation.
- **UI agent:** inspect P3M11/P3M14–15 and P3OP05; maintain its own UI task record. Draft responsive RTL consent/login/chat/history/feedback/error flows, with provisional Citation and stream-safe state boundaries. No claims of live model or verified source resolver. Report evidence locators to foundation.

Each specialist's record must include canonical IDs, starting SHA, implementation status, checks actually run, pending approvals and next actions. Foundation alone adjudicates checklist evidence; supervisor alone accepts Gates. New specialist agent creation is **not** part of this mission.
