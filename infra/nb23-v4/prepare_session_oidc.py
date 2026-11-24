"""Generate disposable, local-only Keycloak realm and TLS material."""
import argparse
import json
from pathlib import Path
import secrets
import subprocess


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("directory", type=Path)
    target = parser.parse_args().directory
    target.mkdir(mode=0o700)
    password = secrets.token_urlsafe(32)
    realm = {
        "realm": "nb23-session-e2e", "enabled": True, "registrationAllowed": False,
        "clients": [{
            "clientId": "nb23-session-browser", "enabled": True,
            "protocol": "openid-connect", "publicClient": True,
            "standardFlowEnabled": True, "directAccessGrantsEnabled": False,
            "redirectUris": ["https://127.0.0.1:19443/realms/nb23-session-e2e/account/"],
            "attributes": {"pkce.code.challenge.method": "S256"},
        }],
        "users": [{
            "username": "session-test-user", "enabled": True,
            "firstName": "Session", "lastName": "Fixture",
            "email": "session-test-user@example.invalid", "emailVerified": True,
            "credentials": [{"type": "password", "value": password, "temporary": False}],
        }],
    }
    config = target / "openssl.cnf"
    config.write_text("[req]\ndistinguished_name=dn\nx509_extensions=leaf\n"
                      "[dn]\n[leaf]\nsubjectAltName=IP:127.0.0.1\n", encoding="utf-8")
    subprocess.run(
        ["openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes", "-days", "2",
         "-subj", "/CN=127.0.0.1", "-config", str(config),
         "-keyout", str(target / "tls.key"), "-out", str(target / "tls.crt")],
        check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
    )
    (target / "realm.json").write_text(json.dumps(realm), encoding="utf-8")
    # Docker reads these files as Keycloak's UID. The parent remains 0700.
    for name in ("realm.json", "tls.key", "tls.crt"):
        (target / name).chmod(0o444)


if __name__ == "__main__":
    main()
