"""
Extracts atomic, checkable claims from a chunk of paper text.

"Atomic" matters here: a sentence like "Our model, building on prior work
on attention [12], achieves 94% accuracy" actually contains a claim about
what [12] showed (implicitly, that attention mechanisms are useful) and a
separate claim about this paper's own result. We only want the part that
attributes something to a citation, since that's what the integrity
engine needs to verify.
"""

from app.core.llm import chat_json

CLAIM_EXTRACTION_PROMPT = """The following sentence cites a reference. Extract the
specific claim being made about what the cited work showed, found, or proposed.
If the sentence doesn't actually attribute a claim to the citation (e.g. it just
lists the reference without saying what it did), return an empty claim.

Sentence: {sentence}

Return JSON: {{"claim": "...", "has_claim": true|false}}"""


def extract_claim_about_citation(sentence_with_citation: str) -> str | None:
    result = chat_json([{"role": "user", "content": CLAIM_EXTRACTION_PROMPT.format(sentence=sentence_with_citation)}])
    if not result.get("has_claim"):
        return None
    claim = (result.get("claim") or "").strip()
    return claim or None


ATOMIC_CLAIM_PROMPT = """Break the following passage into a short list of atomic,
standalone factual claims it makes (things that could be checked against another
paper on the same topic). Skip claims that are just about this paper's own novel
contribution, focus on claims about what is generally true, what methods do, or
what was previously found.

Passage: {passage}

Return JSON: {{"claims": ["...", "..."]}}"""


def extract_atomic_claims(passage: str) -> list[str]:
    result = chat_json([{"role": "user", "content": ATOMIC_CLAIM_PROMPT.format(passage=passage[:1500])}])
    return [c.strip() for c in result.get("claims", []) if c.strip()]
