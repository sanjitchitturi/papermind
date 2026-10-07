from app.generation.answer_generator import GeneratedAnswer
from app.ml.reranker import sigmoid
from app.retrieval.hybrid_search import Passage, retrieval_margin
from app.trust.trust_score import compute_trust


def _passage(score: float, logit: float | None = None) -> Passage:
    return Passage(
        chunk_id="c",
        paper_id="p",
        paper_title="T",
        arxiv_id="",
        section="method",
        page=1,
        text="hello",
        fused_score=score,
        rerank_logit=logit,
        rerank_prob=sigmoid(logit) if logit is not None else None,
    )


def test_retrieval_margin_high_when_top_result_dominates():
    margin = retrieval_margin([_passage(0.9, 6.0), _passage(0.2, -4.0), _passage(0.1, -5.0)])
    assert margin > 0.6


def test_retrieval_margin_low_when_scores_are_similar():
    margin = retrieval_margin([_passage(0.5), _passage(0.49), _passage(0.48)])
    assert margin < 0.1


def test_retrieval_margin_with_single_result_is_neutral():
    assert retrieval_margin([_passage(0.9)]) == 0.5


def test_compute_trust_abstains_on_weak_signals():
    generated = GeneratedAnswer(answer="guess", sources=[], mode="generative")
    result = compute_trust(
        [_passage(0.2, -2.0), _passage(0.19, -2.1)],
        generated,
        citation_pass_rate=0.2,
        self_consistency=0.1,
    )
    assert result.should_abstain is True
    assert result.score < 45


def test_compute_trust_does_not_abstain_on_strong_signals():
    generated = GeneratedAnswer(answer="solid", sources=[], mode="generative")
    result = compute_trust(
        [_passage(0.9, 6.0), _passage(0.1, -3.0)],
        generated,
        citation_pass_rate=1.0,
        self_consistency=0.9,
    )
    assert result.should_abstain is False
    assert result.score >= 80


def test_extractive_trust_ignores_citation_rate():
    generated = GeneratedAnswer(answer="quoted", sources=[], mode="extractive")
    weak_citations = compute_trust([_passage(0.9, 6.0)], generated, citation_pass_rate=0.0, self_consistency=0.0)
    strong_citations = compute_trust([_passage(0.9, 6.0)], generated, citation_pass_rate=1.0, self_consistency=1.0)
    assert weak_citations.score == strong_citations.score
