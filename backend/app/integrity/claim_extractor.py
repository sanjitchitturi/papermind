from app.core.llm import chat_json

CLAIM_EXTRACTION_PROMPT = """The following sentence cites a reference. Extract the
specific claim being made about what the cited work showed, found, or proposed.
If the sentence doesn't actually attribute a claim to the citation, return has_claim=false.

Sentence: {sentence}

Return JSON: {{"claim": "...", "has_claim": true}}"""

ATOMIC_CLAIM_PROMPT = """Break the passage into a short list of atomic, standalone
factual claims that could be checked against another paper on the same topic.
Skip this paper's own novel contribution. Focus on what methods do, what was
previously found, or what is generally claimed to be true.

Passage: {passage}

Return JSON: {{"claims": ["...", "..."]}}"""


def extract_claim_about_citation(sentence_with_citation: str) -> str | None:
    result = chat_json([{"role": "user", "content": CLAIM_EXTRACTION_PROMPT.format(sentence=sentence_with_citation)}])
    if not result.get("has_claim"):
        return None
    claim = (result.get("claim") or "").strip()
    return claim or None


def extract_atomic_claims(passage: str) -> list[str]:
    result = chat_json([{"role": "user", "content": ATOMIC_CLAIM_PROMPT.format(passage=passage[:1500])}])
    return [c.strip() for c in result.get("claims", []) if isinstance(c, str) and c.strip()][:8]
