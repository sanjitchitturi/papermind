"""
Runs the eval suite end to end through the real pipeline (retrieval,
reranking, generation, citation verification, trust scoring) and records
the results as an EvalRun row.

We considered using the ragas library for the standard RAG metrics
(faithfulness, answer relevancy, context precision) but it pulls in a
large dependency tree (langchain, datasets, pandas, etc.) for three
numbers we can compute directly against our own pipeline output. The
metrics in metrics.py cover retrieval quality, answer correctness, and
citation accuracy without that overhead. Swapping in ragas later for the
standard metrics would be a small, isolated change if it's ever worth
the extra dependency weight.
"""

import json
import os
from pathlib import Path

from sqlmodel import Session

from app.db.models import EvalRun
from app.eval.metrics import hit_rate, keyword_match, mean_reciprocal_rank
from app.generation.answer_generator import generate_answer
from app.generation.citation_verifier import pass_rate, verify_citations
from app.retrieval.hybrid_search import retrieve
from app.retrieval.reranker import rerank

DATASET_PATH = Path(__file__).parent / "eval_dataset.json"


def load_dataset() -> dict:
    with open(DATASET_PATH) as f:
        return json.load(f)


def run_eval(session: Session, commit_sha: str = "local", pipeline_config: str = "full") -> EvalRun:
    dataset = load_dataset()
    qa_pairs = dataset["qa_pairs"]

    hit_rates, mrrs, keyword_scores, citation_pass_rates = [], [], [], []

    for pair in qa_pairs:
        question = pair["question"]
        candidates = retrieve(question, use_rewriting=pipeline_config != "baseline")
        # qa_pairs reference papers by arXiv id (that's what's in eval_dataset.json),
        # so we compare against the arxiv_id stored in each chunk's payload rather
        # than the internal paper UUID.
        retrieved_paper_ids = [c["payload"].get("arxiv_id", "") for c in candidates]

        hit_rates.append(hit_rate(retrieved_paper_ids, pair["relevant_paper"]))
        mrrs.append(mean_reciprocal_rank(retrieved_paper_ids, pair["relevant_paper"]))

        if not candidates:
            keyword_scores.append(0.0)
            citation_pass_rates.append(0.0)
            continue

        top_passages = rerank(question, candidates) if pipeline_config == "full" else candidates[:6]
        generated = generate_answer(question, top_passages)
        keyword_scores.append(keyword_match(generated.answer, pair.get("expected_answer_contains", [])))

        checks = verify_citations(generated)
        citation_pass_rates.append(pass_rate(checks))

    metrics = {
        "retrieval_hit_rate": _avg(hit_rates),
        "retrieval_mrr": _avg(mrrs),
        "answer_keyword_match": _avg(keyword_scores),
        "citation_pass_rate": _avg(citation_pass_rates),
        "num_questions": len(qa_pairs),
    }

    eval_run = EvalRun(commit_sha=commit_sha, pipeline_config=pipeline_config, metrics_json=json.dumps(metrics))
    session.add(eval_run)
    session.commit()
    return eval_run


def _avg(values: list[float]) -> float:
    return round(sum(values) / len(values), 4) if values else 0.0


if __name__ == "__main__":
    from app.db.session import get_session, init_db

    init_db()
    commit = os.environ.get("GIT_COMMIT_SHA", "local")
    session = next(get_session())
    run = run_eval(session, commit_sha=commit)
    print(f"Eval run {run.id} stored. Metrics: {run.metrics_json}")
