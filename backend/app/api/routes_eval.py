import json

from fastapi import APIRouter
from sqlmodel import select

from app.api.deps import SessionDep
from app.core.config import get_settings
from app.core.jobs import create_job, submit
from app.db.models import EvalRun, JobKind
from app.eval.eval_runner import run_eval_job

router = APIRouter(prefix="/eval", tags=["eval"])


@router.post("/run")
def trigger_eval(session: SessionDep, suite: str = "retrieval"):
    job = create_job(session, JobKind.eval, payload={"suite": suite, "commit": get_settings().git_commit_sha})
    submit(job.id, run_eval_job)
    from app.api.deps import job_out

    return job_out(job)


@router.get("/history")
def history(session: SessionDep):
    runs = session.exec(select(EvalRun).order_by(EvalRun.created_at)).all()
    return [
        {
            "id": str(r.id),
            "suite": r.suite,
            "commit_sha": r.commit_sha,
            "config": json.loads(r.config_json),
            "metrics": json.loads(r.metrics_json),
            "created_at": r.created_at.isoformat(),
        }
        for r in runs
    ]
