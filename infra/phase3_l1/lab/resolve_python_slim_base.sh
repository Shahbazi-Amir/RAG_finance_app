#!/usr/bin/env bash
# CI-only: resolve candidate base tag to actual registry digest; never deploy.
set -euo pipefail
[[ "${GITHUB_ACTIONS:-}" == true && "${RUNNER_OS:-}" == Linux ]] || exit 70
tag=docker.io/library/python:3.13.5-slim-bookworm
docker pull --platform linux/amd64 "$tag" >&2
ref="$(docker image inspect "$tag" --format '{{range .RepoDigests}}{{println .}}{{end}}' | grep -E '^(python|docker.io/library/python)@sha256:[a-f0-9]{64}$' | sort -u)"
[[ "$ref" =~ ^(python|docker.io/library/python)@sha256:[a-f0-9]{64}$ ]] || exit 70
ref="docker.io/library/python@${ref#*@}"
docker run --rm --network none --platform linux/amd64 "$ref" python3 -c 'import sys; assert sys.version_info[:3] == (3,13,5)' >&2
echo "F3_LAB_PYTHON_BASE=$ref" >&2
printf '%s\n' "$ref"
