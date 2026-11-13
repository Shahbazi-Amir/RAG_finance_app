"""API-only, isolated pre-session mTLS+signed Bootstrap and 009 initial OIDC RPC.

No browser route, production IdP configuration, BFF cookie or Reset/C2.
Only a TLS endpoint with CERT_REQUIRED may supply peer_der. All SQL uses
existing function-only 009 roles and 005 durable JTI; never direct tables.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from hmac import compare_digest
from typing import Callable, Mapping
import base64
import json
import re
import secrets
import time
import uuid

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPublicKey
import httpx
import jwt
import psycopg
from psycopg.rows import dict_row

from src.phase3.storage.postgres import auth_session
from src.phase3.storage.postgres.service_replay import PostgresDurableReplayStore

PURPOSE = "initial-oidc-bootstrap-v1"
PATH_ROOT = "/internal/auth/oidc/v1/"
OPS = {"start", "complete", "status", "ack", "abort"}
HEX = re.compile(r"^[0-9a-f]{64}$")
JTI = re.compile(r"^[A-Za-z0-9_-]{20,128}$")
HEADERS = {"typ", "alg", "kid"}
FIELDS = {"iss", "aud", "iat", "nbf", "exp", "jti", "purpose", "method",
          "raw_path_sha256", "raw_query_sha256", "body_sha256", "body_len",
          "attempt_id", "initiator_sha256"}


class BootstrapDenied(Exception):
    """Never return the signing, Code, IdP, SQL or Product verifier detail."""
    def __init__(self, status=401):
        self.status = status

    def __str__(self):
        return "INITIAL_BOOTSTRAP_DENIED"


@dataclass(frozen=True, repr=False)
class ServiceAttempt:
    issuer: str
    jti: str
    expires_at: int
    attempt_id: str
    initiator_sha256: str
    principal: str

    def __repr__(self):
        return "ServiceAttempt(<redacted>)"


def _json(data):
    return json.dumps(data, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True).encode("ascii")


def _digest(data):
    return sha256(data).hexdigest()


def _uuid(value):
    try:
        return uuid.UUID(value)
    except (ValueError, TypeError, AttributeError):
        raise BootstrapDenied(422) from None


def _fields(data, required, optional=frozenset()):
    if not isinstance(data, dict) or not set(required).issubset(data) or (
            set(data) - set(required) - set(optional)):
        raise BootstrapDenied(422)


class BootstrapOIDC:
    """One config per deployed IdP; client cert principal and RSA keys pinned.

    All workers must share the same Fernet key, issuer/client/redirect config
    and primary PostgreSQL. Encrypted sealed challenge is carried by trusted
    BFF server only; 009 prevents second Code redemption across workers.
    """

    def __init__(self, *, service_issuer, audience, service_keys: Mapping[str, bytes],
                 cert_fingerprints: Mapping[str, str], seal_keys: Mapping[str, bytes], active_seal_kid: str,
                 db_dsn: Mapping[str, str], oidc: dict, client_id: str,
                 redirect_uri: str, exchange: Callable | None = None):
        if (not isinstance(service_issuer, str) or not service_issuer.startswith("urn:")
                or len(service_issuer) > 128 or not audience.startswith("urn:")
                or not cert_fingerprints or not service_keys or not db_dsn):
            raise BootstrapDenied()
        self.issuer = service_issuer
        self.audience = audience
        self.fingerprints = dict(cert_fingerprints)
        self.keys = {}
        try:
            for kid, pem in service_keys.items():
                key = serialization.load_pem_public_key(pem)
                if (not isinstance(key, RSAPublicKey) or key.key_size < 2048
                        or not re.fullmatch(r"[A-Za-z0-9_.-]{1,80}", kid)):
                    raise ValueError()
                self.keys[kid] = key
            if not isinstance(seal_keys, Mapping) or active_seal_kid not in seal_keys:
                raise ValueError()
            self.material_keys = {}
            for kid, raw in seal_keys.items():
                if not isinstance(kid, str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,32}', kid):
                    raise ValueError()
                self.material_keys[kid] = Fernet(raw)
            self.active_material_kid = active_seal_kid
        except (ValueError, TypeError):
            raise BootstrapDenied() from None
        self.dsn = dict(db_dsn)
        if set(self.dsn) != {"replay", "bootstrap", "claim_reader", "issuer", "mapper", "binder", "reader"}:
            raise BootstrapDenied()
        self.oidc = dict(oidc)
        self.client_id = client_id
        self.redirect_uri = redirect_uri
        expected = self.oidc.get("issuer")
        if (not isinstance(expected, str) or not expected.startswith("http://127.0.0.1:")
                or self.oidc.get("token_endpoint")
                   != expected + "/protocol/openid-connect/token"
                or self.oidc.get("jwks_uri")
                   != expected + "/protocol/openid-connect/certs"
                or not self.oidc.get("authorization_endpoint", "").startswith(expected + "/")
                or not redirect_uri.startswith("http://127.0.0.1:")):
            # Strict CI-only loopback policy. Production requires separate review.
            raise BootstrapDenied()
        self.exchange = exchange if exchange is not None else self._redeem

    def _conn(self, role):
        return psycopg.connect(self.dsn[role], autocommit=True,
                               row_factory=dict_row, connect_timeout=5)

    def _call(self, role, sql, values):
        with self._conn(role) as c:
            with c.transaction():
                return c.execute(sql, values).fetchone()["value"]

    def _auth(self, peer_der, header, method, path, body):
        if (not isinstance(peer_der, bytes) or not peer_der or method != "POST"
                or not isinstance(path, str) or path not in
                    {PATH_ROOT + x for x in OPS}
                or not isinstance(header, str) or not header.startswith("Bootstrap ")
                or header.count(" ") != 1 or len(header) > 4150
                or len(body) > 8192):
            raise BootstrapDenied()
        if self.fingerprints.get(self.issuer) != _digest(peer_der):
            raise BootstrapDenied()
        token = header[len("Bootstrap "):]
        try:
            h = jwt.get_unverified_header(token)
            if (set(h) != HEADERS or h["typ"] != "JWT" or h["alg"] != "RS256"
                    or h["kid"] not in self.keys):
                raise BootstrapDenied()
            p = jwt.decode(token, self.keys[h["kid"]], algorithms=["RS256"],
                           issuer=self.issuer, audience=self.audience,
                           options={"require": list(FIELDS), "strict_aud": True},
                           leeway=0)
            now = int(time.time())
            if (set(p) != FIELDS
                    or any(type(p[k]) is not int or p[k] < 0 for k in
                           ("iat", "nbf", "exp", "body_len"))
                    or not p["iat"] <= now or not p["nbf"] <= now < p["exp"]
                    or not 0 < p["exp"] - p["iat"] <= 30
                    or now - p["iat"] > 30
                    or p["purpose"] != PURPOSE or p["method"] != method
                    or not isinstance(p["jti"], str) or not JTI.fullmatch(p["jti"])
                    or p["raw_path_sha256"] != _digest(path.encode("ascii"))
                    or p["raw_query_sha256"] != _digest(b"")
                    or p["body_sha256"] != _digest(body)
                    or p["body_len"] != len(body)
                    or not isinstance(p["attempt_id"], str)
                    or not isinstance(p["initiator_sha256"], str)
                    or not HEX.fullmatch(p["initiator_sha256"])):
                raise BootstrapDenied()
            _uuid(p["attempt_id"])
            return ServiceAttempt(p["iss"], p["jti"], p["exp"], p["attempt_id"],
                                  p["initiator_sha256"], p["iss"])
        except (jwt.PyJWTError, ValueError, KeyError, TypeError, BootstrapDenied):
            raise BootstrapDenied() from None

    def handle(self, *, peer_der, authorization, method, path, raw_body):
        """Call ONLY from authenticated TLS listener; no HTTP retry on unknown."""
        proof = self._auth(peer_der, authorization, method, path, raw_body)
        try:
            def no_duplicates(items):
                obj = {}
                for key, val in items:
                    if key in obj:
                        raise ValueError()
                    obj[key] = val
                return obj
            payload = json.loads(raw_body.decode("utf-8"),
                                 object_pairs_hook=no_duplicates)
            if not isinstance(payload, dict):
                raise BootstrapDenied(422)
            if (payload.get("attempt_id") != proof.attempt_id
                    or payload.get("initiator_sha256") != proof.initiator_sha256):
                raise BootstrapDenied()
            # Replay 005 is a different DB connection/short COMMIT from 009.
            # Any retransmission needs a NEW service JTI; one login Attempt
            # never re-exchanges even with another valid new JTI.
            try:
                with self._conn("replay") as c:
                    with c.transaction():
                        if PostgresDurableReplayStore().consume(c, proof) is not True:
                            raise BootstrapDenied()
            except psycopg.errors.UniqueViolation:
                # Durable 005 JTI collision is an invalid replayed service
                # identity, not a retryable product operation conflict.
                raise BootstrapDenied(401) from None
            operation = path.rsplit("/", 1)[1]
            return getattr(self, "_" + operation)(payload, proof)
        except BootstrapDenied:
            raise
        except (psycopg.Error, ValueError, TypeError, KeyError, RuntimeError,
                UnicodeError, json.JSONDecodeError):
            raise BootstrapDenied(409) from None

    def _seal_material(self, kind, value, ctx):
        kid = self.active_material_kid
        data = {**ctx, "kind": kind, "value": value}
        return b"v1." + kid.encode() + b"." + self.material_keys[kid].encrypt(_json(data))

    def _open_material(self, envelope, kind, ctx, row):
        if not isinstance(envelope, bytes) or len(envelope) > 4096:
            raise BootstrapDenied(409)
        try:
            v, kid, blob = envelope.split(b".", 2)
            if v != b"v1" or not re.fullmatch(rb"[A-Za-z0-9_-]{1,32}", kid):
                raise ValueError()
            key = self.material_keys.get(kid.decode("ascii"))
            if key is None:
                raise BootstrapDenied(409)
            data = json.loads(key.decrypt(blob, ttl=190))
        except (ValueError, TypeError, UnicodeError, InvalidToken):
            raise BootstrapDenied(409) from None
        if (not isinstance(data, dict)
                or set(data) != set(ctx) | {"kind", "value"}
                or data.get("kind") != kind
                or not isinstance(data.get("value"), str)
                or not 32 <= len(data["value"]) <= 256
                or any(data.get(k) != v for k, v in ctx.items())
                or data["expires_at"] <= int(time.time())):
            raise BootstrapDenied(409)
        if abs(row["expires_at"].timestamp()-data["expires_at"]) > 5:
            raise BootstrapDenied(409)
        return data["value"]

    def _start(self, p, proof):
        _fields(p, {"attempt_id", "initiator_sha256", "bff_attempt_id", "start_key"})
        bff_id = str(_uuid(p["bff_attempt_id"]))
        if not isinstance(p["start_key"], str) or not 1 <= len(p["start_key"]) <= 128:
            raise BootstrapDenied(422)
        state = secrets.token_urlsafe(32)
        nonce = secrets.token_urlsafe(32)
        verifier = secrets.token_urlsafe(48)
        state_hash = _digest(state.encode("ascii"))
        context = {
            "version": 1, "attempt_id": proof.attempt_id,
            "bff_principal": proof.principal, "bff_attempt_id": bff_id,
            "initiator_sha256": proof.initiator_sha256, "state_sha256": state_hash,
            "issuer": self.oidc["issuer"], "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "authorization_endpoint": self.oidc["authorization_endpoint"],
            "token_endpoint": self.oidc["token_endpoint"],
            "jwks_uri": self.oidc["jwks_uri"],
            "expires_at": int(time.time()) + 180,
        }
        pkce = base64.urlsafe_b64encode(sha256(verifier.encode("ascii")).digest()).decode("ascii").rstrip("=")
        saved = self._call("bootstrap", """SELECT auth_l1.start_initial_login_attempt(
          %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) AS value""", (
            _uuid(proof.attempt_id), proof.principal, _uuid(bff_id), p["start_key"],
            _digest(_json(p)), state_hash, proof.initiator_sha256,
            self.oidc["issuer"],
            self._seal_material("pkce", verifier, context),
            self._seal_material("nonce", nonce, context), 180))
        if saved is not True:
            raise BootstrapDenied(409)
        from urllib.parse import urlencode
        params = {"response_type": "code", "client_id": self.client_id,
                  "redirect_uri": self.redirect_uri, "scope": "openid email",
                  "state": state, "nonce": nonce,
                  "code_challenge": pkce, "code_challenge_method": "S256",
                  "prompt": "login"}
        # nonce and public S256 challenge necessarily appear in IdP authorize URL.
        # No raw PKCE verifier, stored nonce envelope or BFF continuation exists.
        return 201, {"attempt_id": proof.attempt_id, "state": state,
                     "authorize_url": self.oidc["authorization_endpoint"] + "?" + urlencode(params)}

    def _claim_material(self, p, proof):
        """No IdP HTTP permitted before the same 010 Claim COMMIT succeeds."""
        with self._conn("claim_reader") as c:
            with c.transaction():
                row = c.execute("""SELECT * FROM
                  auth_l1.claim_initial_login_exchange_material(
                  %s,%s,%s,%s,%s)""", (
                    _uuid(proof.attempt_id), proof.principal,
                    _uuid(p["bff_attempt_id"]), proof.initiator_sha256,
                    _digest(p["state"].encode("ascii")))).fetchone()
                if row is None:
                    raise BootstrapDenied(409)
            # This return is reached only after COMMIT acknowledgement.
            return row

    def _redeem(self, code, verifier):
        with httpx.Client(timeout=15, trust_env=False, follow_redirects=False) as c:
            return c.post(self.oidc["token_endpoint"], data={
                "grant_type": "authorization_code", "client_id": self.client_id,
                "redirect_uri": self.redirect_uri, "code": code,
                "code_verifier": verifier})

    def _validate_idp(self, reply, nonce):
        if reply.status_code != 200:
            raise BootstrapDenied(409)
        id_token = reply.json().get("id_token")
        if not isinstance(id_token, str) or len(id_token) > 16000:
            raise BootstrapDenied()
        hdr = jwt.get_unverified_header(id_token)
        if hdr.get("alg") != "RS256" or not isinstance(hdr.get("kid"), str):
            raise BootstrapDenied()
        signing_key = jwt.PyJWKClient(self.oidc["jwks_uri"]).get_signing_key_from_jwt(
            id_token).key
        claims = jwt.decode(id_token, signing_key, algorithms=["RS256"],
                            issuer=self.oidc["issuer"], audience=self.client_id,
                            options={"require": ["iss", "aud", "sub", "exp",
                                                 "iat", "nonce"],
                                     "strict_aud": True}, leeway=0)
        if (claims.get("nonce") != nonce or not isinstance(claims.get("sub"), str)
                or not 1 <= len(claims["sub"]) <= 255
                or claims.get("email_verified") is not True):
            # Missing/false email Verified => NO Owner mapping / NO session.
            raise BootstrapDenied(403)
        return claims["iss"], claims["sub"]

    def _complete(self, p, proof):
        _fields(p, {"attempt_id", "initiator_sha256", "continuation",
                    "state", "code"}, {"callback_issuer"})
        ctx = self._unseal(p, proof)
        if (p["state"] != ctx["state"] or not isinstance(p["code"], str)
                or not p["code"] or len(p["code"]) > 2048
                or p.get("callback_issuer", self.oidc["issuer"]) != self.oidc["issuer"]):
            raise BootstrapDenied()
        self._call("bootstrap", """SELECT auth_l1.claim_initial_login_exchange(
          %s,%s,%s,%s) AS value""", (
            _uuid(proof.attempt_id), proof.principal, proof.initiator_sha256,
            _digest(ctx["state"].encode())))
        # The claim above COMMITS before any IdP request. No DB TX spans HTTP.
        try:
            reply = self.exchange(p["code"], ctx["code_verifier"])
        except (httpx.HTTPError, OSError, TimeoutError):
            self._call("bootstrap", """SELECT auth_l1.mark_initial_login_unknown(
                %s,%s,%s) AS value""", (
                _uuid(proof.attempt_id), proof.principal, proof.initiator_sha256))
            return 202, {"state": "UNKNOWN_RECONCILIATION_REQUIRED"}
        try:
            issuer, sub = self._validate_idp(reply, ctx["nonce"])
        except (jwt.PyJWTError, ValueError, KeyError, TypeError):
            raise BootstrapDenied(403) from None
        with self._conn("mapper") as c:
            mapped = auth_session.map_identity(c, issuer, sub)
        if (mapped.get("gate") != "open" or type(mapped.get("epoch")) is not int):
            raise BootstrapDenied(403)
        # 009 verifies the exact immutable IdP (iss,sub) -> mapped Owner and
        # Owner epoch/gate AGAIN under Owner FOR UPDATE, before pending issue.
        opaque = secrets.token_urlsafe(32)
        issued = self._call("issuer", """SELECT auth_l1.issue_initial_login_pending(
          %s,%s,%s,%s,%s,%s,%s,%s,%s,%s) AS value""", (
            _uuid(proof.attempt_id), proof.principal, proof.initiator_sha256,
            mapped["owner_id"], issuer, sub, mapped["epoch"],
            _digest(opaque.encode("ascii")), 120, 500))
        return 201, {"state": "ISSUED_PENDING_BINDING", "attempt_id": proof.attempt_id,
                     "owner_id": issued["owner_id"], "epoch": issued["epoch"],
                     "generation": issued["generation"],
                     "receipt_id": str(issued["receipt_id"]),
                     "session_verifier": opaque,
                     "idle_expires_at": issued["idle_expires_at"],
                     "absolute_expires_at": issued["absolute_expires_at"]}

    def _status(self, p, proof):
        _fields(p, {"attempt_id", "initiator_sha256"})
        status = self._call("reader", """SELECT auth_l1.status_initial_login_attempt(
          %s,%s,%s) AS value""", (
            _uuid(proof.attempt_id), proof.principal, proof.initiator_sha256))
        if status is None:
            raise BootstrapDenied(404)
        return 200, status  # SQL excludes verifier, Owner, Receipt and ciphertext.

    def _ack(self, p, proof):
        _fields(p, {"attempt_id", "initiator_sha256", "receipt_id",
                    "owner_id", "epoch", "alias_sha256"})
        if (type(p["epoch"]) is not int or not isinstance(p["alias_sha256"], str)
                or not HEX.fullmatch(p["alias_sha256"])):
            raise BootstrapDenied(422)
        self._call("binder", """SELECT auth_l1.ack_initial_login_binding(
          %s,%s,%s,%s,%s,%s,%s) AS value""", (
            _uuid(proof.attempt_id), _uuid(p["receipt_id"]), proof.principal,
            proof.initiator_sha256, p["owner_id"], p["epoch"], p["alias_sha256"]))
        return 200, {"state": "ACTIVE"}

    def _abort(self, p, proof):
        _fields(p, {"attempt_id", "initiator_sha256", "receipt_id",
                    "owner_id", "epoch"})
        if type(p["epoch"]) is not int:
            raise BootstrapDenied(422)
        self._call("binder", """SELECT auth_l1.abort_initial_login_binding(
          %s,%s,%s,%s,%s,%s) AS value""", (
            _uuid(proof.attempt_id), _uuid(p["receipt_id"]), proof.principal,
            proof.initiator_sha256, p["owner_id"], p["epoch"]))
        return 200, {"state": "ABORTED"}
