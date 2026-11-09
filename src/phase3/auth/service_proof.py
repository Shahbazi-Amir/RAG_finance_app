"""API-only BFF service proof: strict static RSA trust, no IdP or product Auth.

No network/JWKS discovery, no keys from token headers, no browser ownership,
no BFF signing credential and no History endpoint integration in this module.
Raw server-side session verifier in signed assertion is SENSITIVE.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import re
import time
from typing import Mapping

import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPublicKey

_MAX_JWT_BYTES = 4096
_MAX_BODY_BYTES = 8192
_MAX_AGE_SECONDS = 30
_ACCEPTED_HEADERS = frozenset(("alg", "kid", "typ"))
_REQUIRED = frozenset((
    "iss", "aud", "iat", "nbf", "exp", "jti", "method",
    "raw_path_sha256", "raw_query_sha256", "body_sha256", "body_len",
    "session_ref", "owner_id", "epoch", "generation",
))
_SHA = re.compile(r"^[0-9a-f]{64}$")
_OPAQUE = re.compile(r"^[A-Za-z0-9_-]{43,256}$")
_JTI = re.compile(r"^[A-Za-z0-9_-]{20,128}$")
_KID = re.compile(r"^[A-Za-z0-9_.-]{1,80}$")
_OWNER = re.compile(r"^[A-Za-z0-9_-]{1,128}$")


class TrustRejected(Exception):
    """Never forward token/header/cryptographic error details to a response."""

    def __str__(self) -> str:
        return "BFF_SERVICE_PROOF_DENIED"


@dataclass(frozen=True, repr=False)
class VerifiedServiceProof:
    """Secret-bearing: only trusted process memory; no repr or logging."""

    issuer: str
    jti: str
    expires_at: int
    session_ref: str
    owner_id: str
    epoch: int
    generation: int

    def __repr__(self) -> str:
        return "VerifiedServiceProof(<redacted>)"


class BFFServiceVerifier:
    """RSA public keys provisioned out-of-band; fail closed on absent/malformed config.

    The 'issuer', 'audience' and 'kid' are explicit fixed deployment
    allowlists, never taken from a browser or decoded unverified payload.
    Only RS256 with >=2048-bit RSA public keys is allowed. No network access.
    """

    def __init__(self, *, issuer: str, audience: str, public_keys: Mapping[str, bytes]):
        if (not isinstance(issuer, str) or not issuer.startswith("urn:")
                or len(issuer) > 180 or not isinstance(audience, str)
                or not audience.startswith("urn:") or len(audience) > 180
                or not isinstance(public_keys, Mapping) or not public_keys):
            raise TrustRejected() from None
        verified_keys: dict[str, RSAPublicKey] = {}
        try:
            for kid, pem in public_keys.items():
                if not isinstance(kid, str) or not _KID.fullmatch(kid):
                    raise TrustRejected()
                if not isinstance(pem, bytes):
                    raise TrustRejected()
                key = serialization.load_pem_public_key(pem)
                if not isinstance(key, RSAPublicKey) or key.key_size < 2048:
                    raise TrustRejected()
                verified_keys[kid] = key
        except (TypeError, ValueError, TrustRejected):
            raise TrustRejected() from None
        self._issuer = issuer
        self._audience = audience
        self._keys = verified_keys

    def verify(self, compact_jwt: str, *, method: str, raw_path: bytes,
               raw_query: bytes, raw_body: bytes, now: int | None = None) -> VerifiedServiceProof:
        if (not isinstance(compact_jwt, str) or len(compact_jwt) > _MAX_JWT_BYTES
                or compact_jwt.count(".") != 2
                or not isinstance(method, str) or not method.isascii()
                or not re.fullmatch(r"[A-Z]{3,8}", method)
                or not isinstance(raw_path, bytes) or not raw_path.startswith(b"/")
                or not isinstance(raw_query, bytes) or not isinstance(raw_body, bytes)
                or len(raw_body) > _MAX_BODY_BYTES):
            raise TrustRejected() from None
        try:
            header = jwt.get_unverified_header(compact_jwt)
            if (set(header) != _ACCEPTED_HEADERS or header.get("typ") != "JWT"
                    or header.get("alg") != "RS256"
                    or not isinstance(header.get("kid"), str)
                    or header["kid"] not in self._keys):
                raise TrustRejected()
            payload = jwt.decode(
                compact_jwt, self._keys[header["kid"]], algorithms=["RS256"],
                issuer=self._issuer, audience=self._audience,
                options={"require": list(_REQUIRED), "strict_aud": True},
                leeway=0,
            )
            if set(payload) != _REQUIRED:
                raise TrustRejected()
            timestamp = int(time.time()) if now is None else now
            if not isinstance(timestamp, int) or isinstance(timestamp, bool):
                raise TrustRejected()
            for field in ("iat", "nbf", "exp", "epoch", "generation", "body_len"):
                v = payload[field]
                if type(v) is not int or v < 0:
                    raise TrustRejected()
            if not (payload["iat"] <= timestamp and payload["nbf"] <= timestamp
                    and timestamp < payload["exp"]
                    and 0 < payload["exp"] - payload["iat"] <= _MAX_AGE_SECONDS
                    and timestamp - payload["iat"] <= _MAX_AGE_SECONDS):
                raise TrustRejected()
            if (not isinstance(payload["iss"], str) or payload["iss"] != self._issuer
                    or type(payload["aud"]) is not str or payload["aud"] != self._audience
                    or type(payload["jti"]) is not str or not _JTI.fullmatch(payload["jti"])
                    or type(payload["session_ref"]) is not str
                    or not _OPAQUE.fullmatch(payload["session_ref"])
                    or type(payload["owner_id"]) is not str
                    or not _OWNER.fullmatch(payload["owner_id"])
                    or payload["method"] != method or payload["body_len"] != len(raw_body)):
                raise TrustRejected()
            for name, original in (
                ("raw_path_sha256", raw_path),
                ("raw_query_sha256", raw_query),
                ("body_sha256", raw_body),
            ):
                digest = payload[name]
                if not isinstance(digest, str) or not _SHA.fullmatch(digest):
                    raise TrustRejected()
                if digest != sha256(original).hexdigest():
                    raise TrustRejected()
            return VerifiedServiceProof(
                self._issuer, payload["jti"], payload["exp"],
                payload["session_ref"], payload["owner_id"],
                payload["epoch"], payload["generation"],
            )
        except (jwt.PyJWTError, ValueError, TypeError, KeyError, TrustRejected):
            raise TrustRejected() from None


def assertion_from_asgi_headers(scope: dict) -> str:
    """Reject duplicate authorization, spoofed owner and ambiguous encoding.

    Only one Authorization: BFF-Assertion <compact JWT>. Nothing is trusted
    from X-Forwarded-User / X-Owner-ID or browser-supplied identity headers.
    """
    try:
        headers = scope["headers"]
        auth = [value for name, value in headers if name.lower() == b"authorization"]
        forbidden = {
            b"x-user-id", b"x-owner-id", b"x-authenticated-user",
            b"x-forwarded-user", b"x-forwarded-owner",
        }
        if (len(auth) != 1 or any(name.lower() in forbidden for name, _ in headers)
                or any(name.lower() == b"content-encoding" and
                       value.lower() not in (b"identity",) for name, value in headers)):
            raise TrustRejected()
        raw = auth[0]
        if len(raw) > _MAX_JWT_BYTES + 32:
            raise TrustRejected()
        # Prevent alternate whitespace, comma-joining duplicate headers and
        # mixed case scheme ambiguity; no claim value ever enters logs.
        prefix = b"BFF-Assertion "
        if not raw.startswith(prefix) or raw.count(b" ") != 1:
            raise TrustRejected()
        return raw[len(prefix):].decode("ascii")
    except (ValueError, UnicodeDecodeError, TypeError, KeyError, TrustRejected):
        raise TrustRejected() from None


def wire_request(scope: dict, body: bytes) -> tuple[str, bytes, bytes, bytes]:
    """Bind exact ASGI raw-path/query/body bytes, not decoded or sorted query.

    The reverse proxy MUST preserve these bytes in scope.raw_path. Normalized
    decoded request.url/path, JSON re-serialization and percent-decoding are
    deliberately not part of this contract.
    """
    try:
        method = scope["method"]
        path = scope["raw_path"]
        query = scope["query_string"]
        if (not isinstance(path, bytes) or not isinstance(query, bytes)
                or len(path) > 2048 or len(query) > 4096
                or len(body) > _MAX_BODY_BYTES):
            raise TrustRejected()
        return method, path, query, body
    except (KeyError, TypeError, TrustRejected):
        raise TrustRejected() from None
