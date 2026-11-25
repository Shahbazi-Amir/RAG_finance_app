#!/usr/bin/env python3
"""Ephemeral APP_ONLY HTTPS/mTLS/Product History -> real PG17.11 probe.

The BFF signer and user identities here are TEST-ONLY synthetics, not a real
OIDC provider or a browser session. Test process and API server are separate
OS processes, communicating over genuine TLS localhost. No engine/011/target.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from threading import Barrier
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
from uuid import uuid4

import httpx
import jwt
import psycopg
from psycopg.rows import dict_row
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID

from src.phase3.storage.postgres import auth_session
from app_only_retry_probe import assert_disabled_retries, row_fingerprint

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
          .add_extension(x509.SubjectKeyIdentifier.from_public_key(ca_key.public_key()), critical=False)
          .add_extension(x509.KeyUsage(
              digital_signature=False, content_commitment=False,
              key_encipherment=False, data_encipherment=False, key_agreement=False,
              key_cert_sign=True, crl_sign=True, encipher_only=False,
              decipher_only=False), critical=True)
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
                   .add_extension(x509.AuthorityKeyIdentifier.from_issuer_public_key(
                       ca_key.public_key()), critical=False)
                   .add_extension(x509.KeyUsage(
                       digital_signature=True, content_commitment=False,
                       key_encipherment=True, data_encipherment=False,
                       key_agreement=False, key_cert_sign=False, crl_sign=False,
                       encipher_only=False, decipher_only=False), critical=True)
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
              owner_override=None, session_override=None, generation_override=None) -> str:
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
        epoch=state["epoch"], generation=(state["generation"] if generation_override is None
                                         else generation_override))
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
    # This negative launch is on the same disposable lab network. The
    # proposed revoke destination is intentionally NOT the History database.
    # The new static pair fence must reject it before binding any listener.
    negative_path = PRIVATE / "split-db-config.json"
    invalid = dict(config, revoke_dsn=psycopg.conninfo.make_conninfo(
        config["revoke_dsn"], dbname="f3_deliberately_invalid_split_database"))
    write_secret(negative_path, json.dumps(invalid).encode())
    try:
        denied = subprocess.run(
            [sys.executable, "-m", "apps.api.private_app_only_asgi",
             "--config", str(negative_path)],
            env=environ, stdin=subprocess.DEVNULL, capture_output=True, timeout=15)
        assert denied.returncode == 78, "SPLIT_DB_MUST_EXIT_78"
        assert denied.stderr.strip() == b"APP_ONLY_STARTUP_DENIED"
        assert b"Uvicorn running" not in denied.stdout + denied.stderr
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(1)
            assert sock.connect_ex(("127.0.0.1", 18443)) != 0
    finally:
        negative_path.unlink(missing_ok=True)
    print("API_F3_SPLIT_DB_STARTUP_DENIED_78_NO_LISTENER=PASS", flush=True)
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


def verify_disabled_send_retries(phase, state):
    """Actual signed HTTPS POST retries with independent scoped PG snapshots."""
    host = "demo-db" if phase == "before" else "restore-db"
    db = ("rag_finance_f3_http_ab_source" if phase == "before"
          else "rag_finance_f3_http_ab_restored")
    tables = ("conversations", "messages", "create_receipts",
              "send_receipts", "execution_attempts", "answers")

    def snapshot():
        rows = []
        with conn("history_app", host, db) as sql:
            for label in ("a", "b"):
                with sql.transaction():
                    sql.execute("SELECT set_config('app.owner_id', %s, true)",
                                (state[label]["owner"],))
                    for table in tables:
                        contents = sql.execute(
                            f"SELECT to_jsonb(t)::text AS row_value FROM history_l1.{table} AS t"
                        ).fetchall()
                        rows.append(row_fingerprint([item["row_value"] for item in contents]))
        # Nonvacuous known synthetic owner inventory. A wrong RLS context
        # must not make an all-zero snapshot appear successful.
        assert tuple(item[0] for item in rows) == (5,4,0,0,0,0,3,2,0,0,0,0)
        return tuple(rows)

    for label in ("a", "b"):
        raw = json.dumps({
            "kind": "send_message_request", "contract_version": "product.v1",
            "requested_conversation_id": f"f3-net-{label}-1",
            "client_message_id": f"app-only-retry-{label}",
            "question": "synthetic app-only retry must not dispatch",
            "idempotency_key": f"app-only-retry-key-{label}",
        }, separators=(",", ":")).encode()
        path = "/v1/messages"
        # Prepare proofs before starting the wave; three retransmit the exact
        # original proof and three represent retries signed anew by the BFF.
        original = signature(label, "POST", path, body=raw)
        proofs = [original] * 3 + [
            signature(label, "POST", path, body=raw) for _ in range(3)]
        def send(index):
            with tls_client() as retry_client:
                result = retry_client.post(BASE + path, content=raw, headers={
                    "Authorization": "BFF-Assertion " + proofs[index],
                    "Content-Type": "application/json"})
                assert result.headers.get("cache-control") == "no-store"
                return result.status_code, result.json()["error"]["code"]
        assert assert_disabled_retries(send, snapshot) == 6
    print(f"API_F3_{phase.upper()}_12_REAL_SIGNED_SEND_RETRIES_ZERO_SCOPED_SQL=PASS", flush=True)
    # All four engine/fixture read routes must fail without entering product
    # admission. With valid mTLS, missing JWT must not reach signed handlers.
    before = snapshot()
    with tls_client() as client:
        for suffix, code in (
            ("engine-status", "ENGINE_STATUS_UNAVAILABLE"),
            ("retrieved-sources", "ENGINE_STATUS_UNAVAILABLE"),
            ("claim-test-status", "TEMPORARILY_UNAVAILABLE"),
            ("invited-live-result", "TEMPORARILY_UNAVAILABLE"),
        ):
            path = "/v1/message-requests/" + suffix
            for label in ("a", "b"):
                result = request(client, label, path, expect=503)
                assert result.json()["error"]["code"] == code
                assert result.headers["cache-control"] == "no-store"
            result = client.get(BASE + path)
            assert result.status_code == 503 and result.json()["error"]["code"] == code
        request(client, "a", "/v1/conversations", expect=200)
        request(client, "b", "/v1/conversations", expect=200)
    assert snapshot() == before
    print(f"API_F3_{phase.upper()}_DISABLED_ROUTES_AND_FULL_ROW_PARITY=PASS", flush=True)


def verify_runtime_signer_drift(phase):
    """Only mutate the synthetic lab public key, restore it even on failure."""
    path = PRIVATE / "signer.pub"
    original = path.read_bytes()
    with tls_client() as client:
        try:
            path.write_bytes(b"synthetic invalid signer configuration")
            for endpoint in ("/internal/ready", "/health/ready", "/v1/conversations"):
                headers = {"Authorization": "BFF-Assertion " +
                           signature("a", "GET", endpoint)}
                result = client.get(BASE + endpoint, headers=headers)
                assert result.status_code == 503
                assert result.headers.get("cache-control") == "no-store"
                assert b"synthetic invalid signer configuration" not in result.content
        finally:
            path.write_bytes(original)
        assert client.get(BASE + "/internal/ready").status_code == 200
        request(client, "a", "/v1/conversations", expect=200)
        request(client, "b", "/v1/conversations", expect=200)
    print(f"API_F3_{phase.upper()}_REAL_SIGNER_DRIFT_503_RECOVERY_200=PASS", flush=True)


def verify_session_lifecycle(phase, state):
    """Use only additional, disposable sessions; do not rotate the main A/B sessions."""
    host = "demo-db" if phase == "before" else "restore-db"
    db = ("rag_finance_f3_http_ab_source" if phase == "before"
          else "rag_finance_f3_http_ab_restored")
    actor = state["a"]
    endpoint = "/v1/conversations"
    with conn("auth_sessions", host, db) as sessions, tls_client() as client:
        def get_session(session, generation=None, path=endpoint):
            proof = signature("a", "GET", path, session_override=session.opaque,
                              generation_override=(session.generation if generation is None
                                                   else generation))
            response = client.get(BASE + path, headers={"Authorization": "BFF-Assertion " + proof})
            assert response.headers["cache-control"] == "no-store"
            return response

        first = auth_session.issue(sessions, actor["owner"], actor["epoch"],
                                   idle_seconds=60, absolute_seconds=300)
        assert get_session(first).status_code == 200
        # A normal History GET must not implicitly extend the DB session deadline.
        observed = auth_session.inspect(sessions, first.opaque)
        assert observed is not None
        assert observed["idle_expires_at"] == first.idle_expires_at
        assert observed["absolute_expires_at"] == first.absolute_expires_at
        rotated = auth_session.rotate(sessions, first.opaque, first.epoch, first.generation)
        assert rotated.generation == first.generation + 1
        assert rotated.absolute_expires_at == first.absolute_expires_at
        assert get_session(first).status_code == 401
        assert get_session(rotated, generation=first.generation).status_code == 401
        response = get_session(rotated)
        assert response.status_code == 200
        assert response.json()["scope_user_id"] == actor["owner"]
        assert get_session(rotated, path="/health/ready").status_code == 200
        # Revoke through the actual signed HTTP endpoint, not directly with
        # the revoker role. Malformed requests must not consume a valid proof.
        revoke_path = "/internal/auth/session/v1/revoke-one"
        operation = str(uuid4())
        raw = json.dumps({"operation_id": operation}, separators=(",", ":")).encode()
        revoke_proof = signature("a", "POST", revoke_path, body=raw,
                                 session_override=rotated.opaque,
                                 generation_override=rotated.generation)
        headers = {"Authorization": "BFF-Assertion " + revoke_proof}
        denied = client.post(BASE + revoke_path, content=raw,
                             headers=dict(headers, **{"Content-Type": "text/plain"}))
        assert denied.status_code == 422
        assert auth_session.inspect(sessions, rotated.opaque) is not None
        assert get_session(rotated).status_code == 200
        # Reusing the identical valid assertion after pre-body rejection
        # must commit one revoke, then subsequent replay must be denied.
        headers["Content-Type"] = "application/json"
        committed = client.post(BASE + revoke_path, content=raw, headers=headers)
        assert committed.status_code == 200
        assert committed.json() == {"state": "REVOKED_COMMITTED", "operation_id": operation}
        assert committed.headers["cache-control"] == "no-store"
        assert auth_session.inspect(sessions, rotated.opaque) is None
        assert get_session(rotated).status_code == 401
        assert client.post(BASE + revoke_path, content=raw, headers=headers).status_code == 401
        print(f"API_F3_{phase.upper()}_SIGNED_REVOKE_COMMIT_REPLAY_AND_PREBODY_DENIAL=PASS", flush=True)

        # Independently exercise idle and absolute expiry with tiny lab-only
        # TTLs. Use the DB's own admission clock, not a guessed wall-clock sleep.
        idle = auth_session.issue(sessions, actor["owner"], actor["epoch"],
                                  idle_seconds=8, absolute_seconds=60)
        absolute = auth_session.issue(sessions, actor["owner"], actor["epoch"],
                                      idle_seconds=8, absolute_seconds=8)
        assert get_session(idle).status_code == 200
        assert get_session(absolute).status_code == 200
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline:
            if (auth_session.inspect(sessions, idle.opaque) is None and
                    auth_session.inspect(sessions, absolute.opaque) is None):
                break
            time.sleep(.1)
        else:
            raise AssertionError("DB_SESSION_EXPIRY_NOT_OBSERVED")
        # A NEW cryptographically valid assertion is not a new DB session.
        for session in (idle, absolute):
            assert get_session(session).status_code == 401
            assert get_session(session, path="/health/ready").status_code == 503
        assert request(client, "a", endpoint).json()["scope_user_id"] == actor["owner"]
        assert request(client, "b", endpoint).json()["scope_user_id"] == state["b"]["owner"]
    print(f"API_F3_{phase.upper()}_SESSION_ROTATION_EXPIRY_NO_IMPLICIT_REFRESH=PASS", flush=True)


def verify_parallel_history_replay(phase, state):
    """One admission for one signed assertion across six simultaneous TLS requests."""
    endpoint = "/v1/conversations"
    for label in ("a", "b"):
        proof = signature(label, "GET", endpoint)
        barrier = Barrier(6, timeout=10)
        def one(_):
            with tls_client() as client:
                barrier.wait()
                response = client.get(BASE + endpoint, headers={
                    "Authorization": "BFF-Assertion " + proof})
                assert response.headers["cache-control"] == "no-store"
                if response.status_code == 200:
                    assert response.json()["scope_user_id"] == state[label]["owner"]
                else:
                    assert response.status_code in (401, 503)
                    assert "items" not in response.json()
                return response.status_code
        with ThreadPoolExecutor(max_workers=6) as pool:
            results = tuple(pool.map(one, range(6)))
        assert results.count(200) == 1, "SINGLE_ASSERTION_PARALLEL_ADMISSION_MISMATCH"
        with tls_client() as client:
            # A separate fresh proof must still read the unchanged owner data.
            request(client, label, endpoint, expect=200)
            assert client.get(BASE + endpoint, headers={
                "Authorization": "BFF-Assertion " + proof}).status_code == 401
    print(f"API_F3_{phase.upper()}_PARALLEL_HISTORY_REPLAY_ONE_ADMISSION_PER_OWNER=PASS", flush=True)


def verify_cursor_restore(phase, state):
    """Bind a real source cursor to its exact page2 IDs across independent restore."""
    cursor_file = PRIVATE / "source_page2.json"
    endpoint = "/v1/conversations"
    with tls_client() as client:
        if phase == "before":
            expected = {}
            for label in ("a", "b"):
                page = request(client, label, endpoint, "limit=2").json()
                cursor = page["page"]["next_cursor"]
                assert cursor
                second = request(client, label, endpoint,
                                 urlencode({"limit": "2", "cursor": cursor})).json()
                expected[label] = {"cursor": cursor, "ids": [
                    item["conversation_id"] for item in second["items"]]}
            write_secret(cursor_file, json.dumps(expected).encode())
            assert expected["a"]["ids"] == ["f3-net-a-3", "f3-net-a-2"]
            assert expected["b"]["ids"] == ["f3-net-b-1"]
            print("API_F3_SOURCE_CURSOR_PAGE2_RECORDED=PASS", flush=True)
        else:
            expected = json.loads(cursor_file.read_text())
            for label, foreign in (("a", "b"), ("b", "a")):
                query = urlencode({"limit": "2", "cursor": expected[label]["cursor"]})
                page = request(client, label, endpoint, query).json()
                assert page["scope_user_id"] == state[label]["owner"]
                assert [item["conversation_id"] for item in page["items"]] == expected[label]["ids"]
                request(client, foreign, endpoint, query, expect=404)
            print("API_F3_RESTORED_SOURCE_CURSOR_PAGE2_OWNER_PARITY=PASS", flush=True)


def verify_history(phase: str):
    state = json.loads((PRIVATE / "session_state.json").read_text())
    with tls_client() as client:
        assert client.get(BASE + "/v1/conversations").status_code == 401
        # The real PG 005 replay ledger makes a signed JWT single-use.
        bound = signature("a", "GET", "/v1/conversations", "limit=2")
        bound_headers = {"Authorization": "BFF-Assertion " + bound}
        assert client.get(BASE + "/v1/conversations?limit=2",
                          headers=bound_headers).status_code == 200
        assert client.get(BASE + "/v1/conversations?limit=2",
                          headers=bound_headers).status_code == 401
        mismatch = signature("a", "GET", "/v1/conversations", "limit=2")
        assert client.get(BASE + "/v1/conversations?limit=3",
                          headers={"Authorization": "BFF-Assertion " + mismatch}).status_code == 401
        poisoned = signature("a", "GET", "/v1/conversations")
        assert client.get(BASE + "/v1/conversations", headers={
            "Authorization": "BFF-Assertion " + poisoned,
            "X-Owner-Id": state["b"]["owner"]
        }).status_code == 401
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
        owner_a_first = request(client, "a", "/v1/conversations", "limit=2").json()
        owner_a_cursor = owner_a_first["page"]["next_cursor"]
        assert owner_a_cursor and owner_a_first["page"]["has_more"]
        # B has a valid signed request; the A-owned HMAC cursor remains forbidden.
        assert request(client, "b", "/v1/conversations",
                       urlencode({"limit": "2", "cursor": owner_a_cursor}),
                       expect=404).status_code == 404
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
    verify_disabled_send_retries(phase, state)
    verify_runtime_signer_drift(phase)
    verify_session_lifecycle(phase, state)
    verify_parallel_history_replay(phase, state)
    verify_cursor_restore(phase, state)
    print(f"HTTPS_APP_ONLY_{phase.upper()}_A_B_OWNER_PAGES_DETAILS_404_SEND503_MTLS_NEGATIVE=PASS", flush=True)
    print(f"HTTPS_APP_ONLY_{phase.upper()}_005_JTI_REPLAY_QUERY_BINDING_CROSS_OWNER_CURSOR_NEGATIVE=PASS", flush=True)


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
    parser.add_argument("phase", choices=("seed", "before", "after", "ready200", "ready503"))
    args = parser.parse_args()
    require_lab()
    if args.phase in ("ready200", "ready503"):
        expected = 200 if args.phase == "ready200" else 503
        with tls_client() as c:
            res = c.get(BASE + "/internal/ready", timeout=12.0)
        assert res.status_code == expected, "PG_DEPENDENCY_READINESS_STATUS_MISMATCH"
        print("HTTPS_APP_ONLY_PG_DEPENDENCY_READY_" + str(expected) + "=PASS", flush=True)
        return
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
