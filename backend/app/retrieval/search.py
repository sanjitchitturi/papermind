"""Deterministic BM25 over persisted chunks. No model downloads or external index.

The corpus is intentionally bounded by max_papers/max_pdf_pages. Statistics are
computed from SQLite on each query so uploads and deletes are visible immediately.
"""

import math
import re
from collections import Counter
from dataclasses import dataclass

from sqlmodel import Session, select

from app.db.models import Chunk, Paper
from app.db.session import engine

_STOPWORDS = frozenset(
    "a an and are as at be by can do does for from how i in is it of on or that the their this to was were what when where which who why with".split()
)


def tokenize(text: str) -> list[str]:
    return [
        word
        for word in re.findall(r"[^\W_]+(?:-[^\W_]+)*", text.casefold())
        if word not in _STOPWORDS and len(word) > 1
    ]


@dataclass
class Hit:
    id: str
    score: float
    payload: dict


def search(query: str, paper_ids: list[str] | None = None, limit: int = 24) -> list[Hit]:
    terms = set(tokenize(query))
    if not terms:
        return []
    with Session(engine) as session:
        rows = session.exec(select(Chunk, Paper).join(Paper, Chunk.paper_id == Paper.id)).all()
        if paper_ids:
            rows = [(c, p) for c, p in rows if str(p.id) in paper_ids]
        if not rows:
            return []
        counts = [Counter(tokenize(c.text)) for c, _ in rows]
        lengths = [sum(c.values()) for c in counts]
        average = max(sum(lengths) / len(rows), 1)
        df = {term: sum(term in words for words in counts) for term in terms}
        hits = []
        for (chunk, paper), words, length in zip(rows, counts, lengths, strict=True):
            score = 0.0
            for term in terms:
                frequency = words[term]
                if frequency:
                    idf = math.log(1 + (len(rows) - df[term] + 0.5) / (df[term] + 0.5))
                    score += idf * frequency * 2.2 / (frequency + 1.2 * (0.25 + 0.75 * length / average))
            if score > 0:
                hits.append(
                    Hit(
                        str(chunk.id),
                        score,
                        {
                            "chunk_id": str(chunk.id),
                            "paper_id": str(paper.id),
                            "paper_title": paper.title,
                            "arxiv_id": paper.arxiv_id or "",
                            "section": chunk.section,
                            "page": chunk.page_start,
                            "text": chunk.text,
                        },
                    )
                )
        return sorted(hits, key=lambda h: (-h.score, h.id))[:limit]
