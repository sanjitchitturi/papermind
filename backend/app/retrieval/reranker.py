"""
Reranks the top-K hybrid search results down to a smaller top-N that
actually goes into the generation prompt.

We use the generation LLM itself as a pointwise reranker (asking it to
score each candidate's relevance to the question) rather than hosting a
dedicated cross-encoder model. A cross-encoder would be marginally faster,
but it means shipping a ~500MB model and a torch dependency just for this
one step. For the traffic volume a portfolio project actually sees, an
LLM-judge reranker is simpler to deploy and good enough. If this were
scaling to real production traffic, that trade-off would flip and a
hosted cross-encoder would be worth the extra infra.
"""

from app.core.config import get_settings
from app.core.llm import chat_json

settings = get_settings()

RERANK_PROMPT = """Question: {question}

Below are candidate passages from academic papers, each with an id. Score
each passage from 0 to 10 on how directly useful it is for answering the
question. A passage that mentions the topic in passing but doesn't answer
the question should score low.

Passages:
{passages}

Return JSON: {{"scores": {{"<id>": <0-10>, ...}}}}"""


def rerank(question: str, candidates: list[dict]) -> list[dict]:
    if not candidates:
        return []

    passage_lines = []
    for c in candidates:
        text = c["payload"].get("text", "")[:800]  # keep the prompt a reasonable size
        passage_lines.append(f"id={c['id']}: {text}")

    result = chat_json(
        [{"role": "user", "content": RERANK_PROMPT.format(question=question, passages="\n\n".join(passage_lines))}]
    )
    scores = result.get("scores", {})

    def score_for(candidate: dict) -> float:
        # Fall back to the original retrieval score if the judge didn't
        # return a score for this id, better than silently dropping it.
        return float(scores.get(str(candidate["id"]), candidate["score"]))

    ranked = sorted(candidates, key=score_for, reverse=True)
    return ranked[: settings.rerank_top_n]
