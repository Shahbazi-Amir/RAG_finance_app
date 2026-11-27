"""Validate protected local deployment inputs and probe TLS without logging them."""
import http.client
import json
from pathlib import Path
import socket
import ssl
import stat
import sys
from urllib.parse import urlsplit


CONFIG = Path("/etc/rag-arvan-candidate")
ORIGIN = "https://ragfinance.ir"
ISSUER = ORIGIN + "/realms/finance-staging"


def require(condition):
    if not condition:
        raise ValueError("deployment input denied")


def protected(name):
    path = Path(name)
    require(path.is_absolute() and ".." not in path.parts)
    info = path.lstat()
    require(stat.S_ISREG(info.st_mode) and stat.S_IMODE(info.st_mode) == 0o600)
    require(info.st_size > 0)
    return path


def profile(name):
    return json.loads(protected(CONFIG / name).read_text(encoding="utf-8"))


def probe_mtls(origin, web):
    endpoint = urlsplit(origin)
    context = ssl.create_default_context(cafile=web["tls_ca_file"])
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    context.maximum_version = ssl.TLSVersion.TLSv1_2

    def request():
        connection = http.client.HTTPSConnection(
            endpoint.hostname, endpoint.port, context=context, timeout=5
        )
        try:
            connection.request("GET", "/")
            return connection.getresponse().status
        finally:
            connection.close()

    # Accept a cleanly classified TLS rejection only after TCP has connected.
    with socket.create_connection((endpoint.hostname, endpoint.port), timeout=5) as tcp:
        with context.wrap_socket(
            tcp, server_hostname=endpoint.hostname, do_handshake_on_connect=False
        ) as anonymous:
            try:
                anonymous.do_handshake()
            except ssl.SSLEOFError as error:
                require(error.reason == "UNEXPECTED_EOF_WHILE_READING")
            except ssl.SSLError as error:
                require(error.reason in {
                    "SSLV3_ALERT_HANDSHAKE_FAILURE", "SSLV3_ALERT_BAD_CERTIFICATE",
                    "TLSV13_ALERT_CERTIFICATE_REQUIRED",
                })
            else:
                raise ValueError("private TLS accepted an anonymous client")
    context.load_cert_chain(web["tls_client_cert_file"], web["tls_client_key_file"])
    require(200 <= request() < 600)


def main():
    web = profile("web-private.json")
    bootstrap = profile("bootstrap-private.json")
    api = profile("api-private.json")
    require(web["public_origin"] == web["idp_authorization_origin"] == ORIGIN)
    require(bootstrap["oidc_issuer"] == ISSUER)
    require(bootstrap["oidc_client_id"] == "rag-finance-web")
    require(bootstrap["oidc_redirect_uri"] == ORIGIN + "/api/auth/callback")
    for field, suffix in (("authorization_endpoint", "auth"),
                          ("token_endpoint", "token"), ("jwks_uri", "certs")):
        require(bootstrap["oidc_" + field] == ISSUER + "/protocol/openid-connect/" + suffix)
    for key, value in web.items():
        if key.endswith("_file"):
            protected(value)
    for prefix, service, port in (("bootstrap", bootstrap, 18444), ("product", api, 18443)):
        require(service["listen_host"] == "127.0.0.1" and service["listen_port"] == port)
        origin = web[prefix + "_origin"]
        require(origin == f"https://127.0.0.1:{port}")
        protected(service["server_tls_key_file"])
        if sys.argv[1:] == ["--smoke-mtls"]:
            probe_mtls(origin, web)
    protected(bootstrap["seal_key_file"])


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, KeyError, TypeError, http.client.HTTPException):
        sys.exit("Arvan protected profile or mTLS check failed")
