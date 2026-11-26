"""Exercise real TLS and Keycloak authorization code + PKCE on loopback."""
import argparse
import base64
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import secrets
import ssl
from urllib.parse import parse_qs, urljoin, urlsplit

import httpx

ORIGIN = "https://127.0.0.1:19443"
ISSUER = ORIGIN + "/realms/nb23-session-e2e"
REDIRECT = ISSUER + "/account/"
CLIENT = "nb23-session-browser"


class LoginForm(HTMLParser):
    action = None

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        if tag == "form" and values.get("id") == "kc-form-login":
            self.action = values["action"]


def loopback(url):
    parsed = urlsplit(url)
    if (parsed.scheme, parsed.hostname, parsed.port) != ("https", "127.0.0.1", 19443):
        raise ValueError("UNEXPECTED_ORIGIN")
    return url


class FixtureTransport(httpx.HTTPTransport):
    def handle_request(self, request):
        loopback(str(request.url))
        if request.url.port != 19443:
            raise ValueError("UNEXPECTED_FIXTURE_PORT")
        # The issuer stays on 19443. Only the TCP destination in the
        # Keycloak container's private namespace uses its listener port.
        request.url = request.url.copy_with(port=8443)
        try:
            return super().handle_request(request)
        finally:
            request.url = request.url.copy_with(port=19443)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("fixture", type=Path)
    parser.add_argument("--inside-keycloak-namespace", action="store_true")
    args = parser.parse_args()
    account, = json.loads((args.fixture / "realm.json").read_text())["users"]
    tls = ssl.create_default_context(cafile=str(args.fixture / "tls.crt"))
    verifier = secrets.token_urlsafe(48)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip("=")
    state = secrets.token_urlsafe(24)
    transport = FixtureTransport(verify=tls, trust_env=False) if args.inside_keycloak_namespace else None
    with httpx.Client(verify=tls, transport=transport, trust_env=False,
                      timeout=httpx.Timeout(45, connect=5)) as client:
        response = client.get(ISSUER + "/.well-known/openid-configuration")
        response.raise_for_status()
        discovery = response.json()
        assert discovery["issuer"] == ISSUER
        response = client.get(loopback(discovery["authorization_endpoint"]), params={
            "response_type": "code", "client_id": CLIENT, "redirect_uri": REDIRECT,
            "scope": "openid", "state": state, "code_challenge": challenge,
            "code_challenge_method": "S256",
        })
        assert response.status_code == 200, f"LOGIN_FORM_HTTP_{response.status_code}"
        form = LoginForm()
        form.feed(response.text)
        assert form.action, "LOGIN_FORM_MISSING"
        response = client.post(loopback(urljoin(str(response.url), form.action)), data={
            "username": account["username"], "password": account["credentials"][0]["value"],
        })
        assert response.status_code in (302, 303), f"LOGIN_HTTP_{response.status_code}"
        location = loopback(response.headers["location"])
        assert location.split("?", 1)[0] == REDIRECT
        query = parse_qs(urlsplit(location).query)
        assert query["state"] == [state]
        token = client.post(loopback(discovery["token_endpoint"]), data={
            "grant_type": "authorization_code", "client_id": CLIENT,
            "redirect_uri": REDIRECT, "code": query["code"][0], "code_verifier": verifier,
        })
        assert token.status_code == 200 and token.json().get("id_token")
        print("HTTPS_DISCOVERY_PASS; REAL_KEYCLOAK_FORM_LOGIN_AND_PKCE_PASS")


if __name__ == "__main__":
    main()
