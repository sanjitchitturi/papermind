import logging
from uuid import uuid4

from sqlmodel import Session, select

from app.core.config import get_settings
from app.core.jobs import JobContext
from app.core.vector_store import upsert_points
from app.db.models import BibliographyEntry, Chunk, Paper, PaperSource
from app.db.session import engine
from app.ingestion.arxiv_fetcher import fetch_and_download
from app.ingestion.bib_parser import extract_bibliography
from app.ingestion.chunker import chunk_document
from app.ingestion.pdf_parser import parse_pdf
from app.ingestion.text_cleanup import first_author_surname, year_from_arxiv_id
from app.ml.embeddings import get_embedder, get_sparse_encoder

logger = logging.getLogger(__name__)


class IngestError(ValueError):
    pass


def ingest_from_payload(ctx: JobContext) -> dict:
    with Session(engine) as session:
        job = session.get(__import__("app.db.models", fromlist=["Job"]).Job, ctx.job_id)
        if job is None:
            return {}
        payload = __import__("json").loads(job.input_json)
        return ingest_paper(session, ctx, payload)


def ingest_paper(session: Session, ctx: JobContext, payload: dict) -> dict:
    settings = get_settings()
    source = PaperSource(payload["source"])
    arxiv_id = payload.get("arxiv_id")
    pdf_path = payload.get("pdf_path")
    title = payload.get("title") or "Untitled"
    authors = payload.get("authors") or ""
    abstract = payload.get("abstract") or ""

    if source == PaperSource.arxiv:
        ctx.update("fetching", 0.05, f"Downloading {arxiv_id} from arXiv")
        fetched = fetch_and_download(arxiv_id)
        pdf_path = fetched.pdf_path
        title, authors, abstract, arxiv_id = fetched.title, ", ".join(fetched.authors), fetched.abstract, fetched.arxiv_id

    existing = _find_duplicate(session, arxiv_id, title)
    if existing is not None:
        ctx.update("complete", 1.0, "Already in the library")
        return {"paper_id": str(existing.id), "duplicate": True, "title": existing.title}

    n_papers = session.exec(select(Paper)).all()
    if len(n_papers) >= settings.max_papers:
        raise IngestError(f"Library is at the {settings.max_papers} paper cap.")

    ctx.update("parsing", 0.15, "Parsing PDF")
    parsed = parse_pdf(pdf_path, max_pages=settings.max_pdf_pages)
    if len(parsed.full_text) < 400:
        raise IngestError("Could not extract enough text from this PDF. It may be a scanned image.")

    ctx.update("chunking", 0.3, "Chunking by section")
    chunks = chunk_document(parsed)
    if not chunks:
        raise IngestError("PDF parsed but produced no chunks.")

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
    session.add(paper)
    session.commit()
    session.refresh(paper)

    ctx.update("bibliography", 0.4, "Parsing references")
    references_text = _section_text(parsed, "references")
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

    ctx.update("embedding", 0.55, f"Embedding {len(chunks)} chunks")
    embedder = get_embedder()
    sparse_encoder = get_sparse_encoder()
    texts = [c.text for c in chunks]
    dense_vectors: list[list[float]] = []
    sparse_vectors = []
    batch = settings.ml_batch_size
    for i in range(0, len(texts), batch):
        slice_texts = texts[i : i + batch]
        dense_vectors.extend(embedder.embed_documents(slice_texts))
        sparse_vectors.extend(sparse_encoder.embed_documents(slice_texts))
        ctx.update("embedding", 0.55 + 0.25 * ((i + batch) / len(texts)), f"Embedded {min(i + batch, len(texts))} / {len(texts)}")

    ctx.update("indexing", 0.85, "Writing to the vector index")
    points = []
    for chunk, dense, sparse in zip(chunks, dense_vectors, sparse_vectors, strict=True):
        db_chunk = Chunk(
            paper_id=paper.id,
            point_id=str(uuid4()),
            section=chunk.section,
            page_start=chunk.page_start,
            page_end=chunk.page_end,
            order_in_paper=chunk.order,
            token_count=chunk.token_count,
            text=chunk.text,
        )
        session.add(db_chunk)
        session.flush()
        points.append(
            {
                "id": db_chunk.point_id,
                "dense": dense,
                "sparse": sparse,
                "payload": {
                    "paper_id": str(paper.id),
                    "arxiv_id": arxiv_id or "",
                    "chunk_id": str(db_chunk.id),
                    "section": chunk.section,
                    "page": chunk.page_start,
                    "text": chunk.text,
                    "paper_title": title,
                },
            }
        )
    session.commit()
    upsert_points(points)

    ctx.update("graph", 0.93, "Extracting entities")
    try:
        from app.graph.graph_builder import build_for_paper

        build_for_paper(session, paper.id, parsed.full_text)
    except Exception:  # noqa: BLE001
        logger.exception("entity extraction failed for %s, continuing", paper.id)

    ctx.update("complete", 1.0, "Ready")
    return {"paper_id": str(paper.id), "duplicate": False, "title": paper.title, "chunks": len(chunks)}


def _find_duplicate(session: Session, arxiv_id: str | None, title: str) -> Paper | None:
    if arxiv_id:
        found = session.exec(select(Paper).where(Paper.arxiv_id == arxiv_id)).first()
        if found:
            return found
    normalized = title.strip().lower()
    if not normalized:
        return None
    for paper in session.exec(select(Paper)).all():
        if paper.title.strip().lower() == normalized:
            return paper
    return None


def _section_text(parsed, name: str) -> str:
    offsets = parsed.section_offsets
    for i, (section, start) in enumerate(offsets):
        if section == name:
            end = offsets[i + 1][1] if i + 1 < len(offsets) else len(parsed.full_text)
            return parsed.full_text[start:end]
    return ""
