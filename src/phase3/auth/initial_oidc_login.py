"""CI-only server OIDC Code+S256 verification to existing Product session primitives.

No FastAPI route, browser cookie, public BFF signer or production IdP configuration
is installed. Caller must provide pinned IdP endpoints and trusted DB role
connections; unverified browser claims MUST NEVER be mapped to an Owner.
"""
from __future__ import annotations

from dataclasses import dataclass
from hmac import compare_digest
from typing import Callable
import secrets

import httpx
import jwt
import psycopg

from src.phase3.storage.postgres import auth_session


class InitialOIDCRejected(Exception):
    """Generic fail-closed error; do not disclose tokens or callback parameters."""

    def __str__(self):
        return "INITIAL_OIDC_REJECTED"


@dataclass(repr=False)
class InitialChallenge:
    """Server-owned one-use state, OIDC nonce and S256 code verifier."""

    state: str
    nonce: str
    code_verifier: str
    used: bool = False

    @classmethod
    def fresh(cls):
        return cls(secrets.token_urlsafe(32), secrets.token_urlsafe(32),
                   secrets.token_urlsafe(48))

    def __repr__(self):
        return "InitialChallenge(<redacted>)"


@dataclass(frozen=True, repr=False)
class VerifiedInitialSession:
    owner_id: str
    issuer: str
    subject: str
    issued: auth_session.Issued

    def __repr__(self):
        return "VerifiedInitialSession(<redacted>)"


def complete_initial_oidc(
    *,
    challenge: InitialChallenge,
    callback: dict,
    oidc: dict,
    client_id: str,
    redirect_uri: str,
    owner_connection: Callable[[], psycopg.Connection],
    session_connection: Callable[[], psycopg.Connection],
    idle_seconds: int = 45,
    absolute_seconds: int = 400,
) -> VerifiedInitialSession:
    """Only issue after actual Keycloak Code exchange + pinned signed ID token.

    Fresh browser authorization must have used server-generated state, nonce
    and S256 PKCE challenge. No user-controlled issuer/sub/owner/epoch inputs.
    Browser callback may contain only Code and state (and optional Keycloak
    iss/session_state); an error or duplicate value is not an authentication.
    """
    if (not isinstance(challenge, InitialChallenge)
            or challenge.used or not isinstance(callback, dict)
            or not isinstance(oidc, dict)):
        raise InitialOIDCRejected() from None

    try:
        state = callback.get("state")
        codes = callback.get("code")
        if ("error" in callback or not isinstance(state, list)
                or not isinstance(codes, list)
                or len(state) != 1 or len(codes) != 1
                or not isinstance(state[0], str)
                or not isinstance(codes[0], str)
                or len(codes[0]) > 2048
                or not codes[0]
                or not compare_digest(state[0], challenge.state)):
            raise InitialOIDCRejected()

        issuer = oidc["issuer"]
        if (not isinstance(issuer, str)
                or not issuer.startswith("http://127.0.0.1:")
                or not isinstance(client_id, str)
                or not isinstance(redirect_uri, str)
                or not redirect_uri.startswith("http://127.0.0.1:")):
            # This module is restricted to the isolated CI, NOT a production
            # validator accepting arbitrary external endpoints or issuers.
            raise InitialOIDCRejected()
        if (oidc["token_endpoint"]
                != issuer + "/protocol/openid-connect/token"
                or oidc["jwks_uri"]
                != issuer + "/protocol/openid-connect/certs"):
            raise InitialOIDCRejected()
        if "iss" in callback and callback["iss"] != [issuer]:
            raise InitialOIDCRejected()

        # Consume one server challenge after state, before remote token
        # exchange. An invalid or replayed Code cannot authorize a second
        # Product issuance even if a callback is submitted repeatedly.
        challenge.used = True
        with httpx.Client(trust_env=False, timeout=15.0,
                          follow_redirects=False) as http:
            token_reply = http.post(oidc["token_endpoint"], data={
                "grant_type": "authorization_code",
                "client_id": client_id,
                "redirect_uri": redirect_uri,
                "code": codes[0],
                "code_verifier": challenge.code_verifier,
            })
        if token_reply.status_code != 200:
            raise InitialOIDCRejected()
        id_token = token_reply.json()["id_token"]
        if not isinstance(id_token, str) or len(id_token) > 16000:
            raise InitialOIDCRejected()
        header = jwt.get_unverified_header(id_token)
        if header.get("alg") != "RS256" or not isinstance(header.get("kid"), str):
            raise InitialOIDCRejected()
        # Fixed, trusted realm JWKS URL; never follow jku/x5u from untrusted
        # JWT headers. Keycloak signs the *real* token obtained via S256.
        signer = jwt.PyJWKClient(oidc["jwks_uri"]).get_signing_key_from_jwt(
            id_token).key
        claims = jwt.decode(
            id_token, signer, algorithms=["RS256"], issuer=issuer,
            audience=client_id,
            options={
                "require": ["iss", "aud", "sub", "exp", "iat", "nonce"],
                "strict_aud": True,
            }, leeway=0)
        if (not isinstance(claims.get("nonce"), str)
                or not compare_digest(claims["nonce"], challenge.nonce)
                or not isinstance(claims.get("sub"), str)
                or not claims["sub"] or len(claims["sub"]) > 255):
            raise InitialOIDCRejected()

        # Only cryptographically VERIFIED IdP issuer and subject reach the
        # immutable Product mapping. Never use email, request owner, or
        # unsigned claims as principal.
        with owner_connection() as conn:
            mapped = auth_session.map_identity(
                conn, claims["iss"], claims["sub"])
        if (not isinstance(mapped, dict)
                or mapped.get("gate") != "open"
                or not isinstance(mapped.get("owner_id"), str)
                or type(mapped.get("epoch")) is not int):
            raise InitialOIDCRejected()
        with session_connection() as conn:
            issued = auth_session.issue(
                conn, mapped["owner_id"], mapped["epoch"],
                idle_seconds=idle_seconds, absolute_seconds=absolute_seconds)
        if (issued.owner_id != mapped["owner_id"]
                or issued.epoch != mapped["epoch"]):
            raise InitialOIDCRejected()
        return VerifiedInitialSession(
            mapped["owner_id"], claims["iss"], claims["sub"], issued)
    except (jwt.PyJWTError, httpx.HTTPError, psycopg.Error, ValueError,
            KeyError, TypeError, AttributeError, InitialOIDCRejected):
        raise InitialOIDCRejected() from None
