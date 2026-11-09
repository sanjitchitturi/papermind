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
from app.retrieval.passages import retrieve
from app.retrieval.search import search

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
    series = {"hit@5": [], "hit@10": [], "mrr": [], "ndcg@10": []}
    for pair in pairs:
        ids = _ids(search(pair["question"], limit=20))
        relevant = pair["relevant_paper"]
        series["hit@5"].append(hit_rate_at_k(ids, relevant, 5))
        series["hit@10"].append(hit_rate_at_k(ids, relevant, 10))
        series["mrr"].append(mean_reciprocal_rank(ids, relevant))
        series["ndcg@10"].append(ndcg_at_k(ids, relevant, 10))
    by_config = {"bm25": series}

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
    from app.db.session import init_db

    init_db()
    print(json.dumps(evaluate_retrieval(), indent=2))
