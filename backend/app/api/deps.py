import json
import logging
import time
from collections import defaultdict
from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, Request
from sqlmodel import Session, select

from app.core.config import get_settings
from app.db.models import Job, Paper
from app.db.session import get_session

logger = logging.getLogger(__name__)

SessionDep = Annotated[Session, Depends(get_session)]

_hits: dict[str, list[float]] = defaultdict(list)
_WINDOW = 60.0
_LIMIT = 30


def rate_limit(request: Request) -> None:
    if not get_settings().rate_limit_enabled:
        return
    ip = request.client.host if request.client else "unknown"
    now = time.monotonic()
    bucket = _hits[ip]
    _hits[ip] = [t for t in bucket if now - t < _WINDOW]
    if len(_hits[ip]) >= _LIMIT:
        raise HTTPException(status_code=429, detail="Too many requests, wait a minute and try again.")
    _hits[ip].append(now)


def paper_or_404(session: Session, paper_id: str) -> Paper:
    try:
        pid = UUID(paper_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid paper id.") from exc
    paper = session.get(Paper, pid)
    if paper is None:
        raise HTTPException(status_code=404, detail="Paper not found.")
    return paper


def job_out(job: Job) -> dict:
    try:
        result = json.loads(job.result_json or "{}")
    except json.JSONDecodeError:
        result = {}
    return {
        "job_id": str(job.id),
        "kind": job.kind.value,
        "status": job.status.value,
        "stage": job.stage,
        "progress": job.progress,
        "message": job.message,
        "error": job.error,
        "paper_id": str(job.paper_id) if job.paper_id else None,
        "result": result,
    }


def paper_out(paper: Paper) -> dict:
    return {
        "id": str(paper.id),
        "title": paper.title,
        "authors": paper.authors,
        "year": paper.year,
        "arxiv_id": paper.arxiv_id,
        "abstract": paper.abstract,
        "num_pages": paper.num_pages,
        "num_chunks": paper.num_chunks,
        "source": paper.source.value,
    }


def list_papers(session: Session) -> list[Paper]:
    return session.exec(select(Paper).order_by(Paper.created_at.desc())).all()
