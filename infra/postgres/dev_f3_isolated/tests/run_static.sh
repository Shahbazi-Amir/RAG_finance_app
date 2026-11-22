#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
python3 tests/test_static.py
case_dir="$(mktemp -d)"
trap 'rm -rf "$case_dir"' EXIT
if LAB_ROOT="$case_dir/CENTRAL_FIRST_START_20261121/protected" SOURCE_REPO="$case_dir/fake" bash scripts/00_prepare_source.sh > "$case_dir/guard.log" 2>&1; then echo 'STATIC_FAIL_PROTECTED_PATH_ACCEPTED'; exit 1; fi
grep -Fq STOP_PROTECTED_PATH "$case_dir/guard.log"
echo 'STATIC_FAIL_CLOSED_DEMO_DIRECTORY=PASS'
