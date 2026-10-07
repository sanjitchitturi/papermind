from uuid import UUID

from fastapi import APIRouter, HTTPException

from app.api.deps import SessionDep
from app.api.schemas import FeedbackRequest
from app.feedback.feedback_store import record_feedback

router = APIRouter(prefix="/feedback", tags=["feedback"])


@router.post("")
def submit_feedback(request: FeedbackRequest, session: SessionDep):
    if request.rating not in (1, -1):
        raise HTTPException(status_code=400, detail="rating must be 1 or -1")
    try:
        answer_id = UUID(request.answer_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid answer id.") from exc
    feedback = record_feedback(session, answer_id, request.rating, request.comment)
    return {"feedback_id": str(feedback.id)}
