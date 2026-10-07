"""
Produces an answer from retrieved passages.

When an LLM is configured, the answer is generated with inline citations
that map to the numbered sources. When it isn't, we fall back to an
extractive answer: the highest-scoring passages, quoted, with enough
context that the user can still use the system as a search engine.
"""

import logging
from dataclasses import dataclass

from app.core.llm import LLMProviderError, chat, llm_available

logger = logging.getLogger(__name__)
from app.retrieval.hybrid_search import Passage

ANSWER_SYSTEM = """You are a research assistant answering questions from academic papers.
Use only the numbered passages. Cite them inline as [1], [2], matching the passage numbers.
If the passages do not contain enough information, say so instead of guessing.
Be precise. Prefer quoting numbers, method names, and claims as they appear."""

ANSWER_PROMPT = """Passages:
{passages}

Question: {question}

Answer with inline citations:"""


@dataclass
class Source:
    index: int
    chunk_id: str
    paper_id: str
    paper_title: str
    section: str
    page: int
    text: str


@dataclass
class GeneratedAnswer:
    answer: str
    sources: list[Source]
    mode: str  # "generative" | "extractive"


def generate_answer(question: str, passages: list[Passage], temperature: float = 0.2) -> GeneratedAnswer:
    sources = [
        Source(
            index=i + 1,
            chunk_id=p.chunk_id,
            paper_id=p.paper_id,
            paper_title=p.paper_title,
            section=p.section,
            page=p.page,
            text=p.text,
        )
        for i, p in enumerate(passages)
    ]
    if not sources:
        return GeneratedAnswer(answer="No relevant passages were found in the library.", sources=[], mode="extractive")
    if llm_available():
        block = "\n\n".join(
            f"[{s.index}] ({s.paper_title}, {s.section}, p.{s.page}): {s.text}" for s in sources
        )
        try:
            answer = chat(
                [{"role": "user", "content": ANSWER_PROMPT.format(passages=block, question=question)}],
                temperature=temperature,
                system=ANSWER_SYSTEM,
            )
            return GeneratedAnswer(answer=answer, sources=sources, mode="generative")
        except LLMProviderError as exc:
            logger.warning("generation failed, falling back to extractive quotes: %s", exc)
    return GeneratedAnswer(answer=_extractive(question, sources), sources=sources, mode="extractive")


def _extractive(question: str, sources: list[Source]) -> str:
    lines = [
        "No language model is configured, so this is an extractive answer: the most relevant passages, quoted.",
        f'Question: "{question}"',
        "",
    ]
    for source in sources[:4]:
        excerpt = source.text.strip()
        if len(excerpt) > 700:
            excerpt = excerpt[:700].rsplit(" ", 1)[0] + "..."
        lines.append(f"[{source.index}] {source.paper_title} · {source.section}, p.{source.page}")
        lines.append(excerpt)
        lines.append("")
    return "\n".join(lines).strip()
