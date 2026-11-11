"""CR-DB-01B: scoped read-only identity lookup on disposable PostgreSQL 17.11.

Only synthetic credentials; no API, IdP calls, real Recovery, email or C2.
Existing 66 DB regressions including real 006 rollback races must still run.
"""
import os
import uuid
import unittest
from concurrent.futures import ThreadPoolExecutor

import psycopg
from psycopg.conninfo import conninfo_to_dict
from psycopg.errors import InsufficientPrivilege
from psycopg.rows import dict_row

from src.phase3.storage.postgres import reset_identity_lookup
from src.phase3.storage.postgres import reset_c1 as reset
from src.phase3.storage.postgres import auth_session as auth
from test_auth_session import db, owner, issue, digest
from test_reset_c1 import mint, reset_db, run, states

def lookup_db():
    if os.getenv("CI")!="true":
        raise RuntimeError("LOOKUP_CI_ONLY")
    dsn=os.environ["AUTH_RESET_LOOKUP_DSN"]
    params=conninfo_to_dict(dsn)
    if not (params.get("host")=="127.0.0.1" and params.get("port")=="5432"
            and params.get("dbname")=="history_ci"
            and params.get("user")=="auth_reset_lookup"
            and set(params).issubset({"host","port","dbname","user","password","connect_timeout"})):
        raise RuntimeError("LOOKUP_UNSAFE_TARGET")
    return psycopg.connect(dsn,autocommit=True,row_factory=dict_row)

def linked_owner():
    oid=owner()["owner_id"]
    with db("MIG") as c:
        identity=c.execute(
            "SELECT issuer,subject FROM auth_l1.identity_links WHERE owner_id=%s",
            (oid,)).fetchone()
    assert identity is not None
    return oid,identity

def scoped(c,cap,oid,issuer,*,kind=None,epoch=None):
    return reset_identity_lookup.resolve(c,cap.opaque,trusted_owner_id=oid,
        kind=cap.kind if kind is None else kind,
        expected_epoch=cap.expected_epoch if epoch is None else epoch,
        expected_issuer=issuer)

def lookup_raw(c,digest_key,oid,kind,purpose,epoch,issuer):
    with c.transaction():
        return c.execute("SELECT auth_l1.resolve_reset_identity(%s,%s,%s,%s,%s,%s) AS identity",
            (digest_key,oid,kind,purpose,epoch,issuer)).fetchone()["identity"]

class ScopedResetIdentityLookup(unittest.TestCase):
    def test_LKP01_one_linked_pair_only_read_only_transaction_and_digest(self):
        oid,identity=linked_owner()
        cap=mint(oid)
        with lookup_db() as c:
            with c.transaction():
                c.execute("SET TRANSACTION READ ONLY")
                pair=scoped(c,cap,oid,identity["issuer"])
                self.assertEqual(pair,dict(identity))
                self.assertEqual(set(pair),{"issuer","subject"})
        self.assertNotIn(cap.opaque,str(pair))
        o,_,ops,consumed=states(oid,cap)
        self.assertEqual((o["session_epoch"],o["reset_gate"]),(0,"open"))
        self.assertEqual(ops,[])
        self.assertIsNone(consumed["consumed_at"])
        with db("MIG") as c:
            n=c.execute("SELECT count(*) AS n FROM auth_l1.identity_links WHERE owner_id=%s",(oid,)).fetchone()["n"]
            self.assertEqual(n,1)

    def test_LKP02_wrong_owner_and_wrong_digest_never_disclose_other_pair(self):
        a,ai=linked_owner(); b,bi=linked_owner()
        cap=mint(a)
        with lookup_db() as c:
            self.assertEqual(scoped(c,cap,a,ai["issuer"]),dict(ai))
            with self.assertRaisesRegex(psycopg.Error,"RESET_IDENTITY_LOOKUP_DENIED"):
                scoped(c,cap,b,bi["issuer"])
            with self.assertRaisesRegex(psycopg.Error,"RESET_IDENTITY_LOOKUP_DENIED"):
                lookup_raw(c,"a"*64,a,reset.KIND_RECOVERY,reset.PURPOSE,0,ai["issuer"])
        self.assertEqual(states(a)[0]["session_epoch"],0)
        self.assertEqual(states(b)[0]["session_epoch"],0)

    def test_LKP03_issuer_kind_purpose_epoch_and_null_sql_inputs_fail_closed(self):
        oid,ident=linked_owner(); cap=mint(oid)
        key=reset.digest_authorization(cap.opaque)
        good=(key,oid,reset.KIND_RECOVERY,reset.PURPOSE,0,ident["issuer"])
        invalid=[
            (key,oid,reset.KIND_RECOVERY,reset.PURPOSE,0,"https://wrong.synthetic.invalid"),
            (key,oid,reset.KIND_AUTHENTICATED,reset.PURPOSE,0,ident["issuer"]),
            (key,oid,reset.KIND_RECOVERY,"WRONG_PURPOSE",0,ident["issuer"]),
            (key,oid,reset.KIND_RECOVERY,reset.PURPOSE,1,ident["issuer"]),
            (None,oid,reset.KIND_RECOVERY,reset.PURPOSE,0,ident["issuer"]),
            ("invalid",oid,reset.KIND_RECOVERY,reset.PURPOSE,0,ident["issuer"]),
            (key,None,reset.KIND_RECOVERY,reset.PURPOSE,0,ident["issuer"]),
            (key,oid,None,reset.PURPOSE,0,ident["issuer"]),
            (key,oid,reset.KIND_RECOVERY,None,0,ident["issuer"]),
            (key,oid,reset.KIND_RECOVERY,reset.PURPOSE,None,ident["issuer"]),
            (key,oid,reset.KIND_RECOVERY,reset.PURPOSE,0,None),
            (key,oid,reset.KIND_RECOVERY,reset.PURPOSE,0,"")
        ]
        with lookup_db() as c:
            self.assertEqual(lookup_raw(c,*good),dict(ident))
            for args in invalid:
                with self.subTest(null_or_wrong=args.index(None) if None in args else "mismatch"):
                    with self.assertRaisesRegex(psycopg.Error,"RESET_IDENTITY_LOOKUP_DENIED"):
                        lookup_raw(c,*args)
        self.assertIsNone(states(oid,cap)[3]["consumed_at"])

    def test_LKP04_replay_after_real_c1_commit_denied(self):
        oid,ident=linked_owner(); cap=mint(oid)
        with lookup_db() as c: self.assertEqual(scoped(c,cap,oid,ident["issuer"]),dict(ident))
        receipt=run(cap)
        self.assertEqual(receipt["status"],"REVOKED_PENDING_IDP")
        with lookup_db() as c:
            with self.assertRaisesRegex(psycopg.Error,"RESET_IDENTITY_LOOKUP_DENIED"):
                scoped(c,cap,oid,ident["issuer"])
        o,_,ops,consumed=states(oid,cap)
        self.assertEqual((o["session_epoch"],o["reset_gate"]),(1,"pending_reauth"))
        self.assertEqual(len(ops),1)
        self.assertIsNotNone(consumed["consumed_at"])

    def test_LKP05_expired_unconsumed_authorization_denied_by_pg_clock(self):
        oid,ident=linked_owner(); cap=mint(oid)
        # Synthetic CI migrator fixture: expire a stored digest without any wait.
        with db("MIG") as c:
            c.execute("""UPDATE auth_l1.reset_c1_authorizations
                SET expires_at=clock_timestamp()-interval '1 second'
                WHERE authorization_sha256=%s""",(reset.digest_authorization(cap.opaque),))
        with lookup_db() as c:
            with self.assertRaisesRegex(psycopg.Error,"RESET_IDENTITY_LOOKUP_DENIED"):
                scoped(c,cap,oid,ident["issuer"])
        with reset_db() as c:
            with self.assertRaises(psycopg.Error):
                with c.transaction():
                    reset.commit_c1(c,cap.opaque,owner_id=oid,kind=cap.kind,expected_epoch=0)
        self.assertEqual(states(oid)[0]["session_epoch"],0)
        self.assertIsNone(states(oid,cap)[3]["consumed_at"])

    def test_LKP06_lookup_then_epoch_change_prevents_c1(self):
        oid,ident=linked_owner(); cap=mint(oid)
        with lookup_db() as c: self.assertEqual(scoped(c,cap,oid,ident["issuer"]),dict(ident))
        with db("REVOKER") as c: self.assertEqual(auth.revoke_all(c,oid,0),1)
        with lookup_db() as c:
            with self.assertRaisesRegex(psycopg.Error,"RESET_IDENTITY_LOOKUP_DENIED"):
                scoped(c,cap,oid,ident["issuer"])
        with reset_db() as c:
            with self.assertRaises(psycopg.Error):
                with c.transaction(): reset.commit_c1(c,cap.opaque,owner_id=oid,kind=cap.kind,expected_epoch=0)
        o,_,ops,consumed=states(oid,cap)
        self.assertEqual((o["session_epoch"],o["reset_gate"]),(1,"pending_reauth"))
        self.assertEqual(ops,[])
        self.assertIsNone(consumed["consumed_at"])

    def test_LKP07_lookup_then_synthetic_fixture_invalidation_blocks_c1(self):
        oid,ident=linked_owner(); cap=mint(oid)
        with lookup_db() as c: self.assertEqual(scoped(c,cap,oid,ident["issuer"]),dict(ident))
        # 006 defines no production cancellation API. This is CI-only forced
        # invalidation of the authority's expiry, NOT proof of real revocation.
        with db("MIG") as c:
            c.execute("""UPDATE auth_l1.reset_c1_authorizations
                SET expires_at=clock_timestamp() WHERE authorization_sha256=%s""",
                (reset.digest_authorization(cap.opaque),))
        with lookup_db() as c:
            with self.assertRaisesRegex(psycopg.Error,"RESET_IDENTITY_LOOKUP_DENIED"):
                scoped(c,cap,oid,ident["issuer"])
        with reset_db() as c:
            with self.assertRaises(psycopg.Error):
                with c.transaction(): reset.commit_c1(c,cap.opaque,owner_id=oid,kind=cap.kind,expected_epoch=0)
        self.assertEqual(states(oid)[0]["reset_gate"],"open")
        self.assertEqual(states(oid)[2],[])

    def test_LKP08_suspended_and_pending_gate_rejected_without_mutation(self):
        oid,ident=linked_owner(); cap=mint(oid)
        with db("MIG") as c:
            c.execute("UPDATE auth_l1.owners SET state='suspended' WHERE owner_id=%s",(oid,))
        with lookup_db() as c:
            with self.assertRaisesRegex(psycopg.Error,"RESET_IDENTITY_LOOKUP_DENIED"):
                scoped(c,cap,oid,ident["issuer"])
        other,other_ident=linked_owner(); other_cap=mint(other)
        with db("REVOKER") as c:
            self.assertEqual(auth.revoke_all(c,other,0),1)
        with lookup_db() as c:
            with self.assertRaisesRegex(psycopg.Error,"RESET_IDENTITY_LOOKUP_DENIED"):
                scoped(c,other_cap,other,other_ident["issuer"])
        self.assertEqual(states(oid,cap)[0]["state"],"suspended")
        self.assertIsNone(states(oid,cap)[3]["consumed_at"])

    def test_LKP09_authenticated_kind_binds_active_session_at_read_time(self):
        oid,ident=linked_owner(); session=issue(oid)
        cap=mint(oid,kind=reset.KIND_AUTHENTICATED,
                 session=digest(session.opaque),gen=0)
        with lookup_db() as c:
            self.assertEqual(scoped(c,cap,oid,ident["issuer"]),dict(ident))
            with self.assertRaisesRegex(psycopg.Error,"RESET_IDENTITY_LOOKUP_DENIED"):
                scoped(c,cap,oid,ident["issuer"],kind=reset.KIND_RECOVERY)
        with db("SESSION") as c:
            rotated=auth.rotate(c,session.opaque,0,0)
        self.assertEqual(rotated.generation,1)
        with lookup_db() as c:
            with self.assertRaisesRegex(psycopg.Error,"RESET_IDENTITY_LOOKUP_DENIED"):
                scoped(c,cap,oid,ident["issuer"])
        self.assertIsNone(states(oid,cap)[3]["consumed_at"])

    def test_LKP10_lookup_role_exact_grants_and_existing_roles_unchanged(self):
        oid,ident=linked_owner(); cap=mint(oid)
        key=reset.digest_authorization(cap.opaque)
        signature="auth_l1.resolve_reset_identity(text,text,text,text,bigint,text)"
        with lookup_db() as c:
            flags=c.execute("""SELECT rolsuper,rolbypassrls,rolcreatedb,rolcreaterole,
                  rolinherit FROM pg_roles WHERE rolname=current_user""").fetchone()
            self.assertFalse(any(flags.values()))
            self.assertEqual(scoped(c,cap,oid,ident["issuer"]),dict(ident))
            for sql in (
                "SELECT * FROM auth_l1.identity_links",
                "SELECT * FROM auth_l1.reset_c1_authorizations",
                "SELECT * FROM auth_l1.reset_c1_operations",
                "SELECT * FROM auth_l1.owners",
                "SELECT * FROM auth_l1.sessions",
                "SELECT * FROM history_l1.conversations",
                "CREATE TABLE auth_l1.illicit_lookup(x integer)",
                "SELECT auth_l1.map_identity('a','b')",
                "SELECT auth_l1.issue_session('bad',0,repeat('a',64),10,60)",
                "SELECT auth_l1.revoke_all('bad',0)",
                "SELECT auth_l1.finish_simulated_reauth('bad',0)",
                "SELECT auth_l1.execute_reset_c1(repeat('a',64),'bad','RECOVERY','CONTROLLED_RESET_C1',0,'00000000-0000-4000-8000-000000000001'::uuid)",
                "SELECT auth_l1.issue_reset_c1_authorization(repeat('a',64),'bad','RECOVERY','CONTROLLED_RESET_C1',0,1,NULL,NULL)"
            ):
                with self.assertRaises(InsufficientPrivilege):
                    with c.transaction(): c.execute(sql)
        for role in ("MAP","SESSION","REVOKER","REAUTH"):
            with db(role) as c:
                with self.assertRaises(InsufficientPrivilege):
                    with c.transaction(): c.execute(
                        "SELECT "+signature.split("(")[0]+"(%s,%s,%s,%s,%s,%s)",
                        (key,oid,cap.kind,reset.PURPOSE,0,ident["issuer"]))
        for role in ("ISSUER","EXEC"):
            with reset_db(role) as c:
                with self.assertRaises(InsufficientPrivilege):
                    with c.transaction():
                        c.execute("SELECT auth_l1.resolve_reset_identity(%s,%s,%s,%s,%s,%s)",
                            (key,oid,cap.kind,reset.PURPOSE,0,ident["issuer"]))
        with db("MIG") as admin:
            pro=admin.execute("""SELECT p.prosecdef,p.proconfig FROM pg_proc p
               WHERE p.oid=%s::regprocedure""",(signature,)).fetchone()
            self.assertTrue(pro["prosecdef"])
            self.assertIn("search_path=pg_catalog",pro["proconfig"])
            self.assertTrue(admin.execute("SELECT has_function_privilege('auth_reset_lookup',%s,'EXECUTE') AS yes",(signature,)).fetchone()["yes"])
            self.assertFalse(admin.execute("""SELECT EXISTS(
                SELECT 1 FROM pg_proc p CROSS JOIN LATERAL aclexplode(p.proacl) acl
                WHERE p.oid=%s::regprocedure AND acl.grantee=0
                AND acl.privilege_type='EXECUTE') AS yes""",(signature,)).fetchone()["yes"])
            for table in ("identity_links","reset_c1_authorizations","reset_c1_operations","owners","sessions"):
                obj="auth_l1."+table
                rights=admin.execute("""SELECT relrowsecurity,relforcerowsecurity FROM pg_class
                    WHERE oid=%s::regclass""",(obj,)).fetchone()
                self.assertTrue(all(rights.values()))
                self.assertFalse(admin.execute(
                    "SELECT has_table_privilege('auth_reset_lookup',%s,'SELECT') AS yes",
                    (obj,)).fetchone()["yes"])
            self.assertFalse(admin.execute(
                "SELECT has_schema_privilege('auth_reset_lookup','history_l1','USAGE') AS yes"
            ).fetchone()["yes"])

    def test_LKP11_no_identity_link_refuses_even_with_valid_owner_authorization(self):
        oid="synthetic_no_link_"+uuid.uuid4().hex
        with db("MIG") as c:
            c.execute("INSERT INTO auth_l1.owners(owner_id) VALUES(%s)",(oid,))
        cap=mint(oid)
        with lookup_db() as c:
            with self.assertRaisesRegex(psycopg.Error,"RESET_IDENTITY_LOOKUP_DENIED"):
                scoped(c,cap,oid,"https://synthetic.invalid/any")
        self.assertIsNone(states(oid,cap)[3]["consumed_at"])

    def test_LKP12_owner_id_and_operation_id_are_not_lookup_authority(self):
        oid,ident=linked_owner()
        with lookup_db() as c:
            for opaque in ("","raw-too-short",None):
                with self.assertRaises(ValueError):
                    reset_identity_lookup.resolve(c,opaque,trusted_owner_id=oid,
                        kind=reset.KIND_RECOVERY,expected_epoch=0,
                        expected_issuer=ident["issuer"])
            for unauthorized_digest in (reset.digest_authorization(str(uuid.uuid4())),"c"*64):
                with self.assertRaisesRegex(psycopg.Error,"RESET_IDENTITY_LOOKUP_DENIED"):
                    lookup_raw(c,unauthorized_digest,oid,reset.KIND_RECOVERY,reset.PURPOSE,0,ident["issuer"])
        self.assertEqual(states(oid)[0]["session_epoch"],0)

    def test_LKP13_nonlocking_snapshot_can_be_stale_during_uncommitted_c1(self):
        oid,ident=linked_owner(); cap=mint(oid)
        with reset_db() as executor:
            with executor.transaction():
                result=reset.commit_c1(executor,cap.opaque,owner_id=oid,
                    kind=cap.kind,expected_epoch=0)
                self.assertEqual(result["revoked_epoch"],1)
                # A separate plain lookup does not block on C1's Owner FOR
                # UPDATE; it sees the earlier committed MVCC snapshot.
                with ThreadPoolExecutor(max_workers=1) as pool:
                    def read():
                        with lookup_db() as look:
                            return scoped(look,cap,oid,ident["issuer"])
                    future=pool.submit(read)
                    self.assertEqual(future.result(timeout=6),dict(ident))
        with lookup_db() as c:
            with self.assertRaisesRegex(psycopg.Error,"RESET_IDENTITY_LOOKUP_DENIED"):
                scoped(c,cap,oid,ident["issuer"])
        self.assertEqual(states(oid)[0]["reset_gate"],"pending_reauth")
