"""
Finds pairs of claims from different papers that appear to be about the
same topic but disagree.

Approach: extract atomic claims, embed them with the local dense model,
and only run the LLM NLI judge on pairs whose cosine similarity is high
enough to plausibly be about the same thing. Without that filter this
would be all-pairs across every claim, which gets expensive fast.
"""

from itertools import combinations
from uuid import UUID

import numpy as np
from sqlmodel import Session, select

from app.core.jobs import JobContext
from app.core.llm import chat_json, llm_available
from app.db.models import Chunk, Claim, Contradiction
from app.db.session import engine
from app.integrity.claim_extractor import extract_atomic_claims
from app.ml.embeddings import get_embedder

SIMILARITY_THRESHOLD = 0.78

NLI_PROMPT = """Do these two claims, from different papers, contradict each other?
They must be about the same topic to count as a contradiction.

Claim A: "{claim_a}"
Claim B: "{claim_b}"

Return JSON: {{"contradicts": true, "explanation": "one short sentence"}}"""


def run_contradiction_job(ctx: JobContext) -> dict:
    with Session(engine) as session:
        n = detect_contradictions(session, ctx)
        return {"found": n}


def extract_claims_for_paper(session: Session, paper_id: UUID) -> int:
    chunks = session.exec(select(Chunk).where(Chunk.paper_id == paper_id)).all()
    created = 0
    for chunk in chunks:
        for text in extract_atomic_claims(chunk.text):
            session.add(Claim(paper_id=paper_id, chunk_id=chunk.id, kind="atomic", claim_text=text, context=chunk.text[:400]))
            created += 1
    session.commit()
    return created


def detect_contradictions(session: Session, ctx: JobContext | None = None) -> int:
    claims = session.exec(select(Claim)).all()
    if len(claims) < 2:
        return 0
    if ctx:
        ctx.update("embedding", 0.2, f"Embedding {len(claims)} claims")
    embedder = get_embedder()
    vectors = np.array(embedder.embed_documents([c.claim_text for c in claims]))
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    norms[norms == 0] = 1
    unit = vectors / norms

    existing = {(c.claim_a_id, c.claim_b_id) for c in session.exec(select(Contradiction)).all()}
    found = 0
    pairs = [
        (i, j, float(unit[i] @ unit[j]))
        for i, j in combinations(range(len(claims)), 2)
        if claims[i].paper_id != claims[j].paper_id
    ]
    pairs = [(i, j, s) for i, j, s in pairs if s >= SIMILARITY_THRESHOLD]
    pairs.sort(key=lambda t: t[2], reverse=True)
    pairs = pairs[:80]  # cap LLM calls on a public demo

    for k, (i, j, sim) in enumerate(pairs):
        a, b = claims[i], claims[j]
        if (a.id, b.id) in existing or (b.id, a.id) in existing:
            continue
        if ctx:
            ctx.update("judging", 0.3 + 0.6 * (k / max(len(pairs), 1)), f"Pair {k + 1} / {len(pairs)}")
        if not llm_available():
            continue
        result = chat_json(
            [{"role": "user", "content": NLI_PROMPT.format(claim_a=a.claim_text, claim_b=b.claim_text)}]
        )
        if not result.get("contradicts"):
            continue
        session.add(
            Contradiction(
                claim_a_id=a.id,
                claim_b_id=b.id,
                explanation=result.get("explanation", ""),
                similarity=sim,
            )
        )
        found += 1
    session.commit()
    return found
