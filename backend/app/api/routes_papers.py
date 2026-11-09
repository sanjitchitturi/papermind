from fastapi import APIRouter, HTTPException
from sqlmodel import select

from app.api.deps import SessionDep, list_papers, paper_or_404, paper_out
from app.core.config import get_settings
from app.db.models import (
    AnswerRecord,
    BibliographyEntry,
    Chunk,
    CitationCheck,
    Claim,
    Contradiction,
    Entity,
    Job,
    PaperCitation,
    PaperEntity,
)

router = APIRouter(prefix="/papers", tags=["papers"])


@router.get("")
def list_all_papers(session: SessionDep):
    return [paper_out(p) for p in list_papers(session)]


@router.get("/{paper_id}")
def get_paper(paper_id: str, session: SessionDep):
    return paper_out(paper_or_404(session, paper_id))


@router.delete("/{paper_id}")
def delete_one(paper_id: str, session: SessionDep):
    if not get_settings().allow_deletes:
        raise HTTPException(status_code=403, detail="Deletes are disabled.")
    paper = paper_or_404(session, paper_id)
    pid = paper.id
    claims = session.exec(select(Claim).where(Claim.paper_id == pid)).all()
    claim_ids = [c.id for c in claims]
    if claim_ids:
        for row in session.exec(
            select(Contradiction).where(
                (Contradiction.claim_a_id.in_(claim_ids)) | (Contradiction.claim_b_id.in_(claim_ids))
            )
        ).all():
            session.delete(row)
        for row in session.exec(select(CitationCheck).where(CitationCheck.claim_id.in_(claim_ids))).all():
            session.delete(row)
    session.flush()
    for row in session.exec(select(Claim).where(Claim.cited_paper_id == pid)).all():
        row.cited_paper_id = None
        session.add(row)
    for row in session.exec(select(AnswerRecord).where(AnswerRecord.paper_id == pid)).all():
        row.paper_id = None
        session.add(row)
    for row in claims:
        session.delete(row)
    session.flush()
    for model in (Chunk, BibliographyEntry, PaperEntity, Job):
        for row in session.exec(select(model).where(model.paper_id == pid)).all():
            session.delete(row)
    for row in session.exec(
        select(PaperCitation).where((PaperCitation.citing_paper_id == pid) | (PaperCitation.cited_paper_id == pid))
    ).all():
        session.delete(row)
    session.flush()
    session.delete(paper)
    session.flush()
    linked = set(session.exec(select(PaperEntity.entity_id)).all())
    for entity in session.exec(select(Entity)).all():
        if entity.id not in linked:
            session.delete(entity)
    session.commit()
    return {"deleted": str(pid)}
