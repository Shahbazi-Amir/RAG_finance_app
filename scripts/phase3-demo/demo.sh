#!/bin/sh
# Prefer the pinned 3.11.3 compatibility interpreter, retain 3.13 fallback.
# Override with RAG_PHASE3_PYTHON=/absolute/path/to/python for a fresh venv.
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
if [ -n "${RAG_PHASE3_PYTHON:-}" ]; then
  exec "$RAG_PHASE3_PYTHON" "$root/scripts/phase3-demo/launcher.py" "$@"
fi
if command -v python3.11 >/dev/null 2>&1; then
  exec python3.11 "$root/scripts/phase3-demo/launcher.py" "$@"
fi
if command -v python3.13 >/dev/null 2>&1; then
  exec python3.13 "$root/scripts/phase3-demo/launcher.py" "$@"
fi
printf 'Python 3.11.3 or existing Python 3.13 is required. Select RAG_PHASE3_PYTHON.\n' >&2
exit 1
