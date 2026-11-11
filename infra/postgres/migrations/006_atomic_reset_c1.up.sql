-- 006_atomic_reset_c1.up.sql — CR-DB-01A; product PostgreSQL ONLY.
-- Apply AFTER unchanged 001..005. CI issuer/executor roles are pre-provisioned.
-- No IdP, email, password, recovery URL, raw token, cookie or public API here.
-- No production credential assurance or authorization-lifetime policy is approved.
CREATE TABLE auth_l1.reset_c1_authorizations (
 authorization_sha256 text PRIMARY KEY CHECK (authorization_sha256 ~ '^[0-9a-f]{64}$'),
 owner_id text NOT NULL REFERENCES auth_l1.owners(owner_id) ON DELETE RESTRICT,
 kind text NOT NULL CHECK (kind IN ('RECOVERY','AUTHENTICATED_PASSWORD_CHANGE')),
 purpose text NOT NULL CHECK (purpose='CONTROLLED_RESET_C1'),
 expected_epoch bigint NOT NULL CHECK (expected_epoch >= 0),
 session_digest_sha256 text,
 session_generation integer,
 issued_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 expires_at timestamptz NOT NULL,
 consumed_at timestamptz,
 consumed_operation_id uuid,
 CHECK ((consumed_at IS NULL) = (consumed_operation_id IS NULL)),
 CHECK (
   (kind='RECOVERY' AND session_digest_sha256 IS NULL AND session_generation IS NULL)
   OR (kind='AUTHENTICATED_PASSWORD_CHANGE'
       AND session_digest_sha256 ~ '^[0-9a-f]{64}$'
       AND session_generation >= 0)
 )
);
CREATE INDEX reset_c1_auth_owner_idx ON auth_l1.reset_c1_authorizations(owner_id,expires_at);
CREATE TABLE auth_l1.reset_c1_operations (
 operation_id uuid PRIMARY KEY,
 owner_id text NOT NULL REFERENCES auth_l1.owners(owner_id) ON DELETE RESTRICT,
 authorization_sha256 text NOT NULL UNIQUE REFERENCES auth_l1.reset_c1_authorizations(authorization_sha256) ON DELETE RESTRICT,
 kind text NOT NULL CHECK(kind IN ('RECOVERY','AUTHENTICATED_PASSWORD_CHANGE')),
 purpose text NOT NULL CHECK(purpose='CONTROLLED_RESET_C1'),
 expected_epoch bigint NOT NULL CHECK(expected_epoch >= 0),
 revoked_epoch bigint NOT NULL CHECK(revoked_epoch=expected_epoch+1),
 status text NOT NULL CHECK(status='REVOKED_PENDING_IDP'),
 active boolean NOT NULL DEFAULT true CHECK(active),
 created_at timestamptz NOT NULL DEFAULT clock_timestamp()
);
-- C1-only: no deactivation or C2 transition. Even an unknown remote outcome
-- keeps the operation active, so a second C1 cannot bump the same owner.
CREATE UNIQUE INDEX reset_c1_one_active_per_owner
 ON auth_l1.reset_c1_operations(owner_id) WHERE active;
ALTER TABLE auth_l1.reset_c1_authorizations ENABLE ROW LEVEL SECURITY;
ALTER TABLE auth_l1.reset_c1_authorizations FORCE ROW LEVEL SECURITY;
CREATE POLICY deny_reset_auth_direct ON auth_l1.reset_c1_authorizations
 FOR ALL TO PUBLIC USING(false) WITH CHECK(false);
ALTER TABLE auth_l1.reset_c1_operations ENABLE ROW LEVEL SECURITY;
ALTER TABLE auth_l1.reset_c1_operations FORCE ROW LEVEL SECURITY;
CREATE POLICY deny_reset_op_direct ON auth_l1.reset_c1_operations
 FOR ALL TO PUBLIC USING(false) WITH CHECK(false);
REVOKE ALL ON TABLE auth_l1.reset_c1_authorizations,auth_l1.reset_c1_operations
 FROM PUBLIC,auth_reset_issuer,auth_reset_executor;

-- A distinct CI-only trusted principal issues server-verified authorizations.
-- The issuer must independently verify recovery/step-up in the future; DB cannot.
-- SHA-256 digest is computed in trusted caller memory; raw proof never reaches SQL.
CREATE FUNCTION auth_l1.issue_reset_c1_authorization(
 p_digest text,p_owner text,p_kind text,p_purpose text,p_epoch bigint,
 p_expires_epoch bigint,p_session_digest text DEFAULT NULL,
 p_session_generation integer DEFAULT NULL
) RETURNS boolean LANGUAGE plpgsql VOLATILE SECURITY DEFINER
SET search_path=pg_catalog AS $$
DECLARE o record; expiry timestamptz; now_db timestamptz;
BEGIN
 IF p_digest IS NULL OR p_digest !~ '^[0-9a-f]{64}$'
   OR p_owner IS NULL OR length(btrim(p_owner))=0
   OR p_kind IS NULL OR p_kind NOT IN ('RECOVERY','AUTHENTICATED_PASSWORD_CHANGE')
   OR p_purpose IS DISTINCT FROM 'CONTROLLED_RESET_C1'
   OR p_epoch IS NULL OR p_epoch<0 OR p_epoch=9223372036854775807
   OR p_expires_epoch IS NULL OR p_expires_epoch<=0 OR p_expires_epoch>253402300799
   OR (p_kind='RECOVERY' AND (p_session_digest IS NOT NULL OR p_session_generation IS NOT NULL))
   OR (p_kind='AUTHENTICATED_PASSWORD_CHANGE'
       AND (p_session_digest IS NULL OR p_session_digest !~ '^[0-9a-f]{64}$'
            OR p_session_generation IS NULL OR p_session_generation<0))
 THEN RAISE EXCEPTION 'RESET_C1_INVALID_ISSUANCE' USING ERRCODE='P0001'; END IF;
 SELECT * INTO o FROM auth_l1.owners WHERE owner_id=p_owner FOR SHARE;
 IF NOT FOUND OR o.state<>'active' OR o.reset_gate<>'open'
    OR o.session_epoch IS DISTINCT FROM p_epoch
    OR EXISTS (SELECT 1 FROM auth_l1.reset_c1_operations WHERE owner_id=p_owner AND active)
 THEN RAISE EXCEPTION 'RESET_C1_ISSUANCE_DENIED' USING ERRCODE='P0001'; END IF;
 now_db:=clock_timestamp();
 expiry:=to_timestamp(p_expires_epoch);
 IF now_db>=expiry THEN RAISE EXCEPTION 'RESET_C1_ISSUANCE_EXPIRED' USING ERRCODE='P0001'; END IF;
 INSERT INTO auth_l1.reset_c1_authorizations
  (authorization_sha256,owner_id,kind,purpose,expected_epoch,
   session_digest_sha256,session_generation,expires_at)
 VALUES(p_digest,p_owner,p_kind,p_purpose,p_epoch,p_session_digest,p_session_generation,expiry);
 RETURN true;
END $$;

-- Owner FOR UPDATE first; authorization FOR UPDATE second; then exact session
-- admission (Owner/Session shared locks, if authenticated); then revoke_all.
-- Existing rotate/revoke/admission use Owner before Session. No inversion.
CREATE FUNCTION auth_l1.execute_reset_c1(
 p_digest text,p_owner text,p_kind text,p_purpose text,
 p_epoch bigint,p_operation_id uuid
) RETURNS jsonb LANGUAGE plpgsql VOLATILE SECURITY DEFINER
SET search_path=pg_catalog AS $$
DECLARE o record; a record; now_db timestamptz; new_epoch bigint;
BEGIN
 IF p_digest IS NULL OR p_digest !~ '^[0-9a-f]{64}$'
   OR p_owner IS NULL OR length(btrim(p_owner))=0
   OR p_kind IS NULL OR p_kind NOT IN ('RECOVERY','AUTHENTICATED_PASSWORD_CHANGE')
   OR p_purpose IS DISTINCT FROM 'CONTROLLED_RESET_C1'
   OR p_epoch IS NULL OR p_epoch<0 OR p_epoch=9223372036854775807
   OR p_operation_id IS NULL
 THEN RAISE EXCEPTION 'RESET_C1_INVALID_INPUT' USING ERRCODE='P0001'; END IF;

 SELECT * INTO o FROM auth_l1.owners WHERE owner_id=p_owner FOR UPDATE;
 IF NOT FOUND OR o.state<>'active' OR o.reset_gate<>'open'
    OR o.session_epoch IS DISTINCT FROM p_epoch
 THEN RAISE EXCEPTION 'RESET_C1_OWNER_CAS_DENIED' USING ERRCODE='P0001'; END IF;
 IF EXISTS(SELECT 1 FROM auth_l1.reset_c1_operations WHERE owner_id=p_owner AND active)
 THEN RAISE EXCEPTION 'RESET_C1_ACTIVE_OPERATION' USING ERRCODE='P0001'; END IF;

 SELECT * INTO a FROM auth_l1.reset_c1_authorizations
 WHERE authorization_sha256=p_digest FOR UPDATE;
 IF NOT FOUND OR a.owner_id IS DISTINCT FROM p_owner
   OR a.kind IS DISTINCT FROM p_kind OR a.purpose IS DISTINCT FROM p_purpose
   OR a.expected_epoch IS DISTINCT FROM p_epoch
   OR a.consumed_operation_id IS NOT NULL
 THEN RAISE EXCEPTION 'RESET_C1_AUTHORIZATION_DENIED' USING ERRCODE='P0001'; END IF;
 -- Time-of-use decision strictly AFTER owner and authorization locks.
 now_db:=clock_timestamp();
 IF now_db>=a.expires_at
 THEN RAISE EXCEPTION 'RESET_C1_AUTHORIZATION_EXPIRED' USING ERRCODE='P0001'; END IF;

 IF a.kind='AUTHENTICATED_PASSWORD_CHANGE' THEN
   -- 004 locks exact Session until the same outer commit; no IdP/step-up proof.
   IF auth_l1.admit_session_fenced(p_owner,a.session_digest_sha256,p_epoch,a.session_generation)
      IS DISTINCT FROM true
   THEN RAISE EXCEPTION 'RESET_C1_SESSION_DENIED' USING ERRCODE='P0001'; END IF;
 END IF;

 -- All mutations are one PG transaction. A raised error aborts outer TX.
 INSERT INTO auth_l1.reset_c1_operations
 (operation_id,owner_id,authorization_sha256,kind,purpose,expected_epoch,revoked_epoch,status)
 VALUES(p_operation_id,p_owner,p_digest,p_kind,p_purpose,p_epoch,p_epoch+1,'REVOKED_PENDING_IDP');
 UPDATE auth_l1.reset_c1_authorizations SET consumed_at=clock_timestamp(),
   consumed_operation_id=p_operation_id WHERE authorization_sha256=p_digest;
 -- Reuse accepted 003 revocation semantics; owner lock already held.
 SELECT auth_l1.revoke_all(p_owner,p_epoch) INTO new_epoch;
 IF new_epoch IS DISTINCT FROM p_epoch+1
 THEN RAISE EXCEPTION 'RESET_C1_REVOKE_MISMATCH' USING ERRCODE='P0001'; END IF;
 RETURN jsonb_build_object('operation_id',p_operation_id,
   'owner_id',p_owner,'expected_epoch',p_epoch,'revoked_epoch',new_epoch,
   'status','REVOKED_PENDING_IDP');
END $$;

-- Defend C1's pending gate even against legacy synthetic reauth entry point.
-- C2 must be a separately reviewed migration and evidence-controlled protocol.
CREATE FUNCTION auth_l1.block_c1_gate_open()
RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER
SET search_path=pg_catalog AS $$
BEGIN
 IF OLD.reset_gate='pending_reauth' AND NEW.reset_gate='open'
    AND EXISTS (SELECT 1 FROM auth_l1.reset_c1_operations
                WHERE owner_id=OLD.owner_id AND active)
 THEN RAISE EXCEPTION 'RESET_C1_GATE_STAYS_CLOSED' USING ERRCODE='P0001'; END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER block_c1_gate_open_trg
 BEFORE UPDATE OF reset_gate ON auth_l1.owners
 FOR EACH ROW EXECUTE FUNCTION auth_l1.block_c1_gate_open();

REVOKE ALL ON FUNCTION auth_l1.issue_reset_c1_authorization(
 text,text,text,text,bigint,bigint,text,integer) FROM PUBLIC;
REVOKE ALL ON FUNCTION auth_l1.execute_reset_c1(
 text,text,text,text,bigint,uuid) FROM PUBLIC;
REVOKE ALL ON FUNCTION auth_l1.block_c1_gate_open() FROM PUBLIC;
GRANT USAGE ON SCHEMA auth_l1 TO auth_reset_issuer,auth_reset_executor;
GRANT EXECUTE ON FUNCTION auth_l1.issue_reset_c1_authorization(
 text,text,text,text,bigint,bigint,text,integer) TO auth_reset_issuer;
GRANT EXECUTE ON FUNCTION auth_l1.execute_reset_c1(
 text,text,text,text,bigint,uuid) TO auth_reset_executor;
