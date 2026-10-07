"""
Expands a user question into a small set of retrieval queries.

The point of this step is that users ask questions in their own words,
which don't always match the vocabulary a paper uses. "How does the model
avoid overfitting" and "regularization techniques" might both be good
retrieval queries for the same underlying question, and generating a
couple of variants before searching catches cases a single query would
miss.
"""

from app.core.llm import chat_json

REWRITE_PROMPT = """You are helping retrieve relevant passages from academic papers.
Given a user's question, produce 1 to 3 alternative search queries that would help
find relevant passages. Include the original question as one of them if it is
already a good search query. Keep each query short, like a search query, not a
full sentence.

Return JSON: {{"queries": ["...", "..."]}}

Question: {question}"""


def rewrite_query(question: str) -> list[str]:
    result = chat_json([{"role": "user", "content": REWRITE_PROMPT.format(question=question)}])
    queries = result.get("queries") or []
    # Always fall back to the raw question if the LLM call failed or
    # returned something unusable, retrieval should never be fully blocked
    # by this optional step.
    if not queries:
        queries = [question]
    return queries[:3]
