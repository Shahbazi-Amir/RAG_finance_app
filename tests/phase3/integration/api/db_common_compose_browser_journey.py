"""Actual Chromium/Next/BFF/Keycloak -> app-only H11 mTLS -> PG CI witness.

Reuse the original real login harness. No route interception, cookie creation,
owner header, fake response or engine. This is a single-runner integration
witness, not Foundation's Docker/fresh-volume or destination acceptance.
"""
from __future__ import annotations

import asyncio
from contextlib import contextmanager
import json
import re
import time
import os
from pathlib import Path
import secrets
import socket
import ssl
import subprocess
import sys
import uuid
from hashlib import sha256

import jwt

import httpx
import psycopg
from psycopg.rows import dict_row
from psycopg import sql
from psycopg.conninfo import conninfo_to_dict, make_conninfo
from playwright.async_api import async_playwright, expect

ROOT = Path(__file__).resolve().parents[4]
sys.path[:0] = [str(ROOT), str(ROOT / "tests/phase3/integration/ui")]
from phase3_auth_demo import Demo, ORIGIN, TITLE, SIGN_ISS, SIGN_AUD, SIGN_KID
from src.phase3.storage.postgres import auth_session
from apps.api import history_api


class AppOnlyBrowserDemo(Demo):
    def add(self, cmd, env=None, cwd=ROOT):
        # Replace only the old test harness's API process, not application
        # source. Production-path TLS protocol and app-only guard are shared
        # with the actual listener; CI DB profile remains explicitly isolated.
        if cmd[:4] == [sys.executable, "-m", "uvicorn", "apps.api.product_session_api:app"]:
            self.api_env = dict(env)
            self.api_env.update(
                PHASE3_APP_MODE="APP_ONLY",
                API_RUNNER_EXECUTION_MODE="APP_ONLY",
                API_CURSOR_KEY=secrets.token_urlsafe(48),
                API_CURSOR_TTL_SECONDS="300",
                APP_ONLY_CI_API_PORT=cmd[cmd.index("--port") + 1],
                APP_ONLY_CI_CLIENT_CERT=str(self.client[0]),
                APP_ONLY_CI_SERVER_CERT=cmd[cmd.index("--ssl-certfile") + 1],
                APP_ONLY_CI_SERVER_KEY=cmd[cmd.index("--ssl-keyfile") + 1],
                APP_ONLY_CI_CLIENT_CA=cmd[cmd.index("--ssl-ca-certs") + 1],
            )
            self.api_command = [sys.executable, "-u", str(ROOT /
                "tests/phase3/integration/api/app_only_signed_pg_ci_h11.py")]
            self.api_process = super().add(self.api_command, self.api_env)
            return self.api_process
        if any(str(x).endswith("bootstrap_010_worker.py") for x in cmd):
            self.bootstrap_command = list(cmd)
            self.bootstrap_process = super().add(cmd, env, cwd)
            return self.bootstrap_process
        if env is not None and "AUTH_CI_LOGIN_MODE" in env:
            env = {**env, "PHASE3_APP_MODE": "APP_ONLY"}
            env.pop("AUTH_CI_PRODUCT_CHAT_MODE", None)
        return super().add(cmd, env, cwd)

    def enforce_pg_tls_only(self, pg_id):
        """Called only for exact source CI service or UUID-labeled restore."""
        assert re.fullmatch(r"[a-f0-9]{64}",pg_id)
        info=json.loads(self.ci_command("docker","inspect",pg_id))[0]
        assert info["Id"]==pg_id and info["State"]["Running"]
        assert info["Config"]["Image"]=="postgres:17.11" or re.fullmatch(r"sha256:[a-f0-9]{64}",info["Config"]["Image"])
        assert (pg_id==os.environ["API_F3_ISOLATED_PG_CID"] or
                re.fullmatch(r"[a-f0-9]{32}",info["Config"]["Labels"].get("rag.finance.ci.restore","")))
        script=("set -eu; cd /var/lib/postgresql/data; test -f pg_hba.conf; "
                "test ! -e pg_hba.f3; "
                "printf 'hostnossl all all all reject\nhostssl all all all scram-sha-256\n' > pg_hba.f3; "
                "cat pg_hba.conf >> pg_hba.f3; chown postgres:postgres pg_hba.f3; "
                "chmod 0600 pg_hba.f3; mv pg_hba.f3 pg_hba.conf")
        self.ci_command("docker","exec","-u","0",pg_id,"sh","-c",script)

    def verify_db_tls(self, dsn, phase):
        cfg=conninfo_to_dict(dsn)
        assert cfg["sslmode"]=="verify-full" and cfg.get("gssencmode")=="disable"
        assert cfg["host"]=="127.0.0.1"
        for _ in range(80):
            try:
                with psycopg.connect(dsn,autocommit=True) as conn:
                    assert conn.execute("SELECT ssl FROM pg_stat_ssl WHERE pid=pg_backend_pid()").fetchone()[0]
                break
            except psycopg.OperationalError:time.sleep(.5)
        else:raise AssertionError("DB_TLS_VERIFY_FULL_NOT_READY")
        for bad in (dict(sslmode="disable"),dict(host="localhost",hostaddr="127.0.0.1")):
            try:
                with psycopg.connect(**dict(cfg,**bad)):pass
            except psycopg.OperationalError:pass
            else:raise AssertionError("DB_TLS_NEGATIVE_ACCEPTED")
        print("DB_COMPOSE_"+phase+"_PG_VERIFY_FULL_NO_PLAINTEXT_WRONG_SAN=PASS",flush=True)

    def db55_readonly_catalog_gate(self, phase, cfg):
        """Run unchanged pinned DB55 verifier with a distinct no-write login.
        CI clone only; no new bridge GRANT, no deployment attestation.
        """
        dsn=cfg["DB55_CI_AUDITOR_DSN"]
        options=conninfo_to_dict(dsn)
        assert options["sslmode"]=="verify-full"
        assert re.fullmatch(r"history_browser_restore_ci_[a-f0-9]{16}",options["dbname"])
        assert options["user"]=="f3_db55_ci_auditor"
        verifier=ROOT/"infra/postgres/staging/db55_verify_staging.sql"
        assert subprocess.check_output(["git","hash-object",str(verifier)],cwd=ROOT,text=True).strip()=="e2115d8cebc649fdf05d3fbee4ef435ad5f39a47"
        with psycopg.connect(dsn,autocommit=True) as conn:
            assert conn.execute("SELECT current_user,rolsuper,rolbypassrls,rolinherit,rolcreatedb,rolcreaterole FROM pg_roles WHERE rolname=current_user").fetchone()==("f3_db55_ci_auditor",False,False,False,False,False)
            assert conn.execute("SELECT ssl FROM pg_stat_ssl WHERE pid=pg_backend_pid()").fetchone()[0]
            assert not conn.execute("SELECT EXISTS(SELECT 1 FROM pg_auth_members WHERE member=(SELECT oid FROM pg_roles WHERE rolname=current_user))").fetchone()[0]
            assert not conn.execute("SELECT has_database_privilege(current_user,current_database(),'CREATE')").fetchone()[0]
            for schema in ("history_l1","auth_l1","db55_audit"):
                assert not conn.execute("SELECT has_schema_privilege(current_user,%s,'USAGE')",(schema,)).fetchone()[0]
        env=dict(os.environ,PGHOST=options["host"],PGPORT=options["port"],PGDATABASE=options["dbname"],PGUSER=options["user"],PGPASSWORD=options["password"],PGSSLMODE="verify-full",PGSSLROOTCERT=options["sslrootcert"],PGGSSENCMODE="disable",PGOPTIONS="-c default_transaction_read_only=on")
        result=subprocess.run(["psql","-X","-v","ON_ERROR_STOP=1","-v","db55_phase=private_no_dispatch","-f",str(verifier)],env=env,capture_output=True,timeout=20)
        assert result.returncode==0 and b"DB55_private_no_dispatch_DB_ROLE_SCHEMA_AND_FUNCTION_GATE_PASS" in result.stderr, "DB55_PINNED_CATALOG_GATE_FAILED"
        print("DB_COMMON_DB55_"+phase+"_PINNED_READONLY_AUDITOR_TLS=PASS",flush=True)

    def restricted_db_snapshot(self, phase, dsns=None, baseline=None, revoked=False):
        """Independent read-only product-role SQL. No admin for History rows.
        Real OIDC owner IDs come only from successful browser logins.
        Both the actual source and restored role connections require TLS.
        """
        assert phase in ("SOURCE","SOURCE_AFTER_SEND","RESTORED","AFTER_OUTAGE","AFTER_BROWSER","AFTER_REVOKE")
        cfg=dsns if dsns is not None else os.environ
        tables=("conversations","messages","create_receipts","send_receipts","execution_attempts","answers")
        result={}
        with psycopg.connect(cfg["DB_APP_DSN"],autocommit=True) as c:
            flags=c.execute("""SELECT current_user,rolsuper,rolbypassrls,rolinherit,
                          rolcreaterole,rolcreatedb FROM pg_roles WHERE rolname=current_user""").fetchone()
            assert flags==("history_app",False,False,False,False,False)
            assert conninfo_to_dict(cfg["DB_APP_DSN"])["sslmode"]=="verify-full"
            assert c.execute("SELECT ssl FROM pg_stat_ssl WHERE pid=pg_backend_pid()").fetchone()[0]
            for label,foreign in (("A","B"),("B","A")):
                with c.transaction():
                    c.execute("SET TRANSACTION READ ONLY")
                    c.execute("SELECT set_config('app.owner_id',%s,true)",(self.owners[label],))
                    scoped={}
                    for table in tables:
                        q=sql.SQL("SELECT owner_id,to_jsonb(t)::text FROM history_l1.{} t ORDER BY to_jsonb(t)::text").format(sql.Identifier(table))
                        rows=c.execute(q).fetchall()
                        assert all(row[0]==self.owners[label] for row in rows)
                        scoped[table]=(len(rows),sha256(json.dumps(rows,ensure_ascii=False).encode()).hexdigest())
                        n=c.execute(sql.SQL("SELECT count(*) FROM history_l1.{} WHERE owner_id=%s").format(sql.Identifier(table)),(self.owners[foreign],)).fetchone()[0]
                        assert n==0
                    assert scoped["conversations"][0]==3 and scoped["messages"][0]>=1
                    assert all(scoped[t][0]==0 for t in ("send_receipts","execution_attempts","answers"))
                    result[label]=scoped
                with c.transaction():
                    c.execute("SET TRANSACTION READ ONLY")
                    for table in tables:
                        assert c.execute(sql.SQL("SELECT count(*) FROM history_l1.{}").format(sql.Identifier(table))).fetchone()[0]==0
        # Validate actual migration execution ledger, not a reconstructed
        # schema-only list. Admin connection for private metadata ONLY.
        admin=dict(conninfo_to_dict(cfg["DB_APP_DSN"]),user="postgres",password=os.environ["PGPASSWORD"])
        manifest=ROOT/"infra/postgres/dev_f3_isolated/MIGRATIONS_001_010_PINNED.tsv"
        assert sha256(manifest.read_bytes()).hexdigest()=="9ff95a59570f5f6c6188479d9c37cf684ef836c599e89d9faa2bb0e17a4946f7"
        expected={}
        for line in manifest.read_text().splitlines()[1:]:
            ver,direction,source,path,blob=line.split("\t")
            if direction=="UP":expected[ver]=(source,blob,sha256((ROOT/path).read_bytes()).hexdigest())
        with psycopg.connect(**admin,autocommit=True) as c:
            with c.transaction():
                c.execute("SET TRANSACTION READ ONLY")
                ledger=c.execute("""SELECT trim(version),trim(source_commit),trim(git_blob_sha1),trim(sql_sha256),
                    status,started_at,applied_at,applied_txid,cluster_system_id
                    FROM db55_audit.migration_runs ORDER BY version""").fetchall()
                assert len(ledger)==10
                for ver,source,blob,digest,status,started,applied,tx,cluster in ledger:
                    assert expected[ver]==(source,blob,digest)
                    assert status=="APPLIED" and applied>=started and tx is not None
                assert len({r[-1] for r in ledger})==1
                physical=c.execute("""SELECT count(*) FROM pg_class k JOIN pg_namespace n ON n.oid=k.relnamespace
                    WHERE n.nspname IN ('history_l1','auth_l1') AND k.relkind IN ('r','p')
                    AND k.relrowsecurity AND k.relforcerowsecurity""").fetchone()[0]
                assert physical==14
                system_id=str(c.execute("SELECT system_identifier FROM pg_control_system()").fetchone()[0])
                # Installation occurred in the original Actions PG. The
                # ordinary source journey is already on a first owned clone.
                # Do not falsely attribute migrations to either new cluster.
                assert ledger[0][-1]==self.db_install_system_id
                assert system_id!=self.db_install_system_id
                if dsns is None:
                    if not hasattr(self,"db_journey_source_system_id"):
                        self.db_journey_source_system_id=system_id
                    assert system_id==self.db_journey_source_system_id
                else:assert system_id!=self.db_journey_source_system_id
        result["ledger"]=sha256(json.dumps(ledger,default=str).encode()).hexdigest()
        if baseline is not None:assert result==baseline,"RESTRICTED_SQL_EXACT_PARITY_DRIFT"
        try:
            with psycopg.connect(cfg["DB_APP_DSN"],autocommit=True) as c:
                c.execute("SELECT count(*) FROM db55_audit.migration_runs")
        except psycopg.errors.InsufficientPrivilege:pass
        else:raise AssertionError("PRODUCT_ROLE_LEDGER_READ_ALLOWED")
        self.db55_readonly_catalog_gate(phase,cfg)
        print("DB_OCI_BROWSER_"+phase+"_SIX_TABLES_AB_EXACT_READ_ONLY_LEDGER_PARITY=PASS",flush=True)
        return result

    def counts(self):
        with psycopg.connect(getattr(self, "restore_mig_dsn", os.environ["DB_MIG_DSN"]),
                             autocommit=True, row_factory=dict_row) as db:
            return db.execute(
                "SELECT (SELECT count(*) FROM history_l1.conversations) AS conv,"
                "(SELECT count(*) FROM history_l1.messages) AS msg,"
                "(SELECT count(*) FROM history_l1.send_receipts) AS t1,"
                "(SELECT count(*) FROM history_l1.execution_attempts) AS t2,"
                "(SELECT count(*) FROM history_l1.answers) AS t3").fetchone()

    def seed_extra(self, label):
        owner = self.owners[label]
        title = "CI restored browser page two " + label
        request = {"kind": "create_conversation_request", "contract_version": "product.v1",
                   "client_conversation_id": history_api.uid(),
                   "idempotency_key": "browser_" + uuid.uuid4().hex, "title": title}
        with psycopg.connect(os.environ["DB_APP_DSN"], autocommit=True,
                             row_factory=dict_row) as db:
            receipt = history_api.create_conversation(
                db, owner, request, history_api.uid(), history_api.uid())
        cid = receipt["conversation"]["conversation_id"]
        mid = history_api.uid()
        message = "متن آزمایشی خصوصی " + label + " " + uuid.uuid4().hex[:12]
        # Pre-existing synthetic fixture data, not a Send endpoint or engine.
        with psycopg.connect(os.environ["DB_MIG_DSN"], autocommit=True) as db:
            db.execute("INSERT INTO history_l1.messages "
                       "(owner_id,id,conversation_id,role,body) VALUES (%s,%s,%s,'user',%s)",
                       (owner, mid, cid, message))
        return cid, mid, message

    def seed_31_source_messages(self, label, conversation_id):
        """31 genuine PostgreSQL History rows; NEVER Send/Engine/Answer fixture.

        These belong only to this disposable integration lab and are written
        by its isolated DB migrator. The user-facing API and React DOM still
        read them through actual signed History requests from Keycloak owners.
        """
        owner = self.owners[label]
        with psycopg.connect(os.environ["DB_MIG_DSN"], autocommit=True,
                             row_factory=dict_row) as db:
            existing = db.execute(
                "SELECT id FROM history_l1.messages WHERE owner_id=%s "
                "AND conversation_id=%s ORDER BY created_at,id",
                (owner, conversation_id)).fetchall()
            assert len(existing) == 1, "LAB_REQUIRES_EXACT_ONE_INITIAL_MESSAGE"
            for sequence in range(2, 32):
                db.execute(
                    "INSERT INTO history_l1.messages "
                    "(owner_id,id,conversation_id,role,body) "
                    "VALUES (%s,%s,%s,'user',%s)",
                    (owner, history_api.uid(), conversation_id,
                     "پیام آزمایشی پایدار " + label + " " + str(sequence)))
        with psycopg.connect(os.environ["DB_APP_DSN"],autocommit=True,row_factory=dict_row) as read:
            with read.transaction():
                read.execute("SET TRANSACTION READ ONLY")
                read.execute("SELECT set_config('app.owner_id',%s,true)",(owner,))
                rows=read.execute("SELECT id,body FROM history_l1.messages WHERE conversation_id=%s ORDER BY created_at,id",(conversation_id,)).fetchall()
        assert len(rows) == 31 and len({row["id"] for row in rows}) == 31
        assert rows[0]["id"] == existing[0]["id"]
        return rows

    async def verify_31_message_page2(self, page, conversation_id, rows, expected_owner):
        """Real Chromium React DOM consumes two signed BFF/API SQL pages."""
        assert len(rows) == 31
        await expect(page.locator('[data-testid^="history-message-"]')).to_have_count(30)
        await expect(page.get_by_test_id("more-messages")).to_be_visible()
        async with page.expect_response(
            lambda r: "/api/history/conversations/" + conversation_id + "/messages?" in r.url
            and "cursor=" in r.url and r.request.method == "GET"
        ) as wait:
            await page.get_by_test_id("more-messages").click()
        response = await wait.value
        assert response.status == 200
        payload = await response.json()
        assert payload["owner_user_id"] == expected_owner
        assert payload["conversation_id"] == conversation_id
        assert payload["page"]["has_more"] is False
        assert [m["message_id"] for m in payload["items"]] == [rows[30]["id"]]
        await expect(page.locator('[data-testid^="history-message-"]')).to_have_count(31)
        for row in rows:
            await expect(page.get_by_test_id("history-message-" + row["id"])).to_contain_text(row["body"])

    def sql_history(self, label):
        with psycopg.connect(os.environ["DB_APP_DSN"], autocommit=True,
                             row_factory=dict_row) as db:
            with db.transaction():
                db.execute("SET TRANSACTION READ ONLY")
                db.execute("SELECT set_config('app.owner_id',%s,true)",(self.owners[label],))
                return db.execute(
                    "SELECT id,title FROM history_l1.conversations "
                    "WHERE state='active' ORDER BY updated_at DESC,id DESC").fetchall()

    def stop_child(self, child):
        entry = next((item for item in self.children if item[0] is child), None)
        if entry is None:
            raise RuntimeError("CI_CHILD_NOT_OWNED")
        if child.poll() is None:
            child.terminate()
            try:
                child.wait(timeout=5)
            except subprocess.TimeoutExpired:
                child.kill()
                child.wait(timeout=5)
        entry[1].close()
        self.children.remove(entry)

    @contextmanager
    def fresh_volume(self):
        """Use only the exact CI source service and newly created resources.

        A fresh Postgres data directory, not another database in the old
        container. Keep dump/role metadata only in process memory; do not
        export credentials, screenshots, or backups from the disposable lab.
        """
        cid = os.environ.get("API_F3_ISOLATED_PG_CID", "")
        if (os.getenv("CI") != "true" or os.getenv("GITHUB_ACTIONS") != "true"
                or not re.fullmatch(r"[a-f0-9]{12,64}", cid)
                or os.getenv("PGHOST") != "127.0.0.1"
                or os.getenv("PGPORT") != "5432"):
            raise RuntimeError("FRESH_VOLUME_CI_FENCE_DENIED")
        source_dsns = {}
        for key, value in os.environ.items():
            if not key.endswith("_DSN"):
                continue
            options = conninfo_to_dict(value)
            if options.get("dbname") != "history_ci":
                continue
            if (options.get("host") != "127.0.0.1" or options.get("port") != "5432"
                    or not options.get("user") or not options.get("password")):
                raise RuntimeError("FRESH_VOLUME_DSN_FENCE_DENIED")
            source_dsns[key] = options
        required = {"DB_APP_DSN", "DB_MIG_DSN", "AUTH_MIG_DSN", "AUTH_REVOKER_DSN",
                    "AUTH_MAP_DSN", "AUTH_SESSION_DSN", "REPLAY_API_DSN",
                    "LOGIN_BOOTSTRAP_DSN", "LOGIN_CLAIM_DSN", "LOGIN_ISSUER_DSN",
                    "LOGIN_BINDER_DSN", "LOGIN_READER_DSN"}
        assert required.issubset(source_dsns)
        def docker(*args, data=None, timeout=60):
            result = subprocess.run(["docker", *args], input=data,
                                    capture_output=True, timeout=timeout)
            if result.returncode:
                raise RuntimeError("FRESH_VOLUME_DOCKER_COMMAND_FAILED")
            return result.stdout
        source = json.loads(docker("inspect", cid))[0]
        assert source["Id"].startswith(cid)
        assert source["Config"]["Image"] == "postgres:17.11" and source["State"]["Running"]
        image = source["Image"]
        assert re.fullmatch(r"sha256:[a-f0-9]{64}", image)
        # No password hashes in the global backup. Restore the exact CI
        # role names and attributes; provision synthetic passwords only
        # from the explicit current-job DSNs in the new server.
        roles = docker("exec", cid, "pg_dumpall", "-U", "postgres", "--roles-only",
                       "--no-role-passwords")
        roles = b"\n".join(line for line in roles.splitlines()
                           if line.strip() != b"CREATE ROLE postgres;") + b"\n"
        dump = docker("exec", cid, "pg_dump", "-U", "postgres", "-Fc", "history_ci")
        assert dump.startswith(b"PGDMP")
        suffix = uuid.uuid4().hex
        name = "api-browser-pg-" + suffix
        volume = name + "-data"
        network = name + "-net"
        dbname = "history_browser_restore_ci_" + suffix[:16]
        label = "rag.finance.ci.restore=" + suffix
        made_volume = made_network = False
        new_id = None
        try:
            assert docker("volume", "create", "--label", label, volume).decode().strip() == volume
            made_volume = True
            docker("network", "create", "--label", label, network)
            made_network = True
            # Docker may allocate a different ephemeral published port on
            # stop/start. Pin the loopback port for both restart exercises.
            with socket.socket() as reservation:
                reservation.bind(("127.0.0.1", 0))
                expected_port = reservation.getsockname()[1]
            assert expected_port != 5432
            result = docker("run", "-d", "--pull", "never", "--name", name,
                            "--label", label, "--network", network,
                            "--network-alias", "pg-restore",
                            "--network-alias", "wrong-pg-name",
                            "-p", f"127.0.0.1:{expected_port}:5432",
                            "--mount", "type=volume,source=" + volume +
                            ",target=/var/lib/postgresql/data",
                            "-e", "POSTGRES_PASSWORD=" + os.environ["PGPASSWORD"], image)
            new_id = result.decode().strip()
            assert re.fullmatch(r"[a-f0-9]{64}", new_id) and new_id != source["Id"]
            info = json.loads(docker("inspect", new_id))[0]
            assert info["Config"]["Labels"]["rag.finance.ci.restore"] == suffix
            assert info["Image"] == image
            mounts = [m for m in info["Mounts"] if m["Destination"] == "/var/lib/postgresql/data"]
            assert len(mounts) == 1 and mounts[0]["Name"] == volume
            assert not any(m.get("Name") == volume for m in source["Mounts"])
            assert set(info["NetworkSettings"]["Networks"]) == {network}
            port_map = info["NetworkSettings"]["Ports"]["5432/tcp"]
            assert len(port_map) == 1 and port_map[0]["HostIp"] == "127.0.0.1"
            port = int(port_map[0]["HostPort"])
            assert port == expected_port
            self.restore_pg_port = port
            admin_opts = dict(host="127.0.0.1", port=port, dbname="postgres",
                              user="postgres", password=os.environ["PGPASSWORD"],
                              connect_timeout=2)
            for _ in range(60):
                try:
                    with psycopg.connect(**admin_opts, autocommit=True):
                        break
                except psycopg.OperationalError:
                    time.sleep(0.5)
            else:
                raise RuntimeError("FRESH_VOLUME_PG_NOT_READY")
            docker("exec", "-i", new_id, "psql", "-X", "-v", "ON_ERROR_STOP=1",
                   "-U", "postgres", "-d", "postgres", data=roles)
            with psycopg.connect(**admin_opts, autocommit=True) as admin:
                for options in source_dsns.values():
                    admin.execute(sql.SQL("ALTER ROLE {} PASSWORD {}").format(
                        sql.Identifier(options["user"]), sql.Literal(options["password"])))
                admin.execute(sql.SQL("CREATE DATABASE {} TEMPLATE template0").format(
                    sql.Identifier(dbname)))
            docker("exec", "-i", new_id, "pg_restore", "-U", "postgres", "--exit-on-error",
                   "-d", dbname, data=dump)
            del roles, dump
            clone_dsns = {key: make_conninfo(**{**value, "port": port, "dbname": dbname})
                          for key, value in source_dsns.items()}
            print("API_F3_BROWSER_INDEPENDENT_NEW_PG_VOLUME_RESTORE_PASS", flush=True)
            yield clone_dsns, new_id, network
        finally:
            # Exact resources generated in this invocation; no prune or
            # deletion of an existing CI/service or legacy volume.
            if new_id is not None:
                docker("rm", "-f", new_id)
            if made_volume:
                docker("volume", "rm", volume)
            if made_network:
                docker("network", "rm", network)

    def spawn_restored(self, command, env=None):
        # Demo.add names log files by the size of its current child list.
        # After stopping children that can overwrite a still-open Next log.
        # Each restarted service gets a new private file instead.
        log = (self.root / ("restore-process-" + uuid.uuid4().hex + ".log")).open("wb")
        try:
            child = subprocess.Popen(command, cwd=ROOT, env=env,
                                     stdout=log, stderr=log)
        except BaseException:
            log.close()
            raise
        self.children.append((child, log))
        return child

    def readiness(self, actor, *, wrong_audience=False, cert=True):
        # Actual synthetic session from ordinary browser login. Proof built
        # only for this CI API health endpoint; no browser-supplied owner.
        now = int(time.time())
        claims = {
            "iss": SIGN_ISS, "aud": "urn:ci:wrong-audience" if wrong_audience else SIGN_AUD,
            "iat": now, "nbf": now, "exp": now + 25,
            "jti": secrets.token_urlsafe(24), "method": "GET",
            "raw_path_sha256": sha256(b"/health/ready").hexdigest(),
            "raw_query_sha256": sha256(b"").hexdigest(),
            "body_sha256": sha256(b"").hexdigest(), "body_len": 0,
            **actor,
        }
        token = jwt.encode(claims, self.product_signer, algorithm="RS256",
                           headers={"typ":"JWT", "kid":SIGN_KID})
        tls = ssl.create_default_context(cafile=self.ca)
        if cert:
            tls.load_cert_chain(self.client[0], self.client[1])
        try:
            with httpx.Client(verify=tls, trust_env=False, timeout=10) as client:
                return client.get(self.product_origin + "/health/ready",
                                  headers={"Authorization": "BFF-Assertion " + token})
        except (httpx.ConnectError, httpx.RemoteProtocolError, httpx.ReadError):
            if not cert:
                return None
            raise

    def assert_restore_pg_binding(self, pg_id):
        info = json.loads(self.ci_command("docker", "inspect", pg_id))[0]
        assert info["Id"] == pg_id
        assert info["State"]["Running"]
        assert info["NetworkSettings"]["Ports"]["5432/tcp"] == [
            {"HostIp":"127.0.0.1", "HostPort":str(self.restore_pg_port)}
        ], "RESTORE_PG_PORT_CHANGED"
        print("API_F3_RESTORE_PG_STABLE_LOOPBACK_BINDING_PASS", flush=True)

    def restore_pg_diagnostic(self, pg_id):
        # Only status and SQLSTATE class, never DSN, logs, or error text.
        info = json.loads(self.ci_command("docker", "inspect", pg_id))[0]
        result = subprocess.run(["docker", "exec", pg_id, "pg_isready",
                                 "-U", "postgres"], capture_output=True, timeout=5)
        report = {"running":info["State"]["Running"],
                  "pg_isready_exit":result.returncode,
                  "binding_same":info["NetworkSettings"]["Ports"].get("5432/tcp") == [
                      {"HostIp":"127.0.0.1","HostPort":str(self.restore_pg_port)}]}
        try:
            with psycopg.connect(self.restore_probe_dsn, autocommit=True) as conn:
                report["verified_db_connection"] = True
        except psycopg.Error as exc:
            report["verified_db_connection"] = False
            report["sqlstate"] = exc.sqlstate or "none"
        print("API_F3_RESTORE_PG_DIAGNOSTIC", json.dumps(report), flush=True)

    def check_restored_outage(self, actor, new_id):
        assert re.fullmatch(r"[a-f0-9]{64}", new_id)
        assert not new_id.startswith(os.environ["API_F3_ISOLATED_PG_CID"])
        def command(*args):
            result = subprocess.run(["docker", *args], capture_output=True,
                                    timeout=30, check=False)
            assert result.returncode == 0, "RESTORED_PG_CONTROL_FAILED"
            return result.stdout
        info = json.loads(command("inspect", new_id))[0]
        assert info["Id"] == new_id and info["State"]["Running"]
        assert re.fullmatch(r"[a-f0-9]{32}",
                            info["Config"]["Labels"]["rag.finance.ci.restore"])
        assert self.readiness(actor).status_code == 200
        invalid = self.readiness(actor, wrong_audience=True)
        assert invalid.status_code == 503
        assert invalid.headers.get("cache-control") == "no-store"
        without = self.readiness(actor, cert=False)
        assert without is None or without.status_code == 401
        stopped = False
        try:
            command("stop", "--time", "2", new_id)
            stopped = True
            denial = self.readiness(actor)
            assert denial.status_code == 503
            assert denial.json()["state"] == "unavailable"
            assert denial.headers.get("cache-control") == "no-store"
            assert "password" not in denial.text.lower()
        finally:
            if stopped:
                command("start", new_id)
                self.assert_restore_pg_binding(new_id)
        for _ in range(60):
            try:
                if self.readiness(actor).status_code == 200:
                    break
            except httpx.HTTPError:
                pass
            time.sleep(0.5)
        else:
            self.restore_pg_diagnostic(new_id)
            raise RuntimeError("RESTORED_PG_READINESS_NOT_RECOVERED")
        print("API_F3_BROWSER_RESTORED_VOLUME_WRONG_SIGNER_PEER_OUTAGE_RECOVERY_PASS", flush=True)

    @staticmethod
    def ci_command(*args, timeout=60, input_data=None):
        """No secret-bearing command/output in a raised exception or CI log."""
        result = subprocess.run(list(args), input=input_data, capture_output=True,
                                timeout=timeout, check=False)
        if result.returncode:
            raise RuntimeError("BROWSER_CONTAINER_CI_COMMAND_FAILED")
        return result.stdout

    def configure_restore_pg_tls(self, pg_id, dsns):
        """Provision a CI-only CA/leaf on the newly owned restored PG."""
        run = self.ci_command
        info = json.loads(run("docker", "inspect", pg_id))[0]
        assert info["Id"] == pg_id and info["State"]["Running"]
        assert re.fullmatch(r"[a-f0-9]{32}",
                            info["Config"]["Labels"]["rag.finance.ci.restore"])
        certs = self.root / "restore-pg-tls"
        certs.mkdir(mode=0o700)
        ca_key, ca = certs / "ca.key", certs / "ca.pem"
        key, csr, leaf = certs / "server.key", certs / "server.csr", certs / "server.pem"
        extensions = certs / "leaf.ext"
        extensions.write_text("basicConstraints=critical,CA:FALSE\n"
                              "keyUsage=critical,digitalSignature,keyEncipherment\n"
                              "extendedKeyUsage=serverAuth\n"
                              "subjectAltName=DNS:pg-restore,IP:127.0.0.1\n")
        run("openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes",
            "-days", "1", "-subj", "/CN=ephemeral-restore-pg-ca",
            "-addext", "basicConstraints=critical,CA:TRUE",
            "-addext", "keyUsage=critical,keyCertSign,cRLSign",
            "-keyout", str(ca_key), "-out", str(ca))
        run("openssl", "req", "-new", "-newkey", "rsa:2048", "-nodes",
            "-subj", "/CN=pg-restore", "-keyout", str(key), "-out", str(csr))
        run("openssl", "x509", "-req", "-in", str(csr), "-CA", str(ca),
            "-CAkey", str(ca_key), "-CAcreateserial", "-days", "1",
            "-extfile", str(extensions), "-out", str(leaf))
        for p in (ca_key, key):
            p.chmod(0o600)
        tls_dir = "/var/lib/postgresql/data/restore-tls"
        run("docker", "exec", "-u", "0", pg_id, "mkdir", "-m", "0700", tls_dir)
        for src, name in ((key, "server.key"), (leaf, "server.pem")):
            run("docker", "cp", str(src), pg_id + ":" + tls_dir + "/" + name)
        run("docker", "exec", "-u", "0", pg_id, "chown", "-R", "postgres:postgres",
            tls_dir)
        run("docker", "exec", "-u", "0", pg_id, "chmod", "0600",
            tls_dir + "/server.key")
        for statement in ("ALTER SYSTEM SET ssl = 'on'",
                          "ALTER SYSTEM SET ssl_cert_file = 'restore-tls/server.pem'",
                          "ALTER SYSTEM SET ssl_key_file = 'restore-tls/server.key'"):
            run("docker", "exec", pg_id, "psql", "-X", "-v", "ON_ERROR_STOP=1",
                "-U", "postgres", "-d", "postgres", "-c", statement)
        self.enforce_pg_tls_only(pg_id)
        run("docker", "restart", "--time", "2", pg_id)
        self.assert_restore_pg_binding(pg_id)
        secure = {name: make_conninfo(dsn, sslmode="verify-full", sslrootcert=str(ca))
                  for name, dsn in dsns.items()}
        secure = {name: make_conninfo(dsn, gssencmode="disable")
                  for name, dsn in secure.items()}
        self.restore_probe_dsn = secure["DB_APP_DSN"]
        for _ in range(60):
            try:
                with psycopg.connect(secure["DB_APP_DSN"], autocommit=True,
                                     row_factory=dict_row) as c:
                    assert c.execute("SELECT ssl FROM pg_stat_ssl "
                                     "WHERE pid=pg_backend_pid()").fetchone()["ssl"]
                break
            except psycopg.OperationalError:
                time.sleep(0.5)
        else:
            self.restore_pg_diagnostic(pg_id)
            raise RuntimeError("RESTORE_PG_TLS_NOT_READY")
        # No host/service other than the exact new restored instance is touched.
        self.restore_pg_ca = ca
        self.verify_db_tls(secure["DB_APP_DSN"],"RESTORED")
        print("API_F3_RESTORED_PG_REAL_TLS_VERIFY_FULL_PASS", flush=True)
        return secure

    def start_container_api(self, dsns, network):
        """Use the exact SHA non-root API image and private Docker DNS."""
        run = self.ci_command
        sha = os.environ.get("F3_EXACT_SHA", "")
        assert re.fullmatch(r"[a-f0-9]{40}", sha)
        assert run("git", "rev-parse", "HEAD").decode().strip() == sha
        image = os.environ.get("API_F3_BROWSER_IMAGE", "")
        assert image == "api-f3-browser:" + sha
        info = json.loads(run("docker", "image", "inspect", image))[0]
        assert info["Config"]["User"] == "11001:11001"
        assert info["Config"]["Labels"]["org.opencontainers.image.revision"] == sha
        assert info["Config"]["Cmd"] == ["python3", "-m", "apps.api.private_app_only_asgi",
                                         "--config", "/run/secrets/phase3-app-only.json"]
        assert re.fullmatch(r"sha256:[a-f0-9]{64}", info["Id"])
        self.api_image_id = info["Id"]
        mount = self.root / "restore-api-container-secrets"
        mount.mkdir(mode=0o700)
        self.container_secret_dir = mount

        def protected(src, name):
            p = mount / name
            p.write_bytes(Path(src).read_bytes())
            p.chmod(0o600)
            return "/run/secrets/" + name

        ca = protected(self.restore_pg_ca, "pg-ca.pem")
        def inside(dsn):
            return make_conninfo(dsn, host="pg-restore", port=5432,
                                 sslmode="verify-full", sslrootcert=ca)

        config = {
            "contract_version": "api.private_app_only_asgi.v1",
            "listen_host": "0.0.0.0", "listen_port": 8443,
            "server_tls_cert_file": protected(self.api_env["APP_ONLY_CI_SERVER_CERT"], "server.pem"),
            "server_tls_key_file": protected(self.api_env["APP_ONLY_CI_SERVER_KEY"], "server.key"),
            "trusted_bff_ca_file": protected(self.ca, "bff-ca.pem"),
            "bff_leaf_cert_sha256": sha256(self.client[2]).hexdigest(),
            "bff_issuer": SIGN_ISS, "bff_audience": SIGN_AUD, "bff_kid": SIGN_KID,
            "bff_rs256_public_key_file": protected(self.api_env["API_PRODUCT_PROOF_PUBLIC_KEY_PATH"], "public.pem"),
            "history_dsn": inside(dsns["DB_APP_DSN"]),
            "revoke_dsn": inside(dsns["AUTH_REVOKER_DSN"]),
        }
        def save(name, data):
            p = mount / name
            p.write_text(json.dumps(data), encoding="utf-8")
            p.chmod(0o600)

        save("phase3-app-only.json", config)
        # Second Docker DNS alias resolves to the same PG container, but
        # the pinned certificate does not cover that name. No hostaddr override.
        invalid = dict(config)
        invalid["history_dsn"] = make_conninfo(config["history_dsn"],
                            host="wrong-pg-name")
        save("wrong-dns.json", invalid)
        invalid = dict(config)
        invalid["history_dsn"] = make_conninfo(config["history_dsn"],
                            sslrootcert="/run/secrets/bff-ca.pem")
        save("wrong-ca.json", invalid)
        invalid = dict(config)
        invalid["history_dsn"] = make_conninfo(config["history_dsn"], hostaddr="192.0.2.10")
        save("hostaddr-override.json", invalid)
        envfile = self.root / "restore-api-cursor.env"
        envfile.write_text("API_CURSOR_KEY=" + self.api_env["API_CURSOR_KEY"] + "\n"
                           "API_CURSOR_TTL_SECONDS=" + self.api_env["API_CURSOR_TTL_SECONDS"] + "\n")
        envfile.chmod(0o600)
        run("sudo", "chown", "-R", "11001:11001", str(mount))
        common = ["--network", network, "--read-only", "--cap-drop", "ALL",
                  "--security-opt", "no-new-privileges",
                  "--mount", "type=bind,source=" + str(mount) +
                  ",target=/run/secrets,readonly", "--env-file", str(envfile)]
        for negative in ("wrong-dns.json", "wrong-ca.json", "hostaddr-override.json"):
            denied = subprocess.run(["docker", "run", "--rm", *common, image,
                      "python3", "-m", "apps.api.private_app_only_asgi",
                      "--config", "/run/secrets/" + negative], capture_output=True,
                      timeout=25)
            assert denied.returncode == 78, "PG_TLS_NEGATIVE_MUST_EXIT_78"
            assert b"APP_ONLY_STARTUP_DENIED" in denied.stderr
            assert b"password=" not in denied.stderr
        print("API_F3_CONTAINER_PG_WRONG_CA_DNS_HOSTADDR_DENIED_PASS", flush=True)
        port = self.api_env["APP_ONLY_CI_API_PORT"]
        name = "api-restored-" + uuid.uuid4().hex
        self.api_container = run("docker", "run", "-d", "--pull", "never", "--name", name,
                                 *common, "-p", "127.0.0.1:" + port + ":8443", image).decode().strip()
        inspected = json.loads(run("docker", "inspect", self.api_container))[0]
        assert inspected["Image"] == self.api_image_id
        assert inspected["Config"]["User"] == "11001:11001"
        assert inspected["HostConfig"]["ReadonlyRootfs"] is True
        assert set(inspected["NetworkSettings"]["Networks"]) == {network}
        ports = inspected["HostConfig"]["PortBindings"]
        assert set(ports) == {"8443/tcp"} and ports["8443/tcp"] == [
            {"HostIp": "127.0.0.1", "HostPort": port}]
        # Independent read-only role and TLS witness from inside the real image.
        probe = """
import json, os, psycopg
from psycopg.rows import dict_row
assert os.geteuid() == 11001
config=json.load(open('/run/secrets/phase3-app-only.json'))
for key,role in (('history_dsn','history_app'),('revoke_dsn','auth_revoker')):
    with psycopg.connect(config[key], row_factory=dict_row) as c:
        row=c.execute('SELECT current_user AS role, ssl FROM pg_stat_ssl WHERE pid=pg_backend_pid()').fetchone()
        assert row == {'role':role, 'ssl':True}
print('API_F3_CONTAINER_PG_RESTRICTED_ROLE_TLS_PASS')
"""
        tls = ssl.create_default_context(cafile=self.ca)
        tls.load_cert_chain(self.client[0], self.client[1])
        self.await_url(self.product_origin + "/internal/ready", tls)
        result = run("docker", "exec", self.api_container, "python3", "-c", probe)
        assert b"API_F3_CONTAINER_PG_RESTRICTED_ROLE_TLS_PASS" in result
        print("API_F3_CONTAINER_PG_RESTRICTED_ROLE_TLS_PASS", flush=True)
        print("API_F3_EXACT_OCI_API_IMAGE=" + self.api_image_id, flush=True)

    def stop_container_api(self):
        if getattr(self, "api_container", None):
            self.ci_command("docker", "rm", "-f", self.api_container)
            self.api_container = None
        if getattr(self, "container_secret_dir", None):
            self.ci_command("sudo", "chown", "-R",
                            str(os.getuid()) + ":" + str(os.getgid()),
                            str(self.container_secret_dir))
            self.container_secret_dir = None

    def switch_to_restored(self, dsns, network):
        """Retain ordinary Next/BFF origins; restart only isolated private services."""
        self.stop_child(self.api_process)
        self.stop_child(self.bootstrap_process)
        original_worker = Path(self.bootstrap_command[-1])
        worker = json.loads(original_worker.read_text(encoding="utf-8"))
        mapping = {"replay": "REPLAY_API_DSN", "bootstrap": "LOGIN_BOOTSTRAP_DSN",
                   "claim_reader": "LOGIN_CLAIM_DSN", "issuer": "LOGIN_ISSUER_DSN",
                   "mapper": "AUTH_MAP_DSN", "binder": "LOGIN_BINDER_DSN",
                   "reader": "LOGIN_READER_DSN"}
        assert set(worker["db_dsn"]) == set(mapping)
        worker["db_dsn"] = {name: dsns[key] for name, key in mapping.items()}
        worker_path = self.root / "restore-bootstrap.json"
        fd = os.open(worker_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as out:
            json.dump(worker, out)
        self.bootstrap_process = self.spawn_restored([*self.bootstrap_command[:-1], str(worker_path)])
        self.api_process = None
        self.start_container_api(dsns, network)
        tls = ssl.create_default_context(cafile=self.ca)
        tls.load_cert_chain(self.client[0], self.client[1])
        self.await_url(self.bootstrap_origin + "/__fixture_health", tls)
        self.await_url(self.product_origin + "/internal/ready", tls)
        self.restore_mig_dsn = dsns["DB_MIG_DSN"]

    async def verify_browser_privacy(self, browser, a, b, raw_a, raw_b, aid, message):
        """Scoped privacy/abuse evidence against real Next/BFF, not LLM policy."""
        same_uri = "/api/history/conversations?limit=2"
        before = self.counts()
        for page, own, foreign in ((a, raw_a, raw_b), (b, raw_b, raw_a),
                                   (a, raw_a, raw_b)):
            response = await page.evaluate("""async ({uri, foreign}) => {
                const r=await fetch(uri,{cache:'no-store',headers:{
                    'If-None-Match':'*',
                    'If-Modified-Since':'Tue, 01 Jan 2030 00:00:00 GMT',
                    'X-Owner-Id':foreign,
                    'X-User-Id':foreign,
                    'X-Forwarded-Client-Cert':'untrusted-browser-header',
                    'X-Auth-Ci-Proxy-Proof':'untrusted-browser-header'
                }});
                return {status:r.status,cache:r.headers.get('cache-control'),body:await r.json()};
            }""", {"uri":same_uri, "foreign":foreign["owner_id"]})
            assert response["status"] == 200
            assert response["cache"] == "no-store"
            assert response["body"]["scope_user_id"] == own["owner_id"]
            assert all(row["owner_user_id"] == own["owner_id"]
                       for row in response["body"]["items"])
        # Real foreign-record request with an adversarial owner header; no
        # identity is injected into the ordinary login/journey above.
        denied = await b.evaluate("""async ({id,owner}) => {
            const r=await fetch('/api/history/conversations/'+id+'/messages?limit=2',
                {cache:'no-store',headers:{'X-Owner-Id':owner,'If-None-Match':'*'}});
            return {status:r.status,cache:r.headers.get('cache-control'),body:await r.text()};
        }""", {"id":aid, "owner":raw_a["owner_id"]})
        assert denied["status"] == 404 and denied["cache"] == "no-store"
        assert message not in denied["body"] and aid not in denied["body"]
        for invalid in ("?limit=2&limit=1", "?limit=2&owner_id=" + raw_a["owner_id"],
                        "?limit=101", "?limit=2&cursor=invalid%20cursor"):
            rejected = await b.evaluate("""async q => {
                const r=await fetch('/api/history/conversations'+q,{cache:'no-store'});
                return {status:r.status,cache:r.headers.get('cache-control')};
            }""", invalid)
            assert rejected == {"status":422, "cache":"no-store"}
        anonymous = await browser.new_context(ignore_https_errors=True)
        try:
            response = await anonymous.request.get(ORIGIN + same_uri, headers={
                "X-Owner-Id":raw_a["owner_id"], "If-None-Match":"*"})
            assert response.status == 401
            assert response.headers.get("cache-control") == "no-store"
            assert message not in await response.text()
        finally:
            await anonymous.close()
        print("API_F3_REAL_BROWSER_PRIVATE_OWNER_HEADER_CACHE_POISON_NEGATIVES_PASS", flush=True)
        # Invalid CSRF token with the actual session cookie, never call
        # revoke or create a durable mutation. Legitimate logout later uses
        # the normal native form with its server-issued token.
        bad_csrf = await a.evaluate("""async () => {
            const r=await fetch('/api/auth/logout',{
                method:'POST',credentials:'same-origin',
                headers:{'Content-Type':'application/x-www-form-urlencoded'},
                body:'csrf=invalid-test-token',redirect:'manual'});
            return {status:r.status,cache:r.headers.get('cache-control')};
        }""")
        assert bad_csrf == {"status":403, "cache":"no-store"}
        assert self.signed_private(raw_a).status_code == 200
        assert self.signed_private(raw_b).status_code == 200
        assert self.counts() == before
        print("API_F3_REAL_BROWSER_BAD_CSRF_NO_REVOKE_NO_HISTORY_MUTATION_PASS", flush=True)

    async def actual_oci_read_blocks_real_logout(self, a, logout, raw_a, conversation_id, rows, restored, pg_id):
        """Actual History request blocked AFTER real session admission.
        The held table lock only forces a deterministic scheduling window;
        the blocking history_app PID belongs to the real OCI HTTP handler.
        No direct protected_transaction substitute or cookie injection.
        """
        assert os.getenv("CI")=="true" and os.getenv("GITHUB_ACTIONS")=="true"
        info=json.loads(self.ci_command("docker","inspect",pg_id))[0]
        assert info["Id"]==pg_id and info["State"]["Running"]
        assert pg_id!=self.source_pg_id
        assert re.fullmatch(r"[a-f0-9]{32}",info["Config"]["Labels"]["rag.finance.ci.restore"])
        cfg=conninfo_to_dict(restored["DB_APP_DSN"])
        assert cfg["dbname"].startswith("history_browser_restore_ci_")
        assert cfg["sslmode"]=="verify-full"
        assert cfg["port"]==str(self.restore_pg_port)
        admin=dict(cfg,user="postgres",password=os.environ["PGPASSWORD"])
        async def request_read():
            return await a.evaluate("""async id => {
                const r=await fetch('/api/history/conversations/'+id+'/messages?limit=30',
                                    {cache:'no-store'});
                return {status:r.status,body:await r.json()};
            }""",conversation_id)
        async def request_logout():
            async with logout.expect_response(
                lambda r:r.url.endswith("/api/auth/logout") and r.request.method=="POST"
            ) as wait:
                await logout.get_by_test_id("logout-submit").click()
            return (await wait.value).status
        tasks=[]
        try:
            with psycopg.connect(**admin,autocommit=True) as lock:
                with lock.transaction():
                    lock.execute("SET LOCAL lock_timeout='1000ms'")
                    lock.execute("LOCK TABLE history_l1.messages IN ACCESS EXCLUSIVE MODE")
                    blocker=lock.execute("SELECT pg_backend_pid()").fetchone()[0]
                    async def blocked(role, blocking_pid):
                        deadline=time.monotonic()+3.0
                        while time.monotonic()<deadline:
                            lock.execute("SELECT pg_stat_clear_snapshot()")
                            hits=lock.execute("""SELECT a.pid FROM pg_stat_activity a
                              JOIN pg_stat_ssl s USING(pid)
                              WHERE a.datname=current_database() AND a.usename=%s
                              AND s.ssl AND a.wait_event_type='Lock'
                              AND %s=ANY(pg_blocking_pids(a.pid))""",
                              (role,blocking_pid)).fetchall()
                            if len(hits)==1:return hits[0][0]
                            assert len(hits)==0,"AMBIGUOUS_BLOCKED_ROLE"
                            await asyncio.sleep(.04)
                        raise AssertionError("EXPECTED_ACTUAL_OCI_DB_LOCK_EDGE_MISSING_"+role)
                    read_task=asyncio.create_task(request_read())
                    tasks.append(read_task)
                    history_pid=await blocked("history_app",blocker)
                    assert not read_task.done()
                    print("DB_COMMON_REAL_OCI_HISTORY_ROLE_BLOCKED_AFTER_ADMISSION=PASS",flush=True)
                    logout_task=asyncio.create_task(request_logout())
                    tasks.append(logout_task)
                    revoke_pid=await blocked("auth_revoker",history_pid)
                    assert len({blocker,history_pid,revoke_pid})==3
                    assert not read_task.done() and not logout_task.done()
                    print("DB_COMMON_REAL_OCI_LOGOUT_PG_BLOCKING_PID_CHAIN=PASS",flush=True)
                # Release ONLY the disposable table lock. Actual HTTP History
                # must finish and commit before the revoke can commit.
            read_result,logout_status=await asyncio.wait_for(asyncio.gather(*tasks),timeout=12)
            assert read_result["status"]==200
            assert read_result["body"]["owner_user_id"]==raw_a["owner_id"]
            assert [x["message_id"] for x in read_result["body"]["items"]]==[x["id"] for x in rows[:30]]
            assert logout_status==303
            print("DB_COMMON_REAL_OCI_READ_THEN_LOGOUT_COMMITTED_EXACT_30_ROWS=PASS",flush=True)
        finally:
            # The lock transaction has already exited on every exception.
            if tasks:
                await asyncio.gather(*tasks,return_exceptions=True)

    async def journey(self, browser, output):
        contexts = []
        try:
            ca, a, _, raw_a = await self.browser_login(browser, "A", False, output)
            contexts.append(ca)
            cb, b, _, raw_b = await self.browser_login(browser, "B", False, output)
            contexts.append(cb)
            assert raw_a["owner_id"] != raw_b["owner_id"]
            print("API_F3_BROWSER_REAL_OIDC_COOKIE_AB_PASS", flush=True)
            aid, mid, message = self.seed_extra("A")
            bid, bmid, bmessage = self.seed_extra("B")
            for label,cid,msg_id,body in (("A",aid,mid,message),("B",bid,bmid,bmessage)):
                with psycopg.connect(os.environ["DB_APP_DSN"],autocommit=True) as read:
                    with read.transaction():
                        read.execute("SET TRANSACTION READ ONLY")
                        read.execute("SELECT set_config('app.owner_id',%s,true)",(self.owners[label],))
                        assert read.execute("SELECT id,body FROM history_l1.messages WHERE conversation_id=%s",(cid,)).fetchall()==[(msg_id,body)]
            print("DB_COMPOSE_SOURCE_EXPECTED_DETAIL_FROM_RESTRICTED_SQL_AB=PASS",flush=True)
            message_rows=self.seed_31_source_messages("A",aid)
            expected = {label: self.sql_history(label) for label in ("A", "B")}
            assert all(len(rows) == 3 for rows in expected.values())
            before = self.counts()
            sql_before=self.restricted_db_snapshot("SOURCE")
            for label, page in (("A", a), ("B", b)):
                foreign = "B" if label == "A" else "A"
                async with page.expect_response(
                    lambda r: "/api/history/conversations?limit=2" in r.url
                    and "cursor=" not in r.url and r.request.method == "GET") as wait:
                    await page.get_by_test_id("refresh-history").click()
                response = await wait.value
                assert response.status == 200
                doc = await response.json()
                assert [x["conversation_id"] for x in doc["items"]] == [
                    x["id"] for x in expected[label][:2]]
                assert doc["scope_user_id"] == self.owners[label]
                cursor = doc["page"]["next_cursor"]
                assert cursor
                async with page.expect_response(
                    lambda r: "/api/history/conversations?" in r.url and
                    "cursor=" in r.url and r.request.method == "GET") as wait:
                    await page.get_by_role("button", name="نمایش گفت‌وگوهای بیشتر").click()
                second = await wait.value
                assert second.status == 200
                second_doc = await second.json()
                assert [x["conversation_id"] for x in second_doc["items"]] == [
                    x["id"] for x in expected[label][2:]]
                for row in expected[label]:
                    await expect(page.get_by_test_id("conversation-" + row["id"])).to_be_visible()
                for row in expected[foreign]:
                    assert await page.get_by_test_id("conversation-" + row["id"]).count() == 0
                # Foreign cursor with the other real browser's session.
                foreign_page = b if label == "A" else a
                status = await foreign_page.evaluate(
                    """async cursor => (await fetch('/api/history/conversations?limit=2&cursor='+
                        encodeURIComponent(cursor), {cache:'no-store'})).status""", cursor)
                assert status == 404
            print("API_F3_BROWSER_PG_HTTP_DOM_PAGE2_AB_PASS", flush=True)
            async with a.expect_response(
                lambda r: "/api/history/conversations/" + aid + "/messages?" in r.url
                and r.request.method == "GET") as wait:
                await a.get_by_test_id("conversation-" + aid).click()
            detail = await wait.value
            assert detail.status == 200
            doc = await detail.json()
            assert doc["owner_user_id"] == self.owners["A"]
            assert len(doc["items"]) == 30 and doc["page"]["has_more"] is True
            assert [x["message_id"] for x in doc["items"]] == [
                row["id"] for row in message_rows[:30]]
            assert any(x["message_id"] == mid and x["text"] == message for x in doc["items"])
            await self.verify_31_message_page2(
                a, aid, message_rows, self.owners["A"])
            print("API_F3_BROWSER_REAL_31_MESSAGE_PAGE2_PRE_RESTORE_PASS", flush=True)
            denial = await b.evaluate("""async id => {
                const r=await fetch('/api/history/conversations/'+id+'/messages?limit=2',
                    {cache:'no-store'}); return {status:r.status,body:await r.text()};
                }""", aid)
            assert denial["status"] == 404 and message not in denial["body"]
            await expect(a.get_by_test_id("app-runtime-capability")).to_contain_text(
                "برنامه در حالت بدون موتور")
            await expect(a.get_by_test_id("create-conversation")).to_be_disabled()
            await expect(a.get_by_test_id("history-question")).to_be_disabled()
            await expect(a.get_by_test_id("history-send")).to_be_disabled()
            result = await a.evaluate("""async () => {
                const r=await fetch('/api/history/messages',{method:'POST',
                    headers:{'Content-Type':'application/json'},body:'{}'});
                return {status:r.status, body:await r.text()};
                }""")
            assert result["status"] == 503 and "ENGINE_NOT_AVAILABLE" in result["body"]
            tls = ssl.create_default_context(cafile=self.ca)
            tls.load_cert_chain(self.client[0], self.client[1])
            with httpx.Client(verify=tls, trust_env=False, timeout=8) as client:
                direct = client.post(self.product_origin + "/v1/messages", content=b"{}")
                assert direct.status_code == 503 and "ENGINE_NOT_CONFIGURED" in direct.text
            await a.reload(wait_until="domcontentloaded")
            await expect(a.get_by_test_id("conversation-" + aid)).to_be_visible()
            assert self.counts() == before
            self.restricted_db_snapshot("SOURCE_AFTER_SEND",baseline=sql_before)
            print("API_F3_BROWSER_DETAIL_REFRESH_SEND_ZERO_SQL_PASS", flush=True)

            # Repeat in a truly independent fresh PostgreSQL volume while
            # keeping real browser contexts and the original BFF signer.
            with self.fresh_volume() as (restored, restored_id, restored_network):
                try:
                    restored = self.configure_restore_pg_tls(restored_id, restored)
                    self.switch_to_restored(restored, restored_network)
                    assert self.counts() == before
                    self.restricted_db_snapshot("RESTORED",restored,sql_before)
                    self.check_restored_outage(raw_b, restored_id)
                    self.restricted_db_snapshot("AFTER_OUTAGE",restored,sql_before)
                    await self.verify_browser_privacy(browser, a, b, raw_a, raw_b, aid, message)
                    # Normal login again, through the restored Bootstrap and
                    # unchanged Next login route. Reuse the demo harness with
                    # SQL-derived expected titles for the first page only.
                    original_titles = TITLE["B"]
                    TITLE["B"] = [row["title"] for row in expected["B"][:2]]
                    try:
                        fresh_ctx, fresh_b, _, fresh_raw = await self.browser_login(
                            browser, "B", False, output)
                        contexts.append(fresh_ctx)
                        assert fresh_raw["owner_id"] == self.owners["B"]
                        assert fresh_raw["session_ref"] != raw_b["session_ref"]
                        with psycopg.connect(restored["AUTH_SESSION_DSN"], autocommit=True,
                                             row_factory=dict_row) as restored_auth:
                            assert auth_session.inspect(restored_auth, fresh_raw["session_ref"]) is not None
                        with psycopg.connect(os.environ["AUTH_SESSION_DSN"], autocommit=True,
                                             row_factory=dict_row) as original:
                            assert auth_session.inspect(original, fresh_raw["session_ref"]) is None
                        await expect(fresh_b.get_by_test_id("conversation-" + bid)).to_be_visible()
                    finally:
                        TITLE["B"] = original_titles
                    print("API_F3_BROWSER_NEW_OIDC_LOGIN_AFTER_FRESH_VOLUME_RESTORE_PASS", flush=True)
                    for label, page in (("A", a), ("B", b)):
                        async with page.expect_response(
                            lambda r: "/api/history/conversations?limit=2" in r.url
                            and "cursor=" not in r.url and r.request.method == "GET"
                        ) as wait:
                            await page.get_by_test_id("refresh-history").click()
                        response = await wait.value
                        assert response.status == 200
                        doc = await response.json()
                        assert doc["scope_user_id"] == self.owners[label]
                        assert [x["conversation_id"] for x in doc["items"]] == [
                            x["id"] for x in expected[label][:2]]
                        async with page.expect_response(
                            lambda r: "/api/history/conversations?" in r.url and
                            "cursor=" in r.url and r.request.method == "GET"
                        ) as wait:
                            await page.get_by_role("button", name="نمایش گفت‌وگوهای بیشتر").click()
                        second = await wait.value
                        assert second.status == 200
                        assert [x["conversation_id"] for x in (await second.json())["items"]] == [
                            x["id"] for x in expected[label][2:]]
                        for row in expected[label]:
                            await expect(page.get_by_test_id("conversation-" + row["id"])).to_be_visible()
                    # Selection can survive a refresh; force a real new
                    # detail request for this conversation after the restart.
                    other_a = next(row["id"] for row in expected["A"] if row["id"] != aid)
                    await a.get_by_test_id("conversation-" + other_a).click()
                    async with a.expect_response(
                        lambda r: "/api/history/conversations/" + aid + "/messages?" in r.url
                        and r.request.method == "GET") as wait:
                        await a.get_by_test_id("conversation-" + aid).click()
                    restored_response = await wait.value
                    assert restored_response.status == 200
                    restored_doc = await restored_response.json()
                    assert len(restored_doc["items"]) == 30 and restored_doc["page"]["has_more"] is True
                    assert [x["message_id"] for x in restored_doc["items"]] == [
                        row["id"] for row in message_rows[:30]]
                    await self.verify_31_message_page2(
                        a, aid, message_rows, self.owners["A"])
                    print("API_F3_BROWSER_REAL_31_MESSAGE_PAGE2_POST_RESTORE_PASS", flush=True)
                    denial = await b.evaluate("""async id => {
                        const r=await fetch('/api/history/conversations/'+id+'/messages?limit=2',
                            {cache:'no-store'}); return {status:r.status,body:await r.text()};
                        }""", aid)
                    assert denial["status"] == 404 and message not in denial["body"]
                    assert (await a.evaluate("""async () => (await fetch('/api/history/messages',
                        {method:'POST',headers:{'Content-Type':'application/json'},body:'{}'})).status""")) == 503
                    await a.reload(wait_until="domcontentloaded")
                    await expect(a.get_by_test_id("conversation-" + aid)).to_be_visible()
                    assert self.counts() == before
                    self.restricted_db_snapshot("AFTER_BROWSER",restored,sql_before)
                    print("API_F3_BROWSER_RESTORED_VOLUME_PG_HTTP_DOM_AB_PASS", flush=True)
                    # The SAME real signed two-owner React page is tested at
                    # 320px: keyboard modal drawer, Escape focus return and
                    # disabled Send. This is Chromium CI, NOT Safari/VoiceOver.
                    await a.set_viewport_size({"width": 320, "height": 720})
                    menu = a.get_by_role("button", name="بازکردن فهرست گفت‌وگوها")
                    await menu.click()
                    await expect(a.get_by_role("button", name="بستن فهرست")).to_be_focused()
                    await a.keyboard.press("Escape")
                    await expect(menu).to_be_focused()
                    await expect(a.get_by_test_id("history-send")).to_be_disabled()
                    assert await a.evaluate(
                        "() => document.documentElement.scrollWidth <= window.innerWidth + 1"), (
                            "SIGNED_HISTORY_HORIZONTAL_OVERFLOW_320")
                    await a.set_viewport_size({"width": 1280, "height": 800})
                    print("API_F3_REAL_SIGNED_320PX_DRAWER_ESCAPE_FOCUS_SEND_DISABLED_PASS", flush=True)
                    # Existing live ordinary browser logout; no cookie injected.
                    logout = await ca.new_page()
                    await logout.goto(ORIGIN + "/login")
                    await self.actual_oci_read_blocks_real_logout(a,logout,raw_a,aid,message_rows,restored,restored_id)
                    await expect(logout.get_by_test_id("logout-success")).to_be_visible()
                    assert self.signed_private(raw_a).status_code == 401
                    assert self.signed_private(raw_b).status_code == 200
                    await a.get_by_test_id("refresh-history").click()
                    await expect(a.get_by_test_id("history-login-required")).to_be_visible()
                    assert await a.locator('[data-testid^="conversation-"]').count() == 0
                    await b.get_by_test_id("refresh-history").click()
                    await expect(b.get_by_test_id("conversation-" + bid)).to_be_visible()
                    assert self.counts() == before
                    self.restricted_db_snapshot("AFTER_REVOKE",restored,sql_before,revoked=True)
                    print("API_F3_BROWSER_COMMITTED_REVOKE_AB_PASS", flush=True)
                    # The old source remains active; only clone A was revoked.
                    with psycopg.connect(os.environ["AUTH_SESSION_DSN"], autocommit=True,
                                         row_factory=dict_row) as original:
                        assert auth_session.inspect(original, raw_a["session_ref"]) is not None
                        assert auth_session.inspect(original, raw_b["session_ref"]) is not None
                    print("API_F3_BROWSER_RESTORE_SOURCE_SESSIONS_UNCHANGED_PASS", flush=True)
                    receipt=ROOT/"ci_receipts/db_oci_browser_restricted_parity.json"
                    receipt.parent.mkdir(exist_ok=True)
                    receipt.write_text(json.dumps({"source_sha":os.environ["F3_EXACT_SHA"],"api_image_id":self.api_image_id,"checkpoints":6,"history_tables":6,"real_31_message_page2_before_after":True,"signed_mobile_320_focus":True,"actual_oci_read_revoke_blocking_pid_chain":True,"real_oidc_owners":2,"exact_row_parity":True,"migration_ledger_rows":10,"data_bearing_up":9,"actual_failed_002_no_autoretry":True,"actual_interrupted_002_no_autoretry":(Path(os.environ["RUNNER_TEMP"])/"f3-actual-migration-interrupted-verified.txt").read_text().strip()=="PASS","db55_pinned_readonly_auditor_checkpoints":6,"force_rls_tables":14,"source_tls":"VERIFY_FULL_NO_PLAINTEXT_WRONG_SAN","restored_tls":"VERIFY_FULL_NO_PLAINTEXT_WRONG_SAN","migration_install_origin":"ACTIONS_PG_BEFORE_FIRST_CLONE","two_journey_clusters_distinct_from_installer":True,"engine_calls":0,"sql_011":False,"target_verified":False,"accepted":False},indent=2)+"\n")
                finally:
                    self.stop_container_api()
                    for child in (self.api_process, self.bootstrap_process):
                        if child is not None and any(p is child for p, _ in self.children):
                            self.stop_child(child)
                    self.__dict__.pop("restore_mig_dsn", None)
        finally:
            for context in contexts:
                await context.close()


def pg_lifecycle_preflight():
    """Fast real PG lifecycle test before Keycloak/Next/Chromium build.

    Reuse exactly the restore and TLS code of the full journey. No separate
    mock implementation and no modifications to the original database.
    """
    if os.getenv("CI") != "true" or os.getenv("GITHUB_ACTIONS") != "true":
        raise RuntimeError("BROWSER_PG_PREFLIGHT_CI_ONLY")
    demo = AppOnlyBrowserDemo()
    try:
        with demo.fresh_volume() as (dsns, pg_id, _):
            dsns = demo.configure_restore_pg_tls(pg_id, dsns)
            def witness():
                with psycopg.connect(dsns["DB_APP_DSN"], autocommit=True,
                                     row_factory=dict_row) as conn:
                    result = conn.execute(
                        "SELECT current_user AS role, current_database() AS db, "
                        "ssl FROM pg_stat_ssl WHERE pid=pg_backend_pid()").fetchone()
                    assert result["role"] == "history_app" and result["ssl"] is True
                    assert result["db"] == conninfo_to_dict(dsns["DB_APP_DSN"])["dbname"]
            witness()
            demo.ci_command("docker", "stop", "--time", "2", pg_id)
            try:
                try:
                    witness()
                except psycopg.OperationalError:
                    print("API_F3_PG_PREFLIGHT_STOP_DENIED_PASS", flush=True)
                else:
                    raise AssertionError("STOPPED_PG_MUST_NOT_ACCEPT_CONNECTION")
            finally:
                demo.ci_command("docker", "start", pg_id)
                demo.assert_restore_pg_binding(pg_id)
            for _ in range(60):
                try:
                    witness()
                    break
                except psycopg.OperationalError:
                    time.sleep(0.5)
            else:
                demo.restore_pg_diagnostic(pg_id)
                raise RuntimeError("PG_PREFLIGHT_RESTART_FAILED")
            print("API_F3_PG_PREFLIGHT_FRESH_VOLUME_TLS_STOP_START_PASS", flush=True)
    finally:
        demo.stop()


async def main():
    if os.getenv("CI") != "true" or os.getenv("GITHUB_ACTIONS") != "true":
        raise RuntimeError("BROWSER_JOURNEY_CI_ONLY")
    demo = AppOnlyBrowserDemo()
    try:
        raise RuntimeError("DB_BOTH_COMPOSE_JOURNEY_REQUIRED")
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            try:
                # Private temporary directory, never upload session material.
                await demo.journey(browser, demo.root / "browser-output")
            finally:
                await browser.close()
        print("API_F3_REAL_NEXT_BROWSER_NONROOT_OCI_API_TLS_PG_JOURNEY_PASS", flush=True)
    finally:
        demo.stop()


if __name__ == "__main__":
    if sys.argv[1:] == ["--pg-preflight"]:
        pg_lifecycle_preflight()
    elif not sys.argv[1:]:
        asyncio.run(main())
    else:
        raise SystemExit("UNKNOWN_CI_ARGUMENT")
