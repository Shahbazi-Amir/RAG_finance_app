-- 004_session_aware_fence.up.sql — bounded BND-DB-02 on PostgreSQL 17.11.
-- Existing 001/002/003 migrations are immutable. Raw opaque tokens NEVER enter SQL.
-- Transactional admission only: this function cannot bind future HTTP/other DB work.
CREATE FUNCTION auth_l1.admit_session_fenced(
 p_owner text, p_digest text, p_epoch bigint, p_generation integer
) RETURNS boolean
LANGUAGE plpgsql VOLATILE SECURITY DEFINER
SET search_path=pg_catalog AS $$
DECLARE
 digest_owner text;
 o record;
 s record;
 admission_at timestamptz;
BEGIN
 -- The SQL boundary, not only Python, rejects malformed/untrusted CAS inputs.
 IF p_owner IS NULL OR length(btrim(p_owner))=0
    OR p_digest IS NULL OR p_digest !~ '^[0-9a-f]{64}$'
    OR p_epoch IS NULL OR p_epoch<0
    OR p_generation IS NULL OR p_generation<0 THEN
  RAISE EXCEPTION 'SESSION_ADMISSION_INVALID_INPUT' USING ERRCODE='P0001';
 END IF;

 -- Lock ordering MUST match 003 rotate/touch/revoke: owner first, session second.
 -- Preliminary digest lookup is not an admission or a trusted authorization.
 SELECT x.owner_id INTO digest_owner
   FROM auth_l1.sessions x WHERE x.digest_sha256=p_digest;
 IF NOT FOUND OR digest_owner IS DISTINCT FROM p_owner THEN RETURN false; END IF;

 -- Acquired locks survive nested successful savepoints, but NOT the enclosing
 -- transaction's COMMIT/ROLLBACK. Owner lock fences revoke_all, suspension,
 -- rotation and revoke_one (all update owner first).
 SELECT x.* INTO o FROM auth_l1.owners x
   WHERE x.owner_id=p_owner FOR SHARE;
 IF NOT FOUND THEN RETURN false; END IF;
 SELECT x.* INTO s FROM auth_l1.sessions x
   WHERE x.digest_sha256=p_digest FOR SHARE;
 IF NOT FOUND THEN RETURN false; END IF;

 -- Single authoritative PostgreSQL wall-clock decision AFTER both locks.
 -- Clock passing expiry AFTER admission does not revoke an already accepted
 -- SQL transaction; only new admissions observe expiry.
 admission_at:=clock_timestamp();
 RETURN (
    o.state='active' AND o.reset_gate='open'
    AND o.session_epoch=p_epoch
    AND s.owner_id=p_owner
    AND s.status='active'
    AND s.session_epoch=p_epoch
    AND s.generation=p_generation
    AND admission_at<s.idle_expires_at
    AND admission_at<s.absolute_expires_at
 );
END $$;
-- Functions default to PUBLIC EXECUTE unless revoked. Existing schema USAGE
-- permits only authorized auth roles, but explicit per-function grant is required.
REVOKE ALL ON FUNCTION auth_l1.admit_session_fenced(text,text,bigint,integer) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION auth_l1.admit_session_fenced(text,text,bigint,integer) TO auth_sessions;
