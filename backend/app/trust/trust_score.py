import math
from dataclasses import asdict, dataclass

from app.core.config import get_settings
from app.core.llm import LLMProviderError, chat, llm_available
from app.generation.answer_generator import GeneratedAnswer
from app.retrieval.passages import Passage, retrieval_margin


def sigmoid(x: float) -> float:
    return 1 / (1 + math.exp(-max(-700, min(700, x))))


@dataclass
class TrustSignals:
    retrieval_margin: float
    rerank_confidence: float
    citation_pass_rate: float
    self_consistency: float
    n_sources: int
    generative: bool


@dataclass
class TrustResult:
    score: int
    explanation: str
    should_abstain: bool
    signals: TrustSignals

    def as_json(self) -> dict:
        return {
            "score": self.score,
            "explanation": self.explanation,
            "should_abstain": self.should_abstain,
            "signals": asdict(self.signals),
        }


def rerank_confidence(passages: list[Passage]) -> float:
    if not passages or passages[0].rerank_logit is None:
        return 0.0
    return sigmoid(passages[0].rerank_logit)


def compute_self_consistency(question: str, passages: list[Passage], first_answer: str) -> float:
    """
    One extra generation at higher temperature. Jaccard overlap of tokens
    is a cheap stand-in for sampling many completions: enough to catch
    cases where the model is clearly unstable on this question, cheap
    enough to run on every request.
    """
    if not llm_available() or not get_settings().trust_self_consistency:
        return 0.0
    block = "\n\n".join(f"[{i + 1}] {p.text}" for i, p in enumerate(passages[:4]))
    try:
        second = chat(
            [{"role": "user", "content": f"Passages:\n{block}\n\nQuestion: {question}\n\nAnswer:"}],
            temperature=0.8,
        )
    except LLMProviderError:
        return 0.0
    a, b = set(first_answer.lower().split()), set(second.lower().split())
    if not a or not b:
        return 0.5
    return len(a & b) / len(a | b)


def compute_trust(
    passages: list[Passage],
    generated: GeneratedAnswer,
    citation_pass_rate: float,
    self_consistency: float,
) -> TrustResult:
    signals = TrustSignals(
        retrieval_margin=retrieval_margin(passages),
        rerank_confidence=rerank_confidence(passages),
        citation_pass_rate=citation_pass_rate,
        self_consistency=self_consistency,
        n_sources=len(passages),
        generative=generated.mode == "generative",
    )
    if signals.generative:
        weighted = (
            0.20 * signals.retrieval_margin
            + 0.20 * signals.rerank_confidence
            + 0.40 * signals.citation_pass_rate
            + 0.20 * signals.self_consistency
        )
    else:
        # Extractive answers don't have generated citations to verify, so
        # the score is about whether retrieval actually found something.
        weighted = (0.5 + 0.5 * signals.retrieval_margin) if passages else 0.0

    score = round(max(0.0, min(1.0, weighted)) * 100)
    reasons = []
    if signals.n_sources == 0:
        reasons.append("no passages were retrieved")
    if signals.citation_pass_rate < 0.7 and signals.generative:
        reasons.append("citation support was not established for every checked claim")
    if signals.retrieval_margin < 0.15:
        reasons.append("top passages were not clearly better than the rest")
    if signals.rerank_confidence < 0.4:
        reasons.append("no neural relevance judgment is available")
    if signals.self_consistency < 0.3 and signals.generative:
        reasons.append("self-consistency was not checked or was low")
    if not reasons:
        reasons.append(
            "retrieval was peaked and citations checked out" if signals.generative else "retrieval was peaked"
        )

    explanation = f"Evidence heuristic {score}/100 (not a probability of correctness): {', '.join(reasons)}."
    should_abstain = score < get_settings().trust_abstain_threshold
    return TrustResult(score=score, explanation=explanation, should_abstain=should_abstain, signals=signals)
