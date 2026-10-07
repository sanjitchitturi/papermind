from dataclasses import dataclass


def hit_rate_at_k(retrieved_ids: list[str], relevant_id: str, k: int) -> float:
    return 1.0 if relevant_id in retrieved_ids[:k] else 0.0


def mean_reciprocal_rank(retrieved_ids: list[str], relevant_id: str) -> float:
    for rank, paper_id in enumerate(retrieved_ids, start=1):
        if paper_id == relevant_id:
            return 1.0 / rank
    return 0.0


def keyword_match(answer: str, expected_keywords: list[str]) -> float:
    answer_lower = answer.lower()
    hits = sum(1 for kw in expected_keywords if kw.lower() in answer_lower)
    return hits / len(expected_keywords) if expected_keywords else 1.0


def ndcg_at_k(retrieved_ids: list[str], relevant_id: str, k: int) -> float:
    """Single-relevant-document nDCG, which reduces to 1/log2(rank+1) if found in the top k."""
    import math

    for rank, paper_id in enumerate(retrieved_ids[:k], start=1):
        if paper_id == relevant_id:
            return 1.0 / math.log2(rank + 1)
    return 0.0


@dataclass
class CalibrationBucket:
    score_range: str
    count: int
    actual_error_rate: float


def trust_calibration(scored_results: list[tuple[int, bool]]) -> list[CalibrationBucket]:
    buckets = [(0, 40), (40, 60), (60, 80), (80, 101)]
    results = []
    for lo, hi in buckets:
        in_bucket = [wrong for score, wrong in scored_results if lo <= score < hi]
        if not in_bucket:
            results.append(CalibrationBucket(score_range=f"{lo}-{hi - 1}", count=0, actual_error_rate=0.0))
            continue
        error_rate = sum(1 for wrong in in_bucket if wrong) / len(in_bucket)
        results.append(CalibrationBucket(score_range=f"{lo}-{hi - 1}", count=len(in_bucket), actual_error_rate=error_rate))
    return results
