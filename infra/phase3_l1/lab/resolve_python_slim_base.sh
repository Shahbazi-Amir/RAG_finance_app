#!/usr/bin/env bash
# CI-only: resolve candidate base tag to actual registry digest; never deploy.
set -euo pipefail
[[ "${GITHUB_ACTIONS:-}" == true && "${RUNNER_OS:-}" == Linux ]] || exit 70
# Exact digest observed in both successful CI jobs on ffdbf03a.
ref=docker.io/library/python@sha256:4c2cf9917bd1cbacc5e9b07320025bdb7cdf2df7b0ceaccb55e9dd7e30987419
docker pull --platform linux/amd64 "$ref" >&2
docker run --rm --network none --platform linux/amd64 "$ref" python3 -c 'import sys; assert sys.version_info[:3] == (3,13,5)' >&2
echo "F3_LAB_PYTHON_BASE=$ref" >&2
printf '%s\n' "$ref"
