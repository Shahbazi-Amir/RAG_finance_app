"""Signed transaction integration test for an isolated disposable database."""
from hashlib import sha256
import secrets

import psycopg
from psycopg.rows import dict_row

from proof_fixture import AUDIENCE, ISSUER, KID, FakeBFFSigner
from src.phase3.auth.service_proof import BFFServiceVerifier, TrustRejected
from src.phase3.auth.transactional_admission import protected_transaction
from src.phase3.storage.postgres.service_replay import PostgresDurableReplayStore


def main():
    signer = FakeBFFSigner()
    verifier = BFFServiceVerifier(issuer=ISSUER, audience=AUDIENCE, public_keys={KID: signer.public_pem})
    session = secrets.token_urlsafe(32)
    digest = sha256(session.encode()).hexdigest()
    conn = psycopg.connect("host=127.0.0.1 dbname=postgres user=postgres",
                           autocommit=True, row_factory=dict_row, connect_timeout=5)
    with conn:
        conn.execute("INSERT INTO auth_l1.owners(owner_id) VALUES ('owner-a'),('owner-b')")
        conn.execute(
            """INSERT INTO auth_l1.sessions VALUES
               (%s,'owner-a',0,0,'active',now()-interval '90 seconds',
                now()-interval '90 seconds',now()+interval '30 seconds',
                now()+interval '410 seconds',120)""", (digest,))

        def deadlines():
            conn.execute("RESET ROLE")
            try:
                return conn.execute("SELECT last_activity_at, idle_expires_at, absolute_expires_at "
                                    "FROM auth_l1.sessions WHERE digest_sha256=%s", (digest,)).fetchone()
            finally:
                conn.execute("SET ROLE history_app")

        def signed(owner="owner-a", method="POST", path=b"/v1/messages"):
            return signer.sign(signer.claims(owner_id=owner, session_ref=session, method=method, path=path))

        def request(token, method="POST", path=b"/v1/messages", renew=True, rollback=False):
            with protected_transaction(conn, verifier=verifier, replay_store=PostgresDurableReplayStore(),
                                       compact_assertion=token, method=method, raw_path=path,
                                       raw_query=b"", body=b"{}", renew_staging_idle=renew) as owner:
                assert owner == "owner-a"
                if rollback:
                    raise ValueError("fixture action failure")

        before = deadlines()
        request(signed(method="GET", path=b"/v1/conversations"),
                method="GET", path=b"/v1/conversations", renew=False)
        assert deadlines() == before
        token = signed()
        request(token)
        after = deadlines()
        assert after["last_activity_at"] > before["last_activity_at"]
        assert after["idle_expires_at"] > before["idle_expires_at"]
        assert after["absolute_expires_at"] == before["absolute_expires_at"]
        for denied in (lambda: request(token),
                       lambda: request(signed("owner-b")),
                       lambda: request("forged"),
                       lambda: request(signed(), rollback=True),
                       lambda: request(signed(method="GET"), method="GET")):
            try:
                denied()
            except TrustRejected:
                assert deadlines() == after
            else:
                raise AssertionError("INVALID_ACTIVITY_ACCEPTED")
        print("signed_send_renewed; safe_get_unchanged; replay/forgery/wrong-owner/GET-renew denied; failed action rolled back")


if __name__ == "__main__":
    main()
