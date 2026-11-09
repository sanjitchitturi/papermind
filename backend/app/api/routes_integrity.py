from fastapi import APIRouter, HTTPException
from sqlmodel import select

from app.api.deps import SessionDep, job_out, paper_or_404
from app.core.jobs import create_job, submit
from app.core.llm import llm_available
from app.db.models import CitationCheck, Claim, Contradiction, JobKind, Paper
from app.integrity.citation_integrity import run_integrity_job
from app.integrity.contradiction_detector import extract_claims_for_paper, run_contradiction_job

router = APIRouter(prefix="/integrity", tags=["integrity"])


@router.post("/papers/{paper_id}/check")
def run_check(paper_id: str, session: SessionDep):
    paper = paper_or_404(session, paper_id)
    if not llm_available():
        raise HTTPException(status_code=503, detail="Citation checks need an LLM API key.")
    job = create_job(session, JobKind.integrity, paper_id=paper.id, payload={"paper_id": str(paper.id)})
    submit(job.id, run_integrity_job)
    return job_out(job)


@router.get("/papers/{paper_id}/report")
def get_report(paper_id: str, session: SessionDep):
    paper = paper_or_404(session, paper_id)
    claims = session.exec(select(Claim).where(Claim.paper_id == paper.id, Claim.kind == "citation")).all()
    rows = []
    for claim in claims:
        check = session.exec(select(CitationCheck).where(CitationCheck.claim_id == claim.id)).first()
        if check is None:
            continue
        cited = session.get(Paper, claim.cited_paper_id) if claim.cited_paper_id else None
        rows.append(
            {
                "claim": claim.claim_text,
                "citation_marker": claim.citation_marker,
                "cited_reference": cited.title if cited else "",
                "verdict": check.verdict.value,
                "evidence": check.evidence_text,
                "evidence_section": check.evidence_section,
                "rationale": check.rationale,
            }
        )
    verified = [r for r in rows if r["verdict"] != "unresolved"]
    supported = [r for r in verified if r["verdict"] == "supported"]
    score = round(len(supported) / len(verified) * 100) if verified else None
    return {"paper_id": paper_id, "integrity_score": score, "citations": rows}


@router.post("/papers/{paper_id}/extract-claims")
def extract_claims(paper_id: str, session: SessionDep):
    paper = paper_or_404(session, paper_id)
    if not llm_available():
        raise HTTPException(status_code=503, detail="Claim extraction needs an LLM API key.")
    n = extract_claims_for_paper(session, paper.id)
    return {"extracted": n}


@router.post("/contradictions/scan")
def scan(session: SessionDep):
    if not llm_available():
        raise HTTPException(status_code=503, detail="Contradiction scan needs an LLM API key.")
    job = create_job(session, JobKind.contradictions)
    submit(job.id, run_contradiction_job)
    return job_out(job)


@router.get("/contradictions")
def list_contradictions(session: SessionDep):
    rows = session.exec(select(Contradiction)).all()
    out = []
    for c in rows:
        a = session.get(Claim, c.claim_a_id)
        b = session.get(Claim, c.claim_b_id)
        out.append(
            {
                "claim_a": a.claim_text if a else "",
                "claim_b": b.claim_text if b else "",
                "explanation": c.explanation,
                "confidence": c.similarity,
            }
        )
    return out
