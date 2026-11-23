"""Prepare a single Keycloak staging invitation using a realm-scoped admin token."""

import argparse
import base64
from getpass import getpass
from http.client import HTTPException, HTTPSConnection
import json
import re
import socket
import ssl
import sys
from urllib.parse import quote, urlencode, urlsplit


class InvitationError(Exception):
    pass


class LoopbackHTTPS(HTTPSConnection):
    def connect(self):
        with_connection = socket.create_connection(("127.0.0.1", self.port), self.timeout)
        try:
            self.sock = self._context.wrap_socket(with_connection, server_hostname=self.host)
        except BaseException:
            with_connection.close()
            raise


def stage_path(issuer):
    value = urlsplit(issuer)
    match = re.fullmatch(r"/realms/([a-zA-Z0-9._-]+)", value.path)
    if (value.scheme != "https" or value.netloc != "idp-staging.ragfinance.ir"
            or value.query or value.fragment or not match
            or match[1].lower() in {"master", ".", ".."}):
        raise InvitationError("INVALID_STAGING_ISSUER")
    return f"/admin/realms/{match[1]}"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("check", "invite", "password-email"))
    parser.add_argument("--issuer", required=True, help="Exact issuer from the staging Bootstrap configuration")
    parser.add_argument("--ca", required=True, help="Path to the trusted local staging CA")
    parser.add_argument("--admin-loopback-port", type=int, required=True,
                        help="Published port of the temporary localhost-only admin listener")
    parser.add_argument("--approved-smtp-host", required=True, help="SMTP host approved by the staging operator")
    args = parser.parse_args()

    if not 1 <= args.admin_loopback_port <= 65535:
        parser.error("--admin-loopback-port must be between 1 and 65535")
    realm_path = stage_path(args.issuer)
    context = ssl.create_default_context(cafile=args.ca)
    if not sys.stdin.isatty():
        raise InvitationError("INTERACTIVE_TERMINAL_REQUIRED")
    token = getpass("Realm-scoped admin access token: ")
    try:
        token_claims = json.loads(base64.urlsafe_b64decode(token.split(".")[1] + "==="))
        if token_claims.get("iss") != args.issuer:
            raise InvitationError("ADMIN_TOKEN_REALM_MISMATCH")
    except (IndexError, ValueError):
        raise InvitationError("INVALID_ADMIN_TOKEN") from None

    def request(method, path, expected, payload=None):
        connection = LoopbackHTTPS("idp-staging.ragfinance.ir", port=args.admin_loopback_port,
                                   timeout=25, context=context)
        try:
            headers = {"Authorization": f"Bearer {token}"}
            body = None
            if payload is not None:
                headers["Content-Type"] = "application/json"
                body = json.dumps(payload)
            connection.request(method, path, headers=headers, body=body)
            response = connection.getresponse()
            if response.status != expected:
                raise InvitationError(f"KEYCLOAK_HTTP_{response.status}")
            return json.load(response) if expected == 200 else None
        finally:
            connection.close()

    realm = request("GET", realm_path, 200)
    if (realm.get("realm") != realm_path.rsplit("/", 1)[1]
            or realm.get("enabled") is not True or realm.get("registrationAllowed") is not False):
        raise InvitationError("REALM_POLICY_MISMATCH")
    smtp = realm.get("smtpServer") or {}
    if (smtp.get("host") != args.approved_smtp_host or not smtp.get("from")
            or not any(smtp.get(k) == "true" for k in ("ssl", "starttls"))):
        raise InvitationError("APPROVED_TLS_SMTP_NOT_CONFIGURED")
    default_role = (realm.get("defaultRole") or {}).get("name")
    if not default_role:
        raise InvitationError("MISSING_DEFAULT_REALM_ROLE")
    defaults = request("GET", realm_path + "/roles/" + quote(default_role, safe="") + "/composites", 200)
    if defaults:
        accounts = request("GET", realm_path + "/clients?clientId=account", 200)
        account_ids = {client["id"] for client in accounts if client.get("clientId") == "account"}
        seen = set()
        while defaults:
            role = defaults.pop()
            role_id = role["id"]
            if role_id in seen:
                continue
            seen.add(role_id)
            if role.get("clientRole"):
                allowed = (role.get("containerId") in account_ids and
                           role.get("name") in {"manage-account", "manage-account-links", "view-profile"})
            else:
                allowed = role.get("name") in {"offline_access", "uma_authorization"}
            if not allowed:
                raise InvitationError("UNEXPECTED_DEFAULT_ROLE_COMPOSITION")
            if role.get("composite"):
                defaults.extend(request("GET", realm_path + "/roles-by-id/" +
                                        quote(role_id, safe="") + "/composites", 200))
    if args.action == "check":
        print("INVITATION_PREFLIGHT_PASS")
        return

    email = getpass("Approved test inbox (hidden): ").strip()
    if not re.fullmatch(r"[^\s@]+@[^\s@]+", email):
        raise InvitationError("INVALID_TEST_INBOX")
    users = realm_path + "/users"

    def lookup():
        query = urlencode({"email": email, "exact": "true", "max": 2})
        return request("GET", f"{users}?{query}", 200)

    existing = lookup()
    if args.action == "invite" and not existing:
        request("POST", users, 201, {
            "username": email, "email": email, "enabled": True,
            "requiredActions": ["VERIFY_EMAIL", "UPDATE_PASSWORD"],
        })
        existing = lookup()
    if len(existing) != 1:
        raise InvitationError("TEST_ACCOUNT_NOT_UNIQUE")

    user = existing[0]
    required = set(user.get("requiredActions") or [])
    expected_actions = {"VERIFY_EMAIL", "UPDATE_PASSWORD"} if args.action == "invite" else {"UPDATE_PASSWORD"}
    verified = args.action == "password-email"
    if (user.get("email") != email or user.get("username") != email
            or user.get("enabled") is not True or user.get("emailVerified", False) is not verified
            or required != expected_actions):
        raise InvitationError("TEST_ACCOUNT_STATE_MISMATCH")
    user_path = users + "/" + quote(user["id"], safe="")
    mappings = request("GET", user_path + "/role-mappings", 200)
    if (mappings.get("clientMappings")
            or any(role.get("name") != default_role for role in mappings.get("realmMappings", []))
            or request("GET", user_path + "/groups", 200)
            or request("GET", user_path + "/credentials", 200)):
        raise InvitationError("UNEXPECTED_TEST_ACCOUNT_PRIVILEGES_OR_CREDENTIALS")

    if args.action == "invite":
        request("PUT", user_path + "/send-verify-email?lifespan=900", 204)
        print("VERIFICATION_EMAIL_ACCEPTED")
    else:
        request("PUT", user_path + "/execute-actions-email?lifespan=900", 204, ["UPDATE_PASSWORD"])
        print("PASSWORD_SETUP_EMAIL_ACCEPTED")


if __name__ == "__main__":
    try:
        main()
    except (InvitationError, HTTPException, OSError, ValueError, KeyError, EOFError) as error:
        print(str(error) if isinstance(error, InvitationError) else "INVITATION_REQUEST_FAILED", file=sys.stderr)
        sys.exit(1)
