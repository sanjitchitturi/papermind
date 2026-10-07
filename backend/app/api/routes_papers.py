from fastapi import APIRouter, HTTPException
from sqlmodel import select

from app.api.deps import SessionDep, list_papers, paper_or_404, paper_out
from app.core.config import get_settings
from app.core.vector_store import delete_paper
from app.db.models import (
    BibliographyEntry,
    Chunk,
    CitationCheck,
    Claim,
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
    try:
        delete_paper(str(pid))
    except Exception:  # noqa: BLE001
        pass

    # Order matters because of foreign keys.
    claim_ids = [c.id for c in session.exec(select(Claim).where(Claim.paper_id == pid)).all()]
    if claim_ids:
        for check in session.exec(select(CitationCheck).where(CitationCheck.claim_id.in_(claim_ids))).all():
            session.delete(check)
    for row in session.exec(select(Claim).where(Claim.paper_id == pid)).all():
        session.delete(row)
    for row in session.exec(select(Chunk).where(Chunk.paper_id == pid)).all():
        session.delete(row)
    for row in session.exec(select(BibliographyEntry).where(BibliographyEntry.paper_id == pid)).all():
        session.delete(row)
    for row in session.exec(select(PaperEntity).where(PaperEntity.paper_id == pid)).all():
        session.delete(row)
    for row in session.exec(
        select(PaperCitation).where((PaperCitation.citing_paper_id == pid) | (PaperCitation.cited_paper_id == pid))
    ).all():
        session.delete(row)
    for row in session.exec(select(Job).where(Job.paper_id == pid)).all():
        session.delete(row)
    session.delete(paper)
    session.commit()
    return {"deleted": str(pid)}
