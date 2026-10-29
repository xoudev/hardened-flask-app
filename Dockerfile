FROM python:3.11-slim-bookworm AS builder

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

FROM gcr.io/distroless/python3-debian12:latest

WORKDIR /app

COPY --from=builder /install /usr/local
COPY app.py .

ENV PYTHONPATH=/usr/local/lib/python3.11/site-packages
ENV PYTHONUNBUFFERED=1

USER nonroot

EXPOSE 5000

ENTRYPOINT ["/usr/bin/python3", "app.py"]