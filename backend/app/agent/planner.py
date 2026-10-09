from app.core.llm import LLMProviderError, chat_json, llm_available

DECOMPOSE_PROMPT = """A user asked a broad research question that likely requires
synthesizing information across multiple papers. Break it into 2 to 4 specific
sub-questions whose answers, combined, would let you address the original question.

Question: {question}

Return JSON: {{"sub_questions": ["...", "..."]}}"""

CRITIQUE_PROMPT = """Decide whether you have gathered enough evidence to write a
well-supported literature review.

Original question: {question}

Evidence so far:
{evidence}

Return JSON: {{"sufficient": true, "missing_sub_question": ""}}"""


def decompose(question: str) -> list[str]:
    if not llm_available():
        return [question]
    try:
        result = chat_json([{"role": "user", "content": DECOMPOSE_PROMPT.format(question=question)}])
    except LLMProviderError:
        return [question]
    sub = [q.strip() for q in result.get("sub_questions", []) if isinstance(q, str) and q.strip()]
    return sub[:4] or [question]


def critique_coverage(question: str, evidence_summaries: list[str]) -> tuple[bool, str | None]:
    if not llm_available():
        return True, None
    evidence = "\n\n".join(evidence_summaries[:16])
    try:
        result = chat_json([{"role": "user", "content": CRITIQUE_PROMPT.format(question=question, evidence=evidence)}])
    except LLMProviderError:
        return True, None
    missing = (result.get("missing_sub_question") or "").strip() or None
    return bool(result.get("sufficient", True)), missing
