-- 007_scoped_reset_identity_lookup.up.sql — CR-DB-01B synthetic-only.
-- Depends on unchanged 003 identity_links and 006 C1 authorization schema.
-- auth_reset_lookup must be a separately pre-provisioned least-privilege role.
-- Read-only function: no row locks, no mutations, no network hold, no C1 rights.
CREATE FUNCTION auth_l1.resolve_reset_identity(
 p_authorization_sha256 text,
 p_owner text,
 p_kind text,
 p_purpose text,
 p_expected_epoch bigint,
 p_expected_issuer text
) RETURNS jsonb
LANGUAGE plpgsql VOLATILE SECURITY DEFINER
SET search_path=pg_catalog AS $$
DECLARE identity_row record;
BEGIN
 IF p_authorization_sha256 IS NULL OR p_authorization_sha256 !~ '^[0-9a-f]{64}$'
    OR p_owner IS NULL OR length(btrim(p_owner))=0
    OR p_kind IS NULL OR p_kind NOT IN ('RECOVERY','AUTHENTICATED_PASSWORD_CHANGE')
    OR p_purpose IS DISTINCT FROM 'CONTROLLED_RESET_C1'
    OR p_expected_epoch IS NULL OR p_expected_epoch<0
       OR p_expected_epoch=9223372036854775807
    OR p_expected_issuer IS NULL OR length(btrim(p_expected_issuer))=0
       OR length(p_expected_issuer)>1024
 THEN
   RAISE EXCEPTION 'RESET_IDENTITY_LOOKUP_DENIED' USING ERRCODE='P0001';
 END IF;

 -- A single MVCC read decides all scopes and expiry with the PostgreSQL
 -- clock; no SELECT FOR SHARE/UPDATE, lock retention, or status writes.
 -- identity_links.owner_id is UNIQUE in 003: at most ONE identity pair.
 SELECT link.issuer,link.subject INTO identity_row
 FROM auth_l1.identity_links AS link
 JOIN auth_l1.owners AS own ON own.owner_id=link.owner_id
 JOIN auth_l1.reset_c1_authorizations AS authz
   ON authz.owner_id=own.owner_id
 WHERE authz.authorization_sha256=p_authorization_sha256
   AND own.owner_id=p_owner
   AND own.state='active'
   AND own.reset_gate='open'
   AND own.session_epoch=p_expected_epoch
   AND authz.expected_epoch=p_expected_epoch
   AND authz.kind=p_kind
   AND authz.purpose=p_purpose
   AND authz.consumed_at IS NULL
   AND authz.consumed_operation_id IS NULL
   AND authz.expires_at>clock_timestamp()
   -- Authenticated kind carries a specific 006 Session digest/generation.
   -- Observe its current validity without locking; 006 C1 still re-admits.
   AND (
     authz.kind='RECOVERY'
     OR EXISTS (
       SELECT 1 FROM auth_l1.sessions AS session_row
       WHERE session_row.digest_sha256=authz.session_digest_sha256
         AND session_row.owner_id=own.owner_id
         AND session_row.session_epoch=p_expected_epoch
         AND session_row.generation=authz.session_generation
         AND session_row.status='active'
         AND session_row.idle_expires_at>clock_timestamp()
         AND session_row.absolute_expires_at>clock_timestamp()
     )
   )
   AND link.issuer=p_expected_issuer
   AND NOT EXISTS (
     SELECT 1 FROM auth_l1.reset_c1_operations AS op
     WHERE op.owner_id=own.owner_id AND op.active
   );
 IF NOT FOUND THEN
   RAISE EXCEPTION 'RESET_IDENTITY_LOOKUP_DENIED' USING ERRCODE='P0001';
 END IF;

 -- Deliberately return exactly two fields and no owner, epoch, auth status,
 -- operation ID, email, token, timestamps, other linked users or row counts.
 RETURN pg_catalog.jsonb_build_object(
   'issuer',identity_row.issuer,'subject',identity_row.subject
 );
END $$;
REVOKE ALL ON FUNCTION auth_l1.resolve_reset_identity(text,text,text,text,bigint,text)
 FROM PUBLIC;
GRANT USAGE ON SCHEMA auth_l1 TO auth_reset_lookup;
GRANT EXECUTE ON FUNCTION auth_l1.resolve_reset_identity(text,text,text,text,bigint,text)
 TO auth_reset_lookup;
