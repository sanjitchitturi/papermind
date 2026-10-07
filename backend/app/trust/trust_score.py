"""
Combines several independent signals into one 0-100 trust score for an
answer, and decides whether the system should abstain instead of
answering.

The goal is to turn "the model sounded confident" into something closer
to a calibrated estimate of whether the answer is actually right. None of
these four signals is reliable alone, retrieval score margins are noisy,
citation verification can miss subtle misrepresentations, and
self-consistency only catches cases where the model itself is unsure.
Combined, they catch more failure modes than any one of them would.
"""

from dataclasses import dataclass

from app.core.config import get_settings
from app.core.llm import chat

settings = get_settings()


@dataclass
class TrustSignals:
    retrieval_margin: float  # 0-1, gap between top result and the rest
    citation_pass_rate: float  # 0-1, from citation_verifier.pass_rate
    self_consistency: float  # 0-1, agreement between repeated generations


@dataclass
class TrustResult:
    score: int
    explanation: str
    should_abstain: bool


def compute_retrieval_margin(scores: list[float]) -> float:
    if len(scores) < 2:
        return 0.5  # not enough results to judge a margin either way
    top = scores[0]
    rest_avg = sum(scores[1:]) / len(scores[1:])
    if top == 0:
        return 0.0
    margin = (top - rest_avg) / top
    return max(0.0, min(1.0, margin))


def compute_self_consistency(question: str, passage_block: str, first_answer: str) -> float:
    """
    Generates a second answer at a higher temperature and checks rough
    agreement with the first. This is a cheap stand-in for sampling many
    completions, one extra call is enough to catch cases where the model
    is clearly unstable on this question.
    """
    second = chat(
        [{"role": "user", "content": f"Passages:\n{passage_block}\n\nQuestion: {question}\n\nAnswer:"}],
        temperature=0.9,
    )
    first_words = set(first_answer.lower().split())
    second_words = set(second.lower().split())
    if not first_words or not second_words:
        return 0.5
    overlap = len(first_words & second_words) / len(first_words | second_words)
    return overlap


def compute_trust(signals: TrustSignals) -> TrustResult:
    # Weighted toward citation pass rate, since a confidently-worded
    # answer that misquotes its sources is the failure mode that matters
    # most for a research assistant.
    weighted = (
        0.25 * signals.retrieval_margin
        + 0.45 * signals.citation_pass_rate
        + 0.30 * signals.self_consistency
    )
    score = round(weighted * 100)

    reasons = []
    if signals.citation_pass_rate < 0.7:
        reasons.append("some citations were not fully supported by their source passages")
    if signals.retrieval_margin < 0.15:
        reasons.append("retrieval results were not clearly better than alternatives")
    if signals.self_consistency < 0.3:
        reasons.append("repeated generations disagreed with each other")
    if not reasons:
        reasons.append("retrieval was strong and citations checked out")

    explanation = f"Trust score {score}/100: {', '.join(reasons)}."
    should_abstain = score < settings.trust_abstain_threshold

    return TrustResult(score=score, explanation=explanation, should_abstain=should_abstain)
