"""
Takes the reranked passages and produces a final answer with inline
citations like [1], [2] that map back to the passages used, in the order
they're listed in the sources panel.
"""

from dataclasses import dataclass

from app.core.config import get_settings
from app.core.llm import chat

settings = get_settings()

ANSWER_PROMPT = """You are answering a question using only the passages provided below.
Cite your sources inline using [1], [2], etc. matching the passage numbers.
If the passages don't contain enough information to answer, say so plainly
instead of guessing.

Passages:
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
    text: str


@dataclass
class GeneratedAnswer:
    answer: str
    sources: list[Source]


def generate_answer(question: str, passages: list[dict], temperature: float = 0.2) -> GeneratedAnswer:
    sources = [
        Source(
            index=i + 1,
            chunk_id=p["payload"].get("chunk_id", ""),
            paper_id=p["payload"].get("paper_id", ""),
            paper_title=p["payload"].get("paper_title", ""),
            section=p["payload"].get("section", ""),
            text=p["payload"].get("text", ""),
        )
        for i, p in enumerate(passages)
    ]

    passage_block = "\n\n".join(f"[{s.index}] ({s.paper_title}, {s.section}): {s.text}" for s in sources)
    answer = chat(
        [{"role": "user", "content": ANSWER_PROMPT.format(passages=passage_block, question=question)}],
        temperature=temperature,
    )
    return GeneratedAnswer(answer=answer, sources=sources)
