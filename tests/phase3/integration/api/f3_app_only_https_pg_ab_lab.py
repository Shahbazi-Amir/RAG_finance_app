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
from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
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
    assert db in ("rag_finance_f3_http_ab_source", "rag_finance_f3_http_ab_restored",
                  "rag_finance_f3_m10_process_crash", "rag_finance_f3_http_ab_revoked_copy")
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


def sql_snapshot(phase: str):
    """Independent service-role SQL, never derived from HTTP or UI output."""
    host, db = {
        "snapshot_source": ("demo-db", "rag_finance_f3_http_ab_source"),
        "snapshot_restore": ("restore-db", "rag_finance_f3_http_ab_restored"),
        "snapshot_revoked_copy": ("demo-db", "rag_finance_f3_http_ab_revoked_copy"),
    }[phase]
    state = json.loads((PRIVATE / "session_state.json").read_text())
    assert state["a"]["owner"] != state["b"]["owner"], "OWNER_COLLISION"
    rows = {}
    with conn("history_app", host, db) as sql:
        for label, nconv, nmsg in (("a", 5, 4), ("b", 3, 2)):
            with sql.transaction():
                sql.execute("SELECT set_config('app.owner_id', %s, true)", (state[label]["owner"],))
                conv = sql.execute(
                    "SELECT id,title,state,created_at,updated_at FROM history_l1.conversations "
                    "ORDER BY updated_at DESC,id DESC").fetchall()
                msg = sql.execute(
                    "SELECT id,conversation_id,role,body,created_at FROM history_l1.messages "
                    "ORDER BY created_at DESC,id DESC").fetchall()
                assert [r["id"] for r in conv] == [
                    f"f3-net-{label}-{n}" for n in range(nconv, 0, -1)]
                assert [r["id"] for r in msg] == [
                    f"f3-net-{label}-msg-{n}" for n in range(nmsg, 0, -1)]
                assert all(r["conversation_id"] == f"f3-net-{label}-1" for r in msg)
                for table in ("send_receipts", "execution_attempts", "answers", "create_receipts"):
                    assert sql.execute(f"SELECT count(*) AS n FROM history_l1.{table}").fetchone()["n"] == 0
                rows[label] = {"conversations": conv, "messages": msg}
            with sql.transaction():
                assert sql.execute("SELECT count(*) AS n FROM history_l1.conversations").fetchone()["n"] == 0
    digest = sha256(json.dumps(rows, sort_keys=True, default=str).encode()).hexdigest()
    baseline = PRIVATE / "sql_history_baseline.sha256"
    if phase == "snapshot_source" and not baseline.exists():
        write_secret(baseline, digest.encode())
    else:
        assert baseline.read_text() == digest, "SQL_HISTORY_SNAPSHOT_DRIFT"
    print("BFF_SQL_" + phase.upper() + "_A5_B3_M4_M2_ZERO_SEND_EXACT_PARITY=PASS", flush=True)


def authenticated_backup():
    """Lab-only AEAD, bounded memory, independent wrong-key/tamper tests.
    No persistent production key custody, rotation, retention or KMS claim.
    """
    source = PRIVATE / "aead_input.dump"
    assert source.is_file() and not source.is_symlink()
    assert (source.stat().st_mode & 0o077) == 0
    assert 0 < source.stat().st_size <= 16 * 1024 * 1024
    payload = source.read_bytes()
    aad = b"f3-db-lab-pg17.11-history-001-010-v1"
    key = AESGCM.generate_key(bit_length=256)
    nonce = secrets.token_bytes(12)
    cipher = AESGCM(key)
    encrypted = cipher.encrypt(nonce, payload, aad)
    out = PRIVATE / "aead_backup.bin"
    write_secret(out, nonce + encrypted)
    envelope = out.read_bytes()
    assert envelope != payload and len(envelope) == len(payload) + 28
    def reject(k, n, data, context):
        try:
            AESGCM(k).decrypt(n, data, context)
        except InvalidTag:
            return
        raise AssertionError("UNAUTHENTICATED_BACKUP_ACCEPTED")
    reject(AESGCM.generate_key(bit_length=256), nonce, encrypted, aad)
    print("DB_BACKUP_AEAD_WRONG_KEY_REJECTED=PASS", flush=True)
    reject(key, nonce, bytes([encrypted[0] ^ 1]) + encrypted[1:], aad)
    print("DB_BACKUP_AEAD_TAMPER_REJECTED=PASS", flush=True)
    reject(key, nonce, encrypted[:-1], aad)
    print("DB_BACKUP_AEAD_TRUNCATION_REJECTED=PASS", flush=True)
    reject(key, nonce, encrypted, aad + b"-wrong")
    print("DB_BACKUP_AEAD_WRONG_CONTEXT_REJECTED=PASS", flush=True)
    restored = cipher.decrypt(envelope[:12], envelope[12:], aad)
    assert sha256(restored).digest() == sha256(payload).digest()
    write_secret(PRIVATE / "aead_verified_restore.dump", restored)
    assert all((p.stat().st_mode & 0o777)==0o600 for p in (
        source,out,PRIVATE/"aead_verified_restore.dump"))
    source.unlink()
    print("DB_BACKUP_AES256_GCM_ROUNDTRIP_MODE0600=PASS", flush=True)


def catalog_snapshot(phase):
    """Versioned metadata evidence, no user data exported, no schema changes."""
    host, db = (("demo-db", "rag_finance_f3_http_ab_source") if phase=="catalog_source"
                else ("restore-db","rag_finance_f3_http_ab_restored"))
    expected = {"conversations","messages","create_receipts","send_receipts",
                "execution_attempts","answers"}
    state = json.loads((PRIVATE/"session_state.json").read_text())
    with conn("history_app",host,db) as c:
        with c.transaction():
            c.execute("SET TRANSACTION READ ONLY")
            c.execute("SELECT set_config('app.owner_id',%s,true)",(state["a"]["owner"],))
            columns=c.execute("""SELECT table_name,column_name,data_type,is_nullable,ordinal_position
                FROM information_schema.columns WHERE table_schema='history_l1'
                ORDER BY table_name,ordinal_position""").fetchall()
            assert {x["table_name"] for x in columns}==expected
            assert {x["table_name"] for x in columns if x["column_name"]=="owner_id"
                    and x["is_nullable"]=="NO" and x["data_type"]=="text"}==expected
            constraints=c.execute("""SELECT r.relname AS tbl,co.conname,co.contype,
                  pg_get_constraintdef(co.oid) AS def,co.convalidated
                  FROM pg_constraint co JOIN pg_class r ON r.oid=co.conrelid
                  JOIN pg_namespace n ON n.oid=r.relnamespace
                  WHERE n.nspname='history_l1' ORDER BY r.relname,co.conname""").fetchall()
            assert {x["tbl"] for x in constraints if x["contype"]=="p"}==expected
            assert all(x["convalidated"] for x in constraints)
            assert all("owner_id" in x["def"] for x in constraints if x["contype"] in ("p","f","u"))
            indexes=c.execute("""SELECT tablename,indexname,indexdef FROM pg_indexes
                WHERE schemaname='history_l1' ORDER BY tablename,indexname""").fetchall()
            assert {"conversation_order_idx","message_order_idx"}.issubset(
                {x["indexname"] for x in indexes})
            policies=c.execute("""SELECT tablename,policyname,roles::text,cmd,qual,with_check
                FROM pg_policies WHERE schemaname='history_l1' ORDER BY tablename,policyname""").fetchall()
            assert {x["tablename"] for x in policies if x["policyname"]=="owner_only"}==expected
            assert len(policies)==6 and all(x["roles"]=="{history_app}" for x in policies)
            for table in expected:
                assert c.execute("SELECT row_security_active(%s::regclass) AS active",
                    ("history_l1."+table,)).fetchone()["active"]
            # Tiny fixtures naturally prefer sequential scans. Force the planner
            # only to prove access-path eligibility, NOT latency or production tuning.
            c.execute("SET LOCAL enable_seqscan=off")
            queries=[
              ("SELECT id FROM history_l1.conversations WHERE owner_id=%s AND state='active' "
               "ORDER BY created_at DESC,id DESC LIMIT 2",(state["a"]["owner"],),"conversation_order_idx"),
              ("SELECT id FROM history_l1.messages WHERE owner_id=%s AND conversation_id=%s "
               "ORDER BY created_at,id LIMIT 2",(state["a"]["owner"],"f3-net-a-1"),"message_order_idx")]
            def index_names(node):
                names={node["Index Name"]} if "Index Name" in node else set()
                for child in node.get("Plans",[]): names.update(index_names(child))
                return names
            for query,params,expected_index in queries:
                plan=c.execute("EXPLAIN (FORMAT JSON, COSTS OFF) "+query,params).fetchone()["QUERY PLAN"]
                assert expected_index in index_names(plan[0]["Plan"]),"EXPECTED_INDEX_ACCESS_PATH_MISSING"
    metadata={"columns":columns,"constraints":constraints,"indexes":indexes,"policies":policies}
    digest=sha256(json.dumps(metadata,sort_keys=True,default=str).encode()).hexdigest()
    baseline=PRIVATE/"catalog_baseline.sha256"
    if phase=="catalog_source":
        write_secret(baseline,digest.encode())
        # Sanitized catalog metadata only; no row bodies, IDs, credentials or DSNs.
        write_secret(PRIVATE/"catalog_counts.json",json.dumps(
            {"tables":len(expected),"columns":len(columns),"constraints":len(constraints),
             "indexes":len(indexes),"policies":len(policies)},sort_keys=True).encode())
    else:
        assert baseline.read_text()==digest,"RESTORE_CATALOG_METADATA_DRIFT"
    print("DB_"+phase.upper()+"_OWNER_KEYS_RLS_METADATA_INDEX_PATHS=PASS",flush=True)


M10_DB = "rag_finance_f3_m10_process_crash"
M10_OWNER = "f3-crash-owner-a"
M10_OTHER = "f3-crash-owner-b"


def m10_request():
    return {"kind": "send_message_request", "contract_version": "product.v1",
            "requested_conversation_id": None, "client_message_id": "1"*32,
            "idempotency_key": "f3-m10-process-replay", "question": "synthetic crash probe"}


def m10_child(mode):
    # Trusted repository fixture only; never expose through HTTP or dispatch.
    from apps.api import history_api
    import repository
    assert mode in ("t1_before", "t1_after", "t2_before", "t2_after")
    req = m10_request()
    def operation(c):
        if mode.startswith("t1"):
            return history_api.send_t1(c, M10_OWNER, req, history_api.uid(), history_api.uid())
        return repository.start_t2(c, M10_OWNER, None, req["client_message_id"],
                                   req["idempotency_key"], history_api.uid(), history_api.uid())
    with conn("history_app", "demo-db", M10_DB) as c:
        if mode.endswith("before"):
            # Repository transaction nests as savepoint; enclosing tx uncommitted.
            with c.transaction():
                operation(c)
                os.kill(os.getpid(), signal.SIGKILL)
        else:
            operation(c)
            os.kill(os.getpid(), signal.SIGKILL)
    raise AssertionError("PROCESS_CRASH_DID_NOT_OCCUR")


def m10_process():
    from apps.api import history_api
    import repository
    req = m10_request()
    def kill_at(mode):
        p = subprocess.run([sys.executable, __file__, "m10_child", "--crash", mode],
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=45)
        assert p.returncode == -signal.SIGKILL and not p.stdout, "CHILD_NOT_KILLED_BEFORE_ACK"
        print("M10_REAL_PROCESS_SIGKILL_" + mode.upper() + "=PASS", flush=True)
    def inventory(owner):
        with conn("history_app", "demo-db", M10_DB) as c:
            with c.transaction():
                c.execute("SET TRANSACTION READ ONLY")
                c.execute("SELECT set_config('app.owner_id', %s, true)", (owner,))
                return {table:c.execute(f"SELECT * FROM history_l1.{table} ORDER BY id").fetchall()
                        for table in ("conversations", "messages", "send_receipts", "execution_attempts", "answers")}
    def counts(rows):
        return tuple(len(rows[t]) for t in (
            "conversations", "messages", "send_receipts", "execution_attempts", "answers"))
    assert counts(inventory(M10_OWNER)) == counts(inventory(M10_OTHER)) == (0,0,0,0,0)
    kill_at("t1_before")
    assert counts(inventory(M10_OWNER)) == (0,0,0,0,0), "UNCOMMITTED_T1_SURVIVED"
    kill_at("t1_after")
    committed = inventory(M10_OWNER)
    assert counts(committed) == (1,1,1,0,0), "COMMITTED_T1_LOST_OR_DUPLICATED"
    original = committed["send_receipts"][0]
    with conn("history_app", "demo-db", M10_DB) as c:
        replay = history_api.send_t1(c, M10_OWNER, req, history_api.uid(), history_api.uid())
        assert replay["disposition"] == "replayed"
        assert replay["message_id"] == original["user_message_id"]
        assert replay["resolved_conversation_id"] == original["resolved_conversation_id"]
        try:
            history_api.send_t1(c, M10_OWNER, dict(req, question="changed payload"),
                                history_api.uid(), history_api.uid())
        except repository.Conflict:
            pass
        else:
            raise AssertionError("CHANGED_PAYLOAD_REPLAY_ACCEPTED")
        b = history_api.send_t1(c, M10_OTHER, req, history_api.uid(), history_api.uid())
        assert b["disposition"] == "created" and b["message_id"] != replay["message_id"]
    assert inventory(M10_OWNER) == committed
    assert counts(inventory(M10_OTHER)) == (1,1,1,0,0)
    kill_at("t2_before")
    assert inventory(M10_OWNER) == committed, "UNCOMMITTED_T2_SURVIVED"
    kill_at("t2_after")
    reserved = inventory(M10_OWNER)
    assert counts(reserved) == (1,1,1,1,0)
    attempt = reserved["execution_attempts"][0]
    with conn("history_app", "demo-db", M10_DB) as c:
        replay_attempt = repository.start_t2(c, M10_OWNER, None, req["client_message_id"],
                                            req["idempotency_key"], history_api.uid(), history_api.uid())
        assert replay_attempt["id"] == attempt["id"]
        assert replay_attempt["reserved_answer_id"] == attempt["reserved_answer_id"]
        assert replay_attempt["send_receipt_id"] == original["id"]
    assert inventory(M10_OWNER) == reserved
    assert counts(inventory(M10_OTHER)) == (1,1,1,0,0)
    assert counts(inventory("")) == (0,0,0,0,0)
    print("M10_REAL_T1_T2_PROCESS_CRASH_REPLAY_EXACT_DURABLE_IDS_ZERO_ANSWERS=PASS", flush=True)


def concurrent_repository_fence():
    """Real LOGIN sessions, same trusted repository, no HTTP Send or dispatch."""
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier
    from apps.api import history_api
    import repository as r
    owner, other = "f3-race-owner-a", "f3-race-owner-b"
    create = {"kind":"create_conversation_request","contract_version":"product.v1",
              "client_conversation_id":"race-conversation","idempotency_key":"race-create-0001",
              "title":"isolated concurrency"}
    send = {"kind":"send_message_request","contract_version":"product.v1",
            "requested_conversation_id":None,"client_message_id":"race-message",
            "idempotency_key":"race-send-0001","question":"synthetic concurrent repository"}
    def connect():
        return conn("history_app","demo-db",M10_DB)
    def race(op):
        barrier=Barrier(6,timeout=15)
        def worker(_):
            with connect() as c:
                c.execute("SET statement_timeout='20s'")
                barrier.wait()
                value=op(c)
                assert c.execute("SELECT count(*) AS n FROM history_l1.conversations").fetchone()["n"]==0
                return value
        with ThreadPoolExecutor(max_workers=6) as pool:
            return list(pool.map(worker,range(6)))
    def create_op(c):
        return r.create_conversation(c,owner,create,r.uid(),r.uid())
    cs=race(create_op)
    assert sorted(x["disposition"] for x in cs)==["created"]+["replayed"]*5
    cid=cs[0]["conversation"]["conversation_id"]
    assert all(x["conversation"]["conversation_id"]==cid for x in cs)
    print("DB_RACE_CREATE_SIX_SESSIONS_ONE_CREATED_FIVE_REPLAYED=PASS",flush=True)
    def send_op(c):
        return r.send_t1(c,owner,send,r.uid(),r.uid())
    ss=race(send_op)
    assert sorted(x["disposition"] for x in ss)==["created"]+["replayed"]*5
    mid,scid=ss[0]["message_id"],ss[0]["resolved_conversation_id"]
    assert all(x["message_id"]==mid and x["resolved_conversation_id"]==scid for x in ss)
    print("DB_RACE_T1_SIX_SESSIONS_ONE_CREATED_FIVE_REPLAYED=PASS",flush=True)
    def attempt_op(c):
        return r.start_t2(c,owner,None,send["client_message_id"],send["idempotency_key"],r.uid(),r.uid())
    attempts=race(attempt_op)
    aid=attempts[0]["id"]
    assert all(x["id"]==aid and x["reserved_answer_id"]==attempts[0]["reserved_answer_id"] for x in attempts)
    print("DB_RACE_T2_SIX_SESSIONS_EXACT_ONE_ATTEMPT=PASS",flush=True)
    q={k:v for k,v in send.items() if k!="question"}
    q["kind"]="message_request_status_query"
    tables=("conversations","messages","create_receipts","send_receipts","execution_attempts","answers")
    def snap(c,actor):
        with c.transaction():
            c.execute("SET TRANSACTION READ ONLY")
            c.execute("SELECT set_config('app.owner_id',%s,true)",(actor,))
            return {t:c.execute(f"SELECT to_jsonb(t)::text AS row FROM history_l1.{t} t ORDER BY 1").fetchall() for t in tables}
    def denied(fn,exc):
        try:fn()
        except exc:return
        raise AssertionError("EXPECTED_REPOSITORY_DENIAL_MISSING")
    with connect() as c:
        a=snap(c,owner)
        assert tuple(map(len,a.values()))==(2,1,1,1,1,0)
        assert all(not v for v in snap(c,other).values())
        # Reuse the SAME physical connection across successful and aborted tx.
        for target in (scid,"nonexistent-race-conversation"):
            denied(lambda:r.list_messages(c,other,target),r.NotFound)
            denied(lambda:r.send_t1(c,other,dict(send,requested_conversation_id=target),r.uid(),r.uid()),r.NotFound)
        denied(lambda:r.read_status(c,other,q,r.uid(),r.uid()),r.NotFound)
        denied(lambda:r.mark_attempt(c,other,aid,"cancelled"),r.NotFound)
        denied(lambda:r.start_t2(c,other,None,send["client_message_id"],send["idempotency_key"],r.uid(),r.uid()),r.NotFound)
        denied(lambda:r.create_conversation(c,owner,dict(create,title="changed"),r.uid(),r.uid()),r.Conflict)
        denied(lambda:r.send_t1(c,owner,dict(send,question="changed"),r.uid(),r.uid()),r.Conflict)
        assert snap(c,owner)==a and all(not v for v in snap(c,other).values())
        print("DB_REPOSITORY_FOREIGN_UNKNOWN_CONFLICT_NINE_DENIALS_ZERO_MUTATION=PASS",flush=True)
        for expected in ("attempt_unknown","cancelled"):
            r.mark_attempt(c,owner,aid,expected)
            status=r.read_status(c,owner,q,r.uid(),r.uid())
            assert status["status"]==expected and status["attempt_id"]==aid and status["answer"] is None
            assert attempt_op(c)["id"]==aid
        denied(lambda:r.mark_attempt(c,owner,aid,"attempt_unknown"),r.Conflict)
        assert r.read_status(c,owner,q,r.uid(),r.uid())["status"]=="cancelled"
        final=snap(c,owner)
        assert tuple(map(len,final.values()))==(2,1,1,1,1,0)
        assert all(final[t]==a[t] for t in tables if t!="execution_attempts")
        assert all(not v for v in snap(c,other).values())
        assert all(c.execute(f"SELECT count(*) AS n FROM history_l1.{t}").fetchone()["n"]==0 for t in tables)
        print("DB_REPOSITORY_UNKNOWN_CANCELLED_TERMINAL_REPLAY_SAME_ID_NO_ANSWER=PASS",flush=True)
        print("DB_REPOSITORY_SAME_CONNECTION_ABORT_UNSET_OWNER_SIX_TABLES_ZERO=PASS",flush=True)


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


def verify_revoked_backup_copy():
    # Restore of a snapshot taken AFTER revocation. The older pre-revoke
    # snapshot is not safe to admit without a separately approved fence.
    state=json.loads((PRIVATE/"session_state.json").read_text())
    with tls_client() as c:
        for path,query in (
            ("/v1/conversations","limit=2"),
            ("/v1/conversations/f3-net-a-1/messages","limit=2"),
        ):
            request(c,"a",path,query,expect=401)
        b=request(c,"b","/v1/conversations","limit=2").json()
        assert b["scope_user_id"]==state["b"]["owner"]
        assert [x["conversation_id"] for x in b["items"]]==["f3-net-b-3","f3-net-b-2"]
        own=request(c,"b","/v1/conversations/f3-net-b-1/messages","limit=2").json()
        assert len(own["items"])==2
        assert all(x["message_id"].startswith("f3-net-b-") for x in own["items"])
        foreign=request(c,"b","/v1/conversations/f3-net-a-1/messages",expect=404).json()
        unknown=request(c,"b","/v1/conversations/f3-net-missing/messages",expect=404).json()
        # Do not compare per-request correlation identifiers.
        for result in (foreign,unknown):
            assert isinstance(result.get("error"),dict)
        assert foreign["error"]["code"]==unknown["error"]["code"]
        assert foreign["error"]["category"]==unknown["error"]["category"]
    print("DB_POST_REVOKE_BACKUP_RESTORED_A401_B200_FOREIGN_UNKNOWN_404=PASS",flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("phase", choices=("seed", "before", "after", "revoke", "snapshot_source", "snapshot_restore", "ready200", "ready503", "m10_process", "m10_child", "authenticated_backup", "catalog_source", "catalog_restore", "snapshot_revoked_copy", "verify_revoked_copy", "concurrent_repository"))
    parser.add_argument("--crash", choices=("t1_before", "t1_after", "t2_before", "t2_after"))
    args = parser.parse_args()
    require_lab()
    if args.phase == "authenticated_backup":
        authenticated_backup()
        return
    if args.phase in ("catalog_source", "catalog_restore"):
        catalog_snapshot(args.phase)
        return
    if args.phase == "concurrent_repository":
        concurrent_repository_fence()
        return
    if args.phase == "m10_process":
        m10_process()
        return
    if args.phase == "m10_child":
        m10_child(args.crash)
        return
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
    if args.phase in ("snapshot_source", "snapshot_restore", "snapshot_revoked_copy"):
        sql_snapshot(args.phase)
        return
    if args.phase == "verify_revoked_copy":
        run_server("demo-db", "rag_finance_f3_http_ab_revoked_copy", verify_revoked_backup_copy)
        return
    host = "demo-db" if args.phase == "before" else "restore-db"
    db = ("rag_finance_f3_http_ab_source" if args.phase == "before"
          else "rag_finance_f3_http_ab_restored")
    def scenario():
        if args.phase == "revoke":
            revoke_and_check()
        else:
            verify_history(args.phase)
    run_server(host, db, scenario)


if __name__ == "__main__":
    main()
