"""PDF ingestion commits paper metadata and searchable chunks atomically."""

import json
import logging
from uuid import uuid4

from sqlmodel import Session, select

from app.core.config import get_settings
from app.core.jobs import JobContext
from app.db.models import BibliographyEntry, Chunk, Job, Paper, PaperSource
from app.db.session import engine
from app.ingestion.arxiv_fetcher import fetch_and_download
from app.ingestion.bib_parser import extract_bibliography
from app.ingestion.chunker import chunk_document
from app.ingestion.pdf_parser import parse_pdf
from app.ingestion.text_cleanup import first_author_surname, year_from_arxiv_id

logger = logging.getLogger(__name__)


class IngestError(ValueError):
    pass


def ingest_from_payload(ctx: JobContext) -> dict:
    with Session(engine) as session:
        job = session.get(Job, ctx.job_id)
        payload = json.loads(job.input_json) if job else None
    if payload is None:
        return {}
    try:
        with Session(engine) as session:
            return ingest_paper(session, ctx, payload)
    finally:
        # Uploaded bytes are temporary; searchable text is persisted in SQLite.
        if payload.get("source") == PaperSource.upload.value:
            from pathlib import Path

            path = payload.get("pdf_path")
            if path:
                Path(path).unlink(missing_ok=True)


def ingest_paper(session: Session, ctx: JobContext, payload: dict) -> dict:
    settings = get_settings()
    source = PaperSource(payload["source"])
    arxiv_id = payload.get("arxiv_id")
    pdf_path = payload.get("pdf_path")
    title, authors, abstract = (
        payload.get("title") or "Untitled",
        payload.get("authors") or "",
        payload.get("abstract") or "",
    )
    if source == PaperSource.arxiv:
        ctx.update("fetching", 0.05, f"Downloading {arxiv_id} from arXiv")
        fetched = fetch_and_download(arxiv_id)
        pdf_path = fetched.pdf_path
        title, authors, abstract, arxiv_id = (
            fetched.title,
            ", ".join(fetched.authors),
            fetched.abstract,
            fetched.arxiv_id,
        )
    existing = _find_duplicate(session, arxiv_id, title)
    if existing:
        return {"paper_id": str(existing.id), "duplicate": True, "title": existing.title}
    if len(session.exec(select(Paper)).all()) >= settings.max_papers:
        raise IngestError(f"Library is at the {settings.max_papers} paper cap.")
    ctx.update("parsing", 0.2, "Extracting text and page references")
    try:
        parsed = parse_pdf(pdf_path, max_pages=settings.max_pdf_pages)
    except Exception as exc:
        raise IngestError("Could not read PDF. Use an unencrypted, text-based PDF within the page limit.") from exc
    if len(parsed.full_text) < 100:
        raise IngestError("Not enough text could be extracted. Scanned PDFs need OCR before uploading.")
    chunks = chunk_document(parsed)
    if not chunks:
        raise IngestError("PDF produced no searchable text.")
    references = extract_bibliography(_section_text(parsed, "references"))
    ctx.update("indexing", 0.7, f"Saving {len(chunks)} searchable passages")
    paper = Paper(
        title=title,
        authors=authors,
        first_author_surname=first_author_surname(authors),
        year=year_from_arxiv_id(arxiv_id),
        abstract=abstract,
        source=source,
        arxiv_id=arxiv_id,
        num_pages=len(parsed.pages),
        num_chunks=len(chunks),
    )
    try:
        session.add(paper)
        session.flush()
        for entry in references:
            session.add(
                BibliographyEntry(
                    paper_id=paper.id,
                    marker=entry.marker,
                    raw_text=entry.raw_text,
                    resolved_arxiv_id=entry.resolved_arxiv_id,
                )
            )
        for chunk in chunks:
            session.add(
                Chunk(
                    paper_id=paper.id,
                    point_id=str(uuid4()),
                    section=chunk.section,
                    page_start=chunk.page_start,
                    page_end=chunk.page_end,
                    order_in_paper=chunk.order,
                    token_count=chunk.token_count,
                    text=chunk.text,
                )
            )
        job = session.get(Job, ctx.job_id)
        if job:
            job.paper_id = paper.id
            session.add(job)
        session.commit()
    except Exception:
        session.rollback()
        raise
    ctx.update("graph", 0.9, "Building local entity connections")
    try:
        from app.graph.graph_builder import build_for_paper

        build_for_paper(session, paper.id, parsed.full_text)
    except Exception:
        session.rollback()
        logger.exception("Entity extraction skipped for %s", paper.id)
    return {"paper_id": str(paper.id), "duplicate": False, "title": paper.title, "chunks": len(chunks)}


def _find_duplicate(session: Session, arxiv_id: str | None, title: str) -> Paper | None:
    for paper in session.exec(select(Paper)).all():
        if (arxiv_id and paper.arxiv_id == arxiv_id) or paper.title.strip().casefold() == title.strip().casefold():
            return paper
    return None


def _section_text(parsed, name: str) -> str:
    for i, (section, start) in enumerate(parsed.section_offsets):
        if section == name:
            end = parsed.section_offsets[i + 1][1] if i + 1 < len(parsed.section_offsets) else len(parsed.full_text)
            return parsed.full_text[start:end]
    return ""
