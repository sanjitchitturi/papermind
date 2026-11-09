import re
from dataclasses import dataclass

from app.core.llm import LLMProviderError, chat_json, llm_available
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
    expected = [
        (sentence, int(match))
        for sentence in _split_sentences(generated.answer)
        for match in (CITATION_PATTERN.findall(sentence) or ["0"])
    ]
    if not expected:
        return []
    passages = "\n\n".join(f"[{s.index}] {s.text[:900]}" for s in generated.sources)
    try:
        result = chat_json(
            [{"role": "user", "content": VERIFY_PROMPT.format(passages=passages, answer=generated.answer)}]
        )
    except LLMProviderError:
        return []
    allowed = {"supported", "partially_supported", "unsupported", "contradicted"}
    checks: dict[tuple[str, int], CitationCheck] = {}
    items = result.get("checks", [])
    if not isinstance(items, list):
        return []
    for item in items:
        if not isinstance(item, dict):
            continue
        try:
            source = int(item.get("source", 0))
        except (TypeError, ValueError):
            continue
        if source not in {s.index for s in generated.sources}:
            continue
        verdict = str(item.get("verdict", "unsupported"))
        if verdict not in allowed:
            verdict = "unsupported"
        sentence = str(item.get("sentence") or "")
        key = (sentence, source)
        if key not in expected:
            continue
        check = CitationCheck(
            sentence=sentence,
            source_index=source,
            verdict=verdict,
            rationale=str(item.get("rationale") or ""),
        )
        previous = checks.get(key)
        if previous is None or check.verdict != "supported":
            checks[key] = check
    return [
        checks.get((sentence, source))
        or CitationCheck(sentence, source, "unsupported", "No matching verification result")
        for sentence, source in expected
    ]


def pass_rate(checks: list[CitationCheck]) -> float:
    if not checks:
        return 0.0
    supported = sum(1 for c in checks if c.verdict == "supported")
    return supported / len(checks)
