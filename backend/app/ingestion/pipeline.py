"""
Orchestrates the full ingestion flow for one paper: parse PDF, chunk it,
parse the bibliography, embed everything, and write it all to Postgres
and Qdrant. This runs inside a FastAPI background task, with progress
reported through the IngestionJob row so the frontend can poll it instead
of needing a websocket or a separate task queue.
"""

import traceback
from uuid import UUID, uuid4

from sqlmodel import Session

from app.core.config import get_settings
from app.core.llm import embed
from app.core.vector_store import upsert_chunks
from app.db.models import BibliographyEntry, Chunk, IngestionJob, JobStatus, Paper, PaperSource
from app.ingestion.bib_parser import extract_bibliography
from app.ingestion.chunker import chunk_document
from app.ingestion.pdf_parser import parse_pdf

settings = get_settings()


def _update_job(session: Session, job: IngestionJob, status: JobStatus, stage: str, error: str | None = None) -> None:
    job.status = status
    job.stage = stage
    job.error = error
    session.add(job)
    session.commit()


def ingest_paper(
    session: Session,
    job_id: UUID,
    pdf_path: str,
    title: str,
    authors: str,
    abstract: str,
    source: PaperSource,
    arxiv_id: str | None = None,
) -> None:
    job = session.get(IngestionJob, job_id)
    if job is None:
        return

    try:
        _update_job(session, job, JobStatus.running, "parsing_pdf")
        parsed = parse_pdf(pdf_path)

        paper = Paper(
            title=title,
            authors=authors,
            abstract=abstract,
            source=source,
            pdf_path=pdf_path,
            num_pages=len(parsed.pages),
            arxiv_id=arxiv_id,
        )
        session.add(paper)
        session.commit()
        job.paper_id = paper.id
        session.add(job)
        session.commit()

        _update_job(session, job, JobStatus.running, "chunking")
        chunks = chunk_document(parsed)
        if not chunks:
            raise ValueError("No text could be extracted from this PDF, it may be scanned images rather than text.")

        _update_job(session, job, JobStatus.running, "parsing_bibliography")
        references_text = next((t for name, t, _ in _sections_named(parsed, "references")), "")
        bib_entries = extract_bibliography(references_text) if references_text else []
        for entry in bib_entries:
            session.add(
                BibliographyEntry(
                    paper_id=paper.id,
                    marker=entry.marker,
                    raw_text=entry.raw_text,
                    resolved_arxiv_id=entry.resolved_arxiv_id,
                )
            )
        session.commit()
        # In-text citations are parsed again later by the claim extractor,
        # which needs the chunk a citation falls in, not just its raw
        # character offset in the full document.

        _update_job(session, job, JobStatus.running, "embedding")
        texts = [c.text for c in chunks]
        # Batch in groups of 100 to stay well under typical embedding API
        # request size limits.
        vectors: list[list[float]] = []
        batch_size = 100
        for i in range(0, len(texts), batch_size):
            vectors.extend(embed(texts[i : i + batch_size]))

        _update_job(session, job, JobStatus.running, "indexing")
        points = []
        for chunk, vector in zip(chunks, vectors, strict=True):
            db_chunk = Chunk(
                paper_id=paper.id,
                qdrant_point_id=str(uuid4()),
                section=chunk.section,
                page=None,
                order_in_paper=chunk.order,
                text=chunk.text,
            )
            session.add(db_chunk)
            session.flush()  # need the generated id before building the qdrant point
            points.append(
                {
                    "id": db_chunk.qdrant_point_id,
                    "dense_vector": vector,
                    "text": chunk.text,
                    "payload": {
                        "paper_id": str(paper.id),
                        "arxiv_id": arxiv_id or "",
                        "chunk_id": str(db_chunk.id),
                        "section": chunk.section,
                        "text": chunk.text,
                        "paper_title": title,
                    },
                }
            )
        session.commit()
        upsert_chunks(points)

        _update_job(session, job, JobStatus.done, "complete")
    except Exception as exc:  # noqa: BLE001 - we want to capture and store any failure, not just specific types
        session.rollback()
        job = session.get(IngestionJob, job_id)
        if job:
            _update_job(session, job, JobStatus.failed, "failed", error=f"{exc}\n{traceback.format_exc()}")


def _sections_named(parsed, name: str):
    from app.ingestion.chunker import _split_into_sections

    return [(n, t, s) for n, t, s in _split_into_sections(parsed) if n == name]
