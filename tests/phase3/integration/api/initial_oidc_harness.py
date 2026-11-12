"""Disposable Keycloak 26.8.2 server harness for initial Code+S256 login.

This is TEST-ONLY. A genuine HTTP callback and Keycloak OIDC token exchange
occur on loopback; synthetic credentials live only in memory. Keycloak uses its
own ephemeral H2 database; Product uses the independent PostgreSQL 17.11 CI
database with unchanged Migration 003. Never log codes, tokens, URLs or secrets.
"""
from __future__ import annotations

from html.parser import HTMLParser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from hashlib import sha256
from queue import Empty, Queue
from threading import Thread
from urllib.parse import parse_qs, urljoin, urlsplit
import base64
import json
import secrets
import socket
import subprocess
import time

import httpx

from src.phase3.auth.initial_oidc_login import InitialChallenge


class IsolatedOIDCFailure(RuntimeError):
    def __str__(self):
        return "ISOLATED_INITIAL_OIDC_FAILED"


class LoginForm(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.active = False
        self.action = None
        self.hidden = {}

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        if tag == "form" and values.get("id") == "kc-form-login":
            self.active = True
            self.action = values.get("action")
        elif self.active and tag == "input":
            if (values.get("type") == "hidden" and values.get("name")):
                self.hidden[values["name"]] = values.get("value", "")

    def handle_endtag(self, tag):
        if tag == "form":
            self.active = False


class CaptureHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlsplit(self.path)
        if parsed.path != "/callback":
            self.send_error(404)
            return
        params = parse_qs(parsed.query, keep_blank_values=True)
        self.server.responses.put(params)
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Content-Security-Policy", "default-src 'none'")
        self.end_headers()
        self.wfile.write(b"Ephemeral callback captured.")

    def log_message(self, *args):
        pass


class CallbackHarness:
    def __init__(self):
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), CaptureHandler)
        self.server.responses = Queue()
        self.url = ("http://127.0.0.1:"
                    + str(self.server.server_address[1]) + "/callback")
        self.thread = Thread(target=self.server.serve_forever, daemon=True)

    def start(self):
        self.thread.start()

    def next(self):
        try:
            return self.server.responses.get(timeout=8)
        except Empty:
            raise IsolatedOIDCFailure() from None

    def stop(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)


class DisposableKeycloak:
    IMAGE = "quay.io/keycloak/keycloak:26.8.2"
    CLIENT_ID = "initial-login-ci"
    REALM = "initial-login-ci"

    def __init__(self):
        suffix = secrets.token_hex(6)
        self.network = "initial-oidc-" + suffix
        self.container = "initial-keycloak-" + suffix
        self.password = secrets.token_urlsafe(36)
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            self.port = sock.getsockname()[1]
        self.base = "http://127.0.0.1:" + str(self.port)
        self.callback = CallbackHarness()
        self.oidc = None
        self.accounts = {}
        self.started = False
        self.network_created = False

    @staticmethod
    def docker(*args, capture=False, timeout=180):
        try:
            return subprocess.run(
                ["docker", *args], check=True, timeout=timeout,
                stdout=subprocess.PIPE if capture else subprocess.DEVNULL,
                stderr=subprocess.DEVNULL, text=True,
            ).stdout
        except (OSError, subprocess.CalledProcessError,
                subprocess.TimeoutExpired):
            raise IsolatedOIDCFailure() from None

    def start(self):
        try:
            self.callback.start()
            self.docker("network", "create", "--driver",
                        "bridge", self.network, timeout=30)
            self.network_created = True
            self.docker(
                "run", "--detach", "--name", self.container,
                "--network", self.network, "--pull", "always",
                "--memory", "1536m", "--pids-limit", "512",
                "--cap-drop", "ALL", "--security-opt", "no-new-privileges",
                "-p", "127.0.0.1:" + str(self.port) + ":8080",
                "-e", "KC_BOOTSTRAP_ADMIN_USERNAME=ci-bootstrap",
                "-e", "KC_BOOTSTRAP_ADMIN_PASSWORD=" + self.password,
                self.IMAGE, "start-dev", timeout=260,
            )
            self.started = True
            # Verify exactly one loopback binding and one disposable network.
            inspected = json.loads(self.docker("inspect", self.container,
                                               capture=True, timeout=30))[0]
            bindings = inspected["HostConfig"]["PortBindings"]
            if (set(bindings) != {"8080/tcp"}
                    or len(bindings["8080/tcp"]) != 1
                    or bindings["8080/tcp"][0]["HostIp"] != "127.0.0.1"
                    or bindings["8080/tcp"][0]["HostPort"] != str(self.port)
                    or set(inspected["NetworkSettings"]["Networks"])
                       != {self.network}):
                raise IsolatedOIDCFailure()
            with httpx.Client(trust_env=False, timeout=4) as client:
                for _ in range(105):
                    try:
                        response = client.get(
                            self.base + "/realms/master/.well-known/openid-configuration")
                        if response.status_code == 200:
                            break
                    except httpx.HTTPError:
                        pass
                    time.sleep(2)
                else:
                    raise IsolatedOIDCFailure()
            self.setup_realm()
        except BaseException:
            self.stop()
            raise

    def stop(self):
        if self.started:
            try:
                self.docker("rm", "-f", self.container, timeout=45)
            except IsolatedOIDCFailure:
                pass
            self.started = False
        if self.network_created:
            try:
                self.docker("network", "rm", self.network, timeout=40)
            except IsolatedOIDCFailure:
                pass
            self.network_created = False
        if self.callback.thread.is_alive():
            self.callback.stop()
        else:
            self.callback.server.server_close()

    def setup_realm(self):
        with httpx.Client(trust_env=False, timeout=20,
                          follow_redirects=False) as client:
            reply = client.post(
                self.base + "/realms/master/protocol/openid-connect/token",
                data={"grant_type": "password", "client_id": "admin-cli",
                      "username": "ci-bootstrap", "password": self.password})
            if reply.status_code != 200:
                raise IsolatedOIDCFailure()
            admin = reply.json()["access_token"]
            headers = {"Authorization": "Bearer " + admin}
            reply = client.post(self.base + "/admin/realms", headers=headers,
                json={"realm": self.REALM, "enabled": True,
                      "sslRequired": "none", "registrationAllowed": False,
                      "verifyEmail": False, "resetPasswordAllowed": False,
                      "bruteForceProtected": False})
            if reply.status_code != 201:
                raise IsolatedOIDCFailure()
            reply = client.post(
                self.base + "/admin/realms/" + self.REALM + "/clients",
                headers=headers,
                json={"clientId": self.CLIENT_ID,
                      "enabled": True, "protocol": "openid-connect",
                      "publicClient": True, "standardFlowEnabled": True,
                      "directAccessGrantsEnabled": False,
                      "implicitFlowEnabled": False,
                      "serviceAccountsEnabled": False,
                      "redirectUris": [self.callback.url],
                      "webOrigins": [],
                      "attributes": {"pkce.code.challenge.method": "S256"}})
            if reply.status_code != 201:
                raise IsolatedOIDCFailure()
            for label in ("A", "B"):
                email = "synthetic-initial-" + label.lower() + "-"
                email += secrets.token_hex(6) + "@example.test"
                password = "Az9!" + secrets.token_urlsafe(24)
                reply = client.post(
                    self.base + "/admin/realms/" + self.REALM + "/users",
                    headers=headers,
                    json={"username": email, "email": email,
                          "enabled": True, "emailVerified": True,
                          "firstName": "Synthetic", "lastName": "Initial",
                          "requiredActions": [],
                          "credentials": [{"type": "password",
                                           "temporary": False,
                                           "value": password}]})
                if reply.status_code != 201:
                    raise IsolatedOIDCFailure()
                users = client.get(
                    self.base + "/admin/realms/" + self.REALM + "/users",
                    headers=headers, params={"email": email, "exact": "true"})
                rows = users.json() if users.status_code == 200 else []
                if len(rows) != 1:
                    raise IsolatedOIDCFailure()
                self.accounts[label] = {
                    "email": email, "password": password, "sub": rows[0]["id"]}
            response = client.get(
                self.base + "/realms/" + self.REALM
                + "/.well-known/openid-configuration")
            if response.status_code != 200:
                raise IsolatedOIDCFailure()
            self.oidc = response.json()
            issuer = self.base + "/realms/" + self.REALM
            if self.oidc.get("issuer") != issuer:
                raise IsolatedOIDCFailure()
            for field in ("authorization_endpoint", "token_endpoint", "jwks_uri"):
                if not self.oidc[field].startswith(issuer + "/"):
                    raise IsolatedOIDCFailure()

    def actual_login_callback(self, label):
        if label not in self.accounts or self.oidc is None:
            raise IsolatedOIDCFailure()
        user = self.accounts[label]
        challenge = InitialChallenge.fresh()
        pkce = base64.urlsafe_b64encode(
            sha256(challenge.code_verifier.encode("ascii")).digest()
        ).decode("ascii").rstrip("=")
        params = {
            "response_type": "code", "client_id": self.CLIENT_ID,
            "redirect_uri": self.callback.url,
            "scope": "openid", "state": challenge.state,
            "nonce": challenge.nonce, "code_challenge": pkce,
            "code_challenge_method": "S256", "prompt": "login",
        }
        # No SSO cookie reuse: a new isolated HTTP browser session per flow.
        with httpx.Client(trust_env=False, timeout=20,
                          follow_redirects=False) as browser:
            response = browser.get(self.oidc["authorization_endpoint"],
                                   params=params)
            submitted = False
            for _ in range(24):
                if response.status_code in (301, 302, 303, 307, 308):
                    location = response.headers.get("location", "")
                    if not location:
                        raise IsolatedOIDCFailure()
                    destination = urljoin(str(response.url), location)
                    if destination.startswith(self.callback.url + "?"):
                        result = browser.get(destination)
                        if result.status_code != 200:
                            raise IsolatedOIDCFailure()
                        callback = self.callback.next()
                        return challenge, callback
                    if not destination.startswith(
                            self.base + "/realms/" + self.REALM + "/"):
                        raise IsolatedOIDCFailure()
                    response = browser.get(destination)
                elif response.status_code == 200 and not submitted:
                    form = LoginForm()
                    form.feed(response.text)
                    if not form.action:
                        raise IsolatedOIDCFailure()
                    action = urljoin(str(response.url), form.action)
                    if not action.startswith(
                            self.base + "/realms/" + self.REALM + "/"):
                        raise IsolatedOIDCFailure()
                    data = dict(form.hidden)
                    data.update(username=user["email"],
                                password=user["password"])
                    submitted = True
                    response = browser.post(action, data=data)
                else:
                    # Fixed-size diagnostics: never log URL, HTML, cookie,
                    # email, token, form action, password or callback Code.
                    body = response.text.lower() if response.status_code in (200, 400, 403) else ""
                    names = {cookie.name for cookie in browser.cookies.jar}
                    print("INITIAL_OIDC_FORM_STAGE", json.dumps({
                        "error_page_cookies_word": "cookie" in body,
                        "error_page_invalid_word": "invalid" in body,
                        "error_page_expired_word": "expired" in body,
                        "error_page_session_word": "session" in body,
                        "error_page_restart_word": "restart" in body,
                        "error_page_https_word": "https" in body,
                        "error_page_client_word": "client" in body,
                        "auth_session_cookie_present": any("AUTH_SESSION" in name for name in names),
                        "cookie_count_nonsecret": len(names),
                        "auth_session_cookie_is_secure": any(
                            cookie.secure for cookie in browser.cookies.jar
                            if "AUTH_SESSION" in cookie.name),
                        "posted_cookie_header_present": bool(
                            response.request.headers.get("cookie")),
                        "posted_cookie_has_auth_session": (
                            "AUTH_SESSION" in response.request.headers.get("cookie", "")),
                        "request_was_login_action": "/login-actions/authenticate" in str(response.request.url),
                        "submitted": submitted,
                        "http_status": response.status_code,
                        "login_form": "kc-form-login" in body,
                        "profile_form": "kc-update-profile-form" in body,
                        "feedback_present": "kc-feedback-text" in body,
                        "flow_step": "after_submit" if submitted else "before_submit",
                    }), flush=True)
                    raise IsolatedOIDCFailure()
        raise IsolatedOIDCFailure()
