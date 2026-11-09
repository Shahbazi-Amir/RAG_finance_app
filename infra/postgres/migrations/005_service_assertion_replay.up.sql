-- 005_service_assertion_replay.up.sql — bounded BND-DB-03, PostgreSQL 17.11
-- Input: only SHA256(verified_issuer + NUL + verified_jti), signed exp seconds.
-- Roles auth_trust_api and auth_replay_cleaner must be pre-provisioned by migrator.
CREATE TABLE auth_l1.service_assertion_replays (
 issuer_jti_sha256 text PRIMARY KEY CHECK(issuer_jti_sha256 ~ '^[0-9a-f]{64}$'),
 expires_at timestamptz NOT NULL,
 consumed_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 CHECK (expires_at > consumed_at)
);
CREATE INDEX service_assertion_replay_expiry_idx
 ON auth_l1.service_assertion_replays(expires_at,issuer_jti_sha256);
ALTER TABLE auth_l1.service_assertion_replays ENABLE ROW LEVEL SECURITY;
ALTER TABLE auth_l1.service_assertion_replays FORCE ROW LEVEL SECURITY;
CREATE POLICY deny_direct_replay ON auth_l1.service_assertion_replays
 FOR ALL TO PUBLIC USING(false) WITH CHECK(false);
REVOKE ALL ON TABLE auth_l1.service_assertion_replays
 FROM PUBLIC,auth_trust_api,auth_replay_cleaner;

CREATE FUNCTION auth_l1.consume_service_assertion(p_issuer_jti_sha256 text,p_expires_epoch bigint)
RETURNS boolean LANGUAGE plpgsql VOLATILE SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE expiry timestamptz; before_wait timestamptz; after_wait timestamptz;
BEGIN
 IF p_issuer_jti_sha256 IS NULL OR p_issuer_jti_sha256 !~ '^[0-9a-f]{64}$'
    OR p_expires_epoch IS NULL OR p_expires_epoch <= 0
    OR p_expires_epoch > 253402300799 THEN
  RAISE EXCEPTION 'REPLAY_INVALID_INPUT' USING ERRCODE='P0001';
 END IF;
 expiry:=to_timestamp(p_expires_epoch);
 before_wait:=clock_timestamp();
 IF before_wait>=expiry OR expiry>before_wait+interval '30 seconds' THEN
  RAISE EXCEPTION 'REPLAY_INVALID_TIME' USING ERRCODE='P0001';
 END IF;
 -- Plain INSERT: PK duplicate raises UniqueViolation AND aborts outer TX.
 -- No ON CONFLICT handler, no SELECT/UPDATE rights for the caller.
 INSERT INTO auth_l1.service_assertion_replays(issuer_jti_sha256,expires_at,consumed_at)
 VALUES(p_issuer_jti_sha256,expiry,clock_timestamp());
 -- If competing insertion rolled back after expiry, fail after lock wait.
 after_wait:=clock_timestamp();
 IF after_wait>=expiry THEN
  RAISE EXCEPTION 'REPLAY_EXPIRED_AFTER_LOCK' USING ERRCODE='P0001';
 END IF;
 RETURN true;
END $$;

CREATE FUNCTION auth_l1.purge_expired_service_assertions(p_batch_limit integer)
RETURNS integer LANGUAGE plpgsql VOLATILE SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE deleted integer;
BEGIN
 IF p_batch_limit IS NULL OR p_batch_limit<1 OR p_batch_limit>1000 THEN
  RAISE EXCEPTION 'REPLAY_INVALID_CLEANUP_LIMIT' USING ERRCODE='P0001';
 END IF;
 WITH victims AS (
  SELECT x.issuer_jti_sha256
  FROM auth_l1.service_assertion_replays x
  WHERE x.expires_at <= clock_timestamp()
  ORDER BY x.expires_at,x.issuer_jti_sha256
  LIMIT p_batch_limit FOR UPDATE SKIP LOCKED
 )
 DELETE FROM auth_l1.service_assertion_replays AS stored
 USING victims WHERE stored.issuer_jti_sha256=victims.issuer_jti_sha256;
 GET DIAGNOSTICS deleted=ROW_COUNT;
 RETURN deleted;
END $$;
REVOKE ALL ON FUNCTION auth_l1.consume_service_assertion(text,bigint) FROM PUBLIC;
REVOKE ALL ON FUNCTION auth_l1.purge_expired_service_assertions(integer) FROM PUBLIC;
GRANT USAGE ON SCHEMA auth_l1 TO auth_trust_api,auth_replay_cleaner;
GRANT EXECUTE ON FUNCTION auth_l1.consume_service_assertion(text,bigint) TO auth_trust_api;
GRANT EXECUTE ON FUNCTION auth_l1.admit_session_fenced(text,text,bigint,integer) TO auth_trust_api;
GRANT EXECUTE ON FUNCTION auth_l1.purge_expired_service_assertions(integer) TO auth_replay_cleaner;
