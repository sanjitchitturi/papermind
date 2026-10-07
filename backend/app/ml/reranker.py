"""
Cross-encoder reranking.

A bi-encoder (the dense embedder) scores query and passage independently,
which is what makes it fast enough for first-stage retrieval over the whole
corpus. A cross-encoder reads the query and passage together, so it catches
things like negation and which entity a sentence is actually about, at the
cost of one forward pass per candidate. Running it only on the top ~12
fused candidates keeps that cost bounded.

MS MARCO cross-encoders output an unbounded relevance logit. The sigmoid of
that logit is used downstream as a rough probability that the passage is
relevant, and feeds the trust score.
"""

import math
import threading
from typing import Protocol

from app.core.config import get_settings
from app.ml.registry import RERANKERS, register_custom_models


def sigmoid(x: float) -> float:
    if x >= 0:
        return 1.0 / (1.0 + math.exp(-x))
    z = math.exp(x)
    return z / (1.0 + z)


class Reranker(Protocol):
    name: str

    def score(self, query: str, passages: list[str]) -> list[float]: ...


class CrossEncoderReranker:
    # The model truncates at 512 tokens anyway, trimming beforehand keeps
    # tokenization and padding cheap on long chunks.
    max_passage_chars = 1600

    def __init__(self, key: str) -> None:
        from fastembed.rerank.cross_encoder import TextCrossEncoder

        if key not in RERANKERS:
            raise ValueError(f"Unknown reranker '{key}'. Known: {sorted(RERANKERS)}")
        settings = get_settings()
        register_custom_models()
        self.name = key
        self._batch_size = settings.ml_batch_size
        self._lock = threading.Lock()
        self._model = TextCrossEncoder(
            f"papermind/{key}", cache_dir=settings.model_cache_dir, threads=settings.ml_threads
        )

    def score(self, query: str, passages: list[str]) -> list[float]:
        if not passages:
            return []
        trimmed = [p[: self.max_passage_chars] for p in passages]
        with self._lock:
            return [float(s) for s in self._model.rerank(query, trimmed, batch_size=self._batch_size)]


_reranker: Reranker | None = None
_reranker_loaded = False
_init_lock = threading.Lock()


def get_reranker() -> Reranker | None:
    """Returns None when reranking is disabled via an empty RERANKER_MODEL."""
    global _reranker, _reranker_loaded
    if not _reranker_loaded:
        with _init_lock:
            if not _reranker_loaded:
                key = get_settings().reranker_model.strip()
                _reranker = CrossEncoderReranker(key) if key else None
                _reranker_loaded = True
    return _reranker


def set_reranker(reranker: Reranker | None) -> None:
    global _reranker, _reranker_loaded
    _reranker = reranker
    _reranker_loaded = True
