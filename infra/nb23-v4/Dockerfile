FROM rag-finance-f3/api:mac-first-start-dense-c90cfa7
COPY --chmod=0444 worker.py engine.py /opt/nb23-v4/
ENTRYPOINT ["/opt/rag-finance-staging/.venv-onnx-probe/bin/python", "-B", "/opt/nb23-v4/worker.py", "/opt/nb23-v4/engine.py", "/tmp/repo", "/inputs/artifacts"]
