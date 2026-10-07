"""
Thin wrapper around Qdrant so the rest of the codebase never has to know
the collection schema or how hybrid search is wired up.

We store two vectors per point: a dense OpenAI embedding for semantic
similarity, and a sparse BM25 vector (via fastembed) for exact keyword
matching. Qdrant fuses the two with RRF, which is what makes the hybrid
search differentiator from the plan actually work.
"""

from fastembed import SparseTextEmbedding
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    Fusion,
    FusionQuery,
    PointStruct,
    Prefetch,
    SparseVector,
    SparseVectorParams,
    VectorParams,
)

from app.core.config import get_settings

settings = get_settings()

DENSE_VECTOR_NAME = "dense"
SPARSE_VECTOR_NAME = "sparse"
DENSE_VECTOR_SIZE = 1536  # text-embedding-3-small output size

_client: QdrantClient | None = None
_sparse_model: SparseTextEmbedding | None = None


def get_client() -> QdrantClient:
    global _client
    if _client is None:
        _client = QdrantClient(url=settings.qdrant_url, api_key=settings.qdrant_api_key)
    return _client


def get_sparse_model() -> SparseTextEmbedding:
    # Loaded lazily and cached because it pulls model weights on first use.
    global _sparse_model
    if _sparse_model is None:
        _sparse_model = SparseTextEmbedding(model_name="Qdrant/bm25")
    return _sparse_model


def ensure_collection() -> None:
    client = get_client()
    existing = {c.name for c in client.get_collections().collections}
    if settings.qdrant_collection in existing:
        return
    client.create_collection(
        collection_name=settings.qdrant_collection,
        vectors_config={DENSE_VECTOR_NAME: VectorParams(size=DENSE_VECTOR_SIZE, distance=Distance.COSINE)},
        sparse_vectors_config={SPARSE_VECTOR_NAME: SparseVectorParams()},
    )


def sparse_embed(text: str) -> SparseVector:
    model = get_sparse_model()
    result = next(model.embed([text]))
    return SparseVector(indices=result.indices.tolist(), values=result.values.tolist())


def upsert_chunks(points: list[dict]) -> None:
    """
    points: list of {id, dense_vector, text, payload} dicts.
    Sparse vectors are computed here so callers only ever deal with text.
    """
    client = get_client()
    structs = []
    for p in points:
        sparse = sparse_embed(p["text"])
        structs.append(
            PointStruct(
                id=p["id"],
                vector={DENSE_VECTOR_NAME: p["dense_vector"], SPARSE_VECTOR_NAME: sparse},
                payload=p["payload"],
            )
        )
    client.upsert(collection_name=settings.qdrant_collection, points=structs)


def hybrid_search(dense_vector: list[float], query_text: str, limit: int, paper_id: str | None = None) -> list[dict]:
    """
    Runs dense + sparse search and fuses with RRF server-side. Optionally
    filters to a single paper (used when the user is chatting with one
    specific paper rather than the whole library).
    """
    client = get_client()
    query_filter = None
    if paper_id:
        from qdrant_client.models import FieldCondition, Filter, MatchValue

        query_filter = Filter(must=[FieldCondition(key="paper_id", match=MatchValue(value=paper_id))])

    sparse = sparse_embed(query_text)
    result = client.query_points(
        collection_name=settings.qdrant_collection,
        prefetch=[
            Prefetch(query=dense_vector, using=DENSE_VECTOR_NAME, limit=limit * 2, filter=query_filter),
            Prefetch(query=sparse, using=SPARSE_VECTOR_NAME, limit=limit * 2, filter=query_filter),
        ],
        query=FusionQuery(fusion=Fusion.RRF),
        limit=limit,
        filter=query_filter,
    )
    return [{"id": pt.id, "score": pt.score, "payload": pt.payload} for pt in result.points]
