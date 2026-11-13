"""Real ephemeral TLS client certificate + signed BFF Bootstrap -> Keycloak 26.8.2
Code+PKCE -> 009 Pending/ACK. Only local PG17 and synthetic identities.
No production Next, real cookie delivery, external IdP, C2 or migration changes.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Thread, Lock, Barrier
from urllib.parse import urlsplit
import ipaddress
import json
import os
import secrets
import sqlite3
import ssl
import sys
import time
import unittest
import uuid

import httpx
import jwt
import psycopg
from psycopg.rows import dict_row
from cryptography import x509
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID, ExtendedKeyUsageOID

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from initial_oidc_harness import DisposableKeycloak
from src.phase3.auth.initial_oidc_login import InitialChallenge
from src.phase3.auth.bootstrap_oidc import BootstrapDenied, BootstrapOIDC, PATH_ROOT
from src.phase3.storage.postgres import auth_session


def cert_bundle(folder):
    """Ephemeral CA, server and BFF certificates; no keys/artifacts saved."""
    now = datetime.now(timezone.utc)
    ca_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    ca_name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "Synthetic Login CI CA")])
    ca = (x509.CertificateBuilder().subject_name(ca_name).issuer_name(ca_name)
          .public_key(ca_key.public_key()).serial_number(x509.random_serial_number())
          .not_valid_before(now - timedelta(days=1))
          .not_valid_after(now + timedelta(days=1))
          .add_extension(x509.BasicConstraints(ca=True, path_length=0), critical=True)
          .add_extension(x509.KeyUsage(digital_signature=True, content_commitment=False,
                        key_encipherment=False, data_encipherment=False,
                        key_agreement=False, key_cert_sign=True, crl_sign=True,
                        encipher_only=False, decipher_only=False), critical=True)
          .add_extension(x509.SubjectKeyIdentifier.from_public_key(
                        ca_key.public_key()), critical=False)
          .sign(ca_key, hashes.SHA256()))
    def pem_cert(cert):
        return cert.public_bytes(serialization.Encoding.PEM)
    def save(name, data):
        p = Path(folder) / name
        p.write_bytes(data)
        return str(p)
    ca_path = save("ca.pem", pem_cert(ca))
    outputs = []
    for kind, eku in (("server", ExtendedKeyUsageOID.SERVER_AUTH),
                      ("client", ExtendedKeyUsageOID.CLIENT_AUTH)):
        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        subject = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, kind + "-synthetic")])
        builder = (x509.CertificateBuilder().subject_name(subject).issuer_name(ca_name)
                   .public_key(key.public_key()).serial_number(x509.random_serial_number())
                   .not_valid_before(now - timedelta(days=1))
                   .not_valid_after(now + timedelta(days=1))
                   .add_extension(x509.ExtendedKeyUsage([eku]), critical=False)
                   .add_extension(x509.AuthorityKeyIdentifier.from_issuer_public_key(
                       ca_key.public_key()), critical=False)
                   .add_extension(x509.SubjectKeyIdentifier.from_public_key(
                       key.public_key()), critical=False))
        if kind == "server":
            builder = builder.add_extension(
                x509.SubjectAlternativeName([x509.IPAddress(ipaddress.ip_address("127.0.0.1"))]),
                critical=False)
        cert = builder.sign(ca_key, hashes.SHA256())
        cert_path = save(kind + ".pem", pem_cert(cert))
        key_path = save(kind + ".key", key.private_bytes(
            serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption()))
        outputs.append((cert_path, key_path, cert.public_bytes(serialization.Encoding.DER)))
    return ca_path, outputs[0], outputs[1]


class PrivateHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        size = self.headers.get("Content-Length", "")
        if not size.isdecimal() or int(size) > 8192:
            self.send_error(413)
            return
        raw = self.rfile.read(int(size))
        try:
            status, result = self.server.app.handle(
                peer_der=self.connection.getpeercert(binary_form=True),
                authorization=self.headers.get("Authorization", ""),
                method="POST", path=urlsplit(self.path).path, raw_body=raw)
        except BootstrapDenied as e:
            status, result = e.status, {"error": "BOOTSTRAP_DENIED"}
        except Exception:
            status, result = 503, {"error": "TEMPORARILY_UNAVAILABLE"}
        body = json.dumps(result, default=str, sort_keys=True).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


class BFFFixture:
    """Real client TLS, independent RSA signer and durable synthetic alias DB."""
    def __init__(self, server_url, cert, key, ca, sqlite_path, alias_key):
        self.url, self.cert, self.key, self.ca = server_url, cert, key, ca
        self.key_rsa = key
        self.alias_db = sqlite_path
        self.alias_key = alias_key
        with sqlite3.connect(self.alias_db) as db:
            db.execute("CREATE TABLE IF NOT EXISTS aliases (alias TEXT PRIMARY KEY, cipher BLOB)")
            db.commit()

    def proof(self, op, payload, *, tamper=False):
        body = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        now = int(time.time())
        claims = {
            "iss": "urn:rag-finance:synthetic-bootstrap",
            "aud": "urn:rag-finance:api:bootstrap-ci", "purpose": "initial-oidc-bootstrap-v1",
            "iat": now, "nbf": now, "exp": now + 25,
            "jti": secrets.token_urlsafe(24), "method": "POST",
            "raw_path_sha256": sha256((PATH_ROOT + op).encode()).hexdigest(),
            "raw_query_sha256": sha256(b"").hexdigest(),
            "body_sha256": sha256(body).hexdigest(),
            "body_len": len(body), "attempt_id": payload["attempt_id"],
            "initiator_sha256": payload["initiator_sha256"],
        }
        if tamper:
            claims["purpose"] = "history-session-not-bootstrap"
        return jwt.encode(claims, self.signer, algorithm="RS256",
                          headers={"typ": "JWT", "kid": "ci-bootstrap-kid"})

    def post(self, op, payload, *, proof=None, cert=True, tamper=False):
        token = proof or self.proof(op, payload, tamper=tamper)
        try:
            # HTTPX 0.28 + OpenSSL requires an explicit SSLContext to send
            # the client certificate. The server always enforces CERT_REQUIRED.
            tls = ssl.create_default_context(cafile=self.ca)
            if cert:
                tls.load_cert_chain(self.cert, self.key)
            with httpx.Client(
                verify=tls, trust_env=False, timeout=22, follow_redirects=False,
            ) as client:
                res = client.post(self.url + PATH_ROOT + op,
                                  content=json.dumps(payload, sort_keys=True,
                                                     separators=(",", ":")).encode(),
                                  headers={"Authorization": "Bootstrap " + token,
                                           "Content-Type": "application/json"})
                return res.status_code, res.json()
        except (httpx.ConnectError, httpx.ReadError):
            return 0, {"error": "TLS_DENIED"}

    def create_alias(self, pending):
        alias = secrets.token_urlsafe(32)
        cipher = Fernet(self.alias_key).encrypt(pending["session_verifier"].encode())
        with sqlite3.connect(self.alias_db) as db:
            db.execute("INSERT INTO aliases(alias,cipher) VALUES(?,?)", (alias, cipher))
            db.commit()
        return sha256(alias.encode()).hexdigest()

    def acknowledge(self, fields, pending, alias_sha):
        p = {**fields, "receipt_id": pending["receipt_id"],
             "owner_id": pending["owner_id"], "epoch": pending["epoch"],
             "alias_sha256": alias_sha}
        return self.post("ack", p)


class InitialBootstrap009(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if (os.getenv("GITHUB_ACTIONS") != "true" or os.getenv("CI") != "true"
                or "dbname=history_ci" not in os.environ.get("LOGIN_BOOTSTRAP_DSN", "")
                or "host=127.0.0.1" not in os.environ.get("LOGIN_BOOTSTRAP_DSN", "")):
            raise RuntimeError("HARD_STOP_DISPOSABLE_CI_ONLY")
        cls.tmp = TemporaryDirectory(prefix="isolated-bootstrap-")
        cls.keycloak = DisposableKeycloak()
        cls.keycloak.start()
        try:
            ca, server, client = cert_bundle(cls.tmp.name)
            cls.seal = Fernet.generate_key()
            cls.alias_key = Fernet.generate_key()
            signer = rsa.generate_private_key(public_exponent=65537, key_size=2048)
            public = signer.public_key().public_bytes(
                serialization.Encoding.PEM,
                serialization.PublicFormat.SubjectPublicKeyInfo)
            cls.app = BootstrapOIDC(
                service_issuer="urn:rag-finance:synthetic-bootstrap",
                audience="urn:rag-finance:api:bootstrap-ci",
                service_keys={"ci-bootstrap-kid": public},
                cert_fingerprints={
                    "urn:rag-finance:synthetic-bootstrap": sha256(client[2]).hexdigest()},
                seal_key=cls.seal, oidc=cls.keycloak.oidc,
                client_id=cls.keycloak.CLIENT_ID,
                redirect_uri=cls.keycloak.callback.url,
                db_dsn={
                    "replay": os.environ["REPLAY_API_DSN"],
                    "bootstrap": os.environ["LOGIN_BOOTSTRAP_DSN"],
                    "issuer": os.environ["LOGIN_ISSUER_DSN"],
                    "mapper": os.environ["AUTH_MAP_DSN"],
                    "binder": os.environ["LOGIN_BINDER_DSN"],
                    "reader": os.environ["LOGIN_READER_DSN"],
                })
            cls.listener = ThreadingHTTPServer(("127.0.0.1", 0), PrivateHandler)
            cls.listener.app = cls.app
            tls = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            tls.load_cert_chain(server[0], server[1])
            tls.load_verify_locations(cafile=ca)
            tls.verify_mode = ssl.CERT_REQUIRED
            cls.listener.socket = tls.wrap_socket(cls.listener.socket, server_side=True)
            cls.thread = Thread(target=cls.listener.serve_forever, daemon=True)
            cls.thread.start()
            cls.bff = BFFFixture(
                "https://127.0.0.1:" + str(cls.listener.server_address[1]),
                client[0], client[1], ca, str(Path(cls.tmp.name)/"alias.sqlite"),
                cls.alias_key)
            cls.bff.signer = signer
        except BaseException:
            cls.keycloak.stop()
            cls.tmp.cleanup()
            raise

    @classmethod
    def tearDownClass(cls):
        cls.listener.shutdown()
        cls.listener.server_close()
        cls.thread.join(timeout=4)
        cls.keycloak.stop()
        cls.tmp.cleanup()

    def tearDown(self):
        self.app.exchange = self.app._redeem

    def fields(self):
        return {"attempt_id": str(uuid.uuid4()),
                "initiator_sha256": sha256(secrets.token_bytes(32)).hexdigest()}

    def new_start(self):
        base = self.fields()
        r = {**base, "bff_attempt_id": str(uuid.uuid4()),
             "start_key": secrets.token_urlsafe(24)}
        status, response = self.bff.post("start", r)
        self.assertEqual(status, 201, {"status": status, "state": response.get("state")})
        return base, response

    def challenge(self, start):
        ctx = json.loads(Fernet(self.seal).decrypt(start["continuation"].encode()))
        return InitialChallenge(state=ctx["state"], nonce=ctx["nonce"],
                                code_verifier=ctx["code_verifier"])

    def callback(self, start, label="A", scope="openid email"):
        return self.keycloak.actual_login_callback(
            label, challenge=self.challenge(start), scope=scope)[1]

    def complete(self, base, start, callback):
        return self.bff.post("complete", {**base, "continuation": start["continuation"],
                                         "state": callback["state"][0],
                                         "code": callback["code"][0]})

    def status(self, base):
        return self.bff.post("status", base)

    def db_count(self, base):
        with psycopg.connect(os.environ["AUTH_MIG_DSN"], row_factory=dict_row) as c:
            return c.execute(
                "SELECT COUNT(*) AS n FROM auth_l1.initial_login_attempts "
                "WHERE attempt_id=%s AND session_digest IS NOT NULL",
                (base["attempt_id"],)).fetchone()["n"]

    def inspect(self, raw):
        with psycopg.connect(os.environ["AUTH_SESSION_DSN"],
                             autocommit=True, row_factory=dict_row) as c:
            return auth_session.inspect(c, raw)

    def test_BOOT01_real_two_owners_pending_then_BFF_ACK(self):
        seen = []
        for label in ("A", "B"):
            base, start = self.new_start()
            status, pending = self.complete(base, start, self.callback(start, label))
            self.assertEqual(status, 201, {"status": status, "state": pending.get("state")})
            self.assertEqual(pending["state"], "ISSUED_PENDING_BINDING")
            self.assertEqual(self.db_count(base), 1)
            self.assertIsNone(self.inspect(pending["session_verifier"]))
            status, state = self.status(base)
            self.assertEqual((status, state["state"]), (200, "ISSUED_PENDING_BINDING"))
            self.assertFalse(set(state) & {
                "session_verifier", "owner_id", "receipt_id", "alias_sha256", "nonce"})
            alias = self.bff.create_alias(pending)  # sqlite COMMIT before ACK
            status, result = self.bff.acknowledge(base, pending, alias)
            self.assertEqual(status, 200, result)
            self.assertEqual(result["state"], "ACTIVE")
            active = self.inspect(pending["session_verifier"])
            self.assertIsNotNone(active)
            self.assertEqual(active["owner_id"], pending["owner_id"])
            seen.append(pending["owner_id"])
            self.assertEqual(self.bff.acknowledge(base, pending, alias)[0], 200)
        self.assertNotEqual(seen[0], seen[1])

    def test_BOOT02_invalid_mTLS_signed_scope_and_durable_jti_replay(self):
        fields = self.fields()
        payload = {**fields, "bff_attempt_id": str(uuid.uuid4()),
                   "start_key": secrets.token_urlsafe(24)}
        self.assertEqual(self.bff.post("start", payload, cert=False)[0], 0)
        self.assertEqual(self.bff.post("start", payload, tamper=True)[0], 401)
        token = self.bff.proof("start", payload)
        self.assertEqual(self.bff.post("start", payload, proof=token)[0], 201)
        self.assertEqual(self.bff.post("start", payload, proof=token)[0], 401)

    def test_BOOT03_concurrent_duplicate_callback_one_code_one_pending(self):
        base, start = self.new_start()
        callback = self.callback(start)
        payload = {**base, "continuation": start["continuation"],
                   "state": callback["state"][0], "code": callback["code"][0]}
        lock = Lock()
        count = []
        original = self.app.exchange
        def counted(code, verifier):
            with lock:
                count.append(1)
            return original(code, verifier)
        self.app.exchange = counted
        barrier = Barrier(2)
        def work(_):
            barrier.wait(timeout=8)
            return self.bff.post("complete", payload)
        with ThreadPoolExecutor(max_workers=2) as pool:
            answers = list(pool.map(work, range(2)))
        self.assertEqual(sorted(x[0] for x in answers), [201, 409], [x[0] for x in answers])
        self.assertEqual(len(count), 1)
        self.assertEqual(self.db_count(base), 1)

    def test_BOOT04_unverified_and_missing_email_claim_no_issue(self):
        self.keycloak.set_email_verified("B", False)
        try:
            base, start = self.new_start()
            response = self.complete(base, start, self.callback(start, "B", "openid email"))
            self.assertEqual(response[0], 403, {"status": response[0]})
            self.assertEqual(self.db_count(base), 0)
        finally:
            self.keycloak.set_email_verified("B", True)
        # Keycloak 26.8.2 assigns email as a default client scope. Merely
        # requesting openid omits nothing until the default email mapper is
        # explicitly removed for this negative, then restored unconditionally.
        self.keycloak.set_default_email_scope(False)
        try:
            base, start = self.new_start()
            response = self.complete(base, start, self.callback(start, "A", "openid"))
            self.assertEqual(response[0], 403, {"status": response[0]})
            self.assertEqual(self.db_count(base), 0)
        finally:
            self.keycloak.set_default_email_scope(True)

    def test_BOOT05_unknown_transport_never_redeems_twice(self):
        base, start = self.new_start()
        callback = self.callback(start)
        count = []
        def timeout_once(code, verifier):
            count.append(1)
            raise httpx.ReadTimeout("test-only post-claim ambiguous outcome")
        self.app.exchange = timeout_once
        payload = {**base, "continuation": start["continuation"],
                   "state": callback["state"][0], "code": callback["code"][0]}
        self.assertEqual(self.bff.post("complete", payload)[0], 202)
        self.assertEqual(self.status(base)[1]["state"],
                         "UNKNOWN_RECONCILIATION_REQUIRED")
        self.assertEqual(self.bff.post("complete", payload)[0], 409)
        self.assertEqual(len(count), 1)
        self.assertEqual(self.db_count(base), 0)

    def test_BOOT06_abort_then_late_ack_and_epoch_drift(self):
        base, start = self.new_start()
        _, pending = self.complete(base, start, self.callback(start))
        abort = {**base, "receipt_id": pending["receipt_id"],
                 "owner_id": pending["owner_id"], "epoch": pending["epoch"]}
        self.assertEqual(self.bff.post("abort", abort)[0], 200)
        self.assertIsNone(self.inspect(pending["session_verifier"]))
        alias = self.bff.create_alias(pending)
        self.assertEqual(self.bff.acknowledge(base, pending, alias)[0], 409)
        base, start = self.new_start()
        _, pending = self.complete(base, start, self.callback(start, "B"))
        with psycopg.connect(os.environ["AUTH_REVOKER_DSN"],
                             autocommit=True, row_factory=dict_row) as c:
            auth_session.revoke_all(c, pending["owner_id"], pending["epoch"])
        alias = self.bff.create_alias(pending)
        self.assertEqual(self.bff.acknowledge(base, pending, alias)[0], 409)
        self.assertIsNone(self.inspect(pending["session_verifier"]))

    def test_BOOT07_status_bound_and_no_raw_verifier(self):
        base, start = self.new_start()
        status, body = self.status(base)
        self.assertEqual((status, body["state"]), (200, "INITIATED"))
        foreign = {**base, "initiator_sha256": sha256(b"other").hexdigest()}
        self.assertEqual(self.status(foreign)[0], 404)
        self.assertFalse(set(body) & {"owner_id", "receipt_id", "session_verifier",
                                     "code_verifier", "nonce", "pkce_envelope"})

    def test_BOOT08_pending_denied_by_real_004_session_fence(self):
        base, start = self.new_start()
        _, pending = self.complete(base, start, self.callback(start))
        with psycopg.connect(os.environ["AUTH_SESSION_DSN"],
                             autocommit=True, row_factory=dict_row) as c:
            with c.transaction():
                self.assertFalse(auth_session.admit_session_fenced(
                    c, pending["session_verifier"], pending["owner_id"],
                    pending["epoch"], pending["generation"]))
        self.assertIsNone(self.inspect(pending["session_verifier"]))


if __name__ == "__main__":
    unittest.main(verbosity=2)
