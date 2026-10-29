FROM python:3.11-slim-bookworm AS builder

WORKDIR /build

COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

FROM gcr.io/distroless/python3-debian12:debug

WORKDIR /app

# Copie des packages Python depuis le builder
COPY --from=builder /root/.local /root/.local
COPY app.py .

ENV PATH=/root/.local/bin:$PATH
ENV PYTHONPATH=/root/.local/lib/python3.11/site-packages

USER 65532:65532

EXPOSE 5000

ENTRYPOINT ["python", "app.py"]