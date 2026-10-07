"""
The planning half of the agentic Research Mode: turning one broad
question into sub-questions, and judging whether retrieved evidence is
enough to answer confidently yet.
"""

from app.core.llm import chat_json

DECOMPOSE_PROMPT = """A user asked a broad research question that likely requires
synthesizing information across multiple papers. Break it into 2 to 4 specific
sub-questions whose answers, combined, would let you address the original question.

Question: {question}

Return JSON: {{"sub_questions": ["...", "..."]}}"""

CRITIQUE_PROMPT = """You are deciding whether you have gathered enough evidence to
answer a research question well.

Original question: {question}

Evidence gathered so far (passages from papers):
{evidence}

Is this enough to write a well-supported literature review answering the question,
or is important information clearly missing? If missing, suggest one additional
sub-question to look into.

Return JSON: {{"sufficient": true|false, "missing_sub_question": "..." }}"""


def decompose(question: str) -> list[str]:
    result = chat_json([{"role": "user", "content": DECOMPOSE_PROMPT.format(question=question)}])
    sub_questions = [q.strip() for q in result.get("sub_questions", []) if q.strip()]
    return sub_questions or [question]


def critique_coverage(question: str, evidence_summaries: list[str]) -> tuple[bool, str | None]:
    evidence_block = "\n\n".join(evidence_summaries)
    result = chat_json([{"role": "user", "content": CRITIQUE_PROMPT.format(question=question, evidence=evidence_block)}])
    sufficient = bool(result.get("sufficient", True))
    missing = (result.get("missing_sub_question") or "").strip() or None
    return sufficient, missing
