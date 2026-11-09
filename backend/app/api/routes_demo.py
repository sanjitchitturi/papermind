"""Authored example notes for an offline, repeatable first-run demonstration."""

from threading import Lock
from uuid import uuid4

from fastapi import APIRouter, HTTPException
from sqlmodel import select

from app.api.deps import SessionDep
from app.core.config import get_settings
from app.db.models import Chunk, Paper, PaperSource
from app.graph.graph_builder import build_for_paper

router = APIRouter(prefix="/demo", tags=["demo"])
_lock = Lock()
NOTES = [
    (
        "Sample note: Attention and sequence models",
        """Sample research note written for the PaperMind demo, not a published paper.
Attention lets a sequence model compare positions when building contextual representations. A transformer uses self-attention to combine information across a sequence. Multi-head attention computes several comparisons in parallel. This example discusses machine translation and language modeling without claiming benchmark results. Attention can connect distant words, but a useful comparison also considers compute, training data, and evaluation conditions. BLEU measures translation overlap and does not prove factual accuracy. These sample notes are for testing search, citations, and graph exploration only.""",
    ),
    (
        "Sample note: Retrieval and grounded answers",
        """Sample research note written for the PaperMind demo, not a published paper.
Retrieval-augmented question answering first searches a document library for evidence. BM25 ranks passages using query terms, term frequency, document length, and inverse document frequency. A generated answer can cite passages, but the presence of a citation does not establish that the claim is supported. Extractive answers quote the retrieved text directly. MRR and NDCG measure ranking against labeled relevance judgments. Search quality depends on the collection and queries. A keyword search may miss synonyms or semantically related passages. No numerical benchmark claims are made in this example.""",
    ),
    (
        "Sample note: Evaluating research evidence",
        """Sample research note written for the PaperMind demo, not a published paper.
A careful literature review compares methods, datasets, evaluation metrics, and limitations. Question answering studies may report F1 and exact match on SQuAD, while translation studies may use BLEU. Scores from different datasets are not directly comparable. A knowledge graph can connect papers that mention the same dataset or method, including transformer and attention. Shared keywords are useful navigation aids; they do not prove that two papers agree. Citation support and contradiction judgments require reading the surrounding evidence. This note is a fictional teaching example with no experimental results.""",
    ),
]


@router.post("/seed")
def seed(session: SessionDep):
    with _lock:
        existing = {paper.title for paper in session.exec(select(Paper)).all()}
        missing = [(title, text) for title, text in NOTES if title not in existing]
        if len(existing) + len(missing) > get_settings().max_papers:
            raise HTTPException(
                status_code=409, detail="The library is full. Remove a paper before loading sample notes."
            )
        created = []
        for title, text in missing:
            paper = Paper(
                title=title,
                authors="PaperMind demo",
                abstract="Authored sample research note. Not a published paper.",
                source=PaperSource.sample,
                num_pages=1,
                num_chunks=1,
            )
            session.add(paper)
            session.flush()
            session.add(
                Chunk(
                    paper_id=paper.id,
                    point_id=str(uuid4()),
                    text=text,
                    order_in_paper=0,
                    page_start=1,
                    page_end=1,
                    section="sample note",
                    token_count=len(text.split()),
                )
            )
            created.append((paper, text))
        session.commit()
        for paper, text in created:
            build_for_paper(session, paper.id, text)
        return {"papers": len(NOTES), "created": len(created)}
