#!/usr/bin/env python3
"""Ephemeral APP_ONLY HTTPS/mTLS/Product History -> real PG17.11 probe.

The BFF signer and user identities here are TEST-ONLY synthetics, not a real
OIDC provider or a browser session. Test process and API server are separate
OS processes, communicating over genuine TLS localhost. No engine/011/target.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import secrets
import signal
import socket
import ssl
import subprocess
import sys
import time
from urllib.parse import urlencode

import httpx
import jwt
import psycopg
from psycopg.rows import dict_row
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID

from src.phase3.storage.postgres import auth_session

LAB = Path("/run/f3_http_probe")
PRIVATE = LAB / "private"
BASE = "https://127.0.0.1:18443"
ISS = "urn:rag-finance:synthetic-bff"
AUD = "urn:rag-finance:api:internal-ci"
KID = "ci-rsa-1"


def require_lab():
    assert os.getenv("F3_ISOLATED_DB_HTTP") == "YES", "DENY_NOT_ISOLATED_DB_HTTP"
    assert LAB.is_dir() and LAB.stat().st_uid == os.geteuid()
    assert (LAB.stat().st_mode & 0o077) == 0, "DENY_UNSAFE_LAB_DIR"
    PRIVATE.mkdir(mode=0o700, exist_ok=True)
    assert PRIVATE.stat().st_uid == os.geteuid()
    assert (PRIVATE.stat().st_mode & 0o077) == 0


def write_secret(path: Path, data: bytes):
    fd = os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(fd, "wb") as out:
            out.write(data)
    except BaseException:
        path.unlink(missing_ok=True)
        raise


def conn(role: str, host: str, db: str):
    cfg = json.loads((LAB / "role_passwords.json").read_text())
    assert host in ("demo-db", "restore-db")
    assert db in ("rag_finance_f3_http_ab_source", "rag_finance_f3_http_ab_restored")
    assert role in ("auth_mapper", "auth_sessions", "auth_revoker", "history_app")
    dsn = psycopg.conninfo.make_conninfo(
        host=host, port=5432, dbname=db, user=role,
        password=cfg[role], sslmode="verify-full",
        sslrootcert=str(LAB / "pg_ca.crt"), connect_timeout=5)
    return psycopg.connect(dsn, autocommit=True, row_factory=dict_row)


def generate_pki():
    now = datetime.now(timezone.utc)
    ca_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    ca_name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "F3 Ephemeral HTTPS Lab CA")])
    ca = (x509.CertificateBuilder().subject_name(ca_name).issuer_name(ca_name)
          .public_key(ca_key.public_key()).serial_number(x509.random_serial_number())
          .not_valid_before(now - timedelta(minutes=1))
          .not_valid_after(now + timedelta(hours=3))
          .add_extension(x509.BasicConstraints(ca=True, path_length=None), critical=True)
          .sign(ca_key, hashes.SHA256()))
    write_secret(PRIVATE / "ca.pem", ca.public_bytes(serialization.Encoding.PEM))
    def leaf(name, server):
        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        subject = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, name)])
        builder = (x509.CertificateBuilder().subject_name(subject).issuer_name(ca_name)
                   .public_key(key.public_key()).serial_number(x509.random_serial_number())
                   .not_valid_before(now - timedelta(minutes=1))
                   .not_valid_after(now + timedelta(hours=3))
                   .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
                   .add_extension(x509.ExtendedKeyUsage(
                       [ExtendedKeyUsageOID.SERVER_AUTH if server else ExtendedKeyUsageOID.CLIENT_AUTH]),
                       critical=False))
        if server:
            import ipaddress
            builder = builder.add_extension(
                x509.SubjectAlternativeName([x509.IPAddress(ipaddress.ip_address("127.0.0.1"))]),
                critical=False)
        cert = builder.sign(ca_key, hashes.SHA256())
        write_secret(PRIVATE / (name + ".pem"), cert.public_bytes(serialization.Encoding.PEM))
        write_secret(PRIVATE / (name + ".key"), key.private_bytes(
            serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption()))
        return cert
    leaf("server", True)
    bff = leaf("bff", False)
    leaf("wrong", False)
    signer = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    write_secret(PRIVATE / "signer.key", signer.private_bytes(
        serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption()))
    write_secret(PRIVATE / "signer.pub", signer.public_key().public_bytes(
        serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo))
    write_secret(PRIVATE / "pinned_bff_leaf_sha256", sha256(
        bff.public_bytes(serialization.Encoding.DER)).hexdigest().encode())
    write_secret(PRIVATE / "cursor.key", secrets.token_urlsafe(32).encode())


def create_fixture():
    assert not (PRIVATE / "session_state.json").exists(), "NO_REUSE_SESSION_FIXTURE"
    generate_pki()
    user_state = {}
    for label in ("a", "b"):
        with conn("auth_mapper", "demo-db", "rag_finance_f3_http_ab_source") as c:
            # These are synthetic identifiers, NOT verified IdP claims.
            owner = auth_session.map_identity(
                c, "https://f3-synthetic-idp.invalid",
                "f3-ci-subject-" + label + "-" + secrets.token_hex(6))["owner_id"]
        with conn("auth_sessions", "demo-db", "rag_finance_f3_http_ab_source") as c:
            issued = auth_session.issue(c, owner, 0, idle_seconds=1800, absolute_seconds=7200)
        user_state[label] = dict(owner=owner, token=issued.opaque,
                                 epoch=issued.epoch, generation=issued.generation)
        with conn("history_app", "demo-db", "rag_finance_f3_http_ab_source") as c:
            with c.transaction():
                c.execute("SELECT set_config('app.owner_id', %s, true)", (owner,))
                conv_count = 5 if label == "a" else 3
                msg_count = 4 if label == "a" else 2
                for n in range(1, conv_count + 1):
                    c.execute(
                        "INSERT INTO history_l1.conversations"
                        "(owner_id,id,title,state,created_at,updated_at)"
                        " VALUES(%s,%s,%s,'active',%s,%s)",
                        (owner, f"f3-net-{label}-{n}", f"synthetic {label} {n}",
                         datetime(2026, 1, 1, tzinfo=timezone.utc) + timedelta(seconds=n),
                         datetime(2026, 1, 1, tzinfo=timezone.utc) + timedelta(seconds=n)))
                for n in range(1, msg_count + 1):
                    c.execute(
                        "INSERT INTO history_l1.messages"
                        "(owner_id,id,conversation_id,role,body,created_at)"
                        " VALUES(%s,%s,%s,'user',%s,%s)",
                        (owner, f"f3-net-{label}-msg-{n}", f"f3-net-{label}-1",
                         "synthetic never-user data",
                         datetime(2026, 1, 1, tzinfo=timezone.utc) + timedelta(seconds=n)))
    write_secret(PRIVATE / "session_state.json", json.dumps(user_state).encode())
    print("HTTPS_LAB_TWO_SYNTHETIC_DB_MAPPED_OWNER_SESSIONS_CREATED=PASS", flush=True)


def signature(label, method: str, raw_path: str, raw_query: str = "", body: bytes = b"",
              owner_override=None, session_override=None) -> str:
    state = json.loads((PRIVATE / "session_state.json").read_text())[label]
    now = int(time.time())
    claims = dict(
        iss=ISS, aud=AUD, iat=now, nbf=now, exp=now + 20,
        jti=secrets.token_urlsafe(24), method=method,
        raw_path_sha256=sha256(raw_path.encode("ascii")).hexdigest(),
        raw_query_sha256=sha256(raw_query.encode("ascii")).hexdigest(),
        body_sha256=sha256(body).hexdigest(), body_len=len(body),
        session_ref=session_override or state["token"],
        owner_id=owner_override or state["owner"],
        epoch=state["epoch"], generation=state["generation"])
    key = serialization.load_pem_private_key((PRIVATE / "signer.key").read_bytes(), password=None)
    return jwt.encode(claims, key, algorithm="RS256", headers={"kid": KID, "typ": "JWT"})


def tls_client(cert="bff"):
    ctx = ssl.create_default_context(cafile=str(PRIVATE / "ca.pem"))
    if cert:
        ctx.load_cert_chain(certfile=str(PRIVATE / (cert + ".pem")),
                            keyfile=str(PRIVATE / (cert + ".key")))
    return httpx.Client(verify=ctx, trust_env=False, timeout=5.0, follow_redirects=False)


def run_server(host, db, scenario):
    assert host in ("demo-db", "restore-db")
    cfg = json.loads((LAB / "role_passwords.json").read_text())
    def dsn(role):
        return psycopg.conninfo.make_conninfo(
            host=host, port=5432, dbname=db, user=role, password=cfg[role],
            sslmode="verify-full", sslrootcert=str(LAB / "pg_ca.crt"),
            connect_timeout=5)
    config = {
        "contract_version": "api.private_app_only_asgi.v1",
        "listen_host": "127.0.0.1", "listen_port": 18443,
        "server_tls_cert_file": str(PRIVATE / "server.pem"),
        "server_tls_key_file": str(PRIVATE / "server.key"),
        "trusted_bff_ca_file": str(PRIVATE / "ca.pem"),
        "bff_leaf_cert_sha256": (PRIVATE / "pinned_bff_leaf_sha256").read_text(),
        "bff_issuer": ISS, "bff_audience": AUD, "bff_kid": KID,
        "bff_rs256_public_key_file": str(PRIVATE / "signer.pub"),
        "history_dsn": dsn("history_app"), "revoke_dsn": dsn("auth_revoker"),
    }
    config_path = PRIVATE / "server-config.json"
    if config_path.exists():
        config_path.unlink()
    write_secret(config_path, json.dumps(config).encode())
    environ = os.environ.copy()
    for key in ("CI", "GITHUB_ACTIONS", "OPENAI_API_KEY", "QDRANT_URL",
                "MODEL_GATEWAY_URL", "C018_RUNNER_PATH", "API_ENGINE_ENABLED",
                "API_PROVIDER_KEY"):
        environ.pop(key, None)
    environ["API_RUNNER_EXECUTION_MODE"] = "APP_ONLY"
    environ["API_CURSOR_KEY"] = (PRIVATE / "cursor.key").read_text()
    environ["API_CURSOR_TTL_SECONDS"] = "300"
    log = open(PRIVATE / "app-only-server.log", "ab")
    p = subprocess.Popen(
        [sys.executable, "-m", "apps.api.private_app_only_asgi",
         "--config", str(config_path)],
        env=environ, stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT)
    try:
        ready = False
        last_http = "NONE"
        last_tls_error = "NONE"
        last_tls_cause = "NONE"
        with tls_client() as c:
            for _ in range(100):
                if p.poll() is not None:
                    break
                try:
                    r = c.get(BASE + "/internal/ready")
                    last_http = str(r.status_code)
                    if r.status_code == 200:
                        assert r.json().get("state") == "ready", "READY_BODY"
                        assert r.json().get("bootstrap_idp") == "not_probed"
                        ready = True
                        break
                except httpx.HTTPError as exc:
                    last_tls_error = type(exc).__name__
                    cause = exc.__cause__
                    last_tls_cause = type(cause).__name__ if cause is not None else "NONE"
                time.sleep(0.15)
        if not ready:
            log.flush()
            log_text = (PRIVATE / "app-only-server.log").read_text(errors="replace")
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(1)
                socket_state = str(sock.connect_ex(("127.0.0.1", 18443)))
            try:
                ctx_probe = ssl.create_default_context(cafile=str(PRIVATE / "ca.pem"))
                ctx_probe.load_cert_chain(str(PRIVATE / "bff.pem"), str(PRIVATE / "bff.key"))
                with socket.create_connection(("127.0.0.1", 18443), timeout=2) as raw:
                    with ctx_probe.wrap_socket(raw, server_hostname="127.0.0.1") as verified:
                        tls_probe = "HANDSHAKE_OK_" + verified.version()
            except (ssl.SSLError, OSError) as exc:
                tls_probe = (type(exc).__name__ + "_" + str(getattr(exc, "reason", "GENERIC"))
                             + "_VERIFY_CODE_" + str(getattr(exc, "verify_code", "NA")))
            print("APP_ONLY_HTTP_LAB_DIAGNOSTIC_TLS=" + tls_probe, flush=True)
            print("APP_ONLY_HTTP_LAB_DIAGNOSTIC_EXIT=" + str(p.poll()) +
                  "_TCP_CONNECT_EX=" + socket_state +
                  "_HTTP=" + last_http + "_NETWORK_CLASS=" + last_tls_error +
                  "_CAUSE_CLASS=" + last_tls_cause +
                  "_UVICORN_BOUND=" + str("Uvicorn running" in log_text) +
                  "_SSL_LOG_MARKER=" + str("SSL" in log_text or "ssl" in log_text) +
                  "_STARTUP_DENIED=" + str("APP_ONLY_STARTUP_DENIED" in log_text) +
                  "_MODULE_MISSING=" + str("ModuleNotFoundError" in log_text), flush=True)
        assert ready, "PRIVATE_ASGI_MTLS_DB_READY_NOT_REACHED"
        print("HTTPS_APP_ONLY_REAL_MTLS_PG_READINESS_200_IDP_NOT_PROBED=PASS", flush=True)
        scenario()
    finally:
        p.terminate()
        try:
            p.wait(timeout=10)
        except subprocess.TimeoutExpired:
            p.kill()
            p.wait(timeout=5)
        log.close()


def request(c, label: str, path: str, query: str = "", *, expect: int = 200, method="GET", body=b""):
    url = BASE + path + (("?" + query) if query else "")
    headers = {"Authorization": "BFF-Assertion " +
               signature(label, method, path, query, body)}
    if body:
        headers["Content-Type"] = "application/json"
    r = c.request(method, url, headers=headers, content=body)
    assert r.status_code == expect, f"SIGNED_HISTORY_STATUS_{expect}_GOT_{r.status_code}"
    return r


def verify_history(phase: str):
    state = json.loads((PRIVATE / "session_state.json").read_text())
    with tls_client() as client:
        assert client.get(BASE + "/v1/conversations").status_code == 401
        for label, count in (("a", 5), ("b", 3)):
            seen = []
            cursor = None
            while True:
                query = urlencode({"limit": "2", **({"cursor": cursor} if cursor else {})})
                page = request(client, label, "/v1/conversations", query).json()
                assert page["kind"] == "conversation_page"
                assert page["scope_user_id"] == state[label]["owner"]
                seen += [x["conversation_id"] for x in page["items"]]
                if not page["page"]["has_more"]:
                    break
                cursor = page["page"]["next_cursor"]
                assert cursor
            assert seen == [f"f3-net-{label}-{i}" for i in range(count, 0, -1)]
        a = request(client, "a", "/v1/conversations/f3-net-a-1/messages", "limit=2").json()
        b = request(client, "b", "/v1/conversations/f3-net-b-1/messages", "limit=2").json()
        assert a["kind"] == b["kind"] == "conversation_messages_page"
        assert len(a["items"]) == len(b["items"]) == 2
        assert all(x["message_id"].startswith("f3-net-a-") for x in a["items"])
        assert all(x["message_id"].startswith("f3-net-b-") for x in b["items"])
        request(client, "b", "/v1/conversations/f3-net-a-1/messages", expect=404)
        request(client, "a", "/v1/conversations/f3-net-b-1/messages", expect=404)
        forged = signature("a", "GET", "/v1/conversations",
                           owner_override=state["b"]["owner"])
        assert client.get(BASE + "/v1/conversations",
                          headers={"Authorization": "BFF-Assertion " + forged}).status_code == 401
        raw = b'{"question":"synthetic must not dispatch"}'
        sent = request(client, "a", "/v1/messages", method="POST", body=raw, expect=503)
        assert sent.json()["error"]["code"] == "ENGINE_NOT_CONFIGURED"
        with conn("history_app", "demo-db" if phase == "before" else "restore-db",
                  "rag_finance_f3_http_ab_source" if phase == "before" else "rag_finance_f3_http_ab_restored") as sql:
            for table in ("send_receipts", "execution_attempts", "answers", "create_receipts"):
                with sql.transaction():
                    sql.execute("SELECT set_config('app.owner_id', %s, true)", (state["a"]["owner"],))
                    assert sql.execute(f"SELECT count(*) AS n FROM history_l1.{table}").fetchone()["n"] == 0
        # Wrong leaf and missing certificate MUST never yield authenticated History.
        for other in ("wrong", None):
            try:
                with tls_client(other) as unauthorized:
                    result = unauthorized.get(BASE + "/v1/conversations",
                                              headers={"X-Forwarded-User": state["a"]["owner"]})
                    assert result.status_code in (401, 403), "WRONG_PEER_AUTHENTICATED"
            except httpx.HTTPError:
                pass
    print(f"HTTPS_APP_ONLY_{phase.upper()}_A_B_OWNER_PAGES_DETAILS_404_SEND503_MTLS_NEGATIVE=PASS", flush=True)


def revoke_and_check():
    state = json.loads((PRIVATE / "session_state.json").read_text())
    with conn("auth_revoker", "restore-db", "rag_finance_f3_http_ab_restored") as c:
        result = auth_session.revoke_one(c, state["a"]["token"], state["a"]["epoch"])
        assert result is not None, "REVOKE_FAILED"
    with tls_client() as client:
        request(client, "a", "/v1/conversations", expect=401)
        request(client, "b", "/v1/conversations", expect=200)
    print("HTTPS_APP_ONLY_REVOKED_A_401_B_UNAFFECTED_200=PASS", flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("phase", choices=("seed", "before", "after"))
    args = parser.parse_args()
    require_lab()
    if args.phase == "seed":
        create_fixture()
        return
    if not (PRIVATE / "session_state.json").is_file():
        raise RuntimeError("NO_SYNTHETIC_SESSION_FIXTURE")
    host = "demo-db" if args.phase == "before" else "restore-db"
    db = ("rag_finance_f3_http_ab_source" if args.phase == "before"
          else "rag_finance_f3_http_ab_restored")
    def scenario():
        verify_history(args.phase)
        if args.phase == "after":
            revoke_and_check()
    run_server(host, db, scenario)


if __name__ == "__main__":
    main()
