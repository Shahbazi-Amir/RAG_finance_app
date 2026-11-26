"""Linux disposable runner browser trust, isolated from host trust stores."""
from contextlib import contextmanager
import os
from pathlib import Path
import subprocess
import tempfile


@contextmanager
def isolated_browser_trust(ca_file):
    ca = Path(ca_file).resolve(strict=True)
    with tempfile.TemporaryDirectory(prefix="f3-browser-trust-") as work:
        home = Path(work)
        db = home / ".pki" / "nssdb"
        db.mkdir(parents=True, mode=0o700)
        for args in (["-N", "--empty-password"], ["-A", "-n", "F3 ephemeral CI CA", "-t", "C,,", "-i", str(ca)]):
            subprocess.run(["certutil", "-d", "sql:" + str(db), *args], check=True, capture_output=True, timeout=15)
        cache = Path(os.environ.get("XDG_CACHE_HOME", str(Path.home() / ".cache")))
        browsers = os.environ.get("PLAYWRIGHT_BROWSERS_PATH") or str(cache / "ms-playwright")
        modern_db = home / ".local" / "share" / "pki" / "nssdb"
        modern_db.parent.mkdir(parents=True)
        modern_db.symlink_to(db, target_is_directory=True)
        keys = ("HOME", "XDG_CONFIG_HOME", "XDG_DATA_HOME", "NODE_EXTRA_CA_CERTS", "PLAYWRIGHT_BROWSERS_PATH")
        old = {k: os.environ.get(k) for k in keys}
        os.environ.update(HOME=str(home), XDG_CONFIG_HOME=str(home / ".config"), XDG_DATA_HOME=str(home / ".local" / "share"), NODE_EXTRA_CA_CERTS=str(ca), PLAYWRIGHT_BROWSERS_PATH=browsers)
        try:
            yield
        finally:
            for key, value in old.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value
