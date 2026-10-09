from dataclasses import dataclass

from app.core.config import get_settings
from app.core.llm import LLMUnavailable, chat_json, llm_available
from app.core.vector_store import Hit, dense_search, hybrid_search, sparse_search
from app.ml.embeddings import get_embedder, get_sparse_encoder
from app.ml.reranker import get_reranker, sigmoid

REWRITE_PROMPT = """You are writing search queries over academic papers.
Given a question, produce 1 to 3 short alternative queries that would retrieve
relevant passages. Include the original if it is already a good search query.

Return JSON: {{"queries": ["...", "..."]}}

Question: {question}"""


@dataclass
class Passage:
    chunk_id: str
    paper_id: str
    paper_title: str
    arxiv_id: str
    section: str
    page: int
    text: str
    fused_score: float
    rerank_logit: float | None
    rerank_prob: float | None


def rewrite_query(question: str) -> list[str]:
    if not llm_available():
        return [question]
    try:
        result = chat_json([{"role": "user", "content": REWRITE_PROMPT.format(question=question)}])
    except (LLMUnavailable, Exception):  # noqa: BLE001
        return [question]
    queries = [q.strip() for q in result.get("queries", []) if isinstance(q, str) and q.strip()]
    return (queries or [question])[:3]


def retrieve(
    question: str,
    paper_ids: list[str] | None = None,
    use_rewriting: bool = True,
    use_hybrid: bool = True,
    use_reranker: bool = True,
    limit: int | None = None,
) -> list[Passage]:
    settings = get_settings()
    candidates = limit or settings.retrieval_candidates
    queries = rewrite_query(question) if use_rewriting else [question]
    embedder = get_embedder()
    sparse_encoder = get_sparse_encoder()

    merged: dict[str, Hit] = {}
    for query in queries:
        dense = embedder.embed_query(query)
        if use_hybrid:
            sparse = sparse_encoder.embed_query(query)
            hits = hybrid_search(dense, sparse, limit=candidates, paper_ids=paper_ids)
        else:
            hits = dense_search(dense, limit=candidates, paper_ids=paper_ids)
        for hit in hits:
            if hit.id not in merged or hit.score > merged[hit.id].score:
                merged[hit.id] = hit

    ranked = sorted(merged.values(), key=lambda h: h.score, reverse=True)[:candidates]
    passages = [_to_passage(h) for h in ranked]
    if use_reranker:
        try:
            passages = rerank_passages(question, passages)
        except Exception:  # noqa: BLE001
            # Free-tier boxes OOM if the cross-encoder loads on top of the
            # embedder. Hybrid RRF still returns a ranked list.
            pass
    return passages[: settings.context_passages]


def retrieve_hits_only(question: str, use_hybrid: bool, paper_ids: list[str] | None = None, limit: int = 24) -> list[Hit]:
    """Used by the retrieval eval, which wants the ranked list before context truncation."""
    embedder = get_embedder()
    dense = embedder.embed_query(question)
    if use_hybrid:
        sparse = get_sparse_encoder().embed_query(question)
        return hybrid_search(dense, sparse, limit=limit, paper_ids=paper_ids)
    return dense_search(dense, limit=limit, paper_ids=paper_ids)


def rerank_passages(question: str, passages: list[Passage]) -> list[Passage]:
    settings = get_settings()
    reranker = get_reranker()
    if reranker is None or not passages:
        return passages
    scored = passages[: settings.rerank_candidates]
    logits = reranker.score(question, [p.text for p in scored])
    for passage, logit in zip(scored, logits, strict=True):
        passage.rerank_logit = logit
        passage.rerank_prob = sigmoid(logit)
    scored.sort(key=lambda p: p.rerank_logit if p.rerank_logit is not None else p.fused_score, reverse=True)
    return scored


def retrieval_margin(passages: list[Passage]) -> float:
    """
    How clearly the top result beats the rest, using rerank probabilities
    when they exist. A tiny margin means the retriever is unsure which
    passage is actually about the question.
    """
    scores = [
        (p.rerank_prob if p.rerank_prob is not None else p.fused_score) for p in passages
    ]
    if len(scores) < 2:
        return 0.5
    top, rest = scores[0], scores[1:]
    rest_avg = sum(rest) / len(rest)
    span = max(top, 1e-6)
    return max(0.0, min(1.0, (top - rest_avg) / span))


def _to_passage(hit: Hit) -> Passage:
    payload = hit.payload
    return Passage(
        chunk_id=str(payload.get("chunk_id", "")),
        paper_id=str(payload.get("paper_id", "")),
        paper_title=str(payload.get("paper_title", "")),
        arxiv_id=str(payload.get("arxiv_id", "")),
        section=str(payload.get("section", "")),
        page=int(payload.get("page") or 1),
        text=str(payload.get("text", "")),
        fused_score=hit.score,
        rerank_logit=None,
        rerank_prob=None,
    )


def sparse_only(question: str, limit: int = 24, paper_ids: list[str] | None = None) -> list[Hit]:
    sparse = get_sparse_encoder().embed_query(question)
    return sparse_search(sparse, limit=limit, paper_ids=paper_ids)
