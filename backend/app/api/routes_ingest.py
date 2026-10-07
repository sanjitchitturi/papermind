"""
Ingestion endpoints: search arXiv, kick off ingestion of an arXiv paper or
an uploaded PDF, and check job status. Ingestion itself runs in a
background task so the request returns immediately with a job id to poll.
"""

import os
import shutil
import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, UploadFile
from sqlmodel import Session

from app.api.schemas import ArxivIngestRequest, ArxivSearchRequest
from app.db.models import IngestionJob, JobStatus, PaperSource
from app.db.session import get_session
from app.ingestion import arxiv_fetcher
from app.ingestion.pipeline import ingest_paper

router = APIRouter(prefix="/ingest", tags=["ingest"])

UPLOAD_DIR = os.environ.get("UPLOAD_STORAGE_DIR", "./storage/uploads")


@router.post("/arxiv/search")
def search_arxiv(request: ArxivSearchRequest):
    return arxiv_fetcher.search(request.query, max_results=request.max_results)


@router.post("/arxiv")
def ingest_from_arxiv(request: ArxivIngestRequest, background_tasks: BackgroundTasks, session: Session = Depends(get_session)):
    job = IngestionJob(status=JobStatus.queued, stage="fetching_from_arxiv")
    session.add(job)
    session.commit()

    def task():
        from sqlmodel import Session as TaskSession

        from app.db.session import engine

        with TaskSession(engine) as task_session:
            try:
                result = arxiv_fetcher.fetch_and_download(request.arxiv_id)
            except Exception as exc:  # noqa: BLE001
                job_row = task_session.get(IngestionJob, job.id)
                if job_row:
                    job_row.status = JobStatus.failed
                    job_row.error = str(exc)
                    task_session.add(job_row)
                    task_session.commit()
                return

            ingest_paper(
                task_session,
                job.id,
                pdf_path=result.pdf_path,
                title=result.title,
                authors=", ".join(result.authors),
                abstract=result.abstract,
                source=PaperSource.arxiv,
                arxiv_id=result.arxiv_id,
            )

    background_tasks.add_task(task)
    return {"job_id": str(job.id)}


@router.post("/upload")
async def ingest_upload(background_tasks: BackgroundTasks, file: UploadFile, session: Session = Depends(get_session)):
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF uploads are supported.")

    os.makedirs(UPLOAD_DIR, exist_ok=True)
    dest_path = os.path.join(UPLOAD_DIR, f"{uuid.uuid4()}_{file.filename}")
    with open(dest_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    job = IngestionJob(status=JobStatus.queued, stage="parsing_pdf")
    session.add(job)
    session.commit()

    def task():
        from sqlmodel import Session as TaskSession

        from app.db.session import engine

        with TaskSession(engine) as task_session:
            ingest_paper(
                task_session,
                job.id,
                pdf_path=dest_path,
                title=file.filename.rsplit(".", 1)[0],
                authors="",
                abstract="",
                source=PaperSource.upload,
            )

    background_tasks.add_task(task)
    return {"job_id": str(job.id)}


@router.get("/jobs/{job_id}")
def job_status(job_id: str, session: Session = Depends(get_session)):
    job = session.get(IngestionJob, uuid.UUID(job_id))
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found.")
    return {
        "job_id": str(job.id),
        "status": job.status.value,
        "stage": job.stage,
        "error": job.error,
        "paper_id": str(job.paper_id) if job.paper_id else None,
    }
