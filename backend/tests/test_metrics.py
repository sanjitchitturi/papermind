from app.eval.metrics import hit_rate, keyword_match, mean_reciprocal_rank, trust_calibration


def test_hit_rate():
    assert hit_rate(["a", "b", "c"], "b") == 1.0
    assert hit_rate(["a", "b", "c"], "z") == 0.0


def test_mean_reciprocal_rank():
    assert mean_reciprocal_rank(["a", "b", "c"], "a") == 1.0
    assert mean_reciprocal_rank(["a", "b", "c"], "b") == 0.5
    assert mean_reciprocal_rank(["a", "b", "c"], "z") == 0.0


def test_keyword_match():
    assert keyword_match("The model uses self-attention.", ["self-attention"]) == 1.0
    assert keyword_match("The model uses convolutions.", ["self-attention"]) == 0.0
    assert keyword_match("masked language model objective", ["masked", "objective"]) == 1.0


def test_trust_calibration_buckets_by_score_range():
    results = [(10, True), (30, False), (50, True), (90, False), (95, False)]
    buckets = trust_calibration(results)
    low_bucket = next(b for b in buckets if b.score_range == "0-39")
    assert low_bucket.count == 2
    assert low_bucket.actual_error_rate == 0.5

    high_bucket = next(b for b in buckets if b.score_range == "80-100")
    assert high_bucket.count == 2
    assert high_bucket.actual_error_rate == 0.0
