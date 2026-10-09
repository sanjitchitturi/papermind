from collections.abc import Callable
from dataclasses import dataclass, field

from app.agent.literature_matrix import MatrixRow, build_matrix
from app.agent.planner import critique_coverage, decompose
from app.core.llm import LLMProviderError, chat, llm_available
from app.retrieval.hybrid_search import retrieve

MAX_LOOPS = 2

SYNTHESIS_PROMPT = """Write a short literature review answering the question,
using the evidence passages. Cite papers by title. Be direct about where
the evidence is thin or where papers disagree.

Question: {question}

Evidence:
{evidence}

Literature review:"""


@dataclass
class TraceStep:
    kind: str
    detail: str


@dataclass
class ResearchResult:
    narrative: str
    matrix: list[MatrixRow]
    trace: list[TraceStep] = field(default_factory=list)


def run_research_mode(question: str, on_step: Callable[[TraceStep], None] | None = None) -> ResearchResult:
    trace: list[TraceStep] = []

    def emit(kind: str, detail: str) -> None:
        step = TraceStep(kind=kind, detail=detail)
        trace.append(step)
        if on_step:
            on_step(step)

    sub_questions = decompose(question)
    emit("decompose", "Broke the question into: " + "; ".join(sub_questions))

    passages_by_paper: dict[str, tuple[str, list[str]]] = {}
    evidence_summaries: list[str] = []

    for _ in range(MAX_LOOPS):
        for sub in sub_questions:
            hits = retrieve(sub)
            emit("retrieve", f"'{sub}' → {len(hits)} passages")
            for hit in hits:
                if hit.paper_id not in passages_by_paper:
                    passages_by_paper[hit.paper_id] = (hit.paper_title, [])
                passages_by_paper[hit.paper_id][1].append(hit.text)
                evidence_summaries.append(f"({hit.paper_title}) {hit.text[:240]}")
        sufficient, missing = critique_coverage(question, evidence_summaries[:20])
        emit("critique", f"sufficient={sufficient}" + (f", missing={missing}" if missing else ""))
        if sufficient or not missing:
            break
        sub_questions = [missing]

    if llm_available():
        try:
            narrative = chat(
                [{"role": "user", "content": SYNTHESIS_PROMPT.format(question=question, evidence="\n\n".join(evidence_summaries[:24]))}]
            )
        except LLMProviderError:
            narrative = _retrieval_only(passages_by_paper, evidence_summaries, provider_failed=True)
    else:
        narrative = _retrieval_only(passages_by_paper, evidence_summaries, provider_failed=False)
    emit("synthesize", "Wrote the review from gathered evidence")
    matrix = build_matrix(passages_by_paper)
    return ResearchResult(narrative=narrative, matrix=matrix, trace=trace)


def _retrieval_only(passages_by_paper: dict, evidence_summaries: list[str], provider_failed: bool) -> str:
    titles = sorted({title for title, _ in passages_by_paper.values()})
    lead = (
        "The language model did not respond, so this is a retrieval-only research pass."
        if provider_failed
        else "No language model is configured, so this is a retrieval-only research pass."
    )
    return (
        lead
        + f"\n\nPapers consulted: {', '.join(titles) or 'none'}.\n\n"
        + "\n\n".join(evidence_summaries[:8])
    )
