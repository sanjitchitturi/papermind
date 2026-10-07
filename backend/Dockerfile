FROM python:3.12-slim

# System deps needed by pymupdf and psycopg's binary wheels at runtime are
# minimal, but libpq is still worth having explicitly rather than relying
# on whatever happens to be in the base image.
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

# Storage dir for downloaded/uploaded PDFs. In production this should
# really be object storage (S3-compatible), a local volume is fine for a
# single-instance free-tier deployment.
RUN mkdir -p /app/storage/papers /app/storage/uploads

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
