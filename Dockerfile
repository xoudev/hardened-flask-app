# Stage 1 : Builder Chainguard (contient l'outillage pip et dev)
FROM cgr.dev/chainguard/python:latest-dev@sha256:6b7c43c25f9446e8b1cf850797826a3d40b7cccdc6370c6e1b31cb28adae0a18 AS builder

WORKDIR /app

RUN python -m venv /home/nonroot/venv
ENV PATH="/home/nonroot/venv/bin:$PATH"

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Stage 2 : Runtime minimale Chainguard (Zero-CVE)
FROM cgr.dev/chainguard/python@sha256:a57ac9d33d8ca6eb2946d1d7e93a5600153d02e0c7c1fa3a322fc343f89451f5

WORKDIR /app

COPY --from=builder /home/nonroot/venv /home/nonroot/venv
COPY app/ ./app/

ENV PATH="/home/nonroot/venv/bin:$PATH"

USER 65532:65532

EXPOSE 5000

ENTRYPOINT ["/home/nonroot/venv/bin/python", "-m", "app"]