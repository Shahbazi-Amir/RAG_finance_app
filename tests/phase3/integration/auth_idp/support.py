"""Private CI-only Keycloak/SMTP helpers. No endpoints in the product.

Never print URL, token, cookie, email body, password or OTP seed. All HTTP
destinations must be loopback; Docker containers have a separate internal-only
network. Credentials are generated in runner temp, never committed.
"""
from __future__ import annotations

import base64
import hashlib
import html
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import queue
import re
import secrets
import threading
from urllib.parse import parse_qs, urlencode, urlparse, urlsplit

import jwt
import requests

BASE = "http://127.0.0.1:8180"
MAIL = "http://127.0.0.1:8025"
CALLBACK = "http://127.0.0.1:8765/callback"
REALM = "auth-idp-ci"
CLIENT = "isolated-oidc-callback"
TIMEOUT = 20


def require_ci() -> None:
    assert os.environ.get("CI") == "true", "CI_ONLY"
    assert os.environ.get("COMPOSE_PROJECT_NAME") == "authidpci", "CI_PROJECT"
    assert os.environ.get("IDP_ENV_FILE") and os.environ.get("IDP_REPORT"), "CI_PATHS"


def credentials() -> dict[str, str]:
    require_ci()
    p = Path(os.environ["IDP_ENV_FILE"])
    assert str(p).startswith(os.environ["RUNNER_TEMP"] + "/")
    return dict(line.split("=", 1) for line in p.read_text().splitlines())


def request(method: str, url: str, **kwargs) -> requests.Response:
    u = urlparse(url)
    assert u.scheme == "http" and u.hostname == "127.0.0.1" and u.port in (8180, 8025), "LOOPBACK_ONLY"
    return requests.request(method, url, timeout=TIMEOUT, allow_redirects=False, **kwargs)


def expect_response(response: requests.Response, statuses: int | tuple[int, ...]) -> requests.Response:
    allowed = {statuses} if isinstance(statuses, int) else set(statuses)
    assert response.status_code in allowed, "UNEXPECTED_HTTP_STATUS"
    return response


def discovery() -> dict:
    value = expect_response(
        request("GET", BASE + f"/realms/{REALM}/.well-known/openid-configuration"), 200
    ).json()
    assert value["issuer"] == BASE + "/realms/" + REALM, "ISSUER_MISMATCH"
    for name in ("authorization_endpoint", "token_endpoint", "jwks_uri", "end_session_endpoint", "userinfo_endpoint"):
        assert urlparse(value[name]).hostname == "127.0.0.1", "ENDPOINT_ESCAPED_LOOPBACK"
    return value


class Admin:
    def __init__(self):
        creds = credentials()
        body = expect_response(request("POST", BASE + "/realms/master/protocol/openid-connect/token",
            data={"grant_type": "password", "client_id": "admin-cli",
                  "username": "ci-bootstrap", "password": creds["IDP_ADMIN_PASSWORD"]}), 200).json()
        self.token = body["access_token"]

    def call(self, method: str, path: str, *, expected: int | tuple[int, ...] = 200, **kwargs):
        response = request(method, BASE + "/admin/realms/" + REALM + path,
            headers={"Authorization": "Bearer " + self.token}, **kwargs)
        return expect_response(response, expected)

    def create_realm(self) -> None:
        data = {
            "realm": REALM, "enabled": True,
            "sslRequired": "none",  # HTTP only inside isolated localhost runner
            "displayName": "Identity candidate CI fixture",
            "registrationAllowed": True,
            "registrationEmailAsUsername": True,
            "loginWithEmailAllowed": True,
            "duplicateEmailsAllowed": False,
            "verifyEmail": True, "resetPasswordAllowed": True,
            "rememberMe": False,
            "bruteForceProtected": True, "failureFactor": 5,
            "waitIncrementSeconds": 5, "maxFailureWaitSeconds": 30,
            "maxDeltaTimeSeconds": 30,
            "passwordPolicy": "length(12) and digits(1) and upperCase(1) and specialChars(1)",
            "accessTokenLifespan": 180,
            "actionTokenGeneratedByAdminLifespan": 180,
            "actionTokenGeneratedByUserLifespan": 180,
            "otpPolicyType": "totp", "otpPolicyAlgorithm": "HmacSHA1",
            "otpPolicyDigits": 6, "otpPolicyPeriod": 30,
            "smtpServer": {
                "host": "mailpit", "port": "1025",
                "from": "idp-only@example.test",
                "fromDisplayName": "Synthetic identity CI",
                "ssl": "false", "starttls": "false", "auth": "false",
            },
        }
        expect_response(request("POST", BASE + "/admin/realms",
            headers={"Authorization": "Bearer " + self.token}, json=data), 201)
        r = self.call("GET", "")
        state = r.json()
        assert state["verifyEmail"] is True and state["bruteForceProtected"] is True
        assert state["registrationEmailAsUsername"] is True
        assert "length(12)" in state["passwordPolicy"]

        client = {
            "clientId": CLIENT, "name": "CI-only callback test",
            "enabled": True, "protocol": "openid-connect",
            "publicClient": True, "standardFlowEnabled": True,
            "directAccessGrantsEnabled": False, "implicitFlowEnabled": False,
            "serviceAccountsEnabled": False,
            "redirectUris": [CALLBACK], "webOrigins": [],
            "attributes": {"pkce.code.challenge.method": "S256"},
        }
        self.call("POST", "/clients", json=client, expected=201)

    def users(self, email: str) -> list:
        return self.call("GET", "/users", params={"email": email, "exact": "true"}).json()

    def user(self, email: str) -> dict:
        users = self.users(email)
        assert len(users) == 1, "EXPECTED_ONE_SYNTHETIC_USER"
        return users[0]

    def create_manager(self, email: str, password: str) -> str:
        user = {"username": email, "email": email,
                "enabled": True, "emailVerified": True,
                "firstName": "Synthetic", "lastName": "Manager",
                "requiredActions": ["CONFIGURE_TOTP"],
                "credentials": [{"type": "password", "temporary": False, "value": password}]}
        self.call("POST", "/users", json=user, expected=201)
        uid = self.user(email)["id"]
        clients = self.call("GET", "/clients", params={"clientId": "realm-management"}).json()
        assert len(clients) == 1
        cid = clients[0]["id"]
        role = self.call("GET", "/clients/" + cid + "/roles/view-users").json()
        self.call("POST", "/users/" + uid + "/role-mappings/clients/" + cid,
                  json=[role], expected=204)
        return uid

    def action_mail(self, uid: str, action: str, ttl: int = 120) -> None:
        self.call("PUT", "/users/" + uid + "/execute-actions-email",
             params={"lifespan": ttl, "client_id": CLIENT, "redirect_uri": CALLBACK},
             json=[action], expected=204)

    def logout_user(self, uid: str) -> None:
        self.call("POST", "/users/" + uid + "/logout", expected=204)


def mail_ids() -> set[str]:
    obj = expect_response(request("GET", MAIL + "/api/v1/messages"), 200).json()
    return {m["ID"] for m in obj.get("messages", [])}


def message_for(email: str, seen: set[str]) -> tuple[str, dict] | None:
    obj = expect_response(request("GET", MAIL + "/api/v1/messages"), 200).json()
    for item in obj.get("messages", []):
        mid = item["ID"]
        if mid in seen:
            continue
        to = item.get("To") or []
        recipients = [v.get("Address", "") for v in to if isinstance(v, dict)]
        if email in recipients:
            detail = expect_response(request("GET", MAIL + "/api/v1/message/" + mid), 200).json()
            return mid, detail
    return None


def action_url(data: dict) -> str:
    body = html.unescape(str(data.get("Text") or "") + " " + str(data.get("HTML") or ""))
    urls = re.findall(r"https?://[^\s<>'\"]+", body)
    for raw in urls:
        value = raw.rstrip(").,;")
        parsed = urlparse(value)
        if parsed.hostname == "127.0.0.1" and parsed.port == 8180 and "/login-actions/action-token" in parsed.path:
            assert "key=" in parsed.query, "MISSING_ACTION_TOKEN"
            return value
    raise AssertionError("NO_ACTION_TOKEN_IN_CAPTURED_LOCAL_EMAIL")


def verifier() -> str:
    return secrets.token_urlsafe(48)


def challenge(value: str) -> str:
    return base64.urlsafe_b64encode(hashlib.sha256(value.encode()).digest()).decode().rstrip("=")


def authorization(config: dict, nonce: str, state: str, proof: str) -> str:
    data = {
        "client_id": CLIENT, "redirect_uri": CALLBACK, "response_type": "code",
        "scope": "openid email profile", "state": state, "nonce": nonce,
        "code_challenge": challenge(proof), "code_challenge_method": "S256",
        "prompt": "login",
    }
    return config["authorization_endpoint"] + "?" + urlencode(data)


def exchange(config: dict, code: str, proof: str, allowed=200):
    result = request("POST", config["token_endpoint"], data={
        "grant_type": "authorization_code", "client_id": CLIENT,
        "redirect_uri": CALLBACK, "code": code, "code_verifier": proof,
    })
    expect_response(result, allowed)
    return result.json() if result.status_code == 200 else None


def refresh(config: dict, value: str) -> int:
    r = request("POST", config["token_endpoint"], data={
        "grant_type": "refresh_token", "client_id": CLIENT, "refresh_token": value,
    })
    return r.status_code


def verify_id(config: dict, token: str, nonce: str):
    jwks = jwt.PyJWKClient(config["jwks_uri"])
    key = jwks.get_signing_key_from_jwt(token).key
    claims = jwt.decode(token, key, algorithms=["RS256"], audience=CLIENT,
        issuer=config["issuer"], options={"require": ["exp", "iat", "iss", "aud", "sub"]})
    assert claims.get("nonce") == nonce, "NONCE_MISMATCH"
    return claims


class Callback(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlsplit(self.path)
        if parsed.path != "/callback":
            self.send_error(404)
            return
        payload = parse_qs(parsed.query, keep_blank_values=True)
        self.server.inbox.put(payload)
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Content-Security-Policy", "default-src 'none'")
        self.end_headers()
        self.wfile.write(b"Isolated CI callback. No product session.")

    def log_message(self, *_):
        pass  # NEVER log a callback URL, authorization code or cookie


class CallbackServer:
    def __enter__(self):
        self.server = ThreadingHTTPServer(("127.0.0.1", 8765), Callback)
        self.server.inbox = queue.Queue()
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        return self

    def __exit__(self, *_):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)

    def next(self):
        try:
            return self.server.inbox.get_nowait()
        except queue.Empty:
            raise AssertionError("NO_ACTUAL_BROWSER_CALLBACK") from None
