-- 003_auth_session.down.sql — destructive ONLY in isolated disposable CI DB.
-- No production retention/backups/restoration policy is decided.
DROP SCHEMA auth_l1 CASCADE;
