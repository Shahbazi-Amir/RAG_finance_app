"""BND-DB-01 restricted-role NULL CAS regression and Owner-only fence proof.

CI-only PostgreSQL 17.11, entirely synthetic. No raw session tokens printed.
"""
import hashlib
import unittest
from concurrent.futures import ThreadPoolExecutor
from test_auth_session import db, owner, issue, observed_wait, digest
import auth_session as auth
import psycopg

class NullCasAndFence(unittest.TestCase):
    def test_BND13_null_reauth_epoch_denied_sql_and_wrapper_state_unchanged(self):
        oid=owner()["owner_id"]
        session=issue(oid)
        with db("REVOKER") as c:
            self.assertEqual(auth.revoke_all(c,oid,0),1)

        def state():
            with db("MIG") as m:
                row=m.execute("SELECT owner_id,state,session_epoch,reset_gate FROM auth_l1.owners WHERE owner_id=%s",(oid,)).fetchone()
                sessions=m.execute("SELECT digest_sha256,status,session_epoch,generation,created_at,last_activity_at,idle_expires_at,absolute_expires_at FROM auth_l1.sessions WHERE owner_id=%s ORDER BY digest_sha256",(oid,)).fetchall()
                return row,sessions
        before=state()
        self.assertEqual(before[0]["reset_gate"],"pending_reauth")
        with db("REAUTH") as c:
            # Direct restricted-role SQL, not only Python validation.
            with self.assertRaisesRegex(psycopg.Error,"INVALID_REAUTH_CAS"):
                c.execute("SELECT auth_l1.finish_simulated_reauth(%s,NULL::bigint)",(oid,))
            with self.assertRaisesRegex(psycopg.Error,"INVALID_REAUTH_CAS"):
                auth.finish_simulated_reauth(c,oid,None)
            with self.assertRaisesRegex(psycopg.Error,"INVALID_REAUTH_CAS"):
                auth.finish_simulated_reauth(c,oid,-1)
            with self.assertRaisesRegex(psycopg.Error,"REAUTH_GATE_DENIED"):
                auth.finish_simulated_reauth(c,oid,0)
        self.assertEqual(state(),before,"NULL/stale epochs must not change epoch/gate/sessions")
        with db("REAUTH") as c:
            self.assertTrue(auth.finish_simulated_reauth(c,oid,1))
        after=state()
        self.assertEqual(after[0]["session_epoch"],1)
        self.assertEqual(after[0]["reset_gate"],"open")
        self.assertEqual(after[1],before[1],"reauth releases gate, never restores old sessions")
        with db() as c:
            self.assertIsNone(auth.inspect(c,session.opaque))

    def test_BND14_all_cas_null_and_out_of_domain_fail_closed(self):
        oid=owner()["owner_id"]
        session=issue(oid)
        old_digest=digest(session.opaque)
        other_digest=hashlib.sha256(b"synthetic_new_opaque_from_test").hexdigest()
        def snapshot():
            with db("MIG") as m:
                o=m.execute("SELECT owner_id,state,session_epoch,reset_gate FROM auth_l1.owners WHERE owner_id=%s",(oid,)).fetchone()
                rows=m.execute("SELECT digest_sha256,status,generation,session_epoch,last_activity_at,idle_expires_at,absolute_expires_at FROM auth_l1.sessions WHERE owner_id=%s ORDER BY digest_sha256",(oid,)).fetchall()
                return o,rows
        before=snapshot()
        # Both direct SQL and wrapper calls (where a Python wrapper exists).
        with db() as c:
            denial=[
                ("SELECT auth_l1.issue_session(%s,NULL::bigint,%s,10,30)",(oid,other_digest)),
                ("SELECT auth_l1.issue_session(%s,-1,%s,10,30)",(oid,other_digest)),
                ("SELECT auth_l1.issue_session(%s,0,%s,NULL::integer,30)",(oid,other_digest)),
                ("SELECT auth_l1.issue_session(%s,0,%s,10,NULL::integer)",(oid,other_digest)),
                ("SELECT auth_l1.issue_session(%s,0,%s,-1,30)",(oid,other_digest)),
                ("SELECT auth_l1.issue_session(%s,0,%s,10,-1)",(oid,other_digest)),
                ("SELECT auth_l1.touch_session(%s,NULL::bigint)",(old_digest,)),
                ("SELECT auth_l1.touch_session(%s,-1)",(old_digest,)),
                ("SELECT auth_l1.rotate_session(%s,%s,NULL::bigint,0)",(old_digest,other_digest)),
                ("SELECT auth_l1.rotate_session(%s,%s,0,NULL::integer)",(old_digest,other_digest)),
                ("SELECT auth_l1.rotate_session(%s,%s,0,-1)",(old_digest,other_digest)),
                ("SELECT auth_l1.rotate_session(%s,%s,0,2147483647)",(old_digest,other_digest)),
                ("SELECT auth_l1.revoke_one(%s,NULL::bigint)",(old_digest,)),
                ("SELECT auth_l1.revoke_one(%s,-1)",(old_digest,)),
                ("SELECT auth_l1.fence_owner(%s,NULL::bigint)",(oid,)),
                ("SELECT auth_l1.fence_owner(%s,-1)",(oid,)),
            ]
            for sql,params in denial:
                with self.subTest(sql=sql):
                    with self.assertRaises(psycopg.Error): c.execute(sql,params)
            for fn in (
                lambda:auth.issue(c,oid,None,idle_seconds=10,absolute_seconds=30),
                lambda:auth.touch(c,session.opaque,None),
                lambda:auth.rotate(c,session.opaque,None,0),
                lambda:auth.rotate(c,session.opaque,0,None),
                lambda:auth.revoke_one(c,session.opaque,None),
                lambda:auth.fence_owner(c,oid,None),
            ):
                with self.assertRaises(psycopg.Error): fn()
        with db("REVOKER") as c:
            for sql,params in [
                ("SELECT auth_l1.revoke_all(%s,NULL::bigint)",(oid,)),
                ("SELECT auth_l1.revoke_all(%s,-1)",(oid,)),
                ("SELECT auth_l1.suspend_owner(%s,NULL::bigint)",(oid,)),
                ("SELECT auth_l1.suspend_owner(%s,-1)",(oid,)),
            ]:
                with self.subTest(sql=sql):
                    with self.assertRaises(psycopg.Error): c.execute(sql,params)
            for fn in (
                lambda:auth.revoke_all(c,oid,None),
                lambda:auth.suspend_owner(c,oid,None),
            ):
                with self.assertRaises(psycopg.Error): fn()
        self.assertEqual(snapshot(),before,"Invalid CAS calls must not mutate owners or sessions")
        with db() as c:
            self.assertTrue(auth.fence_owner(c,oid,0))
            self.assertEqual(auth.inspect(c,session.opaque)["owner_id"],oid)

    def test_BND15_fence_owner_outer_transaction_lock_and_session_gap(self):
        oid=owner()["owner_id"]
        prior=issue(oid)
        second=issue(oid)

        def revoker():
            with db("REVOKER") as c:
                c.execute("SELECT set_config('application_name',%s,false)",("bnd_fence_outer_lock",))
                return auth.revoke_all(c,oid,0)

        # Caller retains owner FOR SHARE lock while outer transaction remains open.
        with ThreadPoolExecutor(max_workers=1) as workers:
            with db() as conn:
                with conn.transaction():
                    self.assertTrue(auth.fence_owner(conn,oid,0))
                    future=workers.submit(revoker)
                    observed_wait(["bnd_fence_outer_lock"])  # actual PG lock wait, not sleep-based sequencing
                    self.assertEqual(auth.inspect(conn,prior.opaque)["owner_id"],oid)
                    self.assertEqual(auth.inspect(conn,second.opaque)["owner_id"],oid)
                    # External revoke-all must not commit while owner lock held.
                    self.assertFalse(future.done())
                # outer transaction COMMIT releases the FOR SHARE lock
            self.assertEqual(future.result(timeout=12),1)
        with db() as c:
            self.assertFalse(auth.fence_owner(c,oid,0))
            self.assertIsNone(auth.inspect(c,prior.opaque))

        # Prove Owner fence ALONE does not check particular session status:
        other=owner()["owner_id"]
        one=issue(other)
        two=issue(other)
        with db() as c:
            self.assertTrue(auth.revoke_one(c,one.opaque,0))
            self.assertTrue(auth.fence_owner(c,other,0))
            self.assertIsNone(auth.inspect(c,one.opaque))
            self.assertIsNotNone(auth.inspect(c,two.opaque))
            rotated=auth.rotate(c,two.opaque,0,0)
            self.assertTrue(auth.fence_owner(c,other,0))
            self.assertIsNone(auth.inspect(c,two.opaque))
            self.assertIsNotNone(auth.inspect(c,rotated.opaque))
        # Expiry is also distinct: no Owner gate change required.
        with db("MIG") as m:
            m.execute("""UPDATE auth_l1.sessions
                SET idle_expires_at=clock_timestamp()-interval '1 second',
                    last_activity_at=clock_timestamp()-interval '2 seconds',
                    created_at=clock_timestamp()-interval '3 seconds'
                WHERE digest_sha256=%s""",(digest(rotated.opaque),))
        with db() as c:
            self.assertTrue(auth.fence_owner(c,other,0))
            self.assertIsNone(auth.inspect(c,rotated.opaque))
