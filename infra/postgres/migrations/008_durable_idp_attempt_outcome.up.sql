-- 008_durable_idp_attempt_outcome.up.sql — CR-DB-01C; synthetic Product PG only.
-- Apply AFTER immutable 001..007; auth_reset_idp_recorder provisioned separately.
-- No IdP call, C2, retry, password, raw token/link/response or error body.
CREATE TABLE auth_l1.reset_idp_attempts (
 attempt_id uuid PRIMARY KEY,
 operation_id uuid NOT NULL UNIQUE
   REFERENCES auth_l1.reset_c1_operations(operation_id) ON DELETE RESTRICT,
 owner_id text NOT NULL REFERENCES auth_l1.owners(owner_id) ON DELETE RESTRICT,
 authorization_sha256 text NOT NULL
   REFERENCES auth_l1.reset_c1_authorizations(authorization_sha256) ON DELETE RESTRICT,
 kind text NOT NULL CHECK(kind IN ('RECOVERY','AUTHENTICATED_PASSWORD_CHANGE')),
 purpose text NOT NULL CHECK(purpose='CONTROLLED_RESET_C1'),
 revoked_epoch bigint NOT NULL CHECK(revoked_epoch>0),
 recorded_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 outcome text CHECK(outcome IN ('OBSERVED_REMOTE_SUCCESS','DEFINITIVE_REJECTION','UNKNOWN')),
 outcome_code text CHECK(outcome_code IN
    ('REMOTE_2XX_OBSERVED','POLICY_REJECTED','ACCOUNT_REJECTED',
     'TIMEOUT','DISCONNECT','REMOTE_5XX','UNVERIFIABLE','OTHER_UNKNOWN')),
 finalized_at timestamptz,
 CHECK (
  (outcome IS NULL AND outcome_code IS NULL AND finalized_at IS NULL)
  OR
  (outcome IS NOT NULL AND outcome_code IS NOT NULL AND finalized_at IS NOT NULL)
 ),
 CHECK(
  outcome IS NULL
  OR (outcome='OBSERVED_REMOTE_SUCCESS' AND outcome_code='REMOTE_2XX_OBSERVED')
  OR (outcome='DEFINITIVE_REJECTION' AND outcome_code IN ('POLICY_REJECTED','ACCOUNT_REJECTED'))
  OR (outcome='UNKNOWN' AND outcome_code IN
      ('TIMEOUT','DISCONNECT','REMOTE_5XX','UNVERIFIABLE','OTHER_UNKNOWN'))
 )
);
CREATE INDEX reset_idp_attempt_owner_idx ON auth_l1.reset_idp_attempts(owner_id,revoked_epoch);
ALTER TABLE auth_l1.reset_idp_attempts ENABLE ROW LEVEL SECURITY;
ALTER TABLE auth_l1.reset_idp_attempts FORCE ROW LEVEL SECURITY;
CREATE POLICY deny_idp_attempt_direct ON auth_l1.reset_idp_attempts
 FOR ALL TO PUBLIC USING(false) WITH CHECK(false);
REVOKE ALL ON TABLE auth_l1.reset_idp_attempts FROM PUBLIC,auth_reset_idp_recorder;

-- Separate non-executor role. Caller presents the consumed proof's SHA256,
-- not merely an operation UUID. A speculative MVCC check BEFORE Owner lock
-- refuses any operation that has not committed on an independent C1 connection.
-- Only the privileged CI migration fixture has table access; runtime role does not.
CREATE FUNCTION auth_l1.record_reset_idp_attempt(
 p_digest text,p_owner text,p_kind text,p_purpose text,
 p_revoked_epoch bigint,p_operation_id uuid,p_attempt_id uuid
) RETURNS jsonb LANGUAGE plpgsql VOLATILE SECURITY DEFINER
SET search_path=pg_catalog AS $$
DECLARE o record; op record;
BEGIN
 IF p_digest IS NULL OR p_digest !~ '^[0-9a-f]{64}$'
    OR p_owner IS NULL OR length(btrim(p_owner))=0
    OR p_kind IS NULL OR p_kind NOT IN ('RECOVERY','AUTHENTICATED_PASSWORD_CHANGE')
    OR p_purpose IS DISTINCT FROM 'CONTROLLED_RESET_C1'
    OR p_revoked_epoch IS NULL OR p_revoked_epoch<=0
    OR p_operation_id IS NULL OR p_attempt_id IS NULL
 THEN RAISE EXCEPTION 'RESET_IDP_ATTEMPT_DENIED' USING ERRCODE='P0001'; END IF;

 -- DDL/UP-DOWN lock ordering: Owner TABLE first. ACCESS SHARE only:
 -- compatible with C1's table ROW EXCLUSIVE and Owner tuple FOR UPDATE.
 -- Blocks 008.down's ACCESS EXCLUSIVE until our outer COMMIT/ROLLBACK.
 -- Do NOT acquire an early Owner tuple lock or any 006/008 table lock first.
 LOCK TABLE auth_l1.owners IN ACCESS SHARE MODE;

 -- Committed MVCC precheck BEFORE potentially blocking Owner tuple FOR SHARE.
 -- Uncommitted C1 in another connection is invisible: fail immediately,
 -- never wait for it to commit and then promote a precommit attempt.
 IF NOT EXISTS (
  SELECT 1 FROM auth_l1.reset_c1_operations
  WHERE operation_id=p_operation_id AND owner_id=p_owner
    AND authorization_sha256=p_digest AND kind=p_kind
    AND purpose=p_purpose AND revoked_epoch=p_revoked_epoch
    AND status='REVOKED_PENDING_IDP' AND active
 ) THEN RAISE EXCEPTION 'RESET_IDP_ATTEMPT_DENIED' USING ERRCODE='P0001'; END IF;

 -- Owner FIRST among all acquired tuple locks, then operation/authorization read
 -- (006 C1 immutable after commit) then INSERT UNIQUE per operation.
 SELECT * INTO o FROM auth_l1.owners WHERE owner_id=p_owner FOR SHARE;
 IF NOT FOUND OR o.state<>'active' OR o.reset_gate<>'pending_reauth'
    OR o.session_epoch IS DISTINCT FROM p_revoked_epoch
 THEN RAISE EXCEPTION 'RESET_IDP_ATTEMPT_DENIED' USING ERRCODE='P0001'; END IF;

 SELECT * INTO op FROM auth_l1.reset_c1_operations AS operation_row
 JOIN auth_l1.reset_c1_authorizations AS a
   ON a.authorization_sha256=operation_row.authorization_sha256
 WHERE operation_row.operation_id=p_operation_id
   AND operation_row.owner_id=p_owner
   AND operation_row.authorization_sha256=p_digest
   AND operation_row.kind=p_kind
   AND operation_row.purpose=p_purpose
   AND operation_row.status='REVOKED_PENDING_IDP' AND operation_row.active
   AND operation_row.revoked_epoch=p_revoked_epoch
   AND operation_row.expected_epoch=p_revoked_epoch-1
   AND a.owner_id=p_owner AND a.kind=p_kind
   AND a.purpose=p_purpose AND a.expected_epoch=operation_row.expected_epoch
   AND a.consumed_operation_id=p_operation_id AND a.consumed_at IS NOT NULL;
 IF NOT FOUND THEN RAISE EXCEPTION 'RESET_IDP_ATTEMPT_DENIED' USING ERRCODE='P0001'; END IF;

 INSERT INTO auth_l1.reset_idp_attempts
 (attempt_id,operation_id,owner_id,authorization_sha256,kind,purpose,revoked_epoch)
 VALUES(p_attempt_id,p_operation_id,p_owner,p_digest,p_kind,p_purpose,p_revoked_epoch);
 -- Returning a receipt is NOT evidence that a request was sent to IdP.
 RETURN pg_catalog.jsonb_build_object(
  'attempt_id',p_attempt_id,'operation_id',p_operation_id,
  'status','NO_OUTCOME_RECORDED'
 );
END $$;

-- One immutable final observation, scoped to the same consumed 006 proof +
-- exact operation, attempt, Owner, kind, purpose and post-C1 epoch.
-- A competing or late responder may never overwrite an existing observation.
CREATE FUNCTION auth_l1.record_reset_idp_outcome(
 p_digest text,p_owner text,p_kind text,p_purpose text,
 p_revoked_epoch bigint,p_operation_id uuid,p_attempt_id uuid,
 p_outcome text,p_code text
) RETURNS jsonb LANGUAGE plpgsql VOLATILE SECURITY DEFINER
SET search_path=pg_catalog AS $$
DECLARE o record; updated_id uuid;
BEGIN
 IF p_digest IS NULL OR p_digest !~ '^[0-9a-f]{64}$'
    OR p_owner IS NULL OR length(btrim(p_owner))=0
    OR p_kind IS NULL OR p_kind NOT IN ('RECOVERY','AUTHENTICATED_PASSWORD_CHANGE')
    OR p_purpose IS DISTINCT FROM 'CONTROLLED_RESET_C1'
    OR p_revoked_epoch IS NULL OR p_revoked_epoch<=0
    OR p_operation_id IS NULL OR p_attempt_id IS NULL
    OR p_outcome IS NULL OR p_code IS NULL
    OR NOT (
      (p_outcome='OBSERVED_REMOTE_SUCCESS' AND p_code='REMOTE_2XX_OBSERVED')
      OR (p_outcome='DEFINITIVE_REJECTION' AND p_code IN ('POLICY_REJECTED','ACCOUNT_REJECTED'))
      OR (p_outcome='UNKNOWN' AND p_code IN
           ('TIMEOUT','DISCONNECT','REMOTE_5XX','UNVERIFIABLE','OTHER_UNKNOWN'))
    )
 THEN RAISE EXCEPTION 'RESET_IDP_OUTCOME_DENIED' USING ERRCODE='P0001'; END IF;

 -- DDL/UP-DOWN lock ordering: Owner TABLE first, ACCESS SHARE only.
 -- No Owner tuple lock yet. This is compatible with uncommitted C1 and
 -- serializes against 008.down's Owner ACCESS EXCLUSIVE-first DDL.
 LOCK TABLE auth_l1.owners IN ACCESS SHARE MODE;

 -- Preserve committed MVCC precheck BEFORE any Owner tuple FOR SHARE.
 -- Noncommitted attempts are invisible; fail without waiting for commit.
 IF NOT EXISTS (
  SELECT 1 FROM auth_l1.reset_idp_attempts
  WHERE attempt_id=p_attempt_id AND operation_id=p_operation_id
    AND owner_id=p_owner AND authorization_sha256=p_digest
    AND kind=p_kind AND purpose=p_purpose AND revoked_epoch=p_revoked_epoch
 ) THEN RAISE EXCEPTION 'RESET_IDP_OUTCOME_DENIED' USING ERRCODE='P0001'; END IF;

 SELECT * INTO o FROM auth_l1.owners WHERE owner_id=p_owner FOR SHARE;
 IF NOT FOUND OR o.reset_gate<>'pending_reauth'
    OR o.session_epoch IS DISTINCT FROM p_revoked_epoch
 THEN RAISE EXCEPTION 'RESET_IDP_OUTCOME_DENIED' USING ERRCODE='P0001'; END IF;

 UPDATE auth_l1.reset_idp_attempts AS a
 SET outcome=p_outcome,outcome_code=p_code,finalized_at=clock_timestamp()
 WHERE a.attempt_id=p_attempt_id
   AND a.operation_id=p_operation_id AND a.owner_id=p_owner
   AND a.authorization_sha256=p_digest AND a.kind=p_kind
   AND a.purpose=p_purpose AND a.revoked_epoch=p_revoked_epoch
   AND a.outcome IS NULL AND a.outcome_code IS NULL AND a.finalized_at IS NULL
   AND EXISTS (
     SELECT 1 FROM auth_l1.reset_c1_operations AS op
     JOIN auth_l1.reset_c1_authorizations AS authority
       ON authority.authorization_sha256=op.authorization_sha256
     WHERE op.operation_id=p_operation_id AND op.owner_id=p_owner
       AND op.authorization_sha256=p_digest AND op.kind=p_kind
       AND op.purpose=p_purpose AND op.revoked_epoch=p_revoked_epoch
       AND op.status='REVOKED_PENDING_IDP' AND op.active
       AND authority.consumed_operation_id=op.operation_id
       AND authority.consumed_at IS NOT NULL
   )
 RETURNING a.attempt_id INTO updated_id;
 IF updated_id IS NULL THEN
  RAISE EXCEPTION 'RESET_IDP_OUTCOME_ALREADY_FINAL_OR_INVALID'
      USING ERRCODE='P0001';
 END IF;
 -- Observed 2xx is only a local recorded observation, not password assurance.
 RETURN pg_catalog.jsonb_build_object(
  'attempt_id',updated_id,'outcome',p_outcome,'code',p_code
 );
END $$;

REVOKE ALL ON FUNCTION auth_l1.record_reset_idp_attempt(
 text,text,text,text,bigint,uuid,uuid) FROM PUBLIC;
REVOKE ALL ON FUNCTION auth_l1.record_reset_idp_outcome(
 text,text,text,text,bigint,uuid,uuid,text,text) FROM PUBLIC;
GRANT USAGE ON SCHEMA auth_l1 TO auth_reset_idp_recorder;
GRANT EXECUTE ON FUNCTION auth_l1.record_reset_idp_attempt(
 text,text,text,text,bigint,uuid,uuid) TO auth_reset_idp_recorder;
GRANT EXECUTE ON FUNCTION auth_l1.record_reset_idp_outcome(
 text,text,text,text,bigint,uuid,uuid,text,text) TO auth_reset_idp_recorder;
