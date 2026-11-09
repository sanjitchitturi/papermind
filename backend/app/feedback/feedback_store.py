from uuid import UUID

from sqlmodel import Session, select

from app.db.models import AnswerRecord, Feedback


def record_feedback(session: Session, answer_id: UUID, rating: int, comment: str | None = None) -> Feedback:
    if session.get(AnswerRecord, answer_id) is None:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Answer not found.")
    feedback = Feedback(answer_id=answer_id, rating=rating, comment=comment)
    session.add(feedback)
    session.commit()
    return feedback


def flagged_disagreements(session: Session) -> list[tuple[AnswerRecord, Feedback]]:
    feedbacks = session.exec(select(Feedback).where(Feedback.rating < 0)).all()
    flagged = []
    for feedback in feedbacks:
        answer = session.get(AnswerRecord, feedback.answer_id)
        if answer and answer.trust_score >= 70:
            flagged.append((answer, feedback))
    return flagged
