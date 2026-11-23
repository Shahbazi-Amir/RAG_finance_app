#!/usr/bin/env python3
"""Read-only Engine mount/runtime probe. NEVER import/execute rag_engine.py."""
from __future__ import annotations
import hashlib
import os
import pathlib
import subprocess
import sys

ROOT = pathlib.Path('/opt/rag-finance-staging')
RUNNER = ROOT / '_RAG_finance_NB22E_v4_outputs/MVP_engine_bundles/93233bfdf25e40684fd9120b82ec19c217695fdb632ed4a1f7d2bb2a3abcb17d/rag_engine.py'
SHA = '93233bfdf25e40684fd9120b82ec19c217695fdb632ed4a1f7d2bb2a3abcb17d'
PYTHON = ROOT / '.venv-onnx-probe/bin/python'
INDEX = ROOT / 'RAG_finance/data/phase2/index/dense_index_v1/qdrant'

def main():
    if not all(p.is_dir() for p in (ROOT / 'RAG_finance', ROOT / '_RAG_finance_NB22E_v4_outputs', ROOT / 'hf/hub', INDEX)):
        return 2
    if not RUNNER.is_file() or not PYTHON.is_file() or not os.access(PYTHON, os.X_OK):
        return 2
    if hashlib.sha256(RUNNER.read_bytes()).hexdigest() != SHA:
        return 2
    # Metadata/version import only: never open embedded Qdrant collection or invoke Runner.
    test = subprocess.run([str(PYTHON), '-c',
       'import sys; from importlib.metadata import version; '
       'assert sys.version_info[:3] == (3,11,18); '
       'assert version("qdrant-client") == "1.18.0"'],
       capture_output=True, timeout=90, check=False)
    return 0 if test.returncode == 0 else 2

if __name__ == '__main__':
    try: sys.exit(main())
    except (OSError, ValueError, subprocess.TimeoutExpired): sys.exit(2)
