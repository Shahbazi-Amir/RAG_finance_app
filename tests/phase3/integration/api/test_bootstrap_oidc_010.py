"""Real separate TLS API processes + Keycloak 26.8.2 + 009/010 Claim/ACK. Only local PG17 and synthetic identities.
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
import socket
import subprocess
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



class InitialBootstrap010(unittest.TestCase):
    """Independent executable API workers with separate RAM, one PG authority."""

    @classmethod
    def setUpClass(cls):
        if (os.getenv("GITHUB_ACTIONS") != "true" or os.getenv("CI") != "true"
                or "dbname=history_ci" not in os.environ.get("LOGIN_CLAIM_DSN", "")
                or "host=127.0.0.1" not in os.environ.get("LOGIN_CLAIM_DSN", "")):
            raise RuntimeError("HARD_STOP_DISPOSABLE_CI_ONLY")
        cls.tmp = TemporaryDirectory(prefix="isolated-api-claim010-")
        cls.children = []
        cls.keycloak = DisposableKeycloak()
        try:
            cls.keycloak.start()
            ca, server, client = cert_bundle(cls.tmp.name)
            signer = rsa.generate_private_key(public_exponent=65537, key_size=2048)
            public = signer.public_key().public_bytes(
                serialization.Encoding.PEM,
                serialization.PublicFormat.SubjectPublicKeyInfo).decode()
            cls.material_old, cls.material_new = Fernet.generate_key(), Fernet.generate_key()
            cls.alias_key = Fernet.generate_key()
            cls.audit = str(Path(cls.tmp.name)/"exchange_audit.sqlite")
            cls.aliasdb = str(Path(cls.tmp.name)/"alias.sqlite")
            with sqlite3.connect(cls.audit) as c:
                c.execute("CREATE TABLE token_exchanges(worker TEXT, code_sha256 TEXT)")
                c.commit()
            cls.clients = {}
            cls.pids = {}
            configurations = {
                "a": ({"old": cls.material_old}, "old", ""),
                "b": ({"old": cls.material_old, "new": cls.material_new}, "new", ""),
                "c": ({"new": cls.material_new}, "new", ""),
                "uncertain": ({"new": cls.material_new}, "new", "claim_commit_uncertain"),
                "timeout": ({"new": cls.material_new}, "new", "timeout_after_exchange"),
            }
            for label, (keys, primary, fault) in configurations.items():
                with socket.socket() as sock:
                    sock.bind(("127.0.0.1", 0))
                    port = sock.getsockname()[1]
                db = {
                    "replay": os.environ["REPLAY_API_DSN"],
                    "bootstrap": os.environ["LOGIN_BOOTSTRAP_DSN"],
                    "claim_reader": os.environ["LOGIN_CLAIM_DSN"],
                    "issuer": os.environ["LOGIN_ISSUER_DSN"],
                    "mapper": os.environ["AUTH_MAP_DSN"],
                    "binder": os.environ["LOGIN_BINDER_DSN"],
                    "reader": os.environ["LOGIN_READER_DSN"],
                }
                config = {
                    "worker_id": label, "port": port, "fault": fault,
                    "service_issuer": "urn:rag-finance:synthetic-bootstrap",
                    "audience": "urn:rag-finance:api:bootstrap-ci",
                    "service_keys": {"ci-bootstrap-kid": public},
                    "fingerprints": {
                        "urn:rag-finance:synthetic-bootstrap": sha256(client[2]).hexdigest()},
                    "material_keys": {k: v.decode() for k, v in keys.items()},
                    "active_kid": primary, "db_dsn": db,
                    "oidc": cls.keycloak.oidc,
                    "client_id": cls.keycloak.CLIENT_ID,
                    "redirect_uri": cls.keycloak.callback.url,
                    "audit_path": cls.audit, "ca": ca,
                    "server_cert": server[0], "server_key": server[1],
                }
                path = Path(cls.tmp.name)/("worker_"+label+".json")
                path.write_text(json.dumps(config))
                path.chmod(0o600)
                child = subprocess.Popen(
                    [sys.executable, "-u", str(Path(__file__).with_name(
                        "bootstrap_010_worker.py")), str(path)],
                    cwd=str(ROOT), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                cls.children.append(child)
                url = "https://127.0.0.1:" + str(port)
                fixture = BFFFixture(url, client[0], client[1], ca, cls.aliasdb, cls.alias_key)
                fixture.signer = signer
                cls.clients[label] = fixture
                tls = ssl.create_default_context(cafile=ca)
                tls.load_cert_chain(client[0], client[1])
                for _ in range(80):
                    if child.poll() is not None:
                        raise AssertionError("INDEPENDENT_WORKER_EXITED_EARLY")
                    try:
                        with httpx.Client(verify=tls, trust_env=False,
                                          timeout=2) as http:
                            response = http.get(url+"/__fixture_health")
                        if response.status_code == 200:
                            cls.pids[label] = response.json()["pid"]
                            break
                    except httpx.HTTPError:
                        time.sleep(0.1)
                else:
                    raise AssertionError("INDEPENDENT_WORKER_NOT_READY")
            assert len(set(cls.pids.values())) == len(cls.pids)
            assert all(pid != os.getpid() for pid in cls.pids.values())
            print("PKCE010_FIVE_INDEPENDENT_WORKER_PIDS_CONFIRMED",
                  len(cls.pids), flush=True)
        except BaseException:
            for child in cls.children:
                child.terminate()
                try:
                    child.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    child.kill()
            cls.keycloak.stop()
            cls.tmp.cleanup()
            raise

    @classmethod
    def tearDownClass(cls):
        for child in cls.children:
            child.terminate()
            try:
                child.wait(timeout=4)
            except subprocess.TimeoutExpired:
                child.kill()
                child.wait(timeout=4)
        cls.keycloak.stop()
        cls.tmp.cleanup()

    def identifiers(self):
        return {
            "attempt_id": str(uuid.uuid4()),
            "initiator_sha256": sha256(secrets.token_bytes(32)).hexdigest(),
        }

    def new_start(self, worker="a"):
        ids = self.identifiers()
        bff_id = str(uuid.uuid4())
        p = {**ids, "bff_attempt_id": bff_id, "start_key": secrets.token_urlsafe(24)}
        status, body = self.clients[worker].post("start", p)
        self.assertEqual(status, 201, {"status": status})
        self.assertEqual(set(body), {"attempt_id", "state", "authorize_url"})
        self.assertNotIn("continuation", json.dumps(body))
        return {**ids, "bff_attempt_id": bff_id}, body

    def callback(self, start, account="A"):
        _, callback = self.keycloak.actual_login_callback(
            account, authorize_url=start["authorize_url"])
        return callback

    def complete(self, worker, ids, start, callback):
        payload = {**ids, "state": callback["state"][0],
                   "code": callback["code"][0]}
        return self.clients[worker].post("complete", payload)

    def scoped(self, ids):
        return {"attempt_id": ids["attempt_id"],
                "initiator_sha256": ids["initiator_sha256"]}

    def status(self, worker, ids):
        return self.clients[worker].post("status", self.scoped(ids))

    def count(self, ids):
        with psycopg.connect(os.environ["AUTH_MIG_DSN"], row_factory=dict_row) as c:
            return c.execute(
                "SELECT count(*) AS n FROM auth_l1.initial_login_attempts "
                "WHERE attempt_id=%s AND session_digest IS NOT NULL",
                (ids["attempt_id"],)).fetchone()["n"]

    def state(self, ids):
        return self.status("b", ids)[1]["state"]

    def total_exchanges(self):
        with sqlite3.connect(self.audit) as c:
            return c.execute("SELECT count(*) FROM token_exchanges").fetchone()[0]

    def inspect(self, raw):
        with psycopg.connect(os.environ["AUTH_SESSION_DSN"],
                             autocommit=True, row_factory=dict_row) as c:
            return auth_session.inspect(c, raw)

    def mutate(self, ids, sql, params=()):
        # Test-only synthetic migrator can mutate isolated Registry to reproduce
        # encryption mismatches without granting the API Registry SELECT/UPDATE.
        with psycopg.connect(os.environ["AUTH_MIG_DSN"], autocommit=True) as c:
            with c.transaction():
                c.execute(sql, (*params, ids["attempt_id"]))

    def alias_ack(self, worker, ids, pending):
        alias = self.clients[worker].create_alias(pending)
        args = {**self.scoped(ids), "receipt_id": pending["receipt_id"],
                "owner_id": pending["owner_id"], "epoch": pending["epoch"],
                "alias_sha256": alias}
        return self.clients[worker].post("ack", args), args

    def test_PKCEAPI01_cross_process_start_complete_real_Keycloak_ACK(self):
        # Process A old-key START -> independent process B new-key-primary
        # permits previous key during bounded window, using 010 Claim.
        owners = []
        for account in ("A", "B"):
            ids, start = self.new_start("a")
            self.assertIn("code_challenge_method=S256", start["authorize_url"])
            self.assertNotIn("code_verifier", start["authorize_url"])
            callback = self.callback(start, account)
            before = self.total_exchanges()
            status, pending = self.complete("b", ids, start, callback)
            self.assertEqual(status, 201, {"status": status})
            self.assertEqual(self.total_exchanges()-before, 1)
            self.assertEqual(self.count(ids), 1)
            self.assertIsNone(self.inspect(pending["session_verifier"]))
            self.assertEqual(self.state(ids), "ISSUED_PENDING_BINDING")
            result, args = self.alias_ack("b", ids, pending)
            self.assertEqual(result[0], 200)
            self.assertEqual(self.clients["b"].post("ack", args)[0], 200)
            self.assertEqual(self.inspect(pending["session_verifier"])["owner_id"],
                             pending["owner_id"])
            owners.append(pending["owner_id"])
        self.assertNotEqual(owners[0], owners[1])
        self.assertNotEqual(self.pids["a"], self.pids["b"])

    def test_PKCEAPI02_concurrent_complete_two_real_processes_one_code(self):
        ids, start = self.new_start("b")
        callback = self.callback(start)
        before = self.total_exchanges()
        payload = {**ids, "state": callback["state"][0], "code": callback["code"][0]}
        barrier = Barrier(2)
        def attempt(worker):
            barrier.wait(timeout=8)
            return self.clients[worker].post("complete", payload)
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(attempt, ("b", "c")))
        self.assertEqual(sorted(x[0] for x in results), [201, 409],
                         [x[0] for x in results])
        self.assertEqual(self.total_exchanges()-before, 1)
        self.assertEqual(self.count(ids), 1)

    def test_PKCEAPI03_bootstrap_mTLS_replay_wrong_BFF_and_state(self):
        ids = self.identifiers()
        payload = {**ids, "bff_attempt_id": str(uuid.uuid4()),
                   "start_key": secrets.token_urlsafe(20)}
        self.assertEqual(self.clients["a"].post("start", payload, cert=False)[0], 0)
        self.assertEqual(self.clients["a"].post("start", payload, tamper=True)[0], 401)
        token = self.clients["a"].proof("start", payload)
        self.assertEqual(self.clients["a"].post("start", payload, proof=token)[0], 201)
        self.assertEqual(self.clients["b"].post("start", payload, proof=token)[0], 401)
        ids, start = self.new_start("b")
        callback = self.callback(start)
        before = self.total_exchanges()
        bad = {**ids, "bff_attempt_id": str(uuid.uuid4()),
               "state": callback["state"][0], "code": callback["code"][0]}
        self.assertEqual(self.clients["c"].post("complete", bad)[0], 409)
        bad["bff_attempt_id"] = ids["bff_attempt_id"]
        bad["state"] = secrets.token_urlsafe(32)
        self.assertEqual(self.clients["c"].post("complete", bad)[0], 409)
        self.assertEqual(self.total_exchanges(), before)

    def test_PKCEAPI04_ciphertext_tamper_foreign_attempt_and_principal(self):
        ids1, start1 = self.new_start("b")
        ids2, start2 = self.new_start("b")
        callback2 = self.callback(start2)
        before = self.total_exchanges()
        self.mutate(ids2, """UPDATE auth_l1.initial_login_attempts SET
            pkce_envelope=(SELECT pkce_envelope FROM auth_l1.initial_login_attempts
              WHERE attempt_id=%s) WHERE attempt_id=%s""", (ids1["attempt_id"],))
        self.assertEqual(self.complete("c", ids2, start2, callback2)[0], 409)
        self.assertEqual(self.total_exchanges(), before)
        ids3, start3 = self.new_start("b")
        callback3 = self.callback(start3)
        self.mutate(ids3, """UPDATE auth_l1.initial_login_attempts
             SET nonce_envelope=decode(repeat('a',128),'hex') WHERE attempt_id=%s""")
        self.assertEqual(self.complete("c", ids3, start3, callback3)[0], 409)
        self.assertEqual(self.total_exchanges(), before)
        # A different actual signed BFF service identity cannot pass fixed iss.
        forged = self.clients["b"].proof("status", self.scoped(ids1))
        self.assertEqual(self.clients["c"].post(
            "status", {**self.scoped(ids1),
                       "initiator_sha256": sha256(b"other").hexdigest()},
            proof=forged)[0], 401)

    def test_PKCEAPI05_expired_registry_claim_no_idp(self):
        ids, start = self.new_start("b")
        callback = self.callback(start)
        self.mutate(ids, """UPDATE auth_l1.initial_login_attempts
            SET created_at=clock_timestamp()-interval '240 seconds',
                expires_at=clock_timestamp()-interval '1 second'
            WHERE attempt_id=%s""")
        before = self.total_exchanges()
        self.assertEqual(self.complete("c", ids, start, callback)[0], 409)
        self.assertEqual(self.total_exchanges(), before)
        self.assertEqual(self.count(ids), 0)

    def test_PKCEAPI06_key_rotation_previous_current_removed_unknown(self):
        # Worker B's keyring retains OLD while new is primary; C has NEW only.
        ids, start = self.new_start("b")
        before = self.total_exchanges()
        self.assertEqual(self.complete("c", ids, start, self.callback(start))[0], 201)
        self.assertEqual(self.total_exchanges()-before, 1)
        ids, start = self.new_start("a")
        before = self.total_exchanges()
        self.assertEqual(self.complete("c", ids, start, self.callback(start))[0], 409)
        self.assertEqual(self.total_exchanges(), before)  # retired key never sent to IdP
        self.assertEqual(self.state(ids), "UNKNOWN_RECONCILIATION_REQUIRED")
        ids, start = self.new_start("b")
        callback = self.callback(start)
        self.mutate(ids, """UPDATE auth_l1.initial_login_attempts
             SET pkce_envelope=convert_to('v1.not-in-ring.','UTF8')
                                || substring(pkce_envelope from position('.' in
                                   convert_from(pkce_envelope,'UTF8'))+1)
              WHERE attempt_id=%s""")
        before = self.total_exchanges()
        self.assertEqual(self.complete("c", ids, start, callback)[0], 409)
        self.assertEqual(self.total_exchanges(), before)

    def test_PKCEAPI07_claim_COMMIT_ack_unknown_blocks_IdP(self):
        ids, start = self.new_start("b")
        callback = self.callback(start)
        before = self.total_exchanges()
        self.assertEqual(self.complete("uncertain", ids, start, callback)[0], 503)
        self.assertEqual(self.total_exchanges(), before)
        self.assertEqual(self.state(ids), "EXCHANGE_STARTED")
        self.assertEqual(self.complete("c", ids, start, callback)[0], 409)
        self.assertEqual(self.count(ids), 0)
        self.assertEqual(self.total_exchanges(), before)

    def test_PKCEAPI08_timeout_after_real_token_exchange_unknown(self):
        ids, start = self.new_start("b")
        callback = self.callback(start)
        before = self.total_exchanges()
        status, body = self.complete("timeout", ids, start, callback)
        self.assertEqual((status, body["state"]),
                         (202, "UNKNOWN_RECONCILIATION_REQUIRED"))
        self.assertEqual(self.total_exchanges()-before, 1)
        self.assertEqual(self.state(ids), "UNKNOWN_RECONCILIATION_REQUIRED")
        self.assertEqual(self.complete("c", ids, start, callback)[0], 409)
        self.assertEqual(self.total_exchanges()-before, 1)
        self.assertEqual(self.count(ids), 0)

    def test_PKCEAPI09_pending_abort_late_ack_and_status_redacted(self):
        ids, start = self.new_start("b")
        _, pending = self.complete("c", ids, start, self.callback(start))
        self.assertEqual(self.count(ids), 1)
        self.assertIsNone(self.inspect(pending["session_verifier"]))
        status, payload = self.status("a", ids)
        self.assertEqual((status, payload["state"]), (200, "ISSUED_PENDING_BINDING"))
        self.assertFalse(set(payload) & {"session_verifier","owner_id",
                                        "receipt_id","pkce_envelope","nonce_envelope"})
        result, args = self.alias_ack("b", ids, pending)
        self.assertEqual(result[0], 200)
        self.assertEqual(self.inspect(pending["session_verifier"])["owner_id"],
                         pending["owner_id"])
        ids2, start2 = self.new_start("b")
        _, pending2 = self.complete("c", ids2, start2, self.callback(start2))
        abort = {**self.scoped(ids2), "receipt_id": pending2["receipt_id"],
                 "owner_id": pending2["owner_id"], "epoch": pending2["epoch"]}
        self.assertEqual(self.clients["a"].post("abort", abort)[0], 200)
        alias2 = self.clients["c"].create_alias(pending2)
        self.assertEqual(self.clients["c"].post(
            "ack", {**abort, "alias_sha256": alias2})[0], 409)
        self.assertIsNone(self.inspect(pending2["session_verifier"]))

    def test_PKCEAPI10_email_false_or_absent_still_denied(self):
        self.keycloak.set_email_verified("B", False)
        try:
            ids, start = self.new_start("b")
            self.assertEqual(self.complete("c", ids, start,
                                          self.callback(start, "B"))[0], 403)
            self.assertEqual(self.count(ids), 0)
        finally:
            self.keycloak.set_email_verified("B", True)
        self.keycloak.set_default_email_scope(False)
        try:
            ids, start = self.new_start("b")
            # Even after removing Keycloak's default email client scope,
            # asking explicitly for scope=email enables the optional mapper.
            # Request only openid for this signed missing-claim negative.
            from urllib.parse import urlsplit, parse_qsl, urlencode, urlunsplit
            raw = urlsplit(start["authorize_url"])
            query = [(k, "openid" if k == "scope" else v)
                     for k, v in parse_qsl(raw.query)]
            public_url = urlunsplit((raw.scheme, raw.netloc, raw.path,
                                     urlencode(query), raw.fragment))
            callback = self.keycloak.actual_login_callback(
                "A", authorize_url=public_url)[1]
            self.assertIn("code", callback)
            self.assertEqual(self.complete("c", ids, start, callback)[0], 403)
            self.assertEqual(self.count(ids), 0)
        finally:
            self.keycloak.set_default_email_scope(True)


if __name__ == "__main__":
    unittest.main(verbosity=2)
