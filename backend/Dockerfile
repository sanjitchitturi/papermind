FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    MODEL_CACHE_DIR=/app/.models \
    HF_HUB_DISABLE_TELEMETRY=1 \
    OMP_NUM_THREADS=1 \
    MKL_NUM_THREADS=1 \
    OPENBLAS_NUM_THREADS=1 \
    NUMEXPR_NUM_THREADS=1 \
    MALLOC_ARENA_MAX=2 \
    ONNXRUNTIME_EXECUTION_PROVIDERS=CPUExecutionProvider

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Bake the int8 ONNX weights into the image so a free-tier cold start does
# not download 50 MB of models on the first request.
COPY app ./app
COPY migrations ./migrations
COPY alembic.ini ./alembic.ini
# Cache both ONNX models. Production still refuses to load the reranker
# when LOW_MEMORY=true, but a local container can turn it on without a download.
RUN python - <<'PY'
from app.ml.embeddings import get_embedder, get_sparse_encoder
from app.ml.reranker import get_reranker
get_embedder()
get_sparse_encoder()
get_reranker()
print("models cached")
PY

COPY scripts ./scripts
RUN mkdir -p /app/storage/papers /app/storage/uploads

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
