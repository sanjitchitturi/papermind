import json

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from app.agent.react_loop import run_research_mode
from app.api.deps import rate_limit
from app.api.schemas import MatrixRowOut, ResearchRequest, ResearchResponse, TraceStepOut

router = APIRouter(prefix="/research", tags=["research"])


@router.post("", response_model=ResearchResponse)
def research(request: ResearchRequest, _: None = Depends(rate_limit)):
    result = run_research_mode(request.question)
    return _to_response(result)


@router.post("/stream")
def research_stream(request: ResearchRequest, _: None = Depends(rate_limit)):
    def events():
        result = run_research_mode(
            request.question, on_step=lambda step: None
        )
        # Stream the finished trace so the UI can render it progressively
        # even though the agent itself is still sequential.
        for step in result.trace:
            yield f"data: {json.dumps({'stage': step.kind, 'detail': step.detail})}\n\n"
        yield f"data: {json.dumps({'stage': 'complete', 'result': _to_response(result).model_dump()})}\n\n"

    return StreamingResponse(events(), media_type="text/event-stream")


def _to_response(result) -> ResearchResponse:
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
