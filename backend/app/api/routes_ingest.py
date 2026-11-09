import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from app.api.deps import SessionDep, job_out, rate_limit
from app.api.schemas import ArxivIngestRequest, ArxivSearchRequest
from app.core.config import get_settings
from app.core.jobs import create_job, submit
from app.db.models import JobKind, Paper, PaperSource
from app.ingestion import arxiv_fetcher
from app.ingestion.pipeline import ingest_from_payload

router = APIRouter(prefix="/ingest", tags=["ingest"])


@router.post("/arxiv/search")
def search_arxiv(request: ArxivSearchRequest, _: None = Depends(rate_limit)):
    try:
        return arxiv_fetcher.search(request.query, max_results=request.max_results)
    except Exception as exc:
        raise HTTPException(status_code=502, detail="arXiv is unavailable. Retry later or upload a PDF.") from exc


@router.post("/arxiv")
def ingest_from_arxiv(request: ArxivIngestRequest, session: SessionDep, _: None = Depends(rate_limit)):
    from sqlmodel import select

    canonical = arxiv_fetcher._canonical_id(request.arxiv_id)
    if not arxiv_fetcher._ARXIV_ID.fullmatch(canonical):
        raise HTTPException(status_code=400, detail="Enter a valid arXiv identifier, for example 1706.03762.")
    existing = session.exec(
        select(Paper).where(Paper.arxiv_id == arxiv_fetcher._canonical_id(request.arxiv_id))
    ).first()
    if existing:
        return {**job_out_stub(existing), "duplicate": True}

    job = create_job(
        session,
        JobKind.ingest,
        payload={"source": PaperSource.arxiv.value, "arxiv_id": request.arxiv_id},
    )
    submit(job.id, ingest_from_payload)
    return job_out(job)


@router.post("/upload")
async def ingest_upload(session: SessionDep, file: UploadFile = File(...), _: None = Depends(rate_limit)):
    settings = get_settings()
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF uploads are supported.")
    # Server-generated paths prevent uploaded filenames from escaping storage.
    filename = Path(file.filename.replace("\\", "/")).name
    dest_dir = Path(settings.storage_dir) / "uploads"
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / f"{uuid.uuid4()}.pdf"
    total = 0
    try:
        with dest.open("wb") as fh:
            while data := await file.read(64 * 1024):
                total += len(data)
                if total > settings.max_upload_mb * 1024 * 1024:
                    raise HTTPException(status_code=413, detail=f"PDF is larger than {settings.max_upload_mb} MB.")
                fh.write(data)
        if not total:
            raise HTTPException(status_code=400, detail="PDF is empty.")
    except Exception:
        dest.unlink(missing_ok=True)
        raise
    finally:
        await file.close()
    title = filename.rsplit(".", 1)[0]
    job = create_job(
        session,
        JobKind.ingest,
        payload={"source": PaperSource.upload.value, "pdf_path": str(dest), "title": title},
    )
    submit(job.id, ingest_from_payload)
    return job_out(job)


@router.get("/jobs/{job_id}")
def job_status(job_id: str, session: SessionDep):
    from app.db.models import Job

    try:
        job = session.get(Job, uuid.UUID(job_id))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid job id.") from exc
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found.")
    return job_out(job)


def job_out_stub(paper: Paper) -> dict:
    return {
        "job_id": str(paper.id),
        "kind": "ingest",
        "status": "done",
        "stage": "complete",
        "progress": 1.0,
        "message": "Already in the library",
        "error": None,
        "paper_id": str(paper.id),
        "result": {"paper_id": str(paper.id), "duplicate": True, "title": paper.title},
    }
