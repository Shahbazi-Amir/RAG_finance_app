-- 010_initial_login_claim_material.up.sql
-- Additive to pinned 009, NOT a replacement for its boolean CLAIM or 009 data.
-- Provision auth_login_claim_reader separately (CI synthetic role only).
-- API must COMMIT this one-use Claim before any IdP Code HTTP request.
BEGIN;

CREATE FUNCTION auth_l1.claim_initial_login_exchange_material(
 p_attempt uuid, p_bff_principal text, p_bff_attempt_id uuid,
 p_initiator_sha256 text, p_state_sha256 text
) RETURNS TABLE(
 expected_issuer text, pkce_envelope bytea, nonce_envelope bytea,
 expires_at timestamptz, claim_version bigint
)
LANGUAGE plpgsql VOLATILE SECURITY DEFINER
SET search_path=pg_catalog AS $$
DECLARE
 a record;
BEGIN
 IF p_attempt IS NULL OR p_bff_attempt_id IS NULL
    OR p_bff_principal IS NULL OR length(p_bff_principal) NOT BETWEEN 1 AND 128
    OR p_initiator_sha256 IS NULL OR p_initiator_sha256 !~ '^[0-9a-f]{64}$'
    OR p_state_sha256 IS NULL OR p_state_sha256 !~ '^[0-9a-f]{64}$' THEN
  RAISE EXCEPTION 'LOGIN_CLAIM_DENIED' USING ERRCODE='P0001';
 END IF;

 -- 009.down takes the Owner table ACCESS EXCLUSIVE first.
 -- Keep the same table ordering; no Owner row is known until AFTER IdP verification.
 LOCK TABLE auth_l1.owners IN ACCESS SHARE MODE;

 -- One immutable Login Attempt controls BOTH old 009 Boolean CLAIM and 010.
 -- Waiting workers re-read committed state while acquiring this actual PG row lock.
 SELECT * INTO a FROM auth_l1.initial_login_attempts
 WHERE attempt_id=p_attempt FOR UPDATE;

 IF NOT FOUND OR a.attempt_id IS DISTINCT FROM p_attempt
    OR a.bff_principal IS DISTINCT FROM p_bff_principal
    OR a.bff_attempt_id IS DISTINCT FROM p_bff_attempt_id
    OR a.initiator_sha256 IS DISTINCT FROM p_initiator_sha256
    OR a.state_sha256 IS DISTINCT FROM p_state_sha256
    OR a.state IS DISTINCT FROM 'INITIATED'
    OR a.session_digest IS NOT NULL OR a.receipt_id IS NOT NULL
    OR a.expected_issuer IS NULL OR length(a.expected_issuer)=0
    OR a.pkce_envelope IS NULL
    OR octet_length(a.pkce_envelope) NOT BETWEEN 32 AND 4096
    OR a.nonce_envelope IS NULL
    OR octet_length(a.nonce_envelope) NOT BETWEEN 32 AND 4096
    OR clock_timestamp()>=a.expires_at THEN
  RAISE EXCEPTION 'LOGIN_CLAIM_DENIED' USING ERRCODE='P0001';
 END IF;

 UPDATE auth_l1.initial_login_attempts
    SET state='EXCHANGE_STARTED', state_version=state_version+1,
        exchange_started_at=clock_timestamp()
 WHERE attempt_id=p_attempt;

 -- Ciphertext only, from exactly this locked row. Function does not decrypt,
 -- create Session, return Code, Owner, Receipt, Cookie or Product verifier.
 RETURN QUERY SELECT a.expected_issuer, a.pkce_envelope, a.nonce_envelope,
                     a.expires_at, a.state_version+1;
END $$;

REVOKE ALL ON FUNCTION auth_l1.claim_initial_login_exchange_material(
 uuid,text,uuid,text,text) FROM PUBLIC;
GRANT USAGE ON SCHEMA auth_l1 TO auth_login_claim_reader;
GRANT EXECUTE ON FUNCTION auth_l1.claim_initial_login_exchange_material(
 uuid,text,uuid,text,text) TO auth_login_claim_reader;
COMMIT;
