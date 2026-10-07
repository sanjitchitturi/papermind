"""
Finds pairs of claims from different papers in the corpus that appear to
be about the same topic but disagree with each other.

Approach: extract atomic claims from each paper's chunks, embed them,
and only run the (expensive, LLM-based) contradiction check on pairs
whose embeddings are close enough to plausibly be about the same thing.
Without that filtering step this would be an all-pairs comparison across
every claim in the corpus, which gets expensive fast as the corpus grows.
"""

from dataclasses import dataclass
from itertools import combinations
from uuid import UUID

import numpy as np
from sqlmodel import Session, select

from app.core.llm import chat_json, embed
from app.db.models import Chunk, Claim, Contradiction
from app.integrity.claim_extractor import extract_atomic_claims

SIMILARITY_THRESHOLD = 0.82  # cosine similarity above this is "plausibly the same topic"

NLI_PROMPT = """Do these two claims, from different research papers, contradict each
other? They should be about the same topic to be a contradiction, not just unrelated.

Claim A: "{claim_a}"
Claim B: "{claim_b}"

Return JSON: {{"contradicts": true|false, "explanation": "one short sentence"}}"""


@dataclass
class ClaimWithEmbedding:
    claim: Claim
    vector: np.ndarray


def extract_claims_for_paper(session: Session, paper_id: UUID) -> list[Claim]:
    chunks = session.exec(select(Chunk).where(Chunk.paper_id == paper_id)).all()
    created = []
    for chunk in chunks:
        for claim_text in extract_atomic_claims(chunk.text):
            claim = Claim(paper_id=paper_id, chunk_id=chunk.id, claim_text=claim_text)
            session.add(claim)
            created.append(claim)
    session.commit()
    return created


def _cosine(a: np.ndarray, b: np.ndarray) -> float:
    denom = np.linalg.norm(a) * np.linalg.norm(b)
    return float(np.dot(a, b) / denom) if denom else 0.0


def detect_contradictions(session: Session) -> list[Contradiction]:
    """
    Runs across the whole corpus. Meant to be called periodically (e.g.
    after a new paper is ingested) rather than on every request, since it
    scans all stored claims.
    """
    claims = session.exec(select(Claim)).all()
    if len(claims) < 2:
        return []

    texts = [c.claim_text for c in claims]
    vectors = embed(texts)
    claim_embeddings = [ClaimWithEmbedding(claim=c, vector=np.array(v)) for c, v in zip(claims, vectors, strict=True)]

    found: list[Contradiction] = []
    for a, b in combinations(claim_embeddings, 2):
        if a.claim.paper_id == b.claim.paper_id:
            continue  # only cross-paper contradictions are interesting here
        similarity = _cosine(a.vector, b.vector)
        if similarity < SIMILARITY_THRESHOLD:
            continue

        result = chat_json(
            [{"role": "user", "content": NLI_PROMPT.format(claim_a=a.claim.claim_text, claim_b=b.claim.claim_text)}]
        )
        if not result.get("contradicts"):
            continue

        contradiction = Contradiction(
            claim_a_id=a.claim.id,
            claim_b_id=b.claim.id,
            explanation=result.get("explanation", ""),
            confidence=similarity,
        )
        session.add(contradiction)
        found.append(contradiction)

    session.commit()
    return found
