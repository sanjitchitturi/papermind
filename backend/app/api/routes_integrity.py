"""Endpoints for the Citation Integrity Engine: per-paper reports and the corpus-wide contradiction feed."""

import uuid

from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from app.db.models import BibliographyEntry, CitationVerification, Claim, Contradiction
from app.db.session import get_session
from app.integrity.citation_integrity import check_paper_citations
from app.integrity.contradiction_detector import detect_contradictions, extract_claims_for_paper

router = APIRouter(prefix="/integrity", tags=["integrity"])


@router.post("/papers/{paper_id}/check")
def run_integrity_check(paper_id: str, session: Session = Depends(get_session)):
    verifications = check_paper_citations(session, uuid.UUID(paper_id))
    return {"checked": len(verifications)}


@router.get("/papers/{paper_id}/report")
def get_integrity_report(paper_id: str, session: Session = Depends(get_session)):
    claims = session.exec(select(Claim).where(Claim.paper_id == uuid.UUID(paper_id))).all()
    rows = []
    for claim in claims:
        verification = session.exec(
            select(CitationVerification).where(CitationVerification.claim_id == claim.id)
        ).first()
        if verification is None:
            continue
        bib_entry = session.get(BibliographyEntry, claim.bib_entry_id) if claim.bib_entry_id else None
        rows.append(
            {
                "claim": claim.claim_text,
                "citation_marker": claim.citation_marker,
                "cited_reference": bib_entry.raw_text if bib_entry else "",
                "verdict": verification.verdict.value,
                "evidence": verification.evidence_text,
                "rationale": verification.judge_rationale,
            }
        )

    verified = [r for r in rows if r["verdict"] != "unresolved"]
    supported = [r for r in verified if r["verdict"] == "supported"]
    integrity_score = round(len(supported) / len(verified) * 100) if verified else None

    return {"paper_id": paper_id, "integrity_score": integrity_score, "citations": rows}


@router.post("/papers/{paper_id}/extract-claims")
def extract_claims(paper_id: str, session: Session = Depends(get_session)):
    claims = extract_claims_for_paper(session, uuid.UUID(paper_id))
    return {"extracted": len(claims)}


@router.post("/contradictions/scan")
def scan_contradictions(session: Session = Depends(get_session)):
    found = detect_contradictions(session)
    return {"found": len(found)}


@router.get("/contradictions")
def list_contradictions(session: Session = Depends(get_session)):
    contradictions = session.exec(select(Contradiction)).all()
    results = []
    for c in contradictions:
        claim_a = session.get(Claim, c.claim_a_id)
        claim_b = session.get(Claim, c.claim_b_id)
        results.append(
            {
                "claim_a": claim_a.claim_text if claim_a else "",
                "claim_b": claim_b.claim_text if claim_b else "",
                "explanation": c.explanation,
                "confidence": c.confidence,
            }
        )
    return results
