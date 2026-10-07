from app.trust.trust_score import TrustSignals, compute_retrieval_margin, compute_trust


def test_retrieval_margin_high_when_top_result_dominates():
    margin = compute_retrieval_margin([0.9, 0.2, 0.1])
    assert margin > 0.6


def test_retrieval_margin_low_when_scores_are_similar():
    margin = compute_retrieval_margin([0.5, 0.49, 0.48])
    assert margin < 0.1


def test_retrieval_margin_with_single_result_is_neutral():
    assert compute_retrieval_margin([0.9]) == 0.5


def test_compute_trust_abstains_on_weak_signals():
    result = compute_trust(TrustSignals(retrieval_margin=0.1, citation_pass_rate=0.2, self_consistency=0.1))
    assert result.should_abstain is True
    assert result.score < 45


def test_compute_trust_does_not_abstain_on_strong_signals():
    result = compute_trust(TrustSignals(retrieval_margin=0.8, citation_pass_rate=1.0, self_consistency=0.9))
    assert result.should_abstain is False
    assert result.score >= 80
