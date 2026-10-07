"""
Custom metrics that don't need an external eval library: retrieval
hit-rate/MRR, a simple answer-contains-keyword check, citation accuracy,
and trust-score calibration. These are cheap to compute and don't depend
on ragas being correctly configured, so the eval harness still produces
useful numbers even if the ragas integration breaks on a version bump.
"""

from dataclasses import dataclass


def hit_rate(retrieved_paper_ids: list[str], relevant_paper_id: str) -> float:
    return 1.0 if relevant_paper_id in retrieved_paper_ids else 0.0


def mean_reciprocal_rank(retrieved_paper_ids: list[str], relevant_paper_id: str) -> float:
    for rank, paper_id in enumerate(retrieved_paper_ids, start=1):
        if paper_id == relevant_paper_id:
            return 1.0 / rank
    return 0.0


def keyword_match(answer: str, expected_keywords: list[str]) -> float:
    answer_lower = answer.lower()
    hits = sum(1 for kw in expected_keywords if kw.lower() in answer_lower)
    return hits / len(expected_keywords) if expected_keywords else 1.0


@dataclass
class CalibrationBucket:
    score_range: str
    count: int
    actual_error_rate: float


def trust_calibration(scored_results: list[tuple[int, bool]]) -> list[CalibrationBucket]:
    """
    scored_results: list of (trust_score, was_answer_actually_wrong).
    A well-calibrated trust score means low scores correlate with higher
    actual error rates. This buckets results into ranges so the dashboard
    can plot score vs. observed error rate.
    """
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
