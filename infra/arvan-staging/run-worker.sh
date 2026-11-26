#!/bin/sh
set -eu
stage=/opt/rag-finance-staging
set --
if [ -e "$stage/RAG_finance/.env" ] || [ -L "$stage/RAG_finance/.env" ]; then
  test -f "$stage/RAG_finance/.env"
  test ! -L "$stage/RAG_finance/.env"
  set -- --mount type=bind,src=/dev/null,dst=/work/repo/.env,readonly
fi
exec /usr/bin/docker run --rm --pull=never --name rag-arvan-retrieval \
  --user "$(id -u rag-arvan-api):$(id -g rag-arvan-api)" \
  --init --network none --read-only --cap-drop ALL --security-opt no-new-privileges \
  --pids-limit 256 --cpus 4 --memory 6g --memory-swap 6g \
  --tmpfs /tmp:rw,nosuid,nodev,size=256m \
  --tmpfs /work:rw,nosuid,nodev,size=2g,mode=1777 \
  --mount "type=bind,src=$stage/.venv-onnx-probe,dst=$stage/.venv-onnx-probe,readonly" \
  --mount "type=bind,src=$stage/.python,dst=$stage/.python,readonly" \
  --mount "type=bind,src=$stage/hf,dst=$stage/hf,readonly" \
  --mount "type=bind,src=$stage/RAG_finance,dst=/work/repo,readonly" \
  "$@" \
  --mount "type=bind,src=$stage/_RAG_finance_NB22E_v4_outputs,dst=/inputs/artifacts,readonly" \
  --mount type=bind,src=/run/rag-arvan-worker,dst=/ipc \
  rag-nb23-worker:arvan-cp45 /work/repo /inputs/artifacts --socket /ipc/retrieval.sock
