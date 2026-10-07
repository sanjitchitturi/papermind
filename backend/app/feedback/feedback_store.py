"""
Stores thumbs up/down feedback on answers. A thumbs-down on an answer
that had a high trust score is exactly the kind of disagreement worth
turning into a regression test case, so that's flagged here rather than
left for someone to notice manually later.
"""

from uuid import UUID

from sqlmodel import Session, select

from app.db.models import AnswerRecord, Feedback


def record_feedback(session: Session, answer_id: UUID, rating: int, comment: str | None = None) -> Feedback:
    feedback = Feedback(answer_id=answer_id, rating=rating, comment=comment)
    session.add(feedback)
    session.commit()
    return feedback


def flagged_disagreements(session: Session) -> list[tuple[AnswerRecord, Feedback]]:
    """
    Answers that scored high on trust but got a thumbs-down. These are the
    most useful signal that the trust score calibration needs attention,
    or that the eval dataset is missing a case like this one.
    """
    feedbacks = session.exec(select(Feedback).where(Feedback.rating < 0)).all()
    flagged = []
    for feedback in feedbacks:
        answer = session.get(AnswerRecord, feedback.answer_id)
        if answer and answer.trust_score >= 70:
            flagged.append((answer, feedback))
    return flagged
