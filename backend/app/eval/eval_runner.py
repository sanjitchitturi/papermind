"""
Eval harness.

Retrieval eval is local and cheap: it runs four ablations (dense, sparse,
hybrid, hybrid+rerank) against the same questions so the dashboard can
show that each stage actually moves the metric, rather than asserting it.

Generation eval is optional and only runs when an LLM is configured.
"""

import json
import logging
from pathlib import Path

from sqlmodel import Session

from app.core.config import get_settings
from app.core.jobs import JobContext
from app.db.models import EvalRun
from app.db.session import engine
from app.eval.metrics import hit_rate_at_k, keyword_match, mean_reciprocal_rank, ndcg_at_k
from app.generation.answer_generator import generate_answer
from app.generation.citation_verifier import pass_rate, verify_citations
from app.ml.reranker import get_reranker
from app.retrieval.hybrid_search import _to_passage, rerank_passages, retrieve, retrieve_hits_only, sparse_only

logger = logging.getLogger(__name__)
DATASET_PATH = Path(__file__).parent / "eval_dataset.json"


def load_dataset() -> dict:
    with open(DATASET_PATH) as f:
        return json.load(f)


def _avg(values: list[float]) -> float:
    return round(sum(values) / len(values), 4) if values else 0.0


def _ids(hits) -> list[str]:
    return [h.payload.get("arxiv_id", "") if hasattr(h, "payload") else h.arxiv_id for h in hits]


def evaluate_retrieval() -> dict:
    pairs = load_dataset()["qa_pairs"]
    reranker = get_reranker()
    configs = {
        "dense": lambda q: retrieve_hits_only(q, use_hybrid=False, limit=20),
        "sparse": lambda q: sparse_only(q, limit=20),
        "hybrid": lambda q: retrieve_hits_only(q, use_hybrid=True, limit=20),
    }

    by_config: dict[str, dict[str, list[float]]] = {
        name: {"hit@5": [], "hit@10": [], "mrr": [], "ndcg@10": []} for name in [*configs, "hybrid+rerank"]
    }

    for pair in pairs:
        q, relevant = pair["question"], pair["relevant_paper"]
        fused_hits = None
        for name, fn in configs.items():
            hits = fn(q)
            if name == "hybrid":
                fused_hits = hits
            ids = _ids(hits)
            by_config[name]["hit@5"].append(hit_rate_at_k(ids, relevant, 5))
            by_config[name]["hit@10"].append(hit_rate_at_k(ids, relevant, 10))
            by_config[name]["mrr"].append(mean_reciprocal_rank(ids, relevant))
            by_config[name]["ndcg@10"].append(ndcg_at_k(ids, relevant, 10))

        if fused_hits is not None and reranker is not None:
            passages = rerank_passages(q, [_to_passage(h) for h in fused_hits])
            ids = [p.arxiv_id for p in passages]
            by_config["hybrid+rerank"]["hit@5"].append(hit_rate_at_k(ids, relevant, 5))
            by_config["hybrid+rerank"]["hit@10"].append(hit_rate_at_k(ids, relevant, 10))
            by_config["hybrid+rerank"]["mrr"].append(mean_reciprocal_rank(ids, relevant))
            by_config["hybrid+rerank"]["ndcg@10"].append(ndcg_at_k(ids, relevant, 10))

    metrics = {"num_questions": len(pairs)}
    for name, series in by_config.items():
        if not series["mrr"]:
            continue
        for key, values in series.items():
            metrics[f"{name}_{key}"] = _avg(values)
    return metrics


def evaluate_generation() -> dict:
    pairs = load_dataset()["qa_pairs"]
    keyword_scores, citation_rates = [], []
    for pair in pairs:
        passages = retrieve(pair["question"])
        if not passages:
            keyword_scores.append(0.0)
            citation_rates.append(0.0)
            continue
        generated = generate_answer(pair["question"], passages)
        keyword_scores.append(keyword_match(generated.answer, pair.get("expected_answer_contains", [])))
        citation_rates.append(pass_rate(verify_citations(generated)))
    return {
        "num_questions": len(pairs),
        "answer_keyword_match": _avg(keyword_scores),
        "citation_pass_rate": _avg(citation_rates),
    }


def persist_run(session: Session, suite: str, metrics: dict, config: dict) -> EvalRun:
    run = EvalRun(
        suite=suite,
        commit_sha=get_settings().git_commit_sha,
        config_json=json.dumps(config),
        metrics_json=json.dumps(metrics),
    )
    session.add(run)
    session.commit()
    return run


def run_eval_job(ctx: JobContext) -> dict:
    import json as _json

    from app.db.models import Job

    with Session(engine) as session:
        job = session.get(Job, ctx.job_id)
        payload = _json.loads(job.input_json) if job else {}
        suite = payload.get("suite", "retrieval")
        ctx.update("running", 0.1, f"Running {suite} eval")
        metrics = evaluate_generation() if suite == "generation" else evaluate_retrieval()
        run = persist_run(session, suite, metrics, payload)
        ctx.update("complete", 1.0, "Eval stored")
        return {"run_id": str(run.id), "metrics": metrics}


if __name__ == "__main__":
    from app.core.vector_store import ensure_collection
    from app.db.session import init_db

    init_db()
    ensure_collection()
    print(json.dumps(evaluate_retrieval(), indent=2))
