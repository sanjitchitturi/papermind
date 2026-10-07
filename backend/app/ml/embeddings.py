"""
Dense and sparse text encoders.

Dense: a small local ONNX model by default (see registry.py), or any
OpenAI-compatible embeddings endpoint when EMBEDDING_MODEL is set to
"openai/<model>". Sparse: BM25 term weights from fastembed, with IDF applied
server-side by Qdrant.

Inference is serialized behind a lock. On a 0.1 CPU container running
two forward passes at once doesn't make anything faster, it only stacks
activation memory, which is what gets a free-tier instance OOM-killed.
"""

import threading
from dataclasses import dataclass
from functools import lru_cache
from typing import Protocol

from app.core.config import get_settings
from app.ml.registry import DENSE_MODELS, register_custom_models


class Embedder(Protocol):
    name: str
    dim: int

    def embed_documents(self, texts: list[str]) -> list[list[float]]: ...

    def embed_query(self, text: str) -> list[float]: ...


class FastEmbedEmbedder:
    def __init__(self, key: str) -> None:
        from fastembed import TextEmbedding

        if key not in DENSE_MODELS:
            raise ValueError(f"Unknown embedding model '{key}'. Known: {sorted(DENSE_MODELS)}")
        settings = get_settings()
        register_custom_models()
        self.spec = DENSE_MODELS[key]
        self.name = key
        self.dim = self.spec.dim
        self._batch_size = settings.ml_batch_size
        self._lock = threading.Lock()
        self._model = TextEmbedding(
            f"papermind/{key}",
            cache_dir=settings.model_cache_dir,
            threads=settings.ml_threads,
            providers=["CPUExecutionProvider"],
            cuda=False,
        )
        # Questions repeat a lot (eval runs, retries, the agent re-asking a
        # sub-question), and a query vector is cheap to keep around.
        self._query_cache = lru_cache(maxsize=64)(self._embed_query_uncached)

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        with self._lock:
            return [v.tolist() for v in self._model.embed(texts, batch_size=self._batch_size)]

    def embed_query(self, text: str) -> list[float]:
        return list(self._query_cache(text))

    def _embed_query_uncached(self, text: str) -> tuple[float, ...]:
        with self._lock:
            vector = next(iter(self._model.embed([self.spec.query_prefix + text])))
        return tuple(vector.tolist())


class OpenAIEmbedder:
    """Remote embeddings through any OpenAI-compatible endpoint."""

    _DIMS = {"text-embedding-3-small": 1536, "text-embedding-3-large": 3072, "text-embedding-ada-002": 1536}

    def __init__(self, model: str) -> None:
        from app.core.llm import get_client

        self.name = f"openai-{model}"
        self.model = model
        self.dim = self._DIMS.get(model, 1536)
        self._client = get_client()

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        vectors: list[list[float]] = []
        for i in range(0, len(texts), 96):
            response = self._client.embeddings.create(model=self.model, input=texts[i : i + 96])
            vectors.extend(item.embedding for item in response.data)
        return vectors

    def embed_query(self, text: str) -> list[float]:
        return self.embed_documents([text])[0]


@dataclass
class SparseVectorData:
    indices: list[int]
    values: list[float]


class SparseEncoder:
    def __init__(self) -> None:
        from fastembed import SparseTextEmbedding

        settings = get_settings()
        self._lock = threading.Lock()
        self._model = SparseTextEmbedding(
            "Qdrant/bm25",
            cache_dir=settings.model_cache_dir,
            threads=settings.ml_threads,
            providers=["CPUExecutionProvider"],
            cuda=False,
        )

    def embed_documents(self, texts: list[str]) -> list[SparseVectorData]:
        with self._lock:
            return [SparseVectorData(r.indices.tolist(), r.values.tolist()) for r in self._model.embed(texts)]

    def embed_query(self, text: str) -> SparseVectorData:
        # BM25 query vectors are binary term indicators, document vectors
        # carry the saturated term frequencies. Using the document encoder
        # for queries silently skews scores toward repeated query words.
        with self._lock:
            result = next(iter(self._model.query_embed(text)))
        return SparseVectorData(result.indices.tolist(), result.values.tolist())


_embedder: Embedder | None = None
_sparse: SparseEncoder | None = None
_init_lock = threading.Lock()


def get_embedder() -> Embedder:
    global _embedder
    if _embedder is None:
        with _init_lock:
            if _embedder is None:
                key = get_settings().embedding_model
                _embedder = OpenAIEmbedder(key.split("/", 1)[1]) if key.startswith("openai/") else FastEmbedEmbedder(key)
    return _embedder


def get_sparse_encoder() -> SparseEncoder:
    global _sparse
    if _sparse is None:
        with _init_lock:
            if _sparse is None:
                _sparse = SparseEncoder()
    return _sparse


def set_encoders(embedder: Embedder | None = None, sparse: SparseEncoder | None = None) -> None:
    """Swap in different encoders, used by tests to avoid loading real models."""
    global _embedder, _sparse
    _embedder = embedder
    _sparse = sparse
