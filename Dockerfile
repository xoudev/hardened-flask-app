# Stage 1 : Builder Chainguard (contient l'outillage pip et dev)
FROM cgr.dev/chainguard/python:latest-dev AS builder

WORKDIR /app

RUN python -m venv /home/nonroot/venv
ENV PATH="/home/nonroot/venv/bin:$PATH"

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Stage 2 : Runtime minimale Chainguard (Zero-CVE)
FROM cgr.dev/chainguard/python:latest

WORKDIR /app


COPY --from=builder /home/nonroot/venv /home/nonroot/venv
COPY app.py .

ENV PATH="/home/nonroot/venv/bin:$PATH"
ENV PYTHONPATH="/home/nonroot/venv/lib/python3.12/site-packages"

USER 65532:65532

EXPOSE 5000

ENTRYPOINT ["/home/nonroot/venv/bin/python", "app.py"]