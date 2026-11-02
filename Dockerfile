# Stage 1 : Builder Chainguard (contient l'outillage pip et dev)
FROM cgr.dev/chainguard/python:latest-dev@sha256:8a5780972067cfba4592b10e786a889807ed876c1100f89410fd0ed4e398992c AS builder

WORKDIR /app

RUN python -m venv /home/nonroot/venv
ENV PATH="/home/nonroot/venv/bin:$PATH"

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Stage 2 : Runtime minimale Chainguard (Zero-CVE)
FROM cgr.dev/chainguard/python@sha256:60e3c0d33ab77e50ace0850ccdf6eaec825ce89dad9b1ec2b0300a2070892b05

WORKDIR /app

COPY --from=builder /home/nonroot/venv /home/nonroot/venv
COPY app/ ./app/

ENV PATH="/home/nonroot/venv/bin:$PATH"

USER 65532:65532

EXPOSE 5000

ENTRYPOINT ["/home/nonroot/venv/bin/python", "-m", "app"]