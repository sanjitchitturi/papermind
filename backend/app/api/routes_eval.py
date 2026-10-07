"""Endpoints for the eval dashboard: trigger a run, read historical results."""

import json

from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from app.db.models import EvalRun
from app.db.session import get_session
from app.eval.eval_runner import run_eval

router = APIRouter(prefix="/eval", tags=["eval"])


@router.post("/run")
def trigger_eval(pipeline_config: str = "full", session: Session = Depends(get_session)):
    run = run_eval(session, pipeline_config=pipeline_config)
    return {"run_id": str(run.id), "metrics": json.loads(run.metrics_json)}


@router.get("/history")
def eval_history(session: Session = Depends(get_session)):
    runs = session.exec(select(EvalRun).order_by(EvalRun.created_at)).all()
    return [
        {
            "id": str(r.id),
            "commit_sha": r.commit_sha,
            "pipeline_config": r.pipeline_config,
            "metrics": json.loads(r.metrics_json),
            "created_at": r.created_at.isoformat(),
        }
        for r in runs
    ]
