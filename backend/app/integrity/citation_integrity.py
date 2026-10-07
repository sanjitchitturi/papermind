"""
Citation Integrity Engine: for every in-text citation, extract the claim
being attributed to the cited work, retrieve evidence from that work if
it's in the corpus, and judge whether the claim is supported.

Unresolvable citations (cited work not ingested) are recorded as
unresolved rather than guessed. Precision over recall is the point of
this feature: a false "supported" is worse than an honest "we couldn't check".
"""

from uuid import UUID

from sqlmodel import Session, select

from app.core.jobs import JobContext
from app.core.llm import chat_json, llm_available
from app.db.models import BibliographyEntry, Chunk, CitationCheck, CitationVerdict, Claim, Paper
from app.db.session import engine
from app.ingestion.bib_parser import find_in_text_citations
from app.integrity.claim_extractor import extract_claim_about_citation
from app.retrieval.hybrid_search import retrieve

JUDGE_PROMPT = """A paper makes this claim about a cited work:

Claim: "{claim}"

Passage from the cited work:
"{evidence}"

Does the passage support the claim? Consider overstatement.

Return JSON: {{"verdict": "supported|partially_supported|unsupported|contradicted", "rationale": "one short sentence"}}"""


def run_integrity_job(ctx: JobContext) -> dict:
    with Session(engine) as session:
        import json

        from app.db.models import Job

        job = session.get(Job, ctx.job_id)
        if job is None or job.paper_id is None:
            return {}
        payload = json.loads(job.input_json)
        paper_id = UUID(payload["paper_id"])
        n = check_paper_citations(session, paper_id, ctx)
        return {"checked": n, "paper_id": str(paper_id)}


def check_paper_citations(session: Session, paper_id: UUID, ctx: JobContext | None = None) -> int:
    chunks = session.exec(select(Chunk).where(Chunk.paper_id == paper_id).order_by(Chunk.order_in_paper)).all()
    bib = {e.marker: e for e in session.exec(select(BibliographyEntry).where(BibliographyEntry.paper_id == paper_id)).all()}
    papers_by_arxiv = {p.arxiv_id: p for p in session.exec(select(Paper)).all() if p.arxiv_id}

    n = 0
    total = max(len(chunks), 1)
    for i, chunk in enumerate(chunks):
        if ctx:
            ctx.update("checking", i / total, f"Chunk {i + 1} / {len(chunks)}")
        for citation in find_in_text_citations(chunk.text):
            bib_entry = bib.get(citation.marker)
            if bib_entry is None:
                continue
            claim_text = extract_claim_about_citation(citation.context) if llm_available() else citation.context[:280]
            if not claim_text:
                continue

            cited_paper = papers_by_arxiv.get(bib_entry.resolved_arxiv_id or "")
            claim = Claim(
                paper_id=paper_id,
                chunk_id=chunk.id,
                cited_paper_id=cited_paper.id if cited_paper else None,
                kind="citation",
                citation_marker=citation.marker,
                context=citation.context,
                claim_text=claim_text,
            )
            session.add(claim)
            session.flush()

            verdict, evidence, section, rationale, score = _verify(bib_entry, cited_paper, claim_text)
            session.add(
                CitationCheck(
                    claim_id=claim.id,
                    verdict=verdict,
                    evidence_text=evidence,
                    evidence_section=section,
                    rationale=rationale,
                    evidence_score=score,
                )
            )
            n += 1
    session.commit()
    return n


def _verify(bib_entry, cited_paper: Paper | None, claim_text: str) -> tuple[CitationVerdict, str, str, str, float]:
    if cited_paper is None:
        return CitationVerdict.unresolved, "", "", "Cited paper is not in the library.", 0.0
    hits = retrieve(claim_text, paper_ids=[str(cited_paper.id)], use_rewriting=False)
    if not hits:
        return CitationVerdict.unresolved, "", "", "No matching passage found in the cited paper.", 0.0
    evidence = hits[0].text
    section = hits[0].section
    score = hits[0].rerank_prob if hits[0].rerank_prob is not None else hits[0].fused_score
    if not llm_available():
        return CitationVerdict.unresolved, evidence, section, "No LLM configured to judge support.", float(score)
    result = chat_json([{"role": "user", "content": JUDGE_PROMPT.format(claim=claim_text, evidence=evidence[:1800])}])
    try:
        verdict = CitationVerdict(result.get("verdict", "unresolved"))
    except ValueError:
        verdict = CitationVerdict.unresolved
    return verdict, evidence, section, result.get("rationale", ""), float(score)
