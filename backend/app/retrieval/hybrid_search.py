"""
Combines query rewriting with Qdrant's hybrid dense+sparse search, and
merges results across the rewritten query variants.

Running one search per rewritten query and merging by max score (rather
than averaging) means a chunk that is a very strong match for even one
phrasing of the question gets surfaced, instead of being pulled down by
being a mediocre match for the others.
"""

from app.core.config import get_settings
from app.core.llm import embed
from app.core.vector_store import hybrid_search as qdrant_hybrid_search
from app.retrieval.query_rewriter import rewrite_query

settings = get_settings()


def retrieve(question: str, paper_id: str | None = None, use_rewriting: bool = True) -> list[dict]:
    queries = rewrite_query(question) if use_rewriting else [question]
    vectors = embed(queries)

    merged: dict[str, dict] = {}
    for query_text, vector in zip(queries, vectors, strict=True):
        hits = qdrant_hybrid_search(vector, query_text, limit=settings.retrieval_top_k, paper_id=paper_id)
        for hit in hits:
            key = str(hit["id"])
            if key not in merged or hit["score"] > merged[key]["score"]:
                merged[key] = hit

    ranked = sorted(merged.values(), key=lambda h: h["score"], reverse=True)
    return ranked[: settings.retrieval_top_k]
