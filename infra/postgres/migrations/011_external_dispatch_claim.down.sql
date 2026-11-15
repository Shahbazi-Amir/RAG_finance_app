-- 011_external_dispatch_claim.down.sql
-- Refuse to destroy ANY committed dispatch evidence, including manually reconciled.
BEGIN;
DO $$
BEGIN
  -- Same order as Claim: execution_attempts first, then dispatch_claims.
  LOCK TABLE history_l1.execution_attempts IN ACCESS EXCLUSIVE MODE;
  LOCK TABLE history_l1.external_dispatch_claims IN ACCESS EXCLUSIVE MODE;
  IF EXISTS(SELECT 1 FROM history_l1.external_dispatch_claims) THEN
    RAISE EXCEPTION 'DISPATCH_011_DOWN_REFUSED_EVIDENCE_EXISTS'
      USING ERRCODE='P0001';
  END IF;
END $$;
DROP FUNCTION history_l1.claim_external_dispatch(text,text,text);
DROP FUNCTION history_l1.status_external_dispatch(text,text,text);
DROP FUNCTION history_l1.flag_external_dispatch_unknown(text,text,text,uuid,text);
DROP FUNCTION history_l1.reconcile_external_dispatch(text,text,text,text,text);
DROP TABLE history_l1.external_dispatch_claims;
REVOKE USAGE ON SCHEMA history_l1 FROM history_dispatch_reporter,history_dispatch_reconciler;
COMMIT;
