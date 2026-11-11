-- 007_scoped_reset_identity_lookup.down.sql — non-destructive.
-- Use -1 -v ON_ERROR_STOP=1 on a disposable CI database.
-- Removes ONLY the 007 lookup function/grant; 003/006 data, roles,
-- existing Gate, Sessions, authorization and operation evidence survive.
REVOKE EXECUTE ON FUNCTION auth_l1.resolve_reset_identity(text,text,text,text,bigint,text)
 FROM auth_reset_lookup;
DROP FUNCTION auth_l1.resolve_reset_identity(text,text,text,text,bigint,text);
REVOKE USAGE ON SCHEMA auth_l1 FROM auth_reset_lookup;
