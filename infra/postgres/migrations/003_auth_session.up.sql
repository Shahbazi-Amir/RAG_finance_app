-- 003_auth_session.up.sql | PostgreSQL 17.11; SYNTHETIC BND-DB-01 ONLY.
-- 001/002 history migrations intentionally unchanged. This schema belongs to product DB.
-- history_app has NO auth_l1 privileges. All issuer/sub values are trusted server inputs,
-- NOT values authenticated by PostgreSQL. Never pass opaque raw session IDs to SQL.
CREATE SCHEMA auth_l1;
REVOKE ALL ON SCHEMA auth_l1 FROM PUBLIC;
CREATE TABLE auth_l1.owners (
 owner_id text PRIMARY KEY,
 state text NOT NULL DEFAULT 'active' CHECK(state IN ('active','suspended')),
 session_epoch bigint NOT NULL DEFAULT 0 CHECK(session_epoch >= 0),
 reset_gate text NOT NULL DEFAULT 'open' CHECK(reset_gate IN ('open','pending_reauth')),
 created_at timestamptz NOT NULL DEFAULT clock_timestamp()
);
CREATE TABLE auth_l1.identity_links (
 issuer text NOT NULL CHECK(length(btrim(issuer)) > 0 AND length(issuer) <= 1024),
 subject text NOT NULL CHECK(length(btrim(subject)) > 0 AND length(subject) <= 255),
 owner_id text NOT NULL UNIQUE REFERENCES auth_l1.owners(owner_id) ON DELETE RESTRICT,
 created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 PRIMARY KEY (issuer,subject)
);
CREATE TABLE auth_l1.sessions (
 digest_sha256 text PRIMARY KEY CHECK(digest_sha256 ~ '^[0-9a-f]{64}$'),
 owner_id text NOT NULL REFERENCES auth_l1.owners(owner_id) ON DELETE RESTRICT,
 session_epoch bigint NOT NULL CHECK(session_epoch >= 0),
 generation integer NOT NULL CHECK(generation >= 0),
 status text NOT NULL CHECK(status IN ('active','rotated','revoked')),
 created_at timestamptz NOT NULL,
 last_activity_at timestamptz NOT NULL,
 idle_expires_at timestamptz NOT NULL,
 absolute_expires_at timestamptz NOT NULL,
 idle_seconds integer NOT NULL CHECK(idle_seconds > 0 AND idle_seconds <= 86400),
 CHECK(created_at <= last_activity_at),
 CHECK(last_activity_at <= idle_expires_at),
 CHECK(idle_expires_at <= absolute_expires_at)
);
CREATE INDEX auth_session_owner_idx ON auth_l1.sessions(owner_id,session_epoch,status);
CREATE INDEX auth_session_expiry_idx ON auth_l1.sessions(idle_expires_at,absolute_expires_at);
CREATE FUNCTION auth_l1.identity_immutable() RETURNS trigger LANGUAGE plpgsql
SET search_path=pg_catalog AS $$
BEGIN
 RAISE EXCEPTION 'IDENTITY_LINK_IMMUTABLE' USING ERRCODE='P0001';
END $$;
CREATE TRIGGER identity_no_mutation BEFORE UPDATE OR DELETE ON auth_l1.identity_links
FOR EACH ROW EXECUTE FUNCTION auth_l1.identity_immutable();
CREATE FUNCTION auth_l1.owner_epoch_guard() RETURNS trigger LANGUAGE plpgsql
SET search_path=pg_catalog AS $$
BEGIN
 IF NEW.owner_id IS DISTINCT FROM OLD.owner_id OR NEW.session_epoch IS NULL
    OR NEW.session_epoch < OLD.session_epoch
    OR (OLD.state='suspended' AND NEW.state IS DISTINCT FROM 'suspended') THEN
  RAISE EXCEPTION 'OWNER_IMMUTABILITY_OR_EPOCH_REGRESSION' USING ERRCODE='P0001';
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER owner_no_regression BEFORE UPDATE ON auth_l1.owners
FOR EACH ROW EXECUTE FUNCTION auth_l1.owner_epoch_guard();

-- Defense in depth: FORCE RLS + no direct table grants for any app/service role.
-- SECURITY DEFINER functions below execute only as trusted migrator (CI BYPASSRLS);
-- production migration/definer privilege model is NOT authorized by this mission.
DO $$
DECLARE name text;
BEGIN
 FOREACH name IN ARRAY ARRAY['owners','identity_links','sessions'] LOOP
  EXECUTE format('ALTER TABLE auth_l1.%I ENABLE ROW LEVEL SECURITY',name);
  EXECUTE format('ALTER TABLE auth_l1.%I FORCE ROW LEVEL SECURITY',name);
  EXECUTE format('CREATE POLICY deny_direct ON auth_l1.%I FOR ALL TO PUBLIC USING(false) WITH CHECK(false)',name);
 END LOOP;
END $$;

CREATE FUNCTION auth_l1.map_identity(p_issuer text,p_subject text)
RETURNS jsonb LANGUAGE plpgsql VOLATILE SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE ident record; o record; id text;
BEGIN
 IF p_issuer IS NULL OR length(btrim(p_issuer))=0 OR length(p_issuer)>1024
    OR p_subject IS NULL OR length(btrim(p_subject))=0 OR length(p_subject)>255 THEN
  RAISE EXCEPTION 'INVALID_TRUSTED_IDENTITY' USING ERRCODE='P0001';
 END IF;
 PERFORM pg_advisory_xact_lock(hashtextextended(p_issuer||chr(31)||p_subject,0));
 SELECT l.owner_id INTO ident FROM auth_l1.identity_links l
  WHERE l.issuer=p_issuer AND l.subject=p_subject;
 IF ident.owner_id IS NULL THEN
  id := gen_random_uuid()::text;
  INSERT INTO auth_l1.owners(owner_id) VALUES(id);
  INSERT INTO auth_l1.identity_links(issuer,subject,owner_id)
   VALUES(p_issuer,p_subject,id);
 ELSE
  id := ident.owner_id;
 END IF;
 SELECT * INTO o FROM auth_l1.owners x WHERE x.owner_id=id FOR SHARE;
 IF o.state <> 'active' THEN
  RAISE EXCEPTION 'IDENTITY_SUSPENDED' USING ERRCODE='P0001';
 END IF;
 RETURN jsonb_build_object('owner_id',id,'epoch',o.session_epoch,'gate',o.reset_gate);
END $$;

CREATE FUNCTION auth_l1.issue_session(p_owner text,p_epoch bigint,p_digest text,
 p_idle_seconds integer,p_absolute_seconds integer)
RETURNS jsonb LANGUAGE plpgsql VOLATILE SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE o record; now_db timestamptz; absolute_deadline timestamptz; idle_deadline timestamptz;
BEGIN
 IF p_owner IS NULL OR length(btrim(p_owner))=0 OR p_epoch IS NULL OR p_epoch<0 THEN
  RAISE EXCEPTION 'INVALID_ISSUE_OWNER_EPOCH' USING ERRCODE='P0001';
 END IF;
 IF p_digest IS NULL OR p_digest !~ '^[0-9a-f]{64}$'
    OR p_idle_seconds IS NULL OR p_absolute_seconds IS NULL
    OR p_idle_seconds<=0 OR p_absolute_seconds < p_idle_seconds
    OR p_absolute_seconds > 86400 THEN
  RAISE EXCEPTION 'INVALID_SYNTHETIC_SESSION_POLICY' USING ERRCODE='P0001';
 END IF;
 SELECT * INTO o FROM auth_l1.owners x WHERE x.owner_id=p_owner FOR UPDATE;
 IF NOT FOUND OR o.state <> 'active' OR o.reset_gate <> 'open'
    OR o.session_epoch IS DISTINCT FROM p_epoch THEN
  RAISE EXCEPTION 'SESSION_ISSUE_DENIED' USING ERRCODE='P0001';
 END IF;
 now_db:=clock_timestamp();
 absolute_deadline:=now_db+make_interval(secs=>p_absolute_seconds);
 idle_deadline:=now_db+make_interval(secs=>p_idle_seconds);
 INSERT INTO auth_l1.sessions(digest_sha256,owner_id,session_epoch,generation,status,
  created_at,last_activity_at,idle_expires_at,absolute_expires_at,idle_seconds)
 VALUES(p_digest,p_owner,p_epoch,0,'active',now_db,now_db,idle_deadline,absolute_deadline,p_idle_seconds);
 RETURN jsonb_build_object('owner_id',p_owner,'epoch',p_epoch,'generation',0,
    'idle_expires_at',idle_deadline,'absolute_expires_at',absolute_deadline);
END $$;

CREATE FUNCTION auth_l1.validate_session(p_digest text) RETURNS jsonb
LANGUAGE plpgsql VOLATILE SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE s record;
BEGIN
 SELECT s0.owner_id,s0.session_epoch,s0.generation,s0.idle_expires_at,
  s0.absolute_expires_at INTO s
 FROM auth_l1.sessions s0 JOIN auth_l1.owners o ON o.owner_id=s0.owner_id
 WHERE s0.digest_sha256=p_digest AND s0.status='active'
 AND o.state='active' AND o.reset_gate='open'
 AND s0.session_epoch=o.session_epoch
 AND clock_timestamp() < s0.idle_expires_at
 AND clock_timestamp() < s0.absolute_expires_at;
 IF NOT FOUND THEN RETURN NULL; END IF;
 RETURN jsonb_build_object('owner_id',s.owner_id,'epoch',s.session_epoch,
  'generation',s.generation,'idle_expires_at',s.idle_expires_at,
  'absolute_expires_at',s.absolute_expires_at);
END $$;

CREATE FUNCTION auth_l1.fence_owner(p_owner text,p_epoch bigint) RETURNS boolean
LANGUAGE plpgsql VOLATILE SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE o record;
BEGIN
 IF p_owner IS NULL OR length(btrim(p_owner))=0 OR p_epoch IS NULL OR p_epoch<0 THEN
  RAISE EXCEPTION 'INVALID_FENCE_OWNER_EPOCH' USING ERRCODE='P0001';
 END IF;
 SELECT * INTO o FROM auth_l1.owners x WHERE x.owner_id=p_owner FOR SHARE;
 RETURN FOUND AND o.state='active' AND o.reset_gate='open' AND o.session_epoch=p_epoch;
END $$;

CREATE FUNCTION auth_l1.touch_session(p_digest text,p_expected_epoch bigint)
RETURNS jsonb LANGUAGE plpgsql VOLATILE SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE old_owner text; o record; s record; now_db timestamptz; deadline timestamptz;
BEGIN
 IF p_digest IS NULL OR p_digest !~ '^[0-9a-f]{64}$'
    OR p_expected_epoch IS NULL OR p_expected_epoch<0 THEN
  RAISE EXCEPTION 'INVALID_TOUCH_CAS' USING ERRCODE='P0001';
 END IF;
 SELECT x.owner_id INTO old_owner FROM auth_l1.sessions x WHERE x.digest_sha256=p_digest;
 IF old_owner IS NULL THEN RAISE EXCEPTION 'SESSION_DENIED' USING ERRCODE='P0001'; END IF;
 SELECT * INTO o FROM auth_l1.owners x WHERE x.owner_id=old_owner FOR UPDATE;
 SELECT * INTO s FROM auth_l1.sessions x WHERE x.digest_sha256=p_digest FOR UPDATE;
 now_db:=clock_timestamp();
 IF o.state<>'active' OR o.reset_gate<>'open' OR o.session_epoch IS DISTINCT FROM p_expected_epoch
  OR s.status<>'active' OR s.session_epoch IS DISTINCT FROM p_expected_epoch
  OR now_db>=s.idle_expires_at OR now_db>=s.absolute_expires_at THEN
  RAISE EXCEPTION 'SESSION_DENIED' USING ERRCODE='P0001';
 END IF;
 deadline:=LEAST(now_db+make_interval(secs=>s.idle_seconds),s.absolute_expires_at);
 UPDATE auth_l1.sessions SET last_activity_at=now_db,idle_expires_at=deadline WHERE digest_sha256=p_digest;
 RETURN jsonb_build_object('owner_id',s.owner_id,'epoch',s.session_epoch,
  'generation',s.generation,'idle_expires_at',deadline,'absolute_expires_at',s.absolute_expires_at);
END $$;

CREATE FUNCTION auth_l1.rotate_session(p_old_digest text,p_new_digest text,
 p_epoch bigint,p_generation integer) RETURNS jsonb
LANGUAGE plpgsql VOLATILE SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE old_owner text; o record; s record; now_db timestamptz; new_idle timestamptz;
BEGIN
 IF p_old_digest IS NULL OR p_old_digest !~ '^[0-9a-f]{64}$'
    OR p_epoch IS NULL OR p_epoch<0 OR p_generation IS NULL
    OR p_generation<0 OR p_generation=2147483647 THEN
  RAISE EXCEPTION 'INVALID_ROTATION_CAS' USING ERRCODE='P0001';
 END IF;
 IF p_new_digest IS NULL OR p_new_digest !~ '^[0-9a-f]{64}$'
    OR p_new_digest=p_old_digest THEN RAISE EXCEPTION 'INVALID_ROTATION' USING ERRCODE='P0001'; END IF;
 SELECT x.owner_id INTO old_owner FROM auth_l1.sessions x WHERE x.digest_sha256=p_old_digest;
 IF old_owner IS NULL THEN RAISE EXCEPTION 'SESSION_DENIED' USING ERRCODE='P0001'; END IF;
 SELECT * INTO o FROM auth_l1.owners x WHERE x.owner_id=old_owner FOR UPDATE;
 SELECT * INTO s FROM auth_l1.sessions x WHERE x.digest_sha256=p_old_digest FOR UPDATE;
 now_db:=clock_timestamp();
 IF o.state<>'active' OR o.reset_gate<>'open' OR o.session_epoch IS DISTINCT FROM p_epoch
    OR s.status<>'active' OR s.session_epoch IS DISTINCT FROM p_epoch OR s.generation IS DISTINCT FROM p_generation
    OR now_db>=s.idle_expires_at OR now_db>=s.absolute_expires_at THEN
  RAISE EXCEPTION 'ROTATION_CAS_DENIED' USING ERRCODE='P0001';
 END IF;
 new_idle:=LEAST(now_db+make_interval(secs=>s.idle_seconds),s.absolute_expires_at);
 UPDATE auth_l1.sessions SET status='rotated' WHERE digest_sha256=p_old_digest;
 INSERT INTO auth_l1.sessions(digest_sha256,owner_id,session_epoch,generation,status,
  created_at,last_activity_at,idle_expires_at,absolute_expires_at,idle_seconds)
 VALUES(p_new_digest,old_owner,p_epoch,p_generation+1,'active',
  now_db,now_db,new_idle,s.absolute_expires_at,s.idle_seconds);
 RETURN jsonb_build_object('owner_id',old_owner,'epoch',p_epoch,
    'generation',p_generation+1,'idle_expires_at',new_idle,
    'absolute_expires_at',s.absolute_expires_at);
END $$;

CREATE FUNCTION auth_l1.revoke_one(p_digest text,p_epoch bigint) RETURNS boolean
LANGUAGE plpgsql VOLATILE SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE old_owner text; o record; s record; now_db timestamptz;
BEGIN
 IF p_digest IS NULL OR p_digest !~ '^[0-9a-f]{64}$'
    OR p_epoch IS NULL OR p_epoch<0 THEN
  RAISE EXCEPTION 'INVALID_REVOKE_ONE_CAS' USING ERRCODE='P0001';
 END IF;
 SELECT x.owner_id INTO old_owner FROM auth_l1.sessions x WHERE x.digest_sha256=p_digest;
 IF old_owner IS NULL THEN RETURN false; END IF;
 SELECT * INTO o FROM auth_l1.owners x WHERE x.owner_id=old_owner FOR UPDATE;
 SELECT * INTO s FROM auth_l1.sessions x WHERE x.digest_sha256=p_digest FOR UPDATE;
 now_db:=clock_timestamp();
 IF o.session_epoch IS DISTINCT FROM p_epoch OR s.session_epoch IS DISTINCT FROM p_epoch
    OR s.status<>'active' OR now_db>=s.idle_expires_at OR now_db>=s.absolute_expires_at THEN
  RETURN false;
 END IF;
 UPDATE auth_l1.sessions SET status='revoked' WHERE digest_sha256=p_digest;
 RETURN true;
END $$;

CREATE FUNCTION auth_l1.revoke_all(p_owner text,p_epoch bigint) RETURNS bigint
LANGUAGE plpgsql VOLATILE SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE o record; new_epoch bigint;
BEGIN
 IF p_owner IS NULL OR length(btrim(p_owner))=0 OR p_epoch IS NULL OR p_epoch<0 THEN
  RAISE EXCEPTION 'INVALID_REVOKE_ALL_CAS' USING ERRCODE='P0001';
 END IF;
 SELECT * INTO o FROM auth_l1.owners x WHERE x.owner_id=p_owner FOR UPDATE;
 IF NOT FOUND OR o.session_epoch IS DISTINCT FROM p_epoch OR o.session_epoch=9223372036854775807 THEN
  RAISE EXCEPTION 'REVOKE_EPOCH_CAS_DENIED' USING ERRCODE='P0001';
 END IF;
 new_epoch:=p_epoch+1;
 UPDATE auth_l1.owners SET session_epoch=new_epoch,reset_gate='pending_reauth'
  WHERE owner_id=p_owner;
 UPDATE auth_l1.sessions SET status='revoked' WHERE owner_id=p_owner AND status='active';
 RETURN new_epoch;
END $$;

CREATE FUNCTION auth_l1.suspend_owner(p_owner text,p_epoch bigint) RETURNS bigint
LANGUAGE plpgsql VOLATILE SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE o record; new_epoch bigint;
BEGIN
 IF p_owner IS NULL OR length(btrim(p_owner))=0 OR p_epoch IS NULL OR p_epoch<0 THEN
  RAISE EXCEPTION 'INVALID_SUSPEND_CAS' USING ERRCODE='P0001';
 END IF;
 SELECT * INTO o FROM auth_l1.owners x WHERE x.owner_id=p_owner FOR UPDATE;
 IF NOT FOUND OR o.state<>'active' OR o.session_epoch IS DISTINCT FROM p_epoch
    OR o.session_epoch=9223372036854775807 THEN
  RAISE EXCEPTION 'SUSPEND_EPOCH_CAS_DENIED' USING ERRCODE='P0001';
 END IF;
 new_epoch:=p_epoch+1;
 UPDATE auth_l1.owners SET session_epoch=new_epoch,state='suspended',reset_gate='pending_reauth'
 WHERE owner_id=p_owner;
 UPDATE auth_l1.sessions SET status='revoked' WHERE owner_id=p_owner AND status='active';
 RETURN new_epoch;
END $$;

CREATE FUNCTION auth_l1.finish_simulated_reauth(p_owner text,p_epoch bigint)
RETURNS boolean LANGUAGE plpgsql VOLATILE SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE o record;
BEGIN
 IF p_owner IS NULL OR length(btrim(p_owner))=0 OR p_epoch IS NULL OR p_epoch<0 THEN
  RAISE EXCEPTION 'INVALID_REAUTH_CAS' USING ERRCODE='P0001';
 END IF;
 -- ONLY a separately authenticated/trusted reauth service may invoke this.
 -- In BND-DB-01 a distinct synthetic CI role emulates that trust; NO IdP proof exists.
 SELECT * INTO o FROM auth_l1.owners x WHERE x.owner_id=p_owner FOR UPDATE;
 IF NOT FOUND OR o.state<>'active' OR o.session_epoch IS DISTINCT FROM p_epoch
    OR o.reset_gate<>'pending_reauth' THEN
  RAISE EXCEPTION 'REAUTH_GATE_DENIED' USING ERRCODE='P0001';
 END IF;
 UPDATE auth_l1.owners SET reset_gate='open' WHERE owner_id=p_owner;
 RETURN true;
END $$;

-- Narrow function-only app grants; never expose raw tables or public execution.
REVOKE ALL ON ALL TABLES IN SCHEMA auth_l1 FROM PUBLIC,history_app,auth_mapper,auth_sessions,auth_revoker,auth_reauth;
REVOKE ALL ON ALL FUNCTIONS IN SCHEMA auth_l1 FROM PUBLIC;
GRANT USAGE ON SCHEMA auth_l1 TO auth_mapper,auth_sessions,auth_revoker,auth_reauth;
GRANT EXECUTE ON FUNCTION auth_l1.map_identity(text,text) TO auth_mapper;
GRANT EXECUTE ON FUNCTION auth_l1.issue_session(text,bigint,text,integer,integer) TO auth_sessions;
GRANT EXECUTE ON FUNCTION auth_l1.validate_session(text) TO auth_sessions;
GRANT EXECUTE ON FUNCTION auth_l1.fence_owner(text,bigint) TO auth_sessions;
GRANT EXECUTE ON FUNCTION auth_l1.touch_session(text,bigint) TO auth_sessions;
GRANT EXECUTE ON FUNCTION auth_l1.rotate_session(text,text,bigint,integer) TO auth_sessions;
GRANT EXECUTE ON FUNCTION auth_l1.revoke_one(text,bigint) TO auth_sessions;
GRANT EXECUTE ON FUNCTION auth_l1.revoke_all(text,bigint) TO auth_revoker;
GRANT EXECUTE ON FUNCTION auth_l1.suspend_owner(text,bigint) TO auth_revoker;
GRANT EXECUTE ON FUNCTION auth_l1.finish_simulated_reauth(text,bigint) TO auth_reauth;
