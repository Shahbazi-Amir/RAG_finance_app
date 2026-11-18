#!/usr/bin/env python3
"""Run the tested Phase-3 browser application locally, never a production service.

Works from a normal Mac Terminal / VS Code checkout. Stages exact tested source
in a disposable detached git worktree, provisions a dedicated Docker PostgreSQL,
then starts real Keycloak, Next and signed API through the original demo harness.
Does not require the GITHUB_ACTIONS environment or touch any preexisting DB.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import platform
import secrets
import shutil
import signal
import socket
import stat
import subprocess
import tarfile
import tempfile
import sys
import time
import venv

REPO = Path(__file__).resolve().parents[2]
BRANCH = "agent/ui-auth-bff-010-integration"
UI = "fee20cc0992f4c26f76757e670cd6425400441cc"
API50 = "62d40f4b4ed254de0aa0dfc21c17d809e24423db"
API48 = "1998b31c86155a972b11ea745d6bb37e09549392"
API36 = "99a917c2f2c519027d0e71643bbbf6973a6c8ac3"
SQL009 = "656604356dadea953031fcdb74650a5d42df4e9b"
SQL010 = "1678e87b7984094b74ec995383b8d4383e5f5ae7"
POSTGRES_IMAGE = "postgres:17.11"
KEYCLOAK_IMAGE = "quay.io/keycloak/keycloak:26.8.2"
NODE_RELEASE = "v22.16.0"
# Official Node 22.16.0 SHA256 from nodejs.org, binaries target macOS >=11.
NODE_MAC_SHA256 = {"x64": "838d400f7e66c804e5d11e2ecb61d6e9e878611146baff69d6a2def3cc23f4ac",
                  "arm64": "1d7f34ec4c03e12d8b33481e5c4560432d7dc31a0ef3ff5a4d9a8ada7cf6ecc9"}
NODE_CACHE = Path.home() / ".cache" / "rag-phase3-demo-node"
ROOT_HASH = hashlib.sha256(str(REPO.resolve()).encode()).hexdigest()[:16]
STATE = Path("/tmp") / ("rag-phase3-local-" + ROOT_HASH)
SOURCE = STATE / "source"
MANIFEST = STATE / "manifest.json"
READY = STATE / "ready.json"
STOP = STATE / "stop.request"
LOG = STATE / "service.log"
CREDENTIALS = STATE / "synthetic-accounts.json"

ROLES = (
    "history_migrator", "history_app", "auth_migrator", "auth_mapper",
    "auth_sessions", "auth_revoker", "auth_reauth", "auth_trust_api",
    "auth_replay_cleaner", "auth_reset_issuer", "auth_reset_executor",
    "auth_reset_lookup", "auth_reset_idp_recorder", "auth_login_bootstrap",
    "auth_login_claim_reader", "auth_login_issuer", "auth_login_binder",
    "auth_login_reader", "auth_login_cleaner",
)


def run(argv, *, cwd=None, env=None, input_text=None, capture=False, timeout=480):
    proc = subprocess.run(argv, cwd=cwd, env=env, input=input_text,
                          text=True, stdout=subprocess.PIPE if capture else None,
                          stderr=subprocess.PIPE if capture else None,
                          timeout=timeout, check=False)
    if proc.returncode:
        stderr = (proc.stderr or "").strip()
        raise RuntimeError(f"COMMAND_FAILED ({argv[0]} exit {proc.returncode}): {stderr[-1000:]}")
    return proc.stdout or ""


def check_repo():
    root = run(["git", "rev-parse", "--show-toplevel"], cwd=REPO, capture=True).strip()
    if Path(root).resolve() != REPO.resolve():
        raise RuntimeError("EXPECTED_THIS_REPOSITORY_CLONE")
    branch = run(["git", "branch", "--show-current"], cwd=REPO, capture=True).strip()
    if branch == BRANCH:
        return
    if branch == "":
        # Accept only detached HEAD at the fetched #49 branch tip.
        head = run(["git", "rev-parse", "HEAD"], cwd=REPO, capture=True).strip()
        tracked = subprocess.run(["git", "rev-parse", "--verify",
            "refs/remotes/origin/" + BRANCH], cwd=REPO, capture_output=True, text=True)
        if tracked.returncode == 0 and tracked.stdout.strip() == head:
            return
        raise RuntimeError("DETACHED_DEMO_NOT_AT_PR49_TIP: git fetch origin " + BRANCH +
                           " && git switch --detach origin/" + BRANCH)
    raise RuntimeError(f"WRONG_BRANCH: {branch!r}; use {BRANCH}")


def compatible_node():
    node = shutil.which("node")
    if not node or not shutil.which("npm"):
        return False
    result = subprocess.run([node, "-v"], capture_output=True, text=True, timeout=12)
    if result.returncode:
        return False
    parts = result.stdout.strip().lstrip("v").split(".")
    try:
        major, minor = int(parts[0]), int(parts[1])
    except (ValueError, IndexError):
        return False
    if major == 24 and sys.platform == "darwin":
        # Official Node 24 macOS binaries require >=13.5. A manually installed
        # Node 24 may report a version on macOS 12 but is not supported there.
        try:
            mac = platform.mac_ver()[0].split(".")
            release = (int(mac[0]), int(mac[1]) if len(mac) > 1 else 0)
        except (ValueError, IndexError):
            return False
        return release >= (13, 5)
    return major == 24 or (major == 22 and minor >= 12)


def ensure_node():
    if compatible_node():
        print("Node runtime:", run(["node", "-v"], capture=True).strip(), flush=True)
        return
    if sys.platform != "darwin":
        raise RuntimeError("Node 22.12+ or Node 24 with npm required on this non-macOS host")
    arch = {"x86_64": "x64", "arm64": "arm64"}.get(platform.machine().lower(), "")
    if arch not in NODE_MAC_SHA256:
        raise RuntimeError("UNSUPPORTED_MAC_NODE_ARCH: " + platform.machine())
    if NODE_CACHE.is_symlink():
        raise RuntimeError("UNSAFE_NODE_CACHE_SYMLINK")
    NODE_CACHE.mkdir(parents=True, mode=0o700, exist_ok=True)
    if NODE_CACHE.stat().st_uid != os.getuid():
        raise RuntimeError("UNSAFE_NODE_CACHE_OWNER")
    base = "node-" + NODE_RELEASE + "-darwin-" + arch
    target = NODE_CACHE / base
    if target.is_symlink():
        raise RuntimeError("UNSAFE_NODE_BINARY_SYMLINK")
    if not (target / "bin/node").is_file():
        if target.exists():
            raise RuntimeError("INCOMPLETE_NODE_CACHE: " + str(target))
        archive_name = base + ".tar.gz"
        url = "https://nodejs.org/dist/" + NODE_RELEASE + "/" + archive_name
        print("در حال دریافت خودکار Node " + NODE_RELEASE + " از nodejs.org ...", flush=True)
        stage = Path(tempfile.mkdtemp(prefix="node-verified-", dir=NODE_CACHE))
        try:
            archive = stage / archive_name
            # macOS's system curl uses the system trust store. Python.org's
            # framework Python 3.11 may not have its optional cert bundle set up.
            # HTTPS-only, fail on HTTP errors; the pinned SHA256 is mandatory.
            run(["curl", "--fail", "--location", "--retry", "2", "--proto", "=https",
                 "--connect-timeout", "20", "--max-time", "300",
                 "--output", str(archive), url], capture=True, timeout=360)
            if archive.stat().st_size >= 90_000_000:
                raise RuntimeError("NODE_DOWNLOAD_SIZE_LIMIT")
            with archive.open("rb") as stream:
                digest = hashlib.file_digest(stream, "sha256").hexdigest()
            if digest != NODE_MAC_SHA256[arch]:
                raise RuntimeError("NODE_ARCHIVE_CHECKSUM_MISMATCH")
            with tarfile.open(archive, "r:gz") as bundle:
                for member in bundle.getmembers():
                    name = Path(member.name)
                    if (name.is_absolute() or ".." in name.parts
                            or not (member.name == base or member.name.startswith(base + "/"))):
                        raise RuntimeError("NODE_UNSAFE_TAR_ENTRY")
                    if member.issym() or member.islnk():
                        target_link = (stage / name.parent / member.linkname).resolve()
                        if not target_link.is_relative_to(stage.resolve()):
                            raise RuntimeError("NODE_UNSAFE_TAR_LINK")
                bundle.extractall(stage)
            extracted = stage / base
            if not (extracted / "bin/node").is_file():
                raise RuntimeError("NODE_EXTRACTION_INCOMPLETE")
            extracted.rename(target)
        finally:
            shutil.rmtree(stage, ignore_errors=True)
    os.environ["PATH"] = str(target / "bin") + os.pathsep + os.environ.get("PATH", "")
    if not compatible_node():
        raise RuntimeError("NODE_BINARY_CANNOT_RUN_ON_THIS_MAC")
    print("Node isolated cache:", run(["node", "-v"], capture=True).strip(), flush=True)


# Playwright 1.64 does not distribute its Chromium for macOS 12. Chrome 150
# is the last Google release for that OS and no longer gets security updates.
# Reuse ONLY an existing official Chrome app, with an explicit local-demo
# opt-in. Never fetch an old browser or run an unverified executable from PATH.
MAC_CHROME_EXECUTABLES = (
    Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"),
    Path.home() / "Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
)


def browser_launch_options():
    if sys.platform != "darwin":
        return {}
    try:
        mac = tuple(int(part) for part in platform.mac_ver()[0].split(".")[:2])
    except ValueError as exc:
        raise RuntimeError("MACOS_VERSION_UNKNOWN_FOR_BROWSER") from exc
    if not mac or mac >= (15, 0):
        return {}
    if os.environ.get("RAG_PHASE3_DEMO_ALLOW_LEGACY_CHROME") != "1":
        raise RuntimeError(
            "MACOS_LEGACY_BROWSER_OPT_IN_REQUIRED: Playwright 1.64 does not "
            "ship Chromium for macOS <15. If official Google Chrome is already "
            "installed, opt into using it ONLY for the loopback synthetic demo "
            "with RAG_PHASE3_DEMO_ALLOW_LEGACY_CHROME=1; older Chrome on "
            "macOS12 no longer receives security updates."
        )
    for executable in MAC_CHROME_EXECUTABLES:
        if executable.is_file() and os.access(executable, os.X_OK):
            return {"executable_path": str(executable)}
    raise RuntimeError(
        "MACOS_LEGACY_CHROME_NOT_INSTALLED: expected /Applications/Google "
        "Chrome.app; no downloads, browser replacements or system changes."
    )


def check_runtime():
    if not ((3, 11) <= sys.version_info[:2] <= (3, 13)):
        raise RuntimeError("Python 3.11–3.13 required; existing Python 3.11.3 is accepted")
    if not shutil.which("git") or not shutil.which("docker"):
        raise RuntimeError("Missing Git or Docker CLI; Docker Desktop must be running")
    if sys.platform not in ("darwin", "linux"):
        raise RuntimeError("Supported: macOS; Linux isolated test only")
    run(["docker", "info", "--format", "{{.ServerVersion}}"], capture=True, timeout=15)
    check_repo()
    ensure_node()
    browser_launch_options()  # Fail early before downloading/building packages.


def free_ports():
    for port in (5432, 3000, 3443):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                # Node/HTTPS may leave harmless TCP TIME_WAIT sockets after
                # stop. Reuse the *address* (never SO_REUSEPORT) so reset can
                # bind again, while an actual listening service still blocks.
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                sock.bind(("127.0.0.1", port))
        except OSError as exc:
            raise RuntimeError(f"PORT_CONFLICT 127.0.0.1:{port}: {exc}; no service was stopped") from exc


def state_is_safe():
    if STATE.is_symlink():
        raise RuntimeError("UNSAFE_STATE_SYMLINK")
    if STATE.exists():
        s = STATE.stat()
        if s.st_uid != os.getuid() or stat.S_IMODE(s.st_mode) != 0o700:
            raise RuntimeError("STATE_OWNER_OR_MODE_MISMATCH")


def write_json(path, value):
    data = json.dumps(value, ensure_ascii=False, indent=2)
    temp = path.with_name(path.name + "." + secrets.token_hex(8) + ".tmp")
    fd = os.open(temp, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    with os.fdopen(fd, "w") as file:
        file.write(data)
        file.flush()
        os.fsync(file.fileno())
    os.replace(temp, path)


def read_json(path):
    if not path.is_file() or path.is_symlink():
        raise RuntimeError(f"STATE_MISSING: {path.name}")
    return json.loads(path.read_text())


def command_git(*args, capture=False):
    return run(["git", *args], cwd=REPO, capture=capture, timeout=160)


def ensure_pin(sha):
    found = subprocess.run(["git", "cat-file", "-e", sha + "^{commit}"],
                           cwd=REPO, stdout=subprocess.DEVNULL,
                           stderr=subprocess.DEVNULL)
    if found.returncode:
        print("در حال دریافت وابستگی پین‌شده:", sha[:12], flush=True)
        command_git("fetch", "--no-tags", "origin", sha)
    resolved = command_git("rev-parse", sha + "^{commit}", capture=True).strip()
    if resolved != sha:
        raise RuntimeError("PIN_SHA_MISMATCH: " + sha)


def stage_source():
    for sha in (UI, API50, API48, API36, SQL009, SQL010):
        ensure_pin(sha)
    command_git("worktree", "add", "--detach", str(SOURCE), UI)
    exact = run(["git", "rev-parse", "HEAD"], cwd=SOURCE, capture=True).strip()
    if exact != UI:
        raise RuntimeError("DEMO_UI_NOT_PINNED")
    pins = {
        API50: ["src/phase3/auth/bootstrap_oidc.py", "apps/api/product_session_api.py",
                "tests/phase3/integration/api/test_product_session_011.py"],
        API48: ["src/phase3/auth/initial_oidc_login.py",
                "tests/phase3/integration/api/bootstrap_010_worker.py",
                "tests/phase3/integration/api/initial_oidc_harness.py",
                "tests/phase3/integration/api/test_bootstrap_oidc_010.py"],
        API36: ["src/phase3/auth/transactional_admission.py"],
        SQL009: [f"infra/postgres/migrations/009_initial_login_attempt_binding.{kind}.sql"
                 for kind in ("up", "down")],
        SQL010: [f"infra/postgres/migrations/010_initial_login_claim_material.{kind}.sql"
                 for kind in ("up", "down")],
    }
    for sha, paths in pins.items():
        for path in paths:
            target = SOURCE / path
            target.parent.mkdir(parents=True, exist_ok=True)
            data = subprocess.run(["git", "show", f"{sha}:{path}"], cwd=REPO,
                                  stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True).stdout
            target.write_bytes(data)
    # Only the disposable stage receives explicit LOCAL launch-mode adaptations.
    # The pinned API/Keycloak contracts and original repo remain unchanged.
    replacements = [
        ("apps/api/product_session_api.py",
         'if os.getenv("CI") != "true" or os.getenv("GITHUB_ACTIONS") != "true":',
         'if os.getenv("CI") != "true" or os.getenv("RAG_PHASE3_DEMO_LOCAL") != "true":'),
        ("tests/phase3/integration/ui/phase3_auth_demo.py",
         'if os.environ.get("CI")!="true" or os.environ.get("GITHUB_ACTIONS")!="true":',
         'if os.environ.get("CI")!="true" or os.environ.get("RAG_PHASE3_DEMO_LOCAL")!="true":'),
        ("tests/phase3/integration/api/initial_oidc_harness.py",
         '"--network", self.network, "--pull", "always",',
         '"--network", self.network, "--pull", "missing",'),
    ]
    for path, old, new in replacements:
        target = SOURCE / path
        original = target.read_text()
        if original.count(old) != 1:
            raise RuntimeError("UNRECOGNIZED_PINNED_SOURCE: " + path)
        target.write_text(original.replace(old, new))
    write_json(STATE / "pinned-sources.json", {
        "ui": UI, "api50": API50, "api48": API48,
        "transaction_36": API36, "migration_009": SQL009, "migration_010": SQL010,
        "local_adaptations": [x[0] for x in replacements],
    })


def prepare_packages():
    run([sys.executable, "-m", "venv", str(STATE / "venv")])
    py = str(STATE / "venv" / "bin" / "python")
    # pyca/cryptography >=49 dropped official macOS Intel wheels. The older
    # 48.0.1 universal2 wheel is affected by 2026 security advisories. Never
    # silently downgrade or attempt an unapproved Rust source build on Intel.
    mac_intel = sys.platform == "darwin" and platform.machine().lower() == "x86_64"
    explicit_source = os.environ.get("RAG_PHASE3_DEMO_ALLOW_CRYPTO_SOURCE") == "1"
    if mac_intel:
        # Upgrade only the disposable demo venv; never modify the Mac's Python.
        run([py, "-m", "pip", "install", "--disable-pip-version-check",
             "--no-cache-dir", "--upgrade", "pip"], timeout=180)
    install = [py, "-m", "pip", "install", "--disable-pip-version-check",
               "--no-cache-dir"]
    if mac_intel and not explicit_source:
        install.append("--only-binary=cryptography")
    install += ["-r", str(SOURCE / "apps/api/requirements-ci.txt"),
                "PyJWT[crypto]==2.15.1", "uvicorn==0.34.3", "playwright==1.64.1"]
    if mac_intel:
        # Known-fixed for CVE-2026-69247/69248/69249; its official PyPI
        # distributions currently have no x86_64/universal2 macOS wheel.
        install.append("cryptography==50.0.2")
    try:
        run(install, timeout=480)
    except RuntimeError as exc:
        if mac_intel and not explicit_source:
            raise RuntimeError(
                "MAC_INTEL_OFFICIAL_SECURE_CRYPTO_WHEEL_UNAVAILABLE: "
                "cryptography 50.0.2 has no official PyPI macOS x86_64 wheel. "
                "pip was upgraded only inside the temporary demo venv; "
                "no vulnerable 48.0.1 downgrade or Rust source build was used. "
                "See scripts/phase3-demo/README_FA.md for the explicit "
                "source-build opt-in and its prerequisites."
            ) from exc
        raise
    if not browser_launch_options():
        run([py, "-m", "playwright", "install", "chromium"], timeout=480)
    else:
        print("MACOS_LEGACY_CHROME_EXISTING_APP_SELECTED (synthetic loopback only)", flush=True)
    run(["npm", "ci", "--no-audit", "--no-fund"], cwd=SOURCE / "apps/web", timeout=480)
    env = dict(os.environ, NEXT_PUBLIC_CI_DEMO_MODE="true", CI="true")
    run(["npm", "run", "typecheck"], cwd=SOURCE / "apps/web", env=env)
    run(["npm", "run", "lint"], cwd=SOURCE / "apps/web", env=env)
    run(["npm", "test"], cwd=SOURCE / "apps/web", env=env)
    run(["npm", "run", "build"], cwd=SOURCE / "apps/web", env=env,timeout=480)


def docker_owned(manifest):
    container = manifest.get("postgres_id", "")
    if not container or not container.startswith("sha256:") and len(container) != 64:
        return False
    proc = subprocess.run(["docker", "inspect", "--format",
                           "{{index .Config.Labels \"rag.phase3.instance\"}}",
                           container], capture_output=True, text=True)
    return proc.returncode == 0 and proc.stdout.strip() == manifest.get("id")


def create_postgres(manifest):
    pw = secrets.token_urlsafe(36)
    name = "rag-phase3-pg-" + manifest["id"][:12]
    if subprocess.run(["docker", "image", "inspect", POSTGRES_IMAGE],
                      stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode != 0:
        run(["docker", "pull", POSTGRES_IMAGE], timeout=360)
    container = run(["docker", "run", "--detach", "--rm", "--name", name,
                     "--label", "rag.phase3.instance=" + manifest["id"],
                     "--memory", "768m", "--pids-limit", "256",
                     "--security-opt", "no-new-privileges",
                     "--tmpfs", "/var/lib/postgresql/data:rw,nosuid,size=640m",
                     "-p", "127.0.0.1:5432:5432",
                     "-e", "POSTGRES_PASSWORD=" + pw,
                     POSTGRES_IMAGE], capture=True, timeout=150).strip()
    manifest["postgres_id"] = container
    write_json(MANIFEST, manifest)
    if not docker_owned(manifest):
        raise RuntimeError("POSTGRES_OWNERSHIP_CHECK_FAILED")
    for _ in range(120):
        result = subprocess.run(["docker", "exec", container,
                                 "pg_isready", "-U", "postgres", "-d", "postgres"],
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if result.returncode == 0:
            return pw
        time.sleep(1)
    raise RuntimeError("POSTGRES_NOT_READY")


def quote(value):
    return "'" + str(value).replace("'", "''") + "'"


def db_sql(container, script, *, user="postgres", database="postgres", password=None):
    cmd = ["docker", "exec", "-i"]
    if password is not None:
        cmd += ["-e", "PGPASSWORD=" + password]
    cmd += [container, "psql", "-h", "127.0.0.1", "-p", "5432",
            "-U", user, "-d", database, "-v", "ON_ERROR_STOP=1", "-q"]
    run(cmd, input_text=script, timeout=140, capture=True)


def init_db(manifest, postgres_password):
    if not docker_owned(manifest):
        raise RuntimeError("POSTGRES_CONTAINER_NOT_OURS")
    passwords = {name: secrets.token_urlsafe(26) for name in ROLES}
    commands = []
    for name in ROLES:
        attributes = ("LOGIN BYPASSRLS" if name in ("history_migrator", "auth_migrator")
                      else "LOGIN NOSUPERUSER NOBYPASSRLS NOINHERIT NOCREATEDB NOCREATEROLE")
        commands.append(f"CREATE ROLE {name} {attributes} PASSWORD {quote(passwords[name])};")
    commands += [
        "GRANT pg_read_all_stats TO auth_migrator;",
        "CREATE DATABASE history_ci;",
        "GRANT CONNECT,CREATE ON DATABASE history_ci TO history_migrator,auth_migrator;",
        "GRANT CONNECT ON DATABASE history_ci TO " + ",".join(
            x for x in ROLES if x not in ("history_migrator", "auth_migrator")) + ";",
    ]
    db_sql(manifest["postgres_id"], "\n".join(commands))
    migrations = [
        ("history_migrator", "001_history_l1"),
        ("history_migrator", "002_one_attempt"),
        ("auth_migrator", "003_auth_session"),
        ("auth_migrator", "004_session_aware_fence"),
        ("auth_migrator", "005_service_assertion_replay"),
        ("auth_migrator", "006_atomic_reset_c1"),
        ("auth_migrator", "007_scoped_reset_identity_lookup"),
        ("auth_migrator", "008_durable_idp_attempt_outcome"),
        ("auth_migrator", "009_initial_login_attempt_binding"),
        ("auth_migrator", "010_initial_login_claim_material"),
    ]
    for user, basename in migrations:
        file = SOURCE / "infra/postgres/migrations" / (basename + ".up.sql")
        db_sql(manifest["postgres_id"], file.read_text(), user=user,
               database="history_ci", password=passwords[user])
        print("Migration:", basename[:3], flush=True)
    # The #50 function-only bridge is approved ONLY inside this disposable DB.
    db_sql(manifest["postgres_id"], """
        GRANT USAGE ON SCHEMA auth_l1 TO history_app;
        GRANT EXECUTE ON FUNCTION auth_l1.consume_service_assertion(text,bigint)
          TO history_app,auth_revoker;
        GRANT EXECUTE ON FUNCTION auth_l1.admit_session_fenced(text,text,bigint,integer)
          TO history_app,auth_revoker;
        GRANT EXECUTE ON FUNCTION auth_l1.revoke_one(text,bigint) TO auth_revoker;
    """, database="history_ci")
    env = {"CI": "true", "RAG_PHASE3_DEMO_LOCAL": "true",
           "TMPDIR": "/tmp", "GITHUB_ACTIONS": ""}
    for role, key in (
        ("auth_mapper", "AUTH_MAP_DSN"), ("auth_sessions", "AUTH_SESSION_DSN"),
        ("auth_revoker", "AUTH_REVOKER_DSN"), ("auth_reauth", "AUTH_REAUTH_DSN"),
        ("auth_migrator", "AUTH_MIG_DSN"),
        ("auth_reset_issuer", "AUTH_RESET_ISSUER_DSN"),
        ("auth_reset_executor", "AUTH_RESET_EXEC_DSN"),
        ("auth_reset_lookup", "AUTH_RESET_LOOKUP_DSN"),
        ("auth_reset_idp_recorder", "AUTH_RESET_IDP_DSN"),
        ("auth_login_bootstrap", "LOGIN_BOOTSTRAP_DSN"),
        ("auth_login_claim_reader", "LOGIN_CLAIM_DSN"),
        ("auth_login_issuer", "LOGIN_ISSUER_DSN"),
        ("auth_login_binder", "LOGIN_BINDER_DSN"),
        ("auth_login_reader", "LOGIN_READER_DSN"),
        ("auth_login_cleaner", "LOGIN_CLEANER_DSN"),
        ("auth_trust_api", "REPLAY_API_DSN"),
        ("auth_replay_cleaner", "REPLAY_CLEANER_DSN"),
        ("history_app", "DB_APP_DSN"),
        ("history_migrator", "DB_MIG_DSN"),
    ):
        env[key] = (f"host=127.0.0.1 port=5432 dbname=history_ci user={role} "
                    f"password={passwords[role]} connect_timeout=5")
    write_json(STATE / "private-db-env.json", env)
    return env


def clean_resources():
    state_is_safe()
    if MANIFEST.exists():
        manifest = read_json(MANIFEST)
        if manifest.get("repo") != str(REPO.resolve()):
            raise RuntimeError("FOREIGN_DEMO_STATE_REFUSED")
        if manifest.get("postgres_id"):
            if docker_owned(manifest):
                run(["docker", "rm", "-f", manifest["postgres_id"]], capture=True, timeout=60)
            else:
                print("PostgreSQL identity missing/mismatched; no external container touched")
    if SOURCE.exists():
        run(["git", "worktree", "remove", "--force", str(SOURCE)], cwd=REPO, timeout=90)
    if STATE.exists():
        shutil.rmtree(STATE)


def alive(pid):
    if not isinstance(pid, int) or pid <= 0:
        return False
    try:
        os.kill(pid, 0)
        state = subprocess.run(["ps", "-o", "stat=", "-p", str(pid)],
                               capture_output=True, text=True)
        return state.returncode == 0 and not state.stdout.strip().startswith("Z")
    except (OSError, ValueError):
        return False


def start():
    check_runtime()
    state_is_safe()
    if MANIFEST.exists():
        old = read_json(MANIFEST)
        if alive(old.get("service_pid")) or READY.exists():
            raise RuntimeError("DEMO_ALREADY_RUNNING; use status or stop")
        raise RuntimeError("STALE_DEMO_STATE; run stop before start")
    free_ports()  # Never stop, reset or connect to a foreign service.
    STATE.mkdir(mode=0o700)
    STATE.chmod(0o700)
    manifest = {"id": secrets.token_hex(16), "repo": str(REPO.resolve()),
                "ui_sha": UI, "postgres_id": "", "service_pid": None}
    write_json(MANIFEST, manifest)
    try:
        stage_source()
        prepare_packages()
        postgres_password = create_postgres(manifest)
        init_db(manifest, postgres_password)
        env = dict(os.environ)
        env.update(read_json(STATE / "private-db-env.json"))
        env.pop("GITHUB_ACTIONS", None)
        env.update(PYTHONUNBUFFERED="1", RAG_PHASE3_DEMO_STATE=str(STATE),
                   RAG_PHASE3_DEMO_CONTAINER=manifest["postgres_id"])
        with LOG.open("ab") as out:
            worker = subprocess.Popen([str(STATE / "venv/bin/python"),
                str(REPO / "scripts/phase3-demo/launcher.py"), "serve"],
                cwd=SOURCE, env=env, stdin=subprocess.DEVNULL,
                stdout=out, stderr=out, start_new_session=True)
        manifest["service_pid"] = worker.pid
        write_json(MANIFEST, manifest)
        for _ in range(600):
            if READY.exists():
                if worker.poll() is not None:
                    raise RuntimeError("DEMO_SERVICES_EXITED_DURING_START")
                info = read_json(READY)
                if info.get("ui_sha") != UI:
                    raise RuntimeError("STARTED_UNEXPECTED_UI_SOURCE")
                print("\n✅ محیط محلی دمو و تمرین Chromium آماده شد")
                print("ورود:", info["login_url"])
                print("حساب‌های مصنوعی: bash scripts/phase3-demo/demo.sh credentials")
                print("توقف: bash scripts/phase3-demo/demo.sh stop")
                print("بازنشانی: bash scripts/phase3-demo/demo.sh reset")
                print("هشدار: فقط مرورگر محلی؛ گواهی TLS موقت و آزمایشی است")
                return
            if worker.poll() is not None:
                tail = LOG.read_text(errors="replace")[-2500:] if LOG.exists() else ""
                raise RuntimeError("DEMO_WORKER_FAILED: " + tail)
            time.sleep(1)
        raise RuntimeError("DEMO_STARTUP_DID_NOT_FINISH: check " + str(LOG))
    except BaseException:
        if MANIFEST.exists():
            current = read_json(MANIFEST)
            if alive(current.get("service_pid")):
                STOP.touch(mode=0o600)
                for _ in range(75):
                    if not alive(current["service_pid"]):
                        break
                    time.sleep(1)
        current = read_json(MANIFEST)
        if not alive(current.get("service_pid")):
            clean_resources()
        raise


def serve():
    if os.environ.get("RAG_PHASE3_DEMO_LOCAL") != "true" or os.environ.get("CI") != "true":
        raise RuntimeError("LOCAL_EXCLUSIVE_RUNNER_REQUIRED")
    if os.environ.get("GITHUB_ACTIONS"):
        raise RuntimeError("GITHUB_ACTIONS_FLAG_MUST_NOT_BE_FORGED")
    manifest = read_json(MANIFEST)
    if not docker_owned(manifest):
        raise RuntimeError("LOCAL_POSTGRES_OWNERSHIP_FAILED")
    if os.environ.get("RAG_PHASE3_DEMO_CONTAINER") != manifest["postgres_id"]:
        raise RuntimeError("LOCAL_CONTAINER_BINDING_FAILED")
    # Import exact demonstrated tests from the detached, staged snapshot.
    sys.path.insert(0, str(SOURCE))
    sys.path.insert(0, str(SOURCE / "tests/phase3/integration/api"))
    sys.path.insert(0, str(SOURCE / "tests/phase3/integration/ui"))
    from phase3_auth_demo import Demo
    from playwright.async_api import async_playwright
    import asyncio
    demo = Demo()
    try:
        demo.start()
        write_json(CREDENTIALS, {
            "note": "محلی و مصنوعی؛ خارج از این دستگاه منتشر نشود",
            "login_url": "https://127.0.0.1:3443/login",
            "A": {"label": "حساب نمایشی الف", "email": demo.kc.accounts["A"]["email"],
                  "password": demo.kc.accounts["A"]["password"]},
            "B": {"label": "حساب نمایشی ب", "email": demo.kc.accounts["B"]["email"],
                  "password": demo.kc.accounts["B"]["password"]},
        })
        async def smoke():
            async with async_playwright() as p:
                browser = await p.chromium.launch(**browser_launch_options())
                try:
                    out = STATE / "browser-check"
                    await demo.scenario(browser, False, out)
                    await demo.scenario(browser, True, out)
                finally:
                    await browser.close()
        asyncio.run(smoke())
        print("LOCAL_DEMO_REAL_A_B_HISTORY_REVOKE_CHROMIUM_PASS", flush=True)
        write_json(READY, {"login_url": "https://127.0.0.1:3443/login",
                           "ui_sha": UI, "pid": os.getpid(), "checks": "PASS"})
        while not STOP.exists():
            if any(p.poll() is not None for p, _ in demo.children):
                raise RuntimeError("DEMO_SERVICE_EXITED_UNEXPECTEDLY")
            if not docker_owned(manifest):
                raise RuntimeError("DEMO_POSTGRES_STOPPED")
            time.sleep(1)
    finally:
        if READY.exists():
            READY.unlink()
        if CREDENTIALS.exists():
            CREDENTIALS.unlink()
        demo.stop()


def stop():
    state_is_safe()
    if not MANIFEST.exists():
        print("دمو در حال اجرا نیست؛ هیچ سرویس دیگری تغییر نکرد")
        return
    manifest = read_json(MANIFEST)
    if manifest.get("repo") != str(REPO.resolve()):
        raise RuntimeError("REFUSE_STOP_FOREIGN_DEMO")
    if alive(manifest.get("service_pid")):
        STOP.touch(mode=0o600)
        for _ in range(85):
            if not alive(manifest["service_pid"]):
                break
            time.sleep(1)
        if alive(manifest["service_pid"]):
            raise RuntimeError("DEMO_STILL_RUNNING; nothing forcibly killed; check service.log")
    clean_resources()
    print("✅ دمو متوقف شد؛ فقط کانتینر PostgreSQL دارای شناسهٔ همین دمو پاک شد")


def status():
    state_is_safe()
    if not MANIFEST.exists():
        print("STOPPED")
        return
    m = read_json(MANIFEST)
    text = "READY" if READY.exists() and alive(m.get("service_pid")) else "INCOMPLETE"
    print(text, "source", m.get("ui_sha"), "postgres_owned", docker_owned(m))
    if READY.exists():
        print("https://127.0.0.1:3443/login")


def credentials():
    state_is_safe()
    if not READY.exists() or not CREDENTIALS.exists():
        raise RuntimeError("DEMO_NOT_READY: run start first")
    print(CREDENTIALS.read_text())


def preflight():
    print("System:", platform.platform(), "Python:", sys.version.split()[0])
    print("Source UI pinned:", UI)
    print("API pins:", API48[:12], API50[:12], "DB 009/010 pinned")
    check_runtime()
    state_is_safe()
    if not MANIFEST.exists():
        free_ports()
    print("PREFLIGHT_OK: current machine has required tooling and free demo ports")


def main():
    cmd = sys.argv[1] if len(sys.argv) == 2 else ""
    if cmd == "preflight":
        preflight()
    elif cmd == "start":
        start()
    elif cmd == "serve":
        serve()
    elif cmd == "stop":
        stop()
    elif cmd == "reset":
        stop()
        start()
    elif cmd == "status":
        status()
    elif cmd == "credentials":
        credentials()
    else:
        raise RuntimeError("Usage: demo.sh preflight|start|status|credentials|stop|reset")


if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, OSError, subprocess.CalledProcessError) as exc:
        print("خطای راه‌انداز:", exc, file=sys.stderr)
        sys.exit(1)
