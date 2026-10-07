"""
Turns a set of retrieved passages, grouped by paper, into a structured
comparison table: method, dataset, metric/result, and limitations per
paper. This is what makes Research Mode output something closer to a
literature review table than a long paragraph of prose.
"""

from dataclasses import dataclass

from app.core.llm import chat_json

EXTRACTION_PROMPT = """Based on the passages below from a single paper, extract a
structured summary for a literature review comparison table. If a field isn't
mentioned in the passages, use an empty string rather than guessing.

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
    passage_block = "\n\n".join(passages[:6])  # cap how much goes into one extraction call
    result = chat_json([{"role": "user", "content": EXTRACTION_PROMPT.format(title=paper_title, passages=passage_block)}])
    return MatrixRow(
        paper_title=paper_title,
        paper_id=paper_id,
        method=result.get("method", ""),
        dataset=result.get("dataset", ""),
        metric_result=result.get("metric_result", ""),
        limitations=result.get("limitations", ""),
    )


def build_matrix(passages_by_paper: dict[str, tuple[str, list[str]]]) -> list[MatrixRow]:
    """passages_by_paper: {paper_id: (paper_title, [passage_text, ...])}"""
    return [build_row(paper_id, title, texts) for paper_id, (title, texts) in passages_by_paper.items()]
