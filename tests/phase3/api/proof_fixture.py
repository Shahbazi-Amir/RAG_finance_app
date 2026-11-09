"""CI-only independent synthetic BFF signer. NOT imported by production API.

No private-key export/print or artifact; fresh keypair in each test process.
The verifier deliberately shares no encoder or canonicalization helper.
"""
from __future__ import annotations

from hashlib import sha256
import secrets
import time

import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

ISSUER = "urn:rag-finance:synthetic-bff"
AUDIENCE = "urn:rag-finance:api:internal-ci"
KID = "ci-rsa-1"


class FakeBFFSigner:
    def __init__(self):
        self.private = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        self.public_pem = self.private.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )

    def claims(self, *, owner_id: str, session_ref: str, epoch: int = 0,
               generation: int = 0, method: str = "POST",
               path: bytes = b"/fixture", query: bytes = b"", body: bytes = b"{}",
               duration: int = 20) -> dict:
        now = int(time.time())
        return {
            "iss": ISSUER, "aud": AUDIENCE,
            "iat": now, "nbf": now, "exp": now + duration,
            "jti": secrets.token_urlsafe(24),
            "method": method,
            "raw_path_sha256": sha256(path).hexdigest(),
            "raw_query_sha256": sha256(query).hexdigest(),
            "body_sha256": sha256(body).hexdigest(),
            "body_len": len(body),
            "session_ref": session_ref, "owner_id": owner_id,
            "epoch": epoch, "generation": generation,
        }

    def sign(self, claims: dict, *, kid: str = KID, key=None,
             extra_headers: dict | None = None) -> str:
        headers = {"kid": kid, "typ": "JWT"}
        if extra_headers:
            headers.update(extra_headers)
        return jwt.encode(claims, self.private if key is None else key,
                          algorithm="RS256", headers=headers)
