"""Endpoint for the agentic Research Mode."""

from fastapi import APIRouter

from app.agent.react_loop import run_research_mode
from app.api.schemas import MatrixRowOut, ResearchRequest, ResearchResponse, TraceStepOut

router = APIRouter(prefix="/research", tags=["research"])


@router.post("", response_model=ResearchResponse)
def research(request: ResearchRequest):
    result = run_research_mode(request.question)
    return ResearchResponse(
        narrative=result.narrative,
        matrix=[
            MatrixRowOut(
                paper_title=row.paper_title,
                paper_id=row.paper_id,
                method=row.method,
                dataset=row.dataset,
                metric_result=row.metric_result,
                limitations=row.limitations,
            )
            for row in result.matrix
        ],
        trace=[TraceStepOut(kind=step.kind, detail=step.detail) for step in result.trace],
    )
