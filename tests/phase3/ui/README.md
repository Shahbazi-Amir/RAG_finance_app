# UI L1 targeted tests

Run from repository root (no backend/model):

    node --experimental-strip-types --test tests/phase3/ui/*.test.mjs

The Node runtime reads the unchanged shared fixture set through apps/web/src/mock/transport.ts. This tests Mock only; browser E2E and real RAG require separate evidence.
