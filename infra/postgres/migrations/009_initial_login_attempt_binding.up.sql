-- 009_initial_login_attempt_binding.up.sql
-- DB-only Option B. Apply after immutable 001..008. No outbound HTTP in a SQL TX.
-- The 5 auth_login_* roles MUST be separately provisioned; never PUBLIC or History.
-- Callers verify mTLS/bootstrap signature and IdP Code+PKCE/JWKS BEFORE SQL issue.
-- PostgreSQL does NOT prove remote IdP exchange, alias persistence or Cookie delivery.
BEGIN;

ALTER TABLE auth_l1.sessions DROP CONSTRAINT sessions_status_check;
ALTER TABLE auth_l1.sessions ADD CONSTRAINT sessions_status_check
  CHECK (status IN ('active','rotated','revoked','PENDING_BINDING'));

CREATE TABLE auth_l1.initial_login_attempts (
 attempt_id uuid PRIMARY KEY,
 bff_principal text NOT NULL CHECK (length(bff_principal) BETWEEN 1 AND 128),
 bff_attempt_id uuid NOT NULL,
 start_key text NOT NULL CHECK (length(start_key) BETWEEN 1 AND 128),
 request_sha256 text NOT NULL CHECK (request_sha256 ~ '^[0-9a-f]{64}$'),
 state_sha256 text NOT NULL UNIQUE CHECK (state_sha256 ~ '^[0-9a-f]{64}$'),
 initiator_sha256 text NOT NULL CHECK (initiator_sha256 ~ '^[0-9a-f]{64}$'),
 expected_issuer text NOT NULL CHECK (length(expected_issuer) BETWEEN 1 AND 1024),
 pkce_envelope bytea NOT NULL CHECK (octet_length(pkce_envelope) BETWEEN 32 AND 4096),
 nonce_envelope bytea NOT NULL CHECK (octet_length(nonce_envelope) BETWEEN 32 AND 4096),
 state text NOT NULL DEFAULT 'INITIATED'
  CHECK (state IN ('INITIATED','EXCHANGE_STARTED','UNKNOWN_RECONCILIATION_REQUIRED',
    'ISSUED_PENDING_BINDING','ACTIVE','ABORTED','EXPIRED')),
 state_version bigint NOT NULL DEFAULT 0 CHECK (state_version>=0),
 created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 expires_at timestamptz NOT NULL CHECK(expires_at>created_at),
 exchange_started_at timestamptz,
 issued_at timestamptz,
 acked_at timestamptz,
 finalized_at timestamptz,
 owner_id text REFERENCES auth_l1.owners(owner_id) ON DELETE RESTRICT,
 issued_epoch bigint CHECK(issued_epoch>=0),
 session_digest text UNIQUE REFERENCES auth_l1.sessions(digest_sha256) ON DELETE RESTRICT,
 receipt_id uuid UNIQUE,
 alias_sha256 text CHECK(alias_sha256 ~ '^[0-9a-f]{64}$'),
 UNIQUE(bff_principal,bff_attempt_id),
 UNIQUE(bff_principal,start_key),
 CHECK (
   (state IN ('INITIATED','EXCHANGE_STARTED','UNKNOWN_RECONCILIATION_REQUIRED')
     AND session_digest IS NULL AND receipt_id IS NULL)
   OR (state IN ('ISSUED_PENDING_BINDING','ACTIVE','ABORTED','EXPIRED'))
 ),
 CHECK ((session_digest IS NULL AND owner_id IS NULL AND issued_epoch IS NULL AND receipt_id IS NULL)
     OR (session_digest IS NOT NULL AND owner_id IS NOT NULL
         AND issued_epoch IS NOT NULL AND receipt_id IS NOT NULL)),
 CHECK (state<>'ACTIVE' OR (alias_sha256 IS NOT NULL AND acked_at IS NOT NULL)),
 CHECK (alias_sha256 IS NULL OR state IN ('ACTIVE','ABORTED'))
);
CREATE INDEX initial_login_expiry_idx
 ON auth_l1.initial_login_attempts(expires_at,attempt_id)
 WHERE state IN ('INITIATED','EXCHANGE_STARTED','ISSUED_PENDING_BINDING');
CREATE INDEX initial_login_owner_idx ON auth_l1.initial_login_attempts(owner_id,issued_epoch)
 WHERE owner_id IS NOT NULL;
ALTER TABLE auth_l1.initial_login_attempts ENABLE ROW LEVEL SECURITY;
ALTER TABLE auth_l1.initial_login_attempts FORCE ROW LEVEL SECURITY;
CREATE POLICY deny_initial_login_direct ON auth_l1.initial_login_attempts
 FOR ALL TO PUBLIC USING(false) WITH CHECK(false);
REVOKE ALL ON TABLE auth_l1.initial_login_attempts FROM PUBLIC,
 auth_login_bootstrap,auth_login_issuer,auth_login_binder,auth_login_reader,auth_login_cleaner;

-- Public trust does NOT originate in this SQL function: the dedicated API must
-- verify bootstrap service principal, request-bound signature and IdP allowlist.
CREATE FUNCTION auth_l1.start_initial_login_attempt(
 p_attempt uuid,p_principal text,p_bff_attempt uuid,p_start_key text,
 p_request_sha256 text,p_state_sha256 text,p_initiator_sha256 text,
 p_expected_issuer text,p_pkce_envelope bytea,p_nonce_envelope bytea,
 p_ttl_seconds integer
) RETURNS boolean LANGUAGE plpgsql VOLATILE SECURITY DEFINER
SET search_path=pg_catalog AS $$
BEGIN
 IF p_attempt IS NULL OR p_bff_attempt IS NULL OR p_principal IS NULL
    OR length(p_principal) NOT BETWEEN 1 AND 128
    OR p_start_key IS NULL OR length(p_start_key) NOT BETWEEN 1 AND 128
    OR p_request_sha256 IS NULL OR p_request_sha256 !~ '^[0-9a-f]{64}$'
    OR p_state_sha256 IS NULL OR p_state_sha256 !~ '^[0-9a-f]{64}$'
    OR p_initiator_sha256 IS NULL OR p_initiator_sha256 !~ '^[0-9a-f]{64}$'
    OR p_expected_issuer IS NULL OR length(p_expected_issuer) NOT BETWEEN 1 AND 1024
    OR p_pkce_envelope IS NULL OR octet_length(p_pkce_envelope) NOT BETWEEN 32 AND 4096
    OR p_nonce_envelope IS NULL OR octet_length(p_nonce_envelope) NOT BETWEEN 32 AND 4096
    OR p_ttl_seconds IS NULL OR p_ttl_seconds NOT BETWEEN 1 AND 900 THEN
  RAISE EXCEPTION 'LOGIN_START_INVALID' USING ERRCODE='P0001';
 END IF;
 -- Same table ordering as 009 DOWN, no early Owner row lock or IdP I/O.
 LOCK TABLE auth_l1.owners IN ACCESS SHARE MODE;
 INSERT INTO auth_l1.initial_login_attempts(
   attempt_id,bff_principal,bff_attempt_id,start_key,request_sha256,
   state_sha256,initiator_sha256,expected_issuer,pkce_envelope,nonce_envelope,
   created_at,expires_at)
 VALUES(p_attempt,p_principal,p_bff_attempt,p_start_key,p_request_sha256,
   p_state_sha256,p_initiator_sha256,p_expected_issuer,p_pkce_envelope,
   p_nonce_envelope,clock_timestamp(),
   clock_timestamp()+make_interval(secs=>p_ttl_seconds));
 -- A UNIQUE violation for duplicate startup is a deliberate closed outcome.
 RETURN true;
END $$;

-- COMMIT this claim BEFORE any IdP HTTP. Never release/renew a claim to
-- re-redeem an ambiguously consumed Authorization Code.
CREATE FUNCTION auth_l1.claim_initial_login_exchange(
 p_attempt uuid,p_principal text,p_initiator_sha256 text,p_state_sha256 text
) RETURNS boolean LANGUAGE plpgsql VOLATILE SECURITY DEFINER
SET search_path=pg_catalog AS $$
DECLARE a record;
BEGIN
 IF p_attempt IS NULL OR p_principal IS NULL OR p_initiator_sha256 IS NULL
    OR p_state_sha256 IS NULL OR p_state_sha256 !~ '^[0-9a-f]{64}$'
    OR p_initiator_sha256 !~ '^[0-9a-f]{64}$' THEN
  RAISE EXCEPTION 'LOGIN_CLAIM_INVALID' USING ERRCODE='P0001';
 END IF;
 LOCK TABLE auth_l1.owners IN ACCESS SHARE MODE;
 SELECT * INTO a FROM auth_l1.initial_login_attempts
 WHERE attempt_id=p_attempt FOR UPDATE;
 IF NOT FOUND OR a.bff_principal IS DISTINCT FROM p_principal
    OR a.initiator_sha256 IS DISTINCT FROM p_initiator_sha256
    OR a.state_sha256 IS DISTINCT FROM p_state_sha256
    OR a.state<>'INITIATED' OR clock_timestamp()>=a.expires_at THEN
  RAISE EXCEPTION 'LOGIN_CLAIM_DENIED' USING ERRCODE='P0001';
 END IF;
 UPDATE auth_l1.initial_login_attempts
 SET state='EXCHANGE_STARTED',state_version=state_version+1,
     exchange_started_at=clock_timestamp()
 WHERE attempt_id=p_attempt;
 RETURN true;
END $$;

CREATE FUNCTION auth_l1.mark_initial_login_unknown(
 p_attempt uuid,p_principal text,p_initiator_sha256 text
) RETURNS boolean LANGUAGE plpgsql VOLATILE SECURITY DEFINER
SET search_path=pg_catalog AS $$
DECLARE a record;
BEGIN
 LOCK TABLE auth_l1.owners IN ACCESS SHARE MODE;
 SELECT * INTO a FROM auth_l1.initial_login_attempts
 WHERE attempt_id=p_attempt FOR UPDATE;
 IF NOT FOUND OR a.bff_principal IS DISTINCT FROM p_principal
    OR a.initiator_sha256 IS DISTINCT FROM p_initiator_sha256
    OR a.state NOT IN ('EXCHANGE_STARTED','UNKNOWN_RECONCILIATION_REQUIRED') THEN
  RAISE EXCEPTION 'LOGIN_UNKNOWN_DENIED' USING ERRCODE='P0001';
 END IF;
 IF a.state='EXCHANGE_STARTED' THEN
  UPDATE auth_l1.initial_login_attempts
  SET state='UNKNOWN_RECONCILIATION_REQUIRED',state_version=state_version+1,
      finalized_at=clock_timestamp() WHERE attempt_id=p_attempt;
 END IF;
 RETURN true;
END $$;

-- Signed IdP issuer+subject validation belongs to the API; this SQL function
-- additionally checks that this exact immutable pair maps to the claimed Owner.
-- Owner row FOR UPDATE precedes registry row FOR UPDATE; both precede Session
-- INSERT. One transaction commits pending Session AND immutable receipt.
CREATE FUNCTION auth_l1.issue_initial_login_pending(
 p_attempt uuid,p_principal text,p_initiator_sha256 text,p_owner text,
 p_issuer text,p_subject text,p_epoch bigint,p_digest text,
 p_idle_seconds integer,p_absolute_seconds integer
) RETURNS jsonb LANGUAGE plpgsql VOLATILE SECURITY DEFINER
SET search_path=pg_catalog AS $$
DECLARE o record; a record; mapped_owner text; issued_receipt uuid;
        now_db timestamptz; absolute_deadline timestamptz;
BEGIN
 IF p_attempt IS NULL OR p_principal IS NULL OR p_initiator_sha256 IS NULL
    OR p_owner IS NULL OR length(btrim(p_owner))=0
    OR p_issuer IS NULL OR p_subject IS NULL OR length(p_subject) NOT BETWEEN 1 AND 255
    OR p_epoch IS NULL OR p_epoch<0
    OR p_digest IS NULL OR p_digest !~ '^[0-9a-f]{64}$'
    OR p_idle_seconds IS NULL OR p_idle_seconds NOT BETWEEN 1 AND 86400
    OR p_absolute_seconds IS NULL OR p_absolute_seconds<p_idle_seconds
    OR p_absolute_seconds>86400 THEN
  RAISE EXCEPTION 'LOGIN_ISSUE_INVALID' USING ERRCODE='P0001';
 END IF;
 LOCK TABLE auth_l1.owners IN ACCESS SHARE MODE;
 -- Noncommitted attempt or claim must NOT wait for another worker's COMMIT.
 PERFORM 1 FROM auth_l1.initial_login_attempts
  WHERE attempt_id=p_attempt AND bff_principal=p_principal
    AND initiator_sha256=p_initiator_sha256 AND state='EXCHANGE_STARTED';
 IF NOT FOUND THEN
  RAISE EXCEPTION 'LOGIN_ISSUE_UNCOMMITTED_OR_INVALID' USING ERRCODE='P0001';
 END IF;
 SELECT * INTO o FROM auth_l1.owners WHERE owner_id=p_owner FOR UPDATE;
 IF NOT FOUND OR o.state<>'active' OR o.reset_gate<>'open'
    OR o.session_epoch IS DISTINCT FROM p_epoch THEN
  RAISE EXCEPTION 'LOGIN_OWNER_EPOCH_OR_GATE_DENIED' USING ERRCODE='P0001';
 END IF;
 SELECT * INTO a FROM auth_l1.initial_login_attempts
  WHERE attempt_id=p_attempt FOR UPDATE;
 IF NOT FOUND OR a.state<>'EXCHANGE_STARTED'
    OR a.bff_principal IS DISTINCT FROM p_principal
    OR a.initiator_sha256 IS DISTINCT FROM p_initiator_sha256
    OR a.expected_issuer IS DISTINCT FROM p_issuer
    OR clock_timestamp()>=a.expires_at OR a.session_digest IS NOT NULL THEN
  RAISE EXCEPTION 'LOGIN_ISSUE_ALREADY_CLAIMED_OR_EXPIRED' USING ERRCODE='P0001';
 END IF;
 SELECT owner_id INTO mapped_owner FROM auth_l1.identity_links
 WHERE issuer=p_issuer AND subject=p_subject;
 IF NOT FOUND OR mapped_owner IS DISTINCT FROM p_owner THEN
  RAISE EXCEPTION 'LOGIN_VERIFIED_OWNER_MISMATCH' USING ERRCODE='P0001';
 END IF;
 now_db:=clock_timestamp();
 absolute_deadline:=now_db+make_interval(secs=>p_absolute_seconds);
 issued_receipt:=gen_random_uuid();
 INSERT INTO auth_l1.sessions(
   digest_sha256,owner_id,session_epoch,generation,status,created_at,
   last_activity_at,idle_expires_at,absolute_expires_at,idle_seconds)
 VALUES(p_digest,p_owner,p_epoch,0,'PENDING_BINDING',now_db,now_db,
   LEAST(now_db+make_interval(secs=>p_idle_seconds),absolute_deadline),
   absolute_deadline,p_idle_seconds);
 UPDATE auth_l1.initial_login_attempts SET
   state='ISSUED_PENDING_BINDING',state_version=state_version+1,
   session_digest=p_digest,receipt_id=issued_receipt,
   owner_id=p_owner,issued_epoch=p_epoch,issued_at=now_db
 WHERE attempt_id=p_attempt;
 RETURN jsonb_build_object(
   'issue_status','ISSUED_PENDING_BINDING','attempt_id',p_attempt,
   'receipt_id',issued_receipt,'owner_id',p_owner,'epoch',p_epoch,
   'generation',0,'idle_expires_at',
       LEAST(now_db+make_interval(secs=>p_idle_seconds),absolute_deadline),
   'absolute_expires_at',absolute_deadline);
END $$;

-- ACK confirms BFF's asserted DURABLE alias store write, not browser Cookie
-- delivery. Browser alias itself and raw verifier never enter Product SQL.
CREATE FUNCTION auth_l1.ack_initial_login_binding(
 p_attempt uuid,p_receipt uuid,p_principal text,p_initiator_sha256 text,
 p_owner text,p_epoch bigint,p_alias_sha256 text
) RETURNS boolean LANGUAGE plpgsql VOLATILE SECURITY DEFINER
SET search_path=pg_catalog AS $$
DECLARE o record; a record; s record; scoped_owner text; now_db timestamptz;
BEGIN
 IF p_attempt IS NULL OR p_receipt IS NULL OR p_principal IS NULL
    OR p_initiator_sha256 IS NULL OR p_owner IS NULL
    OR p_epoch IS NULL OR p_epoch<0
    OR p_alias_sha256 IS NULL OR p_alias_sha256 !~ '^[0-9a-f]{64}$' THEN
  RAISE EXCEPTION 'LOGIN_ACK_INVALID' USING ERRCODE='P0001';
 END IF;
 LOCK TABLE auth_l1.owners IN ACCESS SHARE MODE;
 SELECT owner_id INTO scoped_owner FROM auth_l1.initial_login_attempts
 WHERE attempt_id=p_attempt AND receipt_id=p_receipt
   AND bff_principal=p_principal AND initiator_sha256=p_initiator_sha256;
 IF NOT FOUND OR scoped_owner IS DISTINCT FROM p_owner THEN
  RAISE EXCEPTION 'LOGIN_ACK_SCOPE_DENIED' USING ERRCODE='P0001';
 END IF;
 SELECT * INTO o FROM auth_l1.owners WHERE owner_id=p_owner FOR UPDATE;
 SELECT * INTO a FROM auth_l1.initial_login_attempts
 WHERE attempt_id=p_attempt FOR UPDATE;
 IF NOT FOUND OR a.owner_id IS DISTINCT FROM p_owner
    OR a.receipt_id IS DISTINCT FROM p_receipt
    OR a.bff_principal IS DISTINCT FROM p_principal
    OR a.initiator_sha256 IS DISTINCT FROM p_initiator_sha256
    OR a.issued_epoch IS DISTINCT FROM p_epoch THEN
  RAISE EXCEPTION 'LOGIN_ACK_SCOPE_DENIED' USING ERRCODE='P0001';
 END IF;
 SELECT * INTO s FROM auth_l1.sessions WHERE digest_sha256=a.session_digest FOR UPDATE;
 now_db:=clock_timestamp();
 IF s.digest_sha256 IS NULL OR s.owner_id IS DISTINCT FROM p_owner
    OR s.session_epoch IS DISTINCT FROM p_epoch
    OR o.state<>'active' OR o.reset_gate<>'open'
    OR o.session_epoch IS DISTINCT FROM p_epoch
    OR now_db>=s.idle_expires_at OR now_db>=s.absolute_expires_at THEN
  RAISE EXCEPTION 'LOGIN_ACK_STALE_OR_REVOKED' USING ERRCODE='P0001';
 END IF;
 IF a.state='ACTIVE' AND s.status='active'
    AND a.alias_sha256=p_alias_sha256 THEN
  RETURN true; -- Same receipt and alias idempotency, never re-issue.
 END IF;
 IF a.state<>'ISSUED_PENDING_BINDING' OR s.status<>'PENDING_BINDING'
    OR now_db>=a.expires_at OR a.alias_sha256 IS NOT NULL THEN
  RAISE EXCEPTION 'LOGIN_ACK_CONFLICT' USING ERRCODE='P0001';
 END IF;
 UPDATE auth_l1.sessions SET status='active' WHERE digest_sha256=a.session_digest;
 UPDATE auth_l1.initial_login_attempts
 SET state='ACTIVE',alias_sha256=p_alias_sha256,acked_at=now_db,
     state_version=state_version+1 WHERE attempt_id=p_attempt;
 RETURN true;
END $$;

CREATE FUNCTION auth_l1.abort_initial_login_binding(
 p_attempt uuid,p_receipt uuid,p_principal text,p_initiator_sha256 text,
 p_owner text,p_epoch bigint
) RETURNS boolean LANGUAGE plpgsql VOLATILE SECURITY DEFINER
SET search_path=pg_catalog AS $$
DECLARE o record; a record; s record; scoped_owner text;
BEGIN
 IF p_attempt IS NULL OR p_receipt IS NULL OR p_principal IS NULL
    OR p_initiator_sha256 IS NULL OR p_owner IS NULL
    OR p_epoch IS NULL OR p_epoch<0 THEN
  RAISE EXCEPTION 'LOGIN_ABORT_INVALID' USING ERRCODE='P0001';
 END IF;
 LOCK TABLE auth_l1.owners IN ACCESS SHARE MODE;
 SELECT owner_id INTO scoped_owner FROM auth_l1.initial_login_attempts
 WHERE attempt_id=p_attempt AND receipt_id=p_receipt
   AND bff_principal=p_principal AND initiator_sha256=p_initiator_sha256;
 IF NOT FOUND OR scoped_owner IS DISTINCT FROM p_owner THEN
  RAISE EXCEPTION 'LOGIN_ABORT_SCOPE_DENIED' USING ERRCODE='P0001';
 END IF;
 -- Same Owner -> Registry -> Session ordering as issue/ACK and 003 revoke.
 SELECT * INTO o FROM auth_l1.owners WHERE owner_id=p_owner FOR UPDATE;
 SELECT * INTO a FROM auth_l1.initial_login_attempts
 WHERE attempt_id=p_attempt FOR UPDATE;
 IF NOT FOUND OR a.owner_id IS DISTINCT FROM p_owner
    OR a.receipt_id IS DISTINCT FROM p_receipt
    OR a.bff_principal IS DISTINCT FROM p_principal
    OR a.initiator_sha256 IS DISTINCT FROM p_initiator_sha256
    OR a.issued_epoch IS DISTINCT FROM p_epoch THEN
  RAISE EXCEPTION 'LOGIN_ABORT_SCOPE_DENIED' USING ERRCODE='P0001';
 END IF;
 SELECT * INTO s FROM auth_l1.sessions WHERE digest_sha256=a.session_digest FOR UPDATE;
 IF a.state='ABORTED' AND s.status='revoked' THEN RETURN true; END IF;
 IF a.state<>'ISSUED_PENDING_BINDING' OR s.status<>'PENDING_BINDING' THEN
  RAISE EXCEPTION 'LOGIN_ABORT_CONFLICT' USING ERRCODE='P0001';
 END IF;
 UPDATE auth_l1.sessions SET status='revoked'
 WHERE digest_sha256=a.session_digest;
 UPDATE auth_l1.initial_login_attempts
 SET state='ABORTED',state_version=state_version+1,finalized_at=clock_timestamp()
 WHERE attempt_id=p_attempt;
 RETURN true;
END $$;

-- No receipt, Owner, Alias, Code, verifier, nonce, IdP token or ciphertext.
-- Matching BFF principal+initiator is necessary but API must authenticate it.
CREATE FUNCTION auth_l1.status_initial_login_attempt(
 p_attempt uuid,p_principal text,p_initiator_sha256 text
) RETURNS jsonb LANGUAGE plpgsql STABLE SECURITY DEFINER
SET search_path=pg_catalog AS $$
DECLARE a record;
BEGIN
 IF p_attempt IS NULL OR p_principal IS NULL OR p_initiator_sha256 IS NULL
    OR p_initiator_sha256 !~ '^[0-9a-f]{64}$' THEN
  RAISE EXCEPTION 'LOGIN_STATUS_INVALID' USING ERRCODE='P0001';
 END IF;
 SELECT state,created_at,expires_at,issued_at,acked_at INTO a
 FROM auth_l1.initial_login_attempts
 WHERE attempt_id=p_attempt AND bff_principal=p_principal
   AND initiator_sha256=p_initiator_sha256;
 IF NOT FOUND THEN RETURN NULL; END IF;
 RETURN jsonb_build_object('state',a.state,'created_at',a.created_at,
   'expires_at',a.expires_at,'issued_at',a.issued_at,'acked_at',a.acked_at);
END $$;

-- Narrow single-attempt worker: caller enumerates expired IDs without grant
-- to read registry tables. No silent DELETE; preserve immutable audit.
CREATE FUNCTION auth_l1.cleanup_initial_login_attempt(p_attempt uuid)
RETURNS text LANGUAGE plpgsql VOLATILE SECURITY DEFINER
SET search_path=pg_catalog AS $$
DECLARE initial_owner text; o record; a record; s record; now_db timestamptz;
BEGIN
 IF p_attempt IS NULL THEN
  RAISE EXCEPTION 'LOGIN_CLEANUP_INVALID' USING ERRCODE='P0001';
 END IF;
 LOCK TABLE auth_l1.owners IN ACCESS SHARE MODE;
 SELECT owner_id INTO initial_owner FROM auth_l1.initial_login_attempts
 WHERE attempt_id=p_attempt;
 IF NOT FOUND THEN RETURN 'NOT_FOUND'; END IF;
 -- Do not take a registry tuple lock first and then an Owner tuple lock.
 IF initial_owner IS NOT NULL THEN
  SELECT * INTO o FROM auth_l1.owners WHERE owner_id=initial_owner FOR UPDATE;
 END IF;
 SELECT * INTO a FROM auth_l1.initial_login_attempts
 WHERE attempt_id=p_attempt FOR UPDATE;
 IF NOT FOUND THEN RETURN 'NOT_FOUND'; END IF;
 IF a.owner_id IS DISTINCT FROM initial_owner THEN
  RAISE EXCEPTION 'LOGIN_CLEANUP_SCOPE_DRIFT' USING ERRCODE='P0001';
 END IF;
 now_db:=clock_timestamp();
 IF now_db<a.expires_at THEN RETURN 'NOT_DUE'; END IF;
 IF a.state='ISSUED_PENDING_BINDING' THEN
  SELECT * INTO s FROM auth_l1.sessions WHERE digest_sha256=a.session_digest FOR UPDATE;
  IF NOT FOUND OR s.status<>'PENDING_BINDING' THEN
   RAISE EXCEPTION 'LOGIN_CLEANUP_EVIDENCE_INCONSISTENT' USING ERRCODE='P0001';
  END IF;
  UPDATE auth_l1.sessions SET status='revoked' WHERE digest_sha256=a.session_digest;
  UPDATE auth_l1.initial_login_attempts
  SET state='EXPIRED',state_version=state_version+1,finalized_at=now_db
  WHERE attempt_id=p_attempt;
  RETURN 'EXPIRED_PENDING_REVOKED';
 ELSIF a.state='INITIATED' THEN
  UPDATE auth_l1.initial_login_attempts
  SET state='EXPIRED',state_version=state_version+1,finalized_at=now_db
  WHERE attempt_id=p_attempt;
  RETURN 'EXPIRED_UNCLAIMED';
 ELSIF a.state='EXCHANGE_STARTED' THEN
  UPDATE auth_l1.initial_login_attempts
  SET state='UNKNOWN_RECONCILIATION_REQUIRED',state_version=state_version+1,
      finalized_at=now_db WHERE attempt_id=p_attempt;
  RETURN 'UNKNOWN_EXCHANGE';
 END IF;
 RETURN 'TERMINAL_NO_CHANGE';
END $$;

REVOKE ALL ON FUNCTION auth_l1.start_initial_login_attempt(
 uuid,text,uuid,text,text,text,text,text,bytea,bytea,integer) FROM PUBLIC;
REVOKE ALL ON FUNCTION auth_l1.claim_initial_login_exchange(uuid,text,text,text) FROM PUBLIC;
REVOKE ALL ON FUNCTION auth_l1.mark_initial_login_unknown(uuid,text,text) FROM PUBLIC;
REVOKE ALL ON FUNCTION auth_l1.issue_initial_login_pending(
 uuid,text,text,text,text,text,bigint,text,integer,integer) FROM PUBLIC;
REVOKE ALL ON FUNCTION auth_l1.ack_initial_login_binding(
 uuid,uuid,text,text,text,bigint,text) FROM PUBLIC;
REVOKE ALL ON FUNCTION auth_l1.abort_initial_login_binding(
 uuid,uuid,text,text,text,bigint) FROM PUBLIC;
REVOKE ALL ON FUNCTION auth_l1.status_initial_login_attempt(uuid,text,text) FROM PUBLIC;
REVOKE ALL ON FUNCTION auth_l1.cleanup_initial_login_attempt(uuid) FROM PUBLIC;
GRANT USAGE ON SCHEMA auth_l1 TO
 auth_login_bootstrap,auth_login_issuer,auth_login_binder,
 auth_login_reader,auth_login_cleaner;
GRANT EXECUTE ON FUNCTION auth_l1.start_initial_login_attempt(
 uuid,text,uuid,text,text,text,text,text,bytea,bytea,integer) TO auth_login_bootstrap;
GRANT EXECUTE ON FUNCTION auth_l1.claim_initial_login_exchange(uuid,text,text,text)
 TO auth_login_bootstrap;
GRANT EXECUTE ON FUNCTION auth_l1.mark_initial_login_unknown(uuid,text,text)
 TO auth_login_bootstrap;
GRANT EXECUTE ON FUNCTION auth_l1.issue_initial_login_pending(
 uuid,text,text,text,text,text,bigint,text,integer,integer) TO auth_login_issuer;
GRANT EXECUTE ON FUNCTION auth_l1.ack_initial_login_binding(
 uuid,uuid,text,text,text,bigint,text) TO auth_login_binder;
GRANT EXECUTE ON FUNCTION auth_l1.abort_initial_login_binding(
 uuid,uuid,text,text,text,bigint) TO auth_login_binder;
GRANT EXECUTE ON FUNCTION auth_l1.status_initial_login_attempt(uuid,text,text)
 TO auth_login_reader;
GRANT EXECUTE ON FUNCTION auth_l1.cleanup_initial_login_attempt(uuid)
 TO auth_login_cleaner;
COMMIT;
