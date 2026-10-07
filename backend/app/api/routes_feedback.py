"""Endpoint for thumbs up/down feedback on answers."""

import uuid

from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.api.schemas import FeedbackRequest
from app.db.session import get_session
from app.feedback.feedback_store import record_feedback

router = APIRouter(prefix="/feedback", tags=["feedback"])


@router.post("")
def submit_feedback(request: FeedbackRequest, session: Session = Depends(get_session)):
    feedback = record_feedback(session, uuid.UUID(request.answer_id), request.rating, request.comment)
    return {"feedback_id": str(feedback.id)}
