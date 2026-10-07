"""
Checks that the generated answer's citations actually say what the answer
claims they say. This runs after generation, on the model's own output,
so it catches the common failure mode where a model cites a real passage
but mischaracterizes what it says.
"""

import re
from dataclasses import dataclass

from app.core.llm import chat_json
from app.generation.answer_generator import GeneratedAnswer

CITATION_PATTERN = re.compile(r"\[(\d+)\]")

VERIFY_PROMPT = """A sentence claims the following, citing a source passage:

Sentence: "{sentence}"
Source passage: "{passage}"

Does the source passage support the claim made in the sentence? Answer with
one of: supported, partially_supported, unsupported, contradicted.

Return JSON: {{"verdict": "...", "rationale": "one short sentence"}}"""


@dataclass
class CitationCheck:
    sentence: str
    source_index: int
    verdict: str
    rationale: str


def _split_sentences(text: str) -> list[str]:
    # Good enough splitter for this purpose, we don't need to handle every
    # edge case of sentence boundary detection, just common prose.
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]


def verify_citations(generated: GeneratedAnswer) -> list[CitationCheck]:
    checks: list[CitationCheck] = []
    sources_by_index = {s.index: s for s in generated.sources}

    for sentence in _split_sentences(generated.answer):
        markers = [int(m) for m in CITATION_PATTERN.findall(sentence)]
        if not markers:
            continue
        for marker in markers:
            source = sources_by_index.get(marker)
            if source is None:
                continue
            clean_sentence = CITATION_PATTERN.sub("", sentence).strip()
            result = chat_json(
                [{"role": "user", "content": VERIFY_PROMPT.format(sentence=clean_sentence, passage=source.text)}]
            )
            checks.append(
                CitationCheck(
                    sentence=clean_sentence,
                    source_index=marker,
                    verdict=result.get("verdict", "unresolved"),
                    rationale=result.get("rationale", ""),
                )
            )
    return checks


def pass_rate(checks: list[CitationCheck]) -> float:
    if not checks:
        return 1.0  # no citations to check means nothing was flagged as wrong
    supported = sum(1 for c in checks if c.verdict == "supported")
    return supported / len(checks)
