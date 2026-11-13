"""Real SQL + mTLS HTTP Product-session API (no override), pinned #48 login."""
from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
from http.server import ThreadingHTTPServer
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Thread
from urllib.parse import urljoin, urlsplit, parse_qs
import base64
import json
import os
import secrets
import socket
import ssl
import subprocess
import sys
import time
import unittest
import uuid

import httpx
import jwt
import psycopg
from psycopg.rows import dict_row
from cryptography.hazmat.primitives import serialization

ROOT = Path(__file__).resolve().parents[4]
sys.path[:0] = [str(ROOT), str(Path(__file__).parent)]
import test_bootstrap_oidc_010 as pinned
from initial_oidc_harness import CallbackHarness, LoginForm, IsolatedOIDCFailure
from src.phase3.storage.postgres import auth_session
from src.phase3.storage.postgres.service_replay import _digest_and_exp
from apps.api import history_api

ISSUER = "urn:rag-finance:synthetic-product-session"
AUDIENCE = "urn:rag-finance:api:history-h1-isolated"
KID = "ci-product-session-kid"
REVOKE = "/internal/auth/session/v1/revoke-one"
LIST = "/v1/conversations"


def port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class RealProductSession011(unittest.TestCase):
    """#48 actual Keycloak issue/ACK -> real 004+005 list / revoke / A-B."""

    @classmethod
    def setUpClass(cls):
        if (os.getenv("CI") != "true" or os.getenv("GITHUB_ACTIONS") != "true"
                or "dbname=history_ci" not in os.getenv("AUTH_MIG_DSN", "")):
            raise RuntimeError("HARD_STOP_EPHEMERAL_CI_ONLY")
        cls.base = pinned.InitialBootstrap010
        cls.base.setUpClass()
        cls.children = []
        cls.hcb = None
        try:
            cls.fixture = cls.base.clients["b"]
            cls.temp = Path(cls.base.tmp.name)
            public = cls.fixture.signer.public_key().public_bytes(
                serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo)
            cls.pubkey = cls.temp / "session_signer_public.pem"
            cls.pubkey.write_bytes(public)
            # This is a live permission-denial reproduction, not a production
            # migration. auth_revoker lacks 003 revoke_one and 004/005 grants.
            with psycopg.connect(os.environ["AUTH_REVOKER_DSN"],
                                 autocommit=True, row_factory=dict_row) as c:
                assert c.execute("SELECT has_function_privilege("
                    "current_user,'auth_l1.revoke_one(text,bigint)','EXECUTE') AS ok"
                    ).fetchone()["ok"] is False
                assert c.execute("SELECT has_function_privilege("
                    "current_user,'auth_l1.admit_session_fenced(text,text,bigint,integer)',"
                    "'EXECUTE') AS ok").fetchone()["ok"] is False
                assert c.execute("SELECT has_function_privilege("
                    "current_user,'auth_l1.consume_service_assertion(text,bigint)',"
                    "'EXECUTE') AS ok").fetchone()["ok"] is False
            print("API011_ROLE_GAP_003_004_005_REPRODUCED_PASS", flush=True)
            with psycopg.connect(os.environ["AUTH_MIG_DSN"], autocommit=True) as c:
                # TEMPORARY CI grants; no migration or production roles changed.
                c.execute("GRANT USAGE ON SCHEMA auth_l1 TO history_app")
                for name in (
                    "consume_service_assertion(text,bigint)",
                    "admit_session_fenced(text,text,bigint,integer)",
                ):
                    c.execute("GRANT EXECUTE ON FUNCTION auth_l1." + name +
                              " TO history_app, auth_revoker")
                c.execute("GRANT EXECUTE ON FUNCTION "
                          "auth_l1.revoke_one(text,bigint) TO auth_revoker")
            cls.api_port = port()
            env = dict(os.environ)
            env.update(
                API_PRODUCT_PROOF_PUBLIC_KEY_PATH=str(cls.pubkey),
                API_PRODUCT_PROOF_ISSUER=ISSUER,
                API_PRODUCT_PROOF_AUDIENCE=AUDIENCE,
                API_PRODUCT_PROOF_KID=KID,
            )
            command = [
                sys.executable, "-m", "uvicorn", "apps.api.product_session_api:app",
                "--host", "127.0.0.1", "--port", str(cls.api_port),
                "--ssl-certfile", str(cls.temp / "server.pem"),
                "--ssl-keyfile", str(cls.temp / "server.key"),
                "--ssl-ca-certs", cls.fixture.ca, "--ssl-cert-reqs", "2",
                "--no-access-log",
            ]
            child = subprocess.Popen(command, cwd=ROOT, env=env,
                                     stdout=subprocess.DEVNULL,
                                     stderr=subprocess.DEVNULL)
            cls.children.append(child)
            tls = ssl.create_default_context(cafile=cls.fixture.ca)
            tls.load_cert_chain(cls.fixture.cert, cls.fixture.key)
            cls.tls = tls
            cls.url = "https://127.0.0.1:" + str(cls.api_port)
            for _ in range(80):
                if child.poll() is not None:
                    raise AssertionError("REAL_PRODUCT_API_EARLY_EXIT")
                try:
                    with httpx.Client(verify=tls, trust_env=False,
                                      timeout=1) as c:
                        res = c.get(cls.url + LIST)
                    if res.status_code == 401:
                        break
                except httpx.HTTPError:
                    time.sleep(0.1)
            else:
                raise AssertionError("REAL_PRODUCT_API_NOT_READY")
        except BaseException:
            cls._cleanup()
            raise

    @classmethod
    def _cleanup(cls):
        for child in getattr(cls, "children", []):
            child.terminate()
            try: child.wait(timeout=4)
            except subprocess.TimeoutExpired:
                child.kill();child.wait(timeout=4)
        if getattr(cls, "hcb", None):
            cls.hcb.stop()
        if getattr(cls, "base", None):
            cls.base.tearDownClass()
        # Last resort clean of temporary, CI-only privilege bridging.
        with psycopg.connect(os.environ["AUTH_MIG_DSN"], autocommit=True) as c:
            for name in (
                "consume_service_assertion(text,bigint)",
                "admit_session_fenced(text,text,bigint,integer)",
            ):
                c.execute("REVOKE EXECUTE ON FUNCTION auth_l1." + name +
                          " FROM history_app, auth_revoker")
            c.execute("REVOKE EXECUTE ON FUNCTION "
                      "auth_l1.revoke_one(text,bigint) FROM auth_revoker")
            c.execute("REVOKE USAGE ON SCHEMA auth_l1 FROM history_app")

    @classmethod
    def tearDownClass(cls):
        cls._cleanup()

    def signed(self, pending, method="GET", path=LIST, body=b"", query=b"", *,
               override=None):
        now = int(time.time())
        claims = {
            "iss": ISSUER, "aud": AUDIENCE, "iat": now, "nbf": now,
            "exp": now + 25, "jti": secrets.token_urlsafe(24),
            "method": method,
            "raw_path_sha256": sha256(path.encode("ascii")).hexdigest(),
            "raw_query_sha256": sha256(query).hexdigest(),
            "body_sha256": sha256(body).hexdigest(),
            "body_len": len(body),
            "session_ref": pending["session_verifier"],
            "owner_id": pending["owner_id"],
            "epoch": pending["epoch"],
            "generation": pending["generation"],
        }
        if override:
            claims.update(override)
        return jwt.encode(
            claims, self.fixture.signer, algorithm="RS256",
            headers={"typ": "JWT", "kid": KID}), claims

    def request(self, method, path, token=None, *, body=None, query="",
                headers=None, cert=True):
        h = dict(headers or {})
        if token is not None:
            h["Authorization"] = "BFF-Assertion " + token
        if body is not None:
            h["Content-Type"] = "application/json"
        tls = ssl.create_default_context(cafile=self.fixture.ca)
        if cert:
            tls.load_cert_chain(self.fixture.cert, self.fixture.key)
        try:
            with httpx.Client(verify=tls, trust_env=False,
                              timeout=12, follow_redirects=False) as c:
                return c.request(method, self.url + path + query, content=body,
                                 headers=h)
        except (httpx.ConnectError, httpx.RemoteProtocolError, httpx.ReadError):
            # OpenSSL/uvicorn may abort the mTLS handshake before HTTP,
            # which HTTPX reports as ConnectError OR RemoteProtocolError.
            if not cert:
                return None
            raise

    def login(self, label, ack=True):
        base = self.base("test_PKCEAPI01_cross_process_start_complete_real_Keycloak_ACK")
        ids, start = base.new_start("b")
        callback = base.callback(start, label)
        status, pending = base.complete("c", ids, start, callback)
        self.assertEqual(status, 201)
        self.assertEqual(pending["state"], "ISSUED_PENDING_BINDING")
        if ack:
            self.assertIsNone(base.inspect(pending["session_verifier"]))
            result, _ = base.alias_ack("b", ids, pending)
            self.assertEqual(result[0], 200)
            self.assertEqual(result[1]["state"], "ACTIVE")
            self.assertEqual(base.inspect(pending["session_verifier"])["owner_id"],
                             pending["owner_id"])
        return pending

    def seed(self, pending, title):
        request = {
            "kind": "create_conversation_request", "contract_version": "product.v1",
            "client_conversation_id": history_api.uid(),
            "idempotency_key": "real011_" + uuid.uuid4().hex,
            "title": title,
        }
        with psycopg.connect(os.environ["DB_APP_DSN"], autocommit=True,
                             row_factory=dict_row) as c:
            history_api.create_conversation(c, pending["owner_id"], request,
                                            history_api.uid(), history_api.uid())

    def list(self, pending, *, override=None, token=None, query=""):
        t = token or self.signed(pending, query=query.encode(), override=override)[0]
        return self.request("GET", LIST, t, query=query)

    def test_API011_01_pending_denied_then_A_B_real_owner_lists_and_005_replay(self):
        a = self.login("A", ack=False)
        before, _ = self.signed(a)
        self.assertEqual(self.list(a, token=before).status_code, 401)
        # Pending denial rolls back 005 JTI, as with 004 admission.
        base = self.base("test_PKCEAPI01_cross_process_start_complete_real_Keycloak_ACK")
        with psycopg.connect(os.environ["AUTH_SESSION_DSN"],
                             autocommit=True, row_factory=dict_row) as c:
            self.assertIsNone(auth_session.inspect(c, a["session_verifier"]))
        # Pending fixture never ACKs; create a clean active pair.
        a = self.login("A")
        b = self.login("B")
        self.assertNotEqual(a["owner_id"], b["owner_id"])
        self.seed(a, "real-011-private-A")
        self.seed(b, "real-011-private-B")
        for own, expected, foreign in (
            (a, "real-011-private-A", "real-011-private-B"),
            (b, "real-011-private-B", "real-011-private-A"),
        ):
            token, claims = self.signed(own)
            res = self.list(own, token=token)
            self.assertEqual(res.status_code, 200, res.text)
            doc = res.json()
            self.assertEqual(doc["kind"], "conversation_page")
            self.assertEqual(doc["scope_user_id"], own["owner_id"])
            self.assertIn(expected, [x["title"] for x in doc["items"]])
            self.assertNotIn(foreign, [x["title"] for x in doc["items"]])
            self.assertEqual(self.list(own, token=token).status_code, 401)
            bad = self.list(own, override={"owner_id": b["owner_id"] if own is a else a["owner_id"]})
            self.assertEqual(bad.status_code, 401)
        self.assertEqual(self.request("GET", LIST).status_code, 401)
        self.assertEqual(self.request("GET", LIST, headers={"X-Owner-ID": a["owner_id"]}).status_code, 401)
        self.assertIsNone(self.request("GET", LIST, self.signed(a)[0], cert=False))
        print("API011_REAL_HISTORY_PENDING_REPLAY_OWNER_AB_MTLS_PASS", flush=True)

    def test_API011_02_private_revoke_commit_fresh_A_401_B_200(self):
        a, b = self.login("A"), self.login("B")
        self.seed(a, "real-011-revoked-A")
        self.seed(b, "real-011-live-B")
        self.assertEqual(self.list(a).status_code, 200)
        self.assertEqual(self.list(b).status_code, 200)
        op = str(uuid.uuid4())
        raw = json.dumps({"operation_id": op}, separators=(",", ":")).encode("ascii")
        signed, claims = self.signed(a, "POST", REVOKE, raw)
        response = self.request("POST", REVOKE, signed, body=raw)
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json(), {"state":"REVOKED_COMMITTED","operation_id":op})
        with psycopg.connect(os.environ["AUTH_SESSION_DSN"],
                             autocommit=True, row_factory=dict_row) as c:
            self.assertIsNone(auth_session.inspect(c, a["session_verifier"]))
            self.assertIsNotNone(auth_session.inspect(c, b["session_verifier"]))
        # No false second success and no false success on replay.
        self.assertEqual(self.request("POST", REVOKE, signed, body=raw).status_code, 401)
        self.assertEqual(self.request("POST", REVOKE, self.signed(
            a, "POST", REVOKE, raw)[0], body=raw).status_code, 401)
        self.assertEqual(self.list(a).status_code, 401)
        again = self.list(b)
        self.assertEqual(again.status_code, 200)
        doc = again.json()
        self.assertEqual(doc["scope_user_id"], b["owner_id"])
        self.assertTrue(all(x["owner_user_id"] == b["owner_id"] for x in doc["items"]))
        self.assertNotIn("real-011-revoked-A", [x["title"] for x in doc["items"]])
        print("API011_COMMITTED_REVOKE_A_401_B_OWNER_ONLY_200_PASS", flush=True)

    def test_API011_03_wrong_session_signature_query_body_and_revoker_roles(self):
        a, b = self.login("A"), self.login("B")
        # Same authenticated service key but wrong owner/epoch are DB denied.
        self.assertEqual(self.list(a, override={"owner_id": b["owner_id"]}).status_code, 401)
        self.assertEqual(self.list(a, override={"epoch": a["epoch"]+1}).status_code, 401)
        t, _ = self.signed(a, query=b"limit=2")
        self.assertEqual(self.list(a, token=t).status_code, 401)
        invalid = self.signed(a)[0]
        self.assertEqual(self.request("GET", LIST, invalid, headers={
            "X-Owner-ID":a["owner_id"]}).status_code, 401)
        op=str(uuid.uuid4())
        body=json.dumps({"operation_id":op}).encode()
        token,_=self.signed(a, "POST", REVOKE, body)
        # Valid differently signed JSON has matching schema, but bytes
        # differ from the RSA-bound body: deny proof, not a schema 422.
        tampered = json.dumps({"operation_id":str(uuid.uuid4())}).encode()
        self.assertEqual(self.request("POST", REVOKE, token,
                                     body=tampered).status_code, 401)
        with psycopg.connect(os.environ["AUTH_REVOKER_DSN"],
                             autocommit=True, row_factory=dict_row) as c:
            self.assertFalse(c.execute("SELECT has_table_privilege("
               "current_user,'auth_l1.sessions','SELECT') AS allowed"
            ).fetchone()["allowed"])
            self.assertFalse(c.execute("SELECT has_table_privilege("
               "current_user,'history_l1.conversations','SELECT') AS allowed"
            ).fetchone()["allowed"])
        print("API011_REVOKE_PROOF_BODY_OWNER_AND_RESTRICTED_ROLE_PASS", flush=True)

    def test_API011_99_pinned_https_callback_real_keycloak_and_redirect_denies(self):
        """Actual verified HTTPS callback, same pinned redirect for Code exchange."""
        from cryptography.hazmat.primitives import serialization
        from src.phase3.auth.bootstrap_oidc import BootstrapOIDC, BootstrapDenied
        keycloak = self.base.keycloak
        # The original HTTP callback is no longer used after earlier tests.
        keycloak.callback.stop()
        callback = CallbackHarness()
        tls = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        tls.load_cert_chain(str(self.temp/"server.pem"),str(self.temp/"server.key"))
        callback.server.socket=tls.wrap_socket(callback.server.socket,server_side=True)
        callback.url=("https://127.0.0.1:"+
                      str(callback.server.server_address[1])+"/callback")
        callback.start()
        self.__class__.hcb = callback
        keycloak.callback = callback
        # Test-only Keycloak admin updates EXACT configured client redirect.
        with httpx.Client(trust_env=False, timeout=20) as c:
            token = c.post(keycloak.base+"/realms/master/protocol/openid-connect/token",
                           data={"grant_type":"password","client_id":"admin-cli",
                                 "username":"ci-bootstrap","password":keycloak.password})
            self.assertEqual(token.status_code, 200)
            hdr={"Authorization":"Bearer "+token.json()["access_token"]}
            endpoint=keycloak.base+"/admin/realms/"+keycloak.REALM+"/clients"
            clients=c.get(endpoint,headers=hdr,
                          params={"clientId":keycloak.CLIENT_ID})
            self.assertEqual(clients.status_code,200)
            self.assertEqual(len(clients.json()),1)
            client=clients.json()[0]
            client["redirectUris"]=[callback.url]
            resp=c.put(endpoint+"/"+client["id"],headers=hdr,json=client)
            self.assertEqual(resp.status_code,204)
        # New independent TLS API worker uses pinned HTTPS callback URL.
        template=json.loads((self.temp/"worker_b.json").read_text())
        newport=port()
        template.update(port=newport,worker_id="https",
                        redirect_uri=callback.url)
        path=self.temp/"worker_https.json"
        path.write_text(json.dumps(template));path.chmod(0o600)
        proc=subprocess.Popen(
            [sys.executable,"-u",str(Path(pinned.__file__).with_name(
                "bootstrap_010_worker.py")),str(path)],cwd=ROOT,
            stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        self.children.append(proc)
        apiurl="https://127.0.0.1:"+str(newport)
        worker=pinned.BFFFixture(apiurl,self.fixture.cert,self.fixture.key,
                                 self.fixture.ca,str(self.temp/"alias.sqlite"),
                                 self.base.alias_key)
        worker.signer=self.fixture.signer
        with httpx.Client(verify=self.tls,trust_env=False,timeout=2) as c:
            for _ in range(70):
                if proc.poll() is not None:raise AssertionError("HTTPS_WORKER_EXIT")
                try:
                    if c.get(apiurl+"/__fixture_health").status_code==200:
                        break
                except httpx.HTTPError:
                    time.sleep(0.1)
            else:raise AssertionError("HTTPS_WORKER_UNAVAILABLE")
        identifiers={
            "attempt_id":str(uuid.uuid4()),
            "initiator_sha256":sha256(secrets.token_bytes(32)).hexdigest(),
            "bff_attempt_id":str(uuid.uuid4()),
            "start_key":secrets.token_urlsafe(22),
        }
        result, start=worker.post("start",identifiers)
        self.assertEqual(result,201)
        parsed=urlsplit(start["authorize_url"])
        self.assertEqual(parse_qs(parsed.query)["redirect_uri"],[callback.url])
        # URI is not an accepted browser/BFF field on START or COMPLETE.
        self.assertEqual(worker.post("start",{**identifiers,
            "redirect_uri":"https://evil.example/callback"})[0],422)
        # Change only the IdP authorization query: unregistered redirect
        # cannot mint a Code, preserving server-pinned challenge.
        from urllib.parse import urlencode
        query=parse_qs(parsed.query)
        query["redirect_uri"]=["https://127.0.0.1:1/callback"]
        with httpx.Client(trust_env=False,timeout=8,follow_redirects=False) as c:
            invalid=c.get(keycloak.oidc["authorization_endpoint"],
                          params={k:v[0] for k,v in query.items()})
            self.assertIn(invalid.status_code,(400,403))
        # Genuine IdP login followed by a CA-verified TLS callback GET.
        with httpx.Client(verify=self.fixture.ca,trust_env=False,
                          timeout=20,follow_redirects=False) as browser:
            response=keycloak.same_origin_local_request(
                browser,"GET",keycloak.oidc["authorization_endpoint"],
                params={k:v[0] for k,v in parse_qs(parsed.query).items()})
            submitted=False
            captured=None
            for _ in range(24):
                if response.status_code in (301,302,303,307,308):
                    dest=urljoin(str(response.url),response.headers.get("location",""))
                    if dest.startswith(callback.url+"?"):
                        received=browser.get(dest)
                        self.assertEqual(received.status_code,200)
                        captured=callback.next()
                        break
                    if not dest.startswith(keycloak.base+"/realms/"+keycloak.REALM+"/"):
                        raise IsolatedOIDCFailure()
                    response=keycloak.same_origin_local_request(browser,"GET",dest)
                elif response.status_code==200 and not submitted:
                    form=LoginForm();form.feed(response.text)
                    if not form.action:raise IsolatedOIDCFailure()
                    data=dict(form.hidden)
                    data.update(username=keycloak.accounts["A"]["email"],
                                password=keycloak.accounts["A"]["password"])
                    submitted=True
                    response=keycloak.same_origin_local_request(
                        browser,"POST",urljoin(str(response.url),form.action),
                        data=data)
                else:
                    raise IsolatedOIDCFailure()
        self.assertIsNotNone(captured)
        payload={"attempt_id":identifiers["attempt_id"],
                 "initiator_sha256":identifiers["initiator_sha256"],
                 "bff_attempt_id":identifiers["bff_attempt_id"],
                 "state":captured["state"][0],"code":captured["code"][0]}
        status,pending=worker.post("complete",payload)
        self.assertEqual(status,201,{"status":status})
        # This verifies same configured HTTPS redirect used by token exchange.
        alias=worker.create_alias(pending)
        ack={k:identifiers[k] for k in ("attempt_id","initiator_sha256")}
        ack.update(receipt_id=pending["receipt_id"],owner_id=pending["owner_id"],
                   epoch=pending["epoch"],alias_sha256=alias)
        self.assertEqual(worker.post("ack",ack)[0],200)
        print("API011_PINNED_CA_VERIFIED_HTTPS_CALLBACK_CODE_ACK_PASS",flush=True)
