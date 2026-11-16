"""Isolated real HTTPS IdP config + real OpenSSL mTLS + signed RPC tests.

NO real IdP HTTP, PostgreSQL write, Arvan or session issuance. Business SQL
methods and replay consume are mocked only for the five route dispatch cases.
"""
import asyncio
from contextlib import ExitStack
import hashlib
import json
import os
import secrets
import ssl
import subprocess
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4
from urllib.parse import parse_qs, urlsplit

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
from fastapi.testclient import TestClient
import jwt

from apps.api.private_staging_bootstrap_asgi import (
    CONFIG_VERSION, REDIRECT_URI, ROLES, FUNCTIONS,
    load_staging_bootstrap_config, build_bootstrap_service,
    create_bootstrap_app,
)
from src.phase3.auth.bootstrap_oidc import BootstrapDenied, BootstrapOIDC
from src.phase3.auth.staging_transport_mtls import (
    TrustedBFFTLSBoundary, VerifiedPeerUnavailable,
)

ISSUER = "https://idp.example.invalid/realms/finance"
OIDC = {
    "issuer": ISSUER,
    "authorization_endpoint": ISSUER + "/protocol/openid-connect/auth",
    "token_endpoint": ISSUER + "/protocol/openid-connect/token",
    "jwks_uri": ISSUER + "/protocol/openid-connect/certs",
}


def cmd(*args):
    subprocess.run(["openssl", *map(str, args)], check=True,
                   capture_output=True, timeout=30)


def _tls_pair(client_ctx, server_ctx):
    ci, co = ssl.MemoryBIO(), ssl.MemoryBIO()
    si, so = ssl.MemoryBIO(), ssl.MemoryBIO()
    cli = client_ctx.wrap_bio(ci, co, server_side=False, server_hostname="server")
    srv = server_ctx.wrap_bio(si, so, server_side=True)
    ready = [False, False]
    for _ in range(30):
        for n, obj in enumerate((cli, srv)):
            try:
                obj.do_handshake()
                ready[n] = True
            except (ssl.SSLWantReadError, ssl.SSLWantWriteError):
                pass
            if n == 0:
                data = co.read()
                if data:
                    si.write(data)
            else:
                data = so.read()
                if data:
                    ci.write(data)
        if all(ready):
            return srv
    raise AssertionError("OPENSSL_HANDSHAKE_FAILED")


class FakeConnection:
    def __enter__(self):
        return self
    def __exit__(self, *args):
        return False
    def transaction(self):
        return self


class StagingBootstrapASGITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.folder = tempfile.TemporaryDirectory(prefix="boot-staging-")
        cls.root = Path(cls.folder.name)
        cmd("req","-x509","-newkey","rsa:2048","-nodes",
            "-keyout",cls.root/"ca.key","-out",cls.root/"ca.pem",
            "-days","1","-subj","/CN=ExampleCA",
            "-addext","basicConstraints=critical,CA:TRUE",
            "-addext","keyUsage=critical,keyCertSign,cRLSign")
        for name in ("server", "bff", "other"):
            cmd("req","-newkey","rsa:2048","-nodes",
                "-keyout",cls.root/f"{name}.key",
                "-out",cls.root/f"{name}.csr","-subj",f"/CN={name}")
            ext = cls.root/f"{name}.ext"
            ext.write_text("basicConstraints=critical,CA:FALSE\n"
                           "keyUsage=digitalSignature,keyEncipherment\n"
                           "extendedKeyUsage=serverAuth,clientAuth\n")
            cmd("x509","-req","-in",cls.root/f"{name}.csr",
                "-CA",cls.root/"ca.pem","-CAkey",cls.root/"ca.key",
                "-CAcreateserial","-out",cls.root/f"{name}.pem",
                "-days","1","-extfile",ext)
        cls.fingerprint = hashlib.sha256(ssl.PEM_cert_to_DER_cert(
            (cls.root/"bff.pem").read_text())).hexdigest()
        cls.rsa_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        (cls.root/"sign.pub").write_bytes(cls.rsa_key.public_key().public_bytes(
            serialization.Encoding.PEM,serialization.PublicFormat.SubjectPublicKeyInfo))
        (cls.root/"seal.key").write_bytes(Fernet.generate_key())
        for name in ("server.key", "bff.key", "other.key", "ca.key", "seal.key"):
            (cls.root/name).chmod(0o600)
        cls.doc = {
            "contract_version": CONFIG_VERSION,
            "listen_host":"127.0.0.1","listen_port":18444,
            "server_tls_cert_file":str(cls.root/"server.pem"),
            "server_tls_key_file":str(cls.root/"server.key"),
            "trusted_bff_ca_file":str(cls.root/"ca.pem"),
            "bff_leaf_cert_sha256":cls.fingerprint,
            "bff_issuer":"urn:ragfinance:bootstrap-bff",
            "bff_audience":"urn:ragfinance:bootstrap",
            "bff_kid":"bff-test",
            "bff_rs256_public_key_file":str(cls.root/"sign.pub"),
            "seal_key_file":str(cls.root/"seal.key"),
            "seal_key_kid":"s1",
            "idp_ca_file":str(cls.root/"ca.pem"),
            "oidc_issuer":OIDC["issuer"],
            "oidc_authorization_endpoint":OIDC["authorization_endpoint"],
            "oidc_token_endpoint":OIDC["token_endpoint"],
            "oidc_jwks_uri":OIDC["jwks_uri"],
            "oidc_client_id":"finance-staging-client",
            "oidc_redirect_uri":REDIRECT_URI,
        }
        for name in ROLES:
            cls.doc["dsn_"+name] = "host=/run/postgresql dbname=ragfinance_staging user="+ROLES[name]
        cls.conf = cls.root/"bootstrap.json"
        cls.conf.write_text(json.dumps(cls.doc))
        cls.conf.chmod(0o600)
        cls.server_ctx=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        cls.server_ctx.load_cert_chain(str(cls.root/"server.pem"),
                                       str(cls.root/"server.key"))
        cls.server_ctx.load_verify_locations(cafile=str(cls.root/"ca.pem"))
        cls.server_ctx.verify_mode=ssl.CERT_REQUIRED
        cls.client_ctx=ssl.create_default_context(
            ssl.Purpose.SERVER_AUTH, cafile=str(cls.root/"ca.pem"))
        cls.client_ctx.check_hostname=False
        cls.client_ctx.load_cert_chain(str(cls.root/"bff.pem"),
                                       str(cls.root/"bff.key"))

    @classmethod
    def tearDownClass(cls):
        cls.folder.cleanup()

    def setUp(self):
        self.cfg=load_staging_bootstrap_config(self.conf)
        self.service,self.boundary=build_bootstrap_service(self.cfg,check_db=False)
        self.tls=_tls_pair(self.client_ctx,self.server_ctx)
        self.assertTrue(self.boundary.approved_tls_peer(self.tls))

    def proof(self,path,body,jti=None,*,overrides=None):
        raw=json.dumps(body,separators=(",",":"),ensure_ascii=False).encode()
        now=int(time.time())
        claims={
            "iss":self.cfg.issuer,"aud":self.cfg.audience,"iat":now,
            "nbf":now,"exp":now+20,"jti":jti or secrets.token_urlsafe(24),
            "purpose":"initial-oidc-bootstrap-v1","method":"POST",
            "raw_path_sha256":hashlib.sha256(path.encode()).hexdigest(),
            "raw_query_sha256":hashlib.sha256(b"").hexdigest(),
            "body_sha256":hashlib.sha256(raw).hexdigest(),"body_len":len(raw),
            "attempt_id":body["attempt_id"],
            "initiator_sha256":body["initiator_sha256"],
        }
        if overrides:
            claims.update(overrides)
        token=jwt.encode(claims,self.rsa_key,algorithm="RS256",
                         headers={"typ":"JWT","kid":self.cfg.kid})
        return raw,"Bootstrap "+token

    def example(self,operation):
        base={"attempt_id":str(uuid4()),"initiator_sha256":"b"*64}
        if operation=="start":
            base.update(bff_attempt_id=str(uuid4()),start_key="fixture-key")
        elif operation=="complete":
            base.update(bff_attempt_id=str(uuid4()),state="fixture-state",code="fixture-code")
        elif operation=="ack":
            base.update(receipt_id=str(uuid4()),owner_id="synthetic_owner",
                        epoch=0,alias_sha256="c"*64)
        elif operation=="abort":
            base.update(receipt_id=str(uuid4()),owner_id="synthetic_owner",epoch=0)
        return base

    def client(self,verified=True):
        app=create_bootstrap_app(self.service,self.boundary)
        if verified:
            app=self.boundary.wrap_real_verified_connection(app,self.tls)
        return TestClient(app,base_url="https://127.0.0.1")

    def test_01_https_real_idp_and_exact_public_callback(self):
        self.assertEqual(self.cfg.redirect_uri,
                         "https://ragfinance.ir/api/auth/callback")
        self.assertEqual(self.service.runtime_profile,"private_staging")
        self.assertIsNotNone(self.service.idp_tls_context)
        self.assertTrue(self.service.idp_tls_context.check_hostname)
        self.assertEqual(self.service.oidc, OIDC)

    def test_02_loopback_ci_unchanged_and_bad_staging_urls_denied(self):
        fields={
            "service_issuer":self.cfg.issuer,
            "audience":self.cfg.audience,
            "service_keys":{self.cfg.kid:(self.root/"sign.pub").read_bytes()},
            "cert_fingerprints":{self.cfg.issuer:self.fingerprint},
            "seal_keys":{"s1":(self.root/"seal.key").read_bytes()},
            "active_seal_kid":"s1",
            "db_dsn":self.cfg.dsns,
            "oidc":OIDC,
            "client_id":"finance-staging-client",
            "redirect_uri":REDIRECT_URI,
            "runtime_profile":"private_staging",
        }
        for changes in (
            {"redirect_uri":"http://127.0.0.1:8765/callback"},
            {"redirect_uri":"https://ragfinance.ir/callback"},
            {"redirect_uri":"https://ragfinance.ir/api/auth/callback/"},
            {"redirect_uri":"https://ragfinance.ir/api/auth/callback?next=evil"},
            {"oidc":{**OIDC,"issuer":"http://127.0.0.1:9999/realms/finance"}},
            {"oidc":{**OIDC,"authorization_endpoint":"https://evil.invalid/auth"}},
            {"oidc":{**OIDC,"token_endpoint":"http://idp.example.invalid/token"}},
            {"oidc":{**OIDC,"jwks_uri":"https://other.invalid/certs"}},
            {"oidc":{**OIDC,"issuer":"https://idp.example.invalid:444/realms/finance"}},
        ):
            with self.subTest(changes=changes), self.assertRaises(BootstrapDenied):
                BootstrapOIDC(**{**fields,**changes})
        legacy={**fields,"runtime_profile":"loopback_fixture",
                "redirect_uri":"http://127.0.0.1:8765/callback",
                "oidc":{
                    "issuer":"http://127.0.0.1:8777/realms/finance",
                    "authorization_endpoint":"http://127.0.0.1:8777/realms/finance/protocol/openid-connect/auth",
                    "token_endpoint":"http://127.0.0.1:8777/realms/finance/protocol/openid-connect/token",
                    "jwks_uri":"http://127.0.0.1:8777/realms/finance/protocol/openid-connect/certs",
                }}
        self.assertIsNone(BootstrapOIDC(**legacy).idp_tls_context)

    def test_03_all_five_signed_https_asgi_endpoints_fenced(self):
        results={"start":201,"complete":201,"status":200,"ack":200,"abort":200}
        with ExitStack() as stack:
            stack.enter_context(patch.object(self.service,"_conn",return_value=FakeConnection()))
            consume=stack.enter_context(patch(
                "src.phase3.auth.bootstrap_oidc.PostgresDurableReplayStore.consume",
                return_value=True))
            operations={}
            for name,status in results.items():
                operations[name]=stack.enter_context(patch.object(
                    self.service,"_"+name,return_value=(status,{"state":"FIXTURE_"+name})))
            with self.client() as browser:
                for name,status in results.items():
                    msg=self.example(name)
                    path="/internal/auth/oidc/v1/"+name
                    raw,auth=self.proof(path,msg)
                    response=browser.post(path,content=raw,headers={
                        "Authorization":auth,"Content-Type":"application/json",
                        "X-Forwarded-Client-Cert":"FORGED",
                        "X-SSL-Client-Verify":"SUCCESS"})
                    self.assertEqual(response.status_code,status,response.text)
                    self.assertEqual(response.json(),{"state":"FIXTURE_"+name})
                    self.assertEqual(response.headers["Cache-Control"],"no-store")
                    operations[name].assert_called_once()
            self.assertEqual(consume.call_count,5)
        print("BOOTSTRAP_STAGING_FIVE_SIGNED_MTLS_FIXTURE_ENDPOINTS_PASS",flush=True)

    def test_04_signed_request_without_cert_capability_401(self):
        with self.client(verified=False) as c:
            data=self.example("start")
            path="/internal/auth/oidc/v1/start"
            raw,auth=self.proof(path,data)
            r=c.post(path,content=raw,headers={
                "Authorization":auth,"Content-Type":"application/json",
                "X-Forwarded-Client-Cert":"FORGED",
                "X-SSL-Client-Verify":"SUCCESS"})
            self.assertEqual(r.status_code,401)
            self.assertNotIn("session_verifier", r.text)

    def test_05_wrong_signed_path_and_tampered_body_401(self):
        data=self.example("status");p="/internal/auth/oidc/v1/status"
        raw,auth=self.proof(p,data)
        with self.client() as c:
            wrong=c.post("/internal/auth/oidc/v1/start",content=raw,headers={
                "Authorization":auth,"Content-Type":"application/json"})
            self.assertEqual(wrong.status_code,401)
            tampered=c.post(p,content=raw+b" ",headers={
                "Authorization":auth,"Content-Type":"application/json"})
            self.assertEqual(tampered.status_code,401)

    def test_06_foreign_certificate_or_forged_scope_not_accepted(self):
        self.assertIsNone(self.boundary.peer_der_from_scope({
            "type":"http","scheme":"https",
            "headers":[(b"x-ssl-client-cert",b"FAKE")]}))
        foreign = ssl.create_default_context(
            ssl.Purpose.SERVER_AUTH,cafile=str(self.root/"ca.pem"))
        foreign.check_hostname=False
        foreign.load_cert_chain(str(self.root/"other.pem"),
                                str(self.root/"other.key"))
        foreign_tls=_tls_pair(foreign,self.server_ctx)
        with self.assertRaises(VerifiedPeerUnavailable):
            self.boundary.wrap_real_verified_connection(
                create_bootstrap_app(self.service,self.boundary),foreign_tls)

    def test_07_bad_config_callback_perms_and_origin_rejected(self):
        f=self.root/"bad.json"
        for changes in (
            {"oidc_redirect_uri":"https://ragfinance.ir/callback"},
            {"listen_host":"0.0.0.0"},
            {"listen_port":True},
            {"extra_key":"unreviewed"},
            {"oidc_client_id":""},
        ):
            f.write_text(json.dumps({**self.doc,**changes}))
            f.chmod(0o600)
            with self.subTest(changes=changes),self.assertRaises(Exception):
                load_staging_bootstrap_config(f)
        f.write_text(json.dumps(self.doc));f.chmod(0o644)
        with self.assertRaises(Exception):
            load_staging_bootstrap_config(f)
        f.chmod(0o600)

    def test_08_expired_proof_and_wrong_issuer_denied(self):
        p="/internal/auth/oidc/v1/status";body=self.example("status")
        now=int(time.time())
        for overrides in ({"iss":"urn:other:principal"},
                          {"iat":now-120,"nbf":now-120,"exp":now-90},
                          {"aud":"urn:wrong:audience"}):
            raw,auth=self.proof(p,body,overrides=overrides)
            with self.assertRaises(BootstrapDenied):
                self.service._auth(
                    ssl.PEM_cert_to_DER_cert((self.root/"bff.pem").read_text()),
                    auth,"POST",p,raw)

    def test_09_authorize_url_and_token_exchange_reuse_exact_redirect(self):
        self.assertEqual(self.service.redirect_uri,REDIRECT_URI)
        saved=[]
        def fake_call(role,sql,values):
            saved.append((role,sql,values))
            return True
        attempt=self.example("start")
        proof=type("Proof",(),{
            "attempt_id":attempt["attempt_id"],
            "principal":self.cfg.issuer,
            "initiator_sha256":attempt["initiator_sha256"],
        })()
        with patch.object(self.service,"_call",side_effect=fake_call):
            status,body=self.service._start(attempt,proof)
        self.assertEqual(status,201)
        params=parse_qs(urlsplit(body["authorize_url"]).query)
        self.assertEqual(params["redirect_uri"],[REDIRECT_URI])
        self.assertEqual(params["code_challenge_method"],["S256"])
        self.assertEqual(len(saved),1)
        with patch("src.phase3.auth.bootstrap_oidc.httpx.Client") as client:
            self.service._redeem("fake_code","secret_pkce")
            self.assertIs(client.call_args.kwargs["verify"],
                          self.service.idp_tls_context)
            self.assertEqual(client.return_value.__enter__.return_value.post.call_args.kwargs["data"]["redirect_uri"],REDIRECT_URI)

    def test_10_jwks_validation_uses_https_ca(self):
        with patch("src.phase3.auth.bootstrap_oidc._StagingNoRedirectJWKClient") as client:
            client.return_value.get_signing_key_from_jwt.return_value.key=object()
            with patch("src.phase3.auth.bootstrap_oidc.jwt.get_unverified_header",
                       return_value={"kid":"idp","alg":"RS256"}),patch(
                       "src.phase3.auth.bootstrap_oidc.jwt.decode",
                       return_value={"iss":ISSUER,"sub":"test","nonce":"nonce",
                                     "email_verified":True}):
                r=type("Reply",(),{
                    "status_code":200,"json":lambda self:{"id_token":"synthetic"}
                })()
                self.service._validate_idp(r,"nonce")
            self.assertIs(client.call_args.args[1],
                          self.service.idp_tls_context)
            self.assertEqual(client.call_args.args[0],OIDC["jwks_uri"])

    def test_10b_jwks_redirect_or_oversize_denied(self):
        from src.phase3.auth.bootstrap_oidc import _StagingNoRedirectJWKClient
        client=_StagingNoRedirectJWKClient(
            OIDC["jwks_uri"],self.service.idp_tls_context)
        class Reply:
            def __init__(self, status, data):
                self.status_code=status
                self.content=data
            def json(self):
                return {"keys":[{"kty":"RSA","kid":"test"}]}
        for response in (Reply(302,b""),Reply(200,b"a"*70000)):
            with patch("src.phase3.auth.bootstrap_oidc.httpx.Client") as http:
                http.return_value.__enter__.return_value.get.return_value=response
                with self.assertRaises(jwt.PyJWKClientConnectionError):
                    client.fetch_data()
                self.assertFalse(http.call_args.kwargs["follow_redirects"])
                self.assertIs(http.call_args.kwargs["verify"],
                              self.service.idp_tls_context)

    def test_11_no_initial_auth_direct_postgres_table_access_startup(self):
        self.assertEqual(set(FUNCTIONS),set(ROLES))
        self.assertEqual(ROLES["replay"],"auth_trust_api")
        self.assertEqual(ROLES["claim_reader"],"auth_login_claim_reader")
        from apps.api.private_staging_bootstrap_asgi import verify_bootstrap_roles
        with self.assertRaises(Exception):
            verify_bootstrap_roles({})
        from inspect import getsource
        code=getsource(verify_bootstrap_roles)
        self.assertIn("has_function_privilege",code)
        self.assertIn("has_table_privilege",code)

    def test_12_no_real_db_used_in_fixture(self):
        from apps.api.private_staging_bootstrap_asgi import main
        with patch("apps.api.private_staging_bootstrap_asgi.run_staging_bootstrap") as start:
            self.assertEqual(main(["--config",str(self.conf),
                                   "--preflight-only"]),0)
            start.assert_called_once()
            self.assertTrue(start.call_args.kwargs["preflight_only"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
