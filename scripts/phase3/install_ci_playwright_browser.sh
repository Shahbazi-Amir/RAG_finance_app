#!/usr/bin/env bash
# CI-only bounded install retries. Never bypass dependency or browser failures.
set -euo pipefail
[[ "${CI:-}" == true && "${GITHUB_ACTIONS:-}" == true ]] || { echo CI_ONLY_BROWSER_INSTALL; exit 70; }
[[ "$#" == 1 ]] || exit 64
case "$1" in chromium|firefox|webkit) ;; *) exit 64;; esac
engine="$1"
for attempt in 1 2 3; do
  if python -m playwright install --with-deps "$engine"; then
    echo "F3_BROWSER_DEPENDENCY_INSTALL_PASS engine=$engine attempt=$attempt"
    exit 0
  fi
  echo "F3_BROWSER_DEPENDENCY_INSTALL_RETRY engine=$engine attempt=$attempt" >&2
  if [[ "$attempt" != 3 ]]; then sleep "$((attempt * 5))"; fi
done
echo "F3_BROWSER_DEPENDENCY_INSTALL_FAILED engine=$engine" >&2
exit 1
