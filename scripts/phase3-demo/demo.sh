#!/bin/sh
# Run from any working directory within a normal repository checkout.
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
if command -v python3.13 >/dev/null 2>&1; then
  exec python3.13 "$root/scripts/phase3-demo/launcher.py" "$@"
fi
if command -v python3 >/dev/null 2>&1; then
  exec python3 "$root/scripts/phase3-demo/launcher.py" "$@"
fi
printf 'Python 3.13 is required (brew install python@3.13)\n' >&2
exit 1
