import json
import logging
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from typing import Any
from uuid import UUID

from sqlmodel import Session, select

from app.core.config import get_settings
from app.db.models import Job, JobKind, JobStatus, utcnow
from app.db.session import engine

logger = logging.getLogger(__name__)

_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="papermind-job")


class JobCancelled(Exception):
    pass


class JobContext:
    def __init__(self, job_id: UUID) -> None:
        self.job_id = job_id

    def update(self, stage: str, progress: float | None = None, message: str = "") -> None:
        with Session(engine) as session:
            job = session.get(Job, self.job_id)
            if job is None:
                raise JobCancelled()
            job.stage = stage
            if progress is not None:
                job.progress = max(0.0, min(1.0, progress))
            job.message = message
            job.updated_at = utcnow()
            session.add(job)
            session.commit()


JobFn = Callable[[JobContext], dict[str, Any] | None]


def create_job(session: Session, kind: JobKind, paper_id: UUID | None = None, payload: dict | None = None) -> Job:
    job = Job(kind=kind, paper_id=paper_id, input_json=json.dumps(payload or {}))
    session.add(job)
    session.commit()
    session.refresh(job)
    return job


def submit(job_id: UUID, fn: JobFn) -> None:
    if get_settings().jobs_inline:
        _run(job_id, fn)
    else:
        _executor.submit(_run, job_id, fn)


def _run(job_id: UUID, fn: JobFn) -> None:
    ctx = JobContext(job_id)
    _set_status(job_id, JobStatus.running, stage="starting")
    try:
        result = fn(ctx) or {}
    except JobCancelled:
        return
    except Exception as exc:  # noqa: BLE001 - any failure should land on the job row, not vanish in a thread
        logger.exception("job %s failed", job_id)
        _set_status(job_id, JobStatus.failed, stage="failed", error=_short_error(exc))
        return
    _set_status(job_id, JobStatus.done, stage="complete", progress=1.0, result=result)


def _short_error(exc: Exception) -> str:
    # Full tracebacks go to the logs. The API only exposes a readable
    # message, internal stack traces don't belong in client responses.
    text = str(exc).strip() or exc.__class__.__name__
    return text[:500]


def _set_status(
    job_id: UUID,
    status: JobStatus,
    stage: str,
    progress: float | None = None,
    error: str | None = None,
    result: dict | None = None,
) -> None:
    with Session(engine) as session:
        job = session.get(Job, job_id)
        if job is None:
            return
        job.status = status
        job.stage = stage
        if progress is not None:
            job.progress = progress
        if error is not None:
            job.error = error
        if result is not None:
            job.result_json = json.dumps(result)
        job.updated_at = utcnow()
        session.add(job)
        session.commit()


def recover_interrupted_jobs() -> int:
    """
    Jobs live in this process's memory. If the process restarted (deploys,
    free-tier spin-downs) anything still marked queued or running will never
    finish, so it gets marked failed instead of spinning in the UI forever.
    """
    with Session(engine) as session:
        stale = session.exec(select(Job).where(Job.status.in_([JobStatus.queued, JobStatus.running]))).all()
        for job in stale:
            job.status = JobStatus.failed
            job.stage = "failed"
            job.error = "Interrupted by a server restart, please retry."
            job.updated_at = utcnow()
            session.add(job)
        session.commit()
        return len(stale)


def active_job_exists(session: Session, kind: JobKind, paper_id: UUID | None = None) -> Job | None:
    query = select(Job).where(Job.kind == kind, Job.status.in_([JobStatus.queued, JobStatus.running]))
    if paper_id is not None:
        query = query.where(Job.paper_id == paper_id)
    return session.exec(query).first()
