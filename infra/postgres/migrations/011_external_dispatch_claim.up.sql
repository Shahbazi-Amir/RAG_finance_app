-- 011_external_dispatch_claim.up.sql
-- DB-owned one-shot external dispatch reservation; additive to 001/002.
-- Migration number follows unmerged 009/010; this SQL requires only 001+002.
-- DO NOT send a Gateway request in a transaction or treat CLAIMED as sent.
-- history_dispatch_reporter/reconciler are provisioned by approved role owner;
-- this migration NEVER creates staging/Production roles.
BEGIN;

CREATE TABLE history_l1.external_dispatch_claims (
 owner_id text NOT NULL,
 attempt_id text NOT NULL,
 attempt_trace_id text NOT NULL,
 claim_id uuid NOT NULL DEFAULT gen_random_uuid(),
 state text NOT NULL DEFAULT 'CLAIMED'
   CHECK (state IN ('CLAIMED','UNKNOWN','RECONCILED_DELIVERED','RECONCILED_NOT_DELIVERED')),
 claimed_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 unknown_at timestamptz,
 unknown_reason text CHECK (unknown_reason IS NULL OR
   unknown_reason IN ('TIMEOUT','LOST_RESPONSE','CRASH','COMMIT_UNCERTAIN')),
 reconciled_at timestamptz,
 reconciliation_evidence_sha256 text CHECK (
   reconciliation_evidence_sha256 IS NULL OR
   reconciliation_evidence_sha256 ~ '^[0-9a-f]{64}$'),
 PRIMARY KEY (owner_id,attempt_id),
 UNIQUE(claim_id),
 FOREIGN KEY(owner_id,attempt_id)
   REFERENCES history_l1.execution_attempts(owner_id,id) ON DELETE RESTRICT,
 CHECK (
   (state = 'CLAIMED' AND unknown_at IS NULL AND unknown_reason IS NULL
      AND reconciled_at IS NULL AND reconciliation_evidence_sha256 IS NULL)
   OR (state = 'UNKNOWN' AND unknown_at IS NOT NULL
      AND unknown_reason IS NOT NULL AND reconciled_at IS NULL
      AND reconciliation_evidence_sha256 IS NULL)
   OR (state IN ('RECONCILED_DELIVERED','RECONCILED_NOT_DELIVERED')
      AND reconciled_at IS NOT NULL AND reconciliation_evidence_sha256 IS NOT NULL)
 )
);

CREATE INDEX external_dispatch_claims_state_idx
 ON history_l1.external_dispatch_claims (state,claimed_at,owner_id,attempt_id);
ALTER TABLE history_l1.external_dispatch_claims ENABLE ROW LEVEL SECURITY;
ALTER TABLE history_l1.external_dispatch_claims FORCE ROW LEVEL SECURITY;
CREATE POLICY deny_direct_dispatch ON history_l1.external_dispatch_claims
 FOR ALL TO PUBLIC USING(false) WITH CHECK(false);
REVOKE ALL ON TABLE history_l1.external_dispatch_claims
 FROM PUBLIC,history_app,history_dispatch_reporter,history_dispatch_reconciler;

-- Only the authenticated API's existing history_app session-fenced outer
-- transaction may call Claim. current_setting('app.owner_id') is NOT standalone
-- proof of identity: the caller MUST first verify 005+004 with signed BFF proof.
CREATE FUNCTION history_l1.claim_external_dispatch(
 p_owner text, p_attempt_id text, p_attempt_trace_id text
) RETURNS TABLE(claim_won boolean, claim_id uuid, claimed_at timestamptz)
LANGUAGE plpgsql VOLATILE SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE a record; inserted record;
BEGIN
 IF p_owner IS NULL OR length(p_owner) NOT BETWEEN 1 AND 256
   OR p_attempt_id IS NULL OR p_attempt_id !~ '^[0-9a-f]{32}$'
   OR p_attempt_trace_id IS NULL OR length(p_attempt_trace_id) NOT BETWEEN 1 AND 256
   OR nullif(current_setting('app.owner_id',true),'') IS DISTINCT FROM p_owner THEN
  RETURN QUERY SELECT false,NULL::uuid,NULL::timestamptz;
  RETURN;
 END IF;
 -- Lock order: execution_attempts row first, then dispatch_claims unique insert.
 -- Concurrent 002 T2, T3 finalize or mark_attempt cannot bypass this check.
 SELECT x.owner_id,x.id,x.attempt_trace_id,x.state INTO a
 FROM history_l1.execution_attempts x
 WHERE x.owner_id=p_owner AND x.id=p_attempt_id
   AND x.attempt_trace_id=p_attempt_trace_id
 FOR SHARE;
 IF NOT FOUND OR a.state IS DISTINCT FROM 'attempt_pending' THEN
  RETURN QUERY SELECT false,NULL::uuid,NULL::timestamptz;
  RETURN;
 END IF;
 -- UNIQUE PK is permanent. DO NOTHING is a hard one-time authorization guard.
 -- If the first TX ROLLBACKS, it never authorized an external send; only a
 -- definitively COMMITTED winner can use the returned claim_id.
 INSERT INTO history_l1.external_dispatch_claims AS d
   (owner_id,attempt_id,attempt_trace_id)
 VALUES (p_owner,p_attempt_id,p_attempt_trace_id)
 ON CONFLICT (owner_id,attempt_id) DO NOTHING
 RETURNING d.claim_id,d.claimed_at INTO inserted;
 IF NOT FOUND THEN
  RETURN QUERY SELECT false,NULL::uuid,NULL::timestamptz;
 ELSE
  RETURN QUERY SELECT true,inserted.claim_id,inserted.claimed_at;
 END IF;
END $$;

-- This operation is READ-ONLY. Stale CLAIMED is surfaced as UNKNOWN
-- without changing or reopening the immutable dispatch reservation.
CREATE FUNCTION history_l1.status_external_dispatch(
 p_owner text,p_attempt_id text,p_attempt_trace_id text
) RETURNS TABLE(dispatch_state text,claimed_at timestamptz,
  unknown_at timestamptz,reconciled_at timestamptz)
LANGUAGE plpgsql VOLATILE SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE a record; d record;
BEGIN
 IF p_owner IS NULL OR nullif(current_setting('app.owner_id',true),'') IS DISTINCT FROM p_owner
   OR p_attempt_id IS NULL OR p_attempt_trace_id IS NULL THEN
   RETURN;
 END IF;
 SELECT id INTO a FROM history_l1.execution_attempts
 WHERE owner_id=p_owner AND id=p_attempt_id
   AND attempt_trace_id=p_attempt_trace_id;
 IF NOT FOUND THEN RETURN; END IF;
 SELECT state,claimed_at,unknown_at,reconciled_at INTO d
 FROM history_l1.external_dispatch_claims
 WHERE owner_id=p_owner AND attempt_id=p_attempt_id
   AND attempt_trace_id=p_attempt_trace_id;
 IF NOT FOUND THEN
  RETURN QUERY SELECT 'NOT_CLAIMED'::text,NULL::timestamptz,
                      NULL::timestamptz,NULL::timestamptz;
 ELSE
  RETURN QUERY SELECT
    (CASE WHEN d.state='CLAIMED'
              AND clock_timestamp() >= d.claimed_at+interval '180 seconds'
          THEN 'UNKNOWN' ELSE d.state END)::text,
    d.claimed_at,d.unknown_at,d.reconciled_at;
 END IF;
END $$;

-- Runtime reporter knows the private claim_id from a committed Claim. It can
-- only terminalize ambiguity, NEVER requeue/claim, change Owner, or insert Answer.
CREATE FUNCTION history_l1.flag_external_dispatch_unknown(
 p_owner text,p_attempt_id text,p_attempt_trace_id text,
 p_claim_id uuid,p_reason text
) RETURNS boolean
LANGUAGE plpgsql VOLATILE SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE d record;
BEGIN
 IF p_owner IS NULL OR p_attempt_id IS NULL OR p_attempt_trace_id IS NULL
    OR p_claim_id IS NULL OR p_reason NOT IN
     ('TIMEOUT','LOST_RESPONSE','CRASH','COMMIT_UNCERTAIN') THEN
  RETURN false;
 END IF;
 SELECT * INTO d FROM history_l1.external_dispatch_claims
  WHERE owner_id=p_owner AND attempt_id=p_attempt_id
    AND attempt_trace_id=p_attempt_trace_id AND claim_id=p_claim_id
  FOR UPDATE;
 IF NOT FOUND THEN RETURN false; END IF;
 IF d.state='UNKNOWN' THEN RETURN d.unknown_reason=p_reason; END IF;
 IF d.state<>'CLAIMED' THEN RETURN false; END IF;
 UPDATE history_l1.external_dispatch_claims
  SET state='UNKNOWN',unknown_at=clock_timestamp(),unknown_reason=p_reason
  WHERE owner_id=p_owner AND attempt_id=p_attempt_id;
 RETURN true;
END $$;

-- Reconciler uses immutable Owner+Attempt+Trace after a Worker loses claim_id.
-- Human-controlled reconciliation is an OBSERVATION only, NOT authority to
-- re-dispatch or finalize a Product Answer. Evidence digest may be verified
-- separately by Foundation/Ops; a self-reported digest proves nothing alone.
CREATE FUNCTION history_l1.reconcile_external_dispatch(
 p_owner text,p_attempt_id text,p_attempt_trace_id text,
 p_outcome text,p_evidence_sha256 text
) RETURNS boolean
LANGUAGE plpgsql VOLATILE SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE d record;
BEGIN
 IF p_owner IS NULL OR p_attempt_id IS NULL OR p_attempt_trace_id IS NULL
   OR p_outcome NOT IN
      ('RECONCILED_DELIVERED','RECONCILED_NOT_DELIVERED')
   OR p_evidence_sha256 IS NULL OR p_evidence_sha256 !~ '^[0-9a-f]{64}$' THEN
  RETURN false;
 END IF;
 SELECT * INTO d FROM history_l1.external_dispatch_claims
  WHERE owner_id=p_owner AND attempt_id=p_attempt_id
    AND attempt_trace_id=p_attempt_trace_id
  FOR UPDATE;
 IF NOT FOUND THEN RETURN false; END IF;
 IF d.state IN ('RECONCILED_DELIVERED','RECONCILED_NOT_DELIVERED') THEN
  RETURN d.state=p_outcome AND
         d.reconciliation_evidence_sha256=p_evidence_sha256;
 END IF;
 IF d.state NOT IN ('CLAIMED','UNKNOWN') THEN RETURN false; END IF;
 UPDATE history_l1.external_dispatch_claims
  SET state=p_outcome,reconciled_at=clock_timestamp(),
      reconciliation_evidence_sha256=p_evidence_sha256
  WHERE owner_id=p_owner AND attempt_id=p_attempt_id;
 RETURN true;
END $$;

REVOKE ALL ON FUNCTION history_l1.claim_external_dispatch(text,text,text) FROM PUBLIC;
REVOKE ALL ON FUNCTION history_l1.status_external_dispatch(text,text,text) FROM PUBLIC;
REVOKE ALL ON FUNCTION history_l1.flag_external_dispatch_unknown(text,text,text,uuid,text) FROM PUBLIC;
REVOKE ALL ON FUNCTION history_l1.reconcile_external_dispatch(text,text,text,text,text) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION history_l1.claim_external_dispatch(text,text,text) TO history_app;
GRANT EXECUTE ON FUNCTION history_l1.status_external_dispatch(text,text,text) TO history_app;
GRANT USAGE ON SCHEMA history_l1 TO history_dispatch_reporter,history_dispatch_reconciler;
GRANT EXECUTE ON FUNCTION history_l1.flag_external_dispatch_unknown(text,text,text,uuid,text)
 TO history_dispatch_reporter;
GRANT EXECUTE ON FUNCTION history_l1.reconcile_external_dispatch(text,text,text,text,text)
 TO history_dispatch_reconciler;
COMMIT;
