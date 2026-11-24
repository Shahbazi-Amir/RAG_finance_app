-- Apply only to a separately provisioned disposable staging database.
BEGIN;
CREATE FUNCTION auth_l1.admit_and_renew_staging_session(
    p_owner text, p_digest text, p_epoch bigint, p_generation integer
) RETURNS boolean
LANGUAGE plpgsql VOLATILE SECURITY DEFINER SET search_path=pg_catalog AS $$
BEGIN
    -- Serialize with revoke, rotate and concurrent renewal before admission.
    IF NOT EXISTS (SELECT 1 FROM auth_l1.sessions
                   WHERE digest_sha256=p_digest AND owner_id=p_owner) THEN
        RETURN false;
    END IF;
    PERFORM 1 FROM auth_l1.owners WHERE owner_id=p_owner FOR UPDATE;
    IF NOT FOUND THEN RETURN false; END IF;
    PERFORM 1 FROM auth_l1.sessions
        WHERE digest_sha256=p_digest AND owner_id=p_owner FOR UPDATE;
    IF NOT FOUND THEN RETURN false; END IF;
    IF auth_l1.admit_session_fenced(p_owner,p_digest,p_epoch,p_generation)
       IS DISTINCT FROM true THEN
        RETURN false;
    END IF;
    PERFORM auth_l1.touch_session(p_digest,p_epoch);
    RETURN true;
END;
$$;
REVOKE ALL ON FUNCTION auth_l1.admit_and_renew_staging_session(text,text,bigint,integer) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION auth_l1.admit_and_renew_staging_session(text,text,bigint,integer)
    TO history_app;
COMMIT;
