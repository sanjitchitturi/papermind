"""
The core of the Citation Integrity Engine: for every citation found in a
paper, figure out what claim is being made about the cited work, try to
find the actual cited work in the corpus, and ask an LLM judge whether
the claim is actually supported by what the cited work says.

This is the feature that differentiates PaperMind from "chat with your
PDF" tools: it checks the paper's own citations rather than just
answering questions about the paper.
"""

from uuid import UUID

from sqlmodel import Session, select

from app.core.llm import chat_json
from app.db.models import BibliographyEntry, Chunk, CitationVerdict, CitationVerification, Claim, Paper
from app.ingestion.bib_parser import find_in_text_citations
from app.integrity.claim_extractor import extract_claim_about_citation
from app.retrieval.hybrid_search import retrieve

JUDGE_PROMPT = """A paper makes this claim about a cited work:

Claim: "{claim}"

Here is a passage from the cited work:

Passage: "{evidence}"

Does the passage support the claim? Consider whether the claim overstates,
understates, or accurately represents what the passage says.

Return JSON: {{"verdict": "supported|partially_supported|unsupported|contradicted",
"rationale": "one short sentence explaining why"}}"""


def check_paper_citations(session: Session, paper_id: UUID) -> list[CitationVerification]:
    chunks = session.exec(select(Chunk).where(Chunk.paper_id == paper_id).order_by(Chunk.order_in_paper)).all()
    bib_entries = {e.marker: e for e in session.exec(select(BibliographyEntry).where(BibliographyEntry.paper_id == paper_id)).all()}

    verifications: list[CitationVerification] = []

    for chunk in chunks:
        for citation in find_in_text_citations(chunk.text):
            bib_entry = bib_entries.get(citation.marker)
            if bib_entry is None:
                continue  # citation marker didn't match any parsed reference, skip rather than guess

            claim_text = extract_claim_about_citation(citation.context)
            if claim_text is None:
                continue  # this mention didn't actually attribute a claim to the citation

            claim = Claim(
                paper_id=paper_id,
                chunk_id=chunk.id,
                bib_entry_id=bib_entry.id,
                claim_text=claim_text,
                citation_marker=citation.marker,
            )
            session.add(claim)
            session.commit()

            verdict, evidence_text, rationale, confidence = _verify_claim_against_source(session, bib_entry, claim_text)

            verification = CitationVerification(
                claim_id=claim.id,
                verdict=verdict,
                evidence_text=evidence_text,
                judge_rationale=rationale,
                confidence=confidence,
            )
            session.add(verification)
            verifications.append(verification)

    session.commit()
    return verifications


def _verify_claim_against_source(session: Session, bib_entry: BibliographyEntry, claim_text: str) -> tuple[CitationVerdict, str, str, float]:
    cited_paper = None
    if bib_entry.resolved_arxiv_id:
        cited_paper = session.exec(select(Paper).where(Paper.arxiv_id == bib_entry.resolved_arxiv_id)).first()

    if cited_paper is None:
        # The cited work isn't in our corpus. Rather than guessing, we are
        # honest that we can't verify this one, which matters for the
        # eval metric on this feature (precision over recall).
        return CitationVerdict.unresolved, "", "cited paper is not in the ingested corpus", 0.0

    hits = retrieve(claim_text, paper_id=str(cited_paper.id), use_rewriting=False)
    if not hits:
        return CitationVerdict.unresolved, "", "no matching passage found in the cited paper", 0.0

    evidence_text = hits[0]["payload"].get("text", "")
    result = chat_json([{"role": "user", "content": JUDGE_PROMPT.format(claim=claim_text, evidence=evidence_text)}])
    verdict_str = result.get("verdict", "unresolved")
    try:
        verdict = CitationVerdict(verdict_str)
    except ValueError:
        verdict = CitationVerdict.unresolved

    rationale = result.get("rationale", "")
    confidence = float(hits[0]["score"]) if hits else 0.0
    return verdict, evidence_text, rationale, confidence
