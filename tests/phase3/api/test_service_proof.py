"""Unit proof/byte-binding negatives; no DB, Docker, IdP or HTTP service."""
from __future__ import annotations

from hashlib import sha256
import secrets
import sys
from pathlib import Path
import time
import unittest

import jwt

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from proof_fixture import FakeBFFSigner, ISSUER, AUDIENCE, KID
from src.phase3.auth.service_proof import (
    BFFServiceVerifier, TrustRejected, assertion_from_asgi_headers, wire_request,
)

SESSION = "x" * 43
OWNER = "synthetic_owner_trust_unit"


class StrictBFFServiceProof(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.signer = FakeBFFSigner()
        cls.other_signer = FakeBFFSigner()
        cls.verifier = BFFServiceVerifier(
            issuer=ISSUER, audience=AUDIENCE,
            public_keys={KID: cls.signer.public_pem},
        )

    def token(self, **change):
        data = self.signer.claims(owner_id=OWNER, session_ref=SESSION)
        data.update(change)
        return self.signer.sign(data)

    def check(self, token, *, method="POST", path=b"/fixture",
              query=b"", body=b"{}"):
        return self.verifier.verify(token, method=method,
                                    raw_path=path, raw_query=query,
                                    raw_body=body)

    def test_TRU01_genuine_static_key_and_redaction(self):
        token = self.token()
        proof = self.check(token)
        self.assertEqual((proof.owner_id, proof.epoch, proof.generation),
                         (OWNER, 0, 0))
        self.assertNotIn(SESSION, repr(proof))
        self.assertNotIn(proof.jti, repr(proof))
        self.assertNotIn(token, repr(proof))

    def test_TRU02_invalid_config_fails_before_request(self):
        for config in (
            {"issuer": ISSUER, "audience": AUDIENCE, "public_keys": {}},
            {"issuer": "", "audience": AUDIENCE, "public_keys": {KID: self.signer.public_pem}},
            {"issuer": ISSUER, "audience": "", "public_keys": {KID: self.signer.public_pem}},
            {"issuer": ISSUER, "audience": AUDIENCE, "public_keys": {KID: b"invalid"}},
            {"issuer": ISSUER, "audience": AUDIENCE, "public_keys": {"bad/kid": self.signer.public_pem}},
        ):
            with self.subTest(config=list(config)):
                with self.assertRaises(TrustRejected):
                    BFFServiceVerifier(**config)

    def test_TRU03_signature_wrong_key_and_header_override(self):
        data = self.signer.claims(owner_id=OWNER, session_ref=SESSION)
        wrong_signature = self.other_signer.sign(data)
        unknown_kid = self.signer.sign(data, kid="unknown")
        wrong_alg = jwt.encode(data, "synthetic-HMAC-only-not-public",
                               algorithm="HS256", headers={"kid": KID, "typ": "JWT"})
        untrusted_jku = self.signer.sign(
            data, extra_headers={"jku": "https://attacker.invalid/jwks"})
        untrusted_x5u = self.signer.sign(
            data, extra_headers={"x5u": "https://attacker.invalid/key"})
        for token in (wrong_signature, unknown_kid, wrong_alg, untrusted_jku, untrusted_x5u):
            with self.subTest(negative="signature/key/header"):
                with self.assertRaises(TrustRejected):
                    self.check(token)

    def test_TRU04_issuer_and_audience_and_claim_selection(self):
        for updates in (
            {"iss": "https://synthetic-idp.invalid"},
            {"aud": "urn:other-api"},
            {"aud": [AUDIENCE]},
            {"role": "admin"},
            {"owner_id": ""},
            {"owner_id": "owner\nspoofed"},
            {"epoch": -1},
            {"generation": -1},
            {"epoch": "0"},
            {"generation": True},
            {"body_len": -1},
        ):
            with self.subTest(fields=list(updates)):
                with self.assertRaises(TrustRejected):
                    self.check(self.token(**updates))

    def test_TRU05_expired_future_long_lifetime_and_bad_nbf(self):
        now = int(time.time())
        bads = (
            {"iat": now - 50, "nbf": now - 50, "exp": now - 1},
            {"iat": now + 8, "nbf": now + 8, "exp": now + 22},
            {"iat": now, "nbf": now + 9, "exp": now + 24},
            {"iat": now, "nbf": now, "exp": now + 31},
            {"iat": now - 31, "nbf": now - 31, "exp": now + 1},
            {"iat": True},
            {"exp": str(now + 20)},
        )
        for updates in bads:
            with self.subTest(fields=list(updates)):
                with self.assertRaises(TrustRejected):
                    self.check(self.token(**updates))
        expired_now = self.token(iat=now - 30, nbf=now - 30, exp=now)
        with self.assertRaises(TrustRejected):
            self.check(expired_now)

    def test_TRU06_missing_or_short_reused_jti_rejected(self):
        data = self.signer.claims(owner_id=OWNER, session_ref=SESSION)
        for update in (None, "", "x", 1, "bad characters!?"):
            test_data = data.copy()
            if update is None:
                del test_data["jti"]
            else:
                test_data["jti"] = update
            with self.assertRaises(TrustRejected):
                self.check(self.signer.sign(test_data))

    def test_TRU07_actual_bytes_query_order_case_body_method_path(self):
        body = b'{"unicode":"\\u00e9","amount":10}'
        path = b"/fixture/%2F"
        query = b"b=2&a=%2f"
        signed = self.signer.sign(self.signer.claims(
            owner_id=OWNER, session_ref=SESSION, body=body,
            path=path, query=query,
        ))
        self.check(signed, path=path, query=query, body=body)
        changes = (
            ("GET", path, query, body),
            ("POST", b"/fixture/%2f", query, body),
            ("POST", path, b"a=%2f&b=2", body),
            ("POST", path, b"b=2&a=%2F", body),
            ("POST", path, query, '{"unicode":"é","amount":10}'.encode("utf-8")),
            ("POST", path, query, body + b" "),
        )
        for method, p, q, b in changes:
            with self.subTest(kind="wire bytes"):
                with self.assertRaises(TrustRejected):
                    self.check(signed, method=method, path=p, query=q, body=b)

    def test_TRU08_claim_fields_cannot_choose_owner_epoch_generation(self):
        for key, value in (("owner_id", "other_owner"),
                           ("epoch", 1), ("generation", 1),
                           ("session_ref", "y"*43)):
            data = self.signer.claims(owner_id=OWNER, session_ref=SESSION)
            # Attack changes a signed claim without re-signing.
            signed = self.signer.sign(data)
            parts = signed.split(".")
            # Attempted JWT payload reserialization invalidates RSA signature.
            import base64, json
            raw = json.loads(base64.urlsafe_b64decode(parts[1]+"="*(-len(parts[1])%4)))
            raw[key] = value
            changed = base64.urlsafe_b64encode(json.dumps(raw).encode()).decode().rstrip("=")
            with self.assertRaises(TrustRejected):
                self.check(".".join((parts[0], changed, parts[2])))

    def test_TRU09_header_spoof_direct_missing_duplicate_and_body_encoding(self):
        good = self.token().encode()
        header = [(b"authorization", b"BFF-Assertion " + good)]
        self.assertTrue(assertion_from_asgi_headers({"headers": header}))
        for headers in (
            [],
            [(b"x-owner-id", b"victim"), *header],
            [(b"x-user-id", b"victim"), *header],
            [(b"x-forwarded-user", b"victim"), *header],
            [*header, *header],
            [(b"authorization", b"Bearer " + good)],
            [(b"authorization", b"BFF-Assertion  " + good)],
            [*header, (b"content-encoding", b"gzip")],
        ):
            with self.subTest(header="negative"):
                with self.assertRaises(TrustRejected):
                    assertion_from_asgi_headers({"headers": headers})

    def test_TRU10_raw_scope_requirement_and_size_bounds(self):
        good = {"method": "POST", "raw_path": b"/fixture",
                "query_string": b"a=1", "headers": []}
        self.assertEqual(wire_request(good, b"ok"),
                         ("POST", b"/fixture", b"a=1", b"ok"))
        with self.assertRaises(TrustRejected):
            wire_request({"method": "POST", "path": "/fixture",
                          "query_string": b"a=1"}, b"ok")
        with self.assertRaises(TrustRejected):
            wire_request(good, b"x"*8193)
        with self.assertRaises(TrustRejected):
            self.check(self.token(), body=b"x"*8193)


if __name__ == "__main__":
    unittest.main(verbosity=2)
