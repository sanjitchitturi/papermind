from dataclasses import dataclass

from app.core.llm import chat_json, llm_available
from app.db.models import EntityType
from app.graph.entity_extractor import extract_entities

EXTRACTION_PROMPT = """Based on the passages from a single paper, fill a literature
review comparison row. Use an empty string rather than guessing.

Paper title: {title}
Passages:
{passages}

Return JSON: {{"method": "...", "dataset": "...", "metric_result": "...", "limitations": "..."}}"""


@dataclass
class MatrixRow:
    paper_title: str
    paper_id: str
    method: str
    dataset: str
    metric_result: str
    limitations: str


def build_row(paper_id: str, paper_title: str, passages: list[str]) -> MatrixRow:
    if llm_available():
        result = chat_json(
            [{"role": "user", "content": EXTRACTION_PROMPT.format(title=paper_title, passages="\n\n".join(passages[:5]))}]
        )
        return MatrixRow(
            paper_title=paper_title,
            paper_id=paper_id,
            method=result.get("method", ""),
            dataset=result.get("dataset", ""),
            metric_result=result.get("metric_result", ""),
            limitations=result.get("limitations", ""),
        )
    names = {t: [] for t in EntityType}
    for name, etype, _ in extract_entities(" ".join(passages)[:8000]):
        names[etype].append(name)
    return MatrixRow(
        paper_title=paper_title,
        paper_id=paper_id,
        method=", ".join(names[EntityType.method][:4]),
        dataset=", ".join(names[EntityType.dataset][:4]),
        metric_result=", ".join(names[EntityType.metric][:4]),
        limitations="",
    )


def build_matrix(passages_by_paper: dict[str, tuple[str, list[str]]]) -> list[MatrixRow]:
    return [build_row(paper_id, title, texts) for paper_id, (title, texts) in passages_by_paper.items()]
