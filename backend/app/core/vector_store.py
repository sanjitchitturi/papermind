"""
Thin wrapper around Qdrant so the rest of the codebase never has to know
the collection schema or how hybrid search is wired up.

Each point stores two vectors: a dense embedding for semantic similarity
and a sparse BM25 vector for exact term matching (model names, dataset
names, acronyms, the things dense models are worst at). The sparse vector
config uses Qdrant's IDF modifier, so documents carry term frequencies and
Qdrant applies corpus-level IDF at query time, which is what makes it
actual BM25 rather than plain term overlap.

The collection name includes the embedding model and dimension, so
switching models creates a fresh collection instead of mixing vectors from
two embedding spaces.
"""

import re
import threading
from dataclasses import dataclass

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    Fusion,
    FusionQuery,
    MatchAny,
    MatchValue,
    Modifier,
    PayloadSchemaType,
    PointStruct,
    Prefetch,
    SparseVector,
    SparseVectorParams,
    VectorParams,
)

from app.core.config import get_settings
from app.ml.embeddings import SparseVectorData

DENSE = "dense"
SPARSE = "sparse"

_client: QdrantClient | None = None
_lock = threading.Lock()


@dataclass
class Hit:
    id: str
    score: float
    payload: dict


def get_client() -> QdrantClient:
    global _client
    if _client is None:
        with _lock:
            if _client is None:
                settings = get_settings()
                if settings.qdrant_url == ":memory:":
                    _client = QdrantClient(location=":memory:")
                else:
                    _client = QdrantClient(
                        url=settings.qdrant_url,
                        api_key=settings.qdrant_api_key or None,
                        timeout=30,
                        check_compatibility=False,
                    )
    return _client


def reset_client() -> None:
    global _client
    _client = None


def collection_name(embedder_name: str | None = None, dim: int | None = None) -> str:
    from app.ml.embeddings import get_embedder

    if embedder_name is None or dim is None:
        embedder = get_embedder()
        embedder_name, dim = embedder.name, embedder.dim
    slug = re.sub(r"[^a-z0-9]+", "-", embedder_name.lower()).strip("-")
    return f"{get_settings().qdrant_collection_prefix}_chunks_{slug}_{dim}"


def ensure_collection() -> str:
    from app.ml.embeddings import get_embedder

    embedder = get_embedder()
    name = collection_name(embedder.name, embedder.dim)
    client = get_client()
    if client.collection_exists(name):
        return name
    client.create_collection(
        collection_name=name,
        vectors_config={DENSE: VectorParams(size=embedder.dim, distance=Distance.COSINE)},
        sparse_vectors_config={SPARSE: SparseVectorParams(modifier=Modifier.IDF)},
    )
    # Retrieval is often scoped to one or a few papers, an index on the
    # filter field keeps that from degrading into a full scan.
    client.create_payload_index(name, field_name="paper_id", field_schema=PayloadSchemaType.KEYWORD)
    return name


def _sparse(vector: SparseVectorData) -> SparseVector:
    return SparseVector(indices=vector.indices, values=vector.values)


def upsert_points(points: list[dict]) -> None:
    """points: [{id, dense, sparse: SparseVectorData, payload}]"""
    name = collection_name()
    client = get_client()
    for i in range(0, len(points), 64):
        batch = points[i : i + 64]
        client.upsert(
            collection_name=name,
            points=[
                PointStruct(id=p["id"], vector={DENSE: p["dense"], SPARSE: _sparse(p["sparse"])}, payload=p["payload"])
                for p in batch
            ],
        )


def _paper_filter(paper_ids: list[str] | None) -> Filter | None:
    if not paper_ids:
        return None
    if len(paper_ids) == 1:
        return Filter(must=[FieldCondition(key="paper_id", match=MatchValue(value=paper_ids[0]))])
    return Filter(must=[FieldCondition(key="paper_id", match=MatchAny(any=paper_ids))])


def _to_hits(points) -> list[Hit]:
    return [Hit(id=str(p.id), score=float(p.score), payload=p.payload or {}) for p in points]


def hybrid_search(
    dense: list[float], sparse: SparseVectorData, limit: int, paper_ids: list[str] | None = None
) -> list[Hit]:
    """Dense and BM25 candidates fused with reciprocal rank fusion, server-side."""
    query_filter = _paper_filter(paper_ids)
    result = get_client().query_points(
        collection_name=collection_name(),
        prefetch=[
            Prefetch(query=dense, using=DENSE, limit=limit * 2, filter=query_filter),
            Prefetch(query=_sparse(sparse), using=SPARSE, limit=limit * 2, filter=query_filter),
        ],
        query=FusionQuery(fusion=Fusion.RRF),
        limit=limit,
        with_payload=True,
    )
    return _to_hits(result.points)


def dense_search(dense: list[float], limit: int, paper_ids: list[str] | None = None) -> list[Hit]:
    result = get_client().query_points(
        collection_name=collection_name(), query=dense, using=DENSE, limit=limit,
        query_filter=_paper_filter(paper_ids), with_payload=True,
    )
    return _to_hits(result.points)


def sparse_search(sparse: SparseVectorData, limit: int, paper_ids: list[str] | None = None) -> list[Hit]:
    result = get_client().query_points(
        collection_name=collection_name(), query=_sparse(sparse), using=SPARSE, limit=limit,
        query_filter=_paper_filter(paper_ids), with_payload=True,
    )
    return _to_hits(result.points)


def delete_paper(paper_id: str) -> None:
    get_client().delete(
        collection_name=collection_name(),
        points_selector=Filter(must=[FieldCondition(key="paper_id", match=MatchValue(value=paper_id))]),
    )


def count_points() -> int:
    return get_client().count(collection_name=collection_name(), exact=False).count


def healthy() -> bool:
    try:
        get_client().get_collections()
        return True
    except Exception:  # noqa: BLE001
        return False
