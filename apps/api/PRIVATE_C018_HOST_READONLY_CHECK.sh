#!/usr/bin/env bash
# SSH/Ops READ-ONLY, after approved maintenance window. No Runner invocation,
# Qdrant copy, systemd start, SQL write, secret/config dump, or .env sourcing.
set -euo pipefail
UNIT=${API_UNIT:-rag-finance-api.service}  # candidate, NOT host attested
EXPECTED=93233bfdf25e40684fd9120b82ec19c217695fdb632ed4a1f7d2bb2a3abcb17d
RUNNER=/opt/rag-finance-staging/_RAG_finance_NB22E_v4_outputs/MVP_engine_bundles/$EXPECTED/rag_engine.py
ENGINE_PY=/opt/rag-finance-staging/.venv-onnx-probe/bin/python
ROOT=/opt/rag-finance-staging/RAG_finance
ARTIFACTS=/opt/rag-finance-staging/_RAG_finance_NB22E_v4_outputs
CACHE=/opt/rag-finance-staging/hf/hub
PRODUCT_CONFIG=${PRODUCT_CONFIG:-/etc/rag-finance/phase3-api-private.json}
API_PY=${API_PY:-/opt/rag-finance-staging/phase3/.venv-api/bin/python}

if [[ $(id -u) -ne 0 ]]; then echo 'PRIVILEGED_OPERATOR=REQUIRED'; exit 2; fi
if ! systemctl show "$UNIT" -p LoadState --value 2>/dev/null | grep -qx loaded; then
  echo 'PRODUCT_SERVICE_UNIT=NOT_INSTALLED_OR_UNKNOWN'; exit 2
fi
SVC=$(systemctl show "$UNIT" --property=User --value)
WD=$(systemctl show "$UNIT" --property=WorkingDirectory --value)
if [[ -z "$SVC" || "$SVC" = root || "$SVC" = '0' || -z "$WD" || ! -d "$WD" ]]; then
  echo 'PRODUCT_SERVICE_IDENTITY=NOT_ATTESTED'; exit 2
fi
echo 'PRODUCT_SERVICE_IDENTITY=NONROOT_UNIT_DISCOVERED'
if ! command -v sudo >/dev/null; then
  echo 'NONROOT_ACCOUNT_EXEC=BLOCKED_SUDO_UNAVAILABLE'; exit 2
fi
# Python checks run AS THE ACTUAL nonroot systemd user, not root. Qdrant
# source must be supplied from an independently reviewed engine layout.
sudo -n -u "$SVC" -- env \
  C018_PY="$ENGINE_PY" C018_RUNNER="$RUNNER" C018_ROOT="$ROOT" \
  C018_ARTIFACTS="$ARTIFACTS" C018_HF="$CACHE" \
  QDRANT_STORE="${QDRANT_STORE:-}" \
  /usr/bin/python3 - <<'PY'
import hashlib, os, pathlib, shutil
P=pathlib.Path
expected='93233bfdf25e40684fd9120b82ec19c217695fdb632ed4a1f7d2bb2a3abcb17d'
paths={
 'ENGINE_PY':P(os.environ['C018_PY']),
 'RUNNER':P(os.environ['C018_RUNNER']),
 'REPO':P(os.environ['C018_ROOT']),
 'ARTIFACTS':P(os.environ['C018_ARTIFACTS']),
 'HF_CACHE':P(os.environ['C018_HF']),
}
checks={}
for label,path in paths.items():
  isfile=label in ('ENGINE_PY','RUNNER')
  checks[label]=(path.is_file() if isfile else path.is_dir()) and os.access(
    path, os.R_OK | (os.X_OK if label != 'RUNNER' else 0))
  print(label+'_READABLE='+('PASS' if checks[label] else 'FAIL'))
if checks['RUNNER']:
  with paths['RUNNER'].open('rb') as fp:
    digest=hashlib.file_digest(fp,'sha256').hexdigest()
  checks['SHA256']=(digest==expected)
  print('C018_RUNNER_SHA256='+('PASS' if checks['SHA256'] else 'FAIL'))
else:
  checks['SHA256']=False
  print('C018_RUNNER_SHA256=NOT_CHECKED')
q=os.environ.get('QDRANT_STORE','')
if not q:
  print('QDRANT_COPY_FEASIBILITY=UNKNOWN_SOURCE_NOT_SUPPLIED')
else:
  src=P(q)
  readable=(src.is_dir() and not src.is_symlink() and
            os.access(src,os.R_OK | os.X_OK))
  print('QDRANT_READABLE='+('PASS' if readable else 'FAIL'))
  try:
    # Bounded metadata-only estimate; consistent snapshots need separate approval.
    space=shutil.disk_usage('/tmp').free
    total=0;scanned=0
    if readable:
      for base, dirs, files in os.walk(src,followlinks=False):
        for f in files:
          file=P(base)/f
          if not file.is_symlink():total+=file.stat().st_size
          scanned+=1
          if scanned>10000:raise RuntimeError('scan cap reached')
    capacity=(space>=2*total and total>0)
    print('QDRANT_TEMP_DISK_CAPACITY='+('PASS' if capacity else 'FAIL'))
  except (OSError, RuntimeError):
    print('QDRANT_TEMP_DISK_CAPACITY=NOT_ATTESTED')
  print('QDRANT_CONSISTENT_SNAPSHOT=NOT_ATTESTED')
print('C018_ACCOUNT_ACCESS='+('PASS' if all(checks.values()) else 'BLOCKED'))
PY
# Product --preflight-only makes READ-ONLY DB metadata queries, PKI+RS256,
# and pinned C018 checks. It neither listens nor runs any Runner child.
if [[ ! -x "$API_PY" || ! -f "$PRODUCT_CONFIG" ]]; then
  echo 'PRODUCT_PREFLIGHT=BLOCKED_API_PY_OR_CONFIG_NOT_PROVISIONED';exit 2
fi
if (cd "$WD" && sudo -n -u "$SVC" -- env \
    API_RUNNER_EXECUTION_MODE=NO_DISPATCH_ONLY \
    HF_HUB_CACHE="$CACHE" HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
    "$API_PY" -m apps.api.private_staging_asgi \
    --config "$PRODUCT_CONFIG" --preflight-only) >/dev/null 2>&1; then
  echo 'PRODUCT_PREFLIGHT_REAL_SERVICE_UID=PASS'
else
  echo 'PRODUCT_PREFLIGHT_REAL_SERVICE_UID=BLOCKED';exit 2
fi
