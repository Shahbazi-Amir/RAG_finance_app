-- 004_session_aware_fence.down.sql. NON-destructive: removes only 004 routine.
-- Safe for seeded disposable test DB; no 003/Owner/Session/History data deleted.
REVOKE ALL ON FUNCTION auth_l1.admit_session_fenced(text,text,bigint,integer) FROM auth_sessions;
DROP FUNCTION auth_l1.admit_session_fenced(text,text,bigint,integer);
