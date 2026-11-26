"""Render an Nginx header include from the protected Web profile without output."""
import json
import os
from pathlib import Path
import re
import stat
import sys
from tempfile import NamedTemporaryFile


def protected(path):
    info = path.lstat()
    if (not stat.S_ISREG(info.st_mode) or info.st_mode & 0o077
            or not 1 <= info.st_size <= 65536):
        raise ValueError()
    return path.read_text(encoding="utf-8")


def main():
    config = Path("/etc/rag-arvan-candidate/web-private.json")
    output = Path("/etc/nginx/rag-arvan-proxy-proof.inc")
    proof = protected(Path(json.loads(protected(config))["proxy_proof_file"])).strip()
    if not re.fullmatch(r"[A-Za-z0-9_.+/=-]{32,256}", proof):
        raise ValueError()
    with NamedTemporaryFile(mode="w", dir=output.parent, delete=False) as staged:
        path = Path(staged.name)
        try:
            staged.write(f'proxy_set_header X-Auth-Staging-Proxy-Proof "{proof}";\n')
            staged.flush()
            os.replace(path, output)
        finally:
            path.unlink(missing_ok=True)


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, KeyError, TypeError):
        sys.exit("NGINX_PROOF_RENDER_DENIED")
