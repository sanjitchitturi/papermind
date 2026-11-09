"""Passage retrieval using local BM25; optional query rewriting uses the configured LLM."""

from dataclasses import dataclass

from app.core.config import get_settings
from app.core.llm import LLMProviderError, LLMUnavailable, chat_json, llm_available
from app.retrieval.search import Hit, search


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
    rerank_logit: float | None = None
    rerank_prob: float | None = None


def rewrite_query(question: str) -> list[str]:
    if not llm_available():
        return [question]
    try:
        result = chat_json(
            [
                {
                    "role": "user",
                    "content": 'Return JSON {"queries": ["short query"]} with at most two alternate search queries for: '
                    + question,
                }
            ]
        )
    except (LLMProviderError, LLMUnavailable):
        return [question]
    values = result.get("queries", [])
    if not isinstance(values, list):
        return [question]
    return [question, *[q.strip() for q in values if isinstance(q, str) and q.strip()][:2]]


def retrieve(
    question: str,
    paper_ids: list[str] | None = None,
    use_rewriting: bool = True,
    limit: int | None = None,
) -> list[Passage]:
    settings = get_settings()
    queries = rewrite_query(question) if use_rewriting else [question]
    merged: dict[str, Hit] = {}
    for query in queries:
        for hit in search(query, paper_ids=paper_ids, limit=limit or settings.retrieval_candidates):
            if hit.id not in merged or hit.score > merged[hit.id].score:
                merged[hit.id] = hit
    ranked = sorted(merged.values(), key=lambda h: (-h.score, h.id))
    return [_to_passage(hit) for hit in ranked[: settings.context_passages]]


def retrieval_margin(passages: list[Passage]) -> float:
    if not passages:
        return 0.0
    scores = [p.rerank_prob if p.rerank_prob is not None else p.fused_score for p in passages]
    if len(scores) == 1:
        return 0.5
    return max(0.0, min(1.0, (scores[0] - sum(scores[1:]) / len(scores[1:])) / max(scores[0], 1e-6)))


def _to_passage(hit: Hit) -> Passage:
    p = hit.payload
    return Passage(
        chunk_id=p["chunk_id"],
        paper_id=p["paper_id"],
        paper_title=p["paper_title"],
        arxiv_id=p["arxiv_id"],
        section=p["section"],
        page=p["page"],
        text=p["text"],
        fused_score=hit.score,
    )
