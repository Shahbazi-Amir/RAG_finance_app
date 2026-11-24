\set ON_ERROR_STOP on
GRANT USAGE ON SCHEMA auth_l1 TO history_app;
INSERT INTO auth_l1.owners(owner_id) VALUES ('test-a'), ('test-b');
INSERT INTO auth_l1.sessions
    (digest_sha256, owner_id, session_epoch, generation, status, created_at,
     last_activity_at, idle_expires_at, absolute_expires_at, idle_seconds)
SELECT repeat(v.key,64), 'test-a', 0, 0, v.status, t.now-v.age * interval '1 second',
       t.now-v.age * interval '1 second', t.now+(120-v.age)*interval '1 second',
       t.now+(500-v.age)*interval '1 second', 120
FROM (VALUES ('a','active',90), ('b','active',121), ('c','active',501),
             ('d','revoked',30), ('e','active',470), ('f','active',90))
     AS v(key,status,age)
CROSS JOIN (SELECT clock_timestamp() AS now) t;
-- Model recent valid activity in the final 120 seconds of the absolute window.
UPDATE auth_l1.sessions SET last_activity_at=clock_timestamp()-interval '45 seconds',
    idle_expires_at=absolute_expires_at WHERE digest_sha256=repeat('e',64);

SET ROLE history_app;
DO $test$
BEGIN
    IF auth_l1.admit_and_renew_staging_session('test-a',repeat('a',64),0,0)
       IS DISTINCT FROM true OR
       auth_l1.admit_and_renew_staging_session('test-a',repeat('e',64),0,0)
       IS DISTINCT FROM true THEN
        RAISE EXCEPTION 'Expected eligible activity to renew';
    END IF;
    IF auth_l1.admit_and_renew_staging_session('test-b',repeat('a',64),0,0)
       OR auth_l1.admit_and_renew_staging_session('test-a',repeat('a',64),0,1)
       OR auth_l1.admit_and_renew_staging_session('test-a',repeat('b',64),0,0)
       OR auth_l1.admit_and_renew_staging_session('test-a',repeat('c',64),0,0)
       OR auth_l1.admit_and_renew_staging_session('test-a',repeat('d',64),0,0) THEN
        RAISE EXCEPTION 'Invalid or expired activity accepted';
    END IF;
END;
$test$;
BEGIN;
SELECT auth_l1.admit_and_renew_staging_session('test-a',repeat('f',64),0,0);
ROLLBACK;
RESET ROLE;
DO $test$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM auth_l1.sessions WHERE digest_sha256=repeat('a',64)
       AND idle_expires_at=last_activity_at+interval '120 seconds'
       AND absolute_expires_at=created_at+interval '500 seconds'
       AND last_activity_at>created_at) THEN
        RAISE EXCEPTION 'Renewal changed session policy';
    END IF;
    IF NOT EXISTS (SELECT 1 FROM auth_l1.sessions WHERE digest_sha256=repeat('e',64)
       AND idle_expires_at=absolute_expires_at AND absolute_expires_at=created_at+interval '500 seconds')
       OR NOT EXISTS (SELECT 1 FROM auth_l1.sessions WHERE digest_sha256=repeat('f',64)
       AND last_activity_at=created_at) THEN
        RAISE EXCEPTION 'Absolute cap or rollback failed';
    END IF;
    IF has_function_privilege('history_app','auth_l1.touch_session(text,bigint)','EXECUTE')
       OR has_table_privilege('history_app','auth_l1.sessions','UPDATE')
       OR has_function_privilege('public','auth_l1.admit_and_renew_staging_session(text,text,bigint,integer)','EXECUTE') THEN
        RAISE EXCEPTION 'Unexpected grant';
    END IF;
END;
$test$;
SELECT 'staging idle renewal SQL boundary PASS';
