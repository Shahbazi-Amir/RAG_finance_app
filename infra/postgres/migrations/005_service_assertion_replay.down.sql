-- 005_service_assertion_replay.down.sql: removes replay records on disposable CI only.
-- Not restoration; no preexisting History / Owner / Session artifacts are changed.
REVOKE EXECUTE ON FUNCTION auth_l1.admit_session_fenced(text,text,bigint,integer) FROM auth_trust_api;
DROP FUNCTION auth_l1.consume_service_assertion(text,bigint);
DROP FUNCTION auth_l1.purge_expired_service_assertions(integer);
DROP TABLE auth_l1.service_assertion_replays;
REVOKE USAGE ON SCHEMA auth_l1 FROM auth_trust_api,auth_replay_cleaner;
