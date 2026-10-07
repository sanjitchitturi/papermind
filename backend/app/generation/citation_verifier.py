"""
Checks that a generated answer's citations actually support the claims
they are attached to. Runs after generation, on the model's own output,
so it catches the common failure where a model cites a real passage but
mischaracterizes it.

All cited sentences go in one JSON judge call rather than one call per
citation, which is both cheaper and more consistent.
"""

import re
from dataclasses import dataclass

from app.core.llm import chat_json, llm_available
from app.generation.answer_generator import GeneratedAnswer

CITATION_PATTERN = re.compile(r"\[(\d+)\]")

VERIFY_PROMPT = """A generated answer cites numbered source passages. For each cited sentence,
does the cited passage actually support the claim?

Return JSON: {{"checks": [{{"sentence": "...", "source": 1, "verdict": "supported|partially_supported|unsupported|contradicted", "rationale": "one short sentence"}}]}}

Passages:
{passages}

Answer:
{answer}"""


@dataclass
class CitationCheck:
    sentence: str
    source_index: int
    verdict: str
    rationale: str


def _split_sentences(text: str) -> list[str]:
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]


def verify_citations(generated: GeneratedAnswer) -> list[CitationCheck]:
    if generated.mode != "generative" or not llm_available():
        return []
    cited = [s for s in _split_sentences(generated.answer) if CITATION_PATTERN.search(s)]
    if not cited:
        return []
    passages = "\n\n".join(f"[{s.index}] {s.text[:900]}" for s in generated.sources)
    result = chat_json([{"role": "user", "content": VERIFY_PROMPT.format(passages=passages, answer=generated.answer)}])
    allowed = {"supported", "partially_supported", "unsupported", "contradicted"}
    checks: list[CitationCheck] = []
    for item in result.get("checks", []):
        try:
            source = int(item.get("source", 0))
        except (TypeError, ValueError):
            continue
        verdict = str(item.get("verdict", "unsupported"))
        if verdict not in allowed:
            verdict = "unsupported"
        checks.append(
            CitationCheck(
                sentence=str(item.get("sentence") or ""),
                source_index=source,
                verdict=verdict,
                rationale=str(item.get("rationale") or ""),
            )
        )
    return checks


def pass_rate(checks: list[CitationCheck]) -> float:
    if not checks:
        return 1.0
    supported = sum(1 for c in checks if c.verdict == "supported")
    return supported / len(checks)
