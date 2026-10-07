"""
Orchestrates Research Mode end to end: decompose the question, retrieve
evidence for each sub-question, self-critique whether coverage is
sufficient and loop if not, then synthesize a narrative review plus a
comparison matrix. Every step is recorded into a reasoning trace that the
frontend renders so the agent's process is visible, not just its output.
"""

from dataclasses import dataclass, field

from app.agent.literature_matrix import MatrixRow, build_matrix
from app.agent.planner import critique_coverage, decompose
from app.core.llm import chat
from app.retrieval.hybrid_search import retrieve

MAX_LOOPS = 2  # keeps worst-case latency and API cost bounded for a demo-sized project

SYNTHESIS_PROMPT = """Write a short literature review answering the question below,
using the evidence passages provided. Cite papers by title inline. Be direct about
where the evidence is thin or where papers disagree.

Question: {question}

Evidence:
{evidence}

Literature review:"""


@dataclass
class TraceStep:
    kind: str  # "decompose" | "retrieve" | "critique" | "synthesize"
    detail: str


@dataclass
class ResearchResult:
    narrative: str
    matrix: list[MatrixRow]
    trace: list[TraceStep] = field(default_factory=list)


def run_research_mode(question: str) -> ResearchResult:
    trace: list[TraceStep] = []

    sub_questions = decompose(question)
    trace.append(TraceStep(kind="decompose", detail=f"Broke question into: {sub_questions}"))

    passages_by_paper: dict[str, tuple[str, list[str]]] = {}
    evidence_summaries: list[str] = []

    for _loop_index in range(MAX_LOOPS):
        for sub_question in sub_questions:
            hits = retrieve(sub_question)
            trace.append(TraceStep(kind="retrieve", detail=f"'{sub_question}' -> {len(hits)} passages"))

            for hit in hits:
                paper_id = hit["payload"].get("paper_id", "")
                paper_title = hit["payload"].get("paper_title", "")
                text = hit["payload"].get("text", "")
                if paper_id not in passages_by_paper:
                    passages_by_paper[paper_id] = (paper_title, [])
                passages_by_paper[paper_id][1].append(text)
                evidence_summaries.append(f"({paper_title}) {text[:200]}")

        sufficient, missing_sub_question = critique_coverage(question, evidence_summaries[:20])
        trace.append(TraceStep(kind="critique", detail=f"sufficient={sufficient}, missing={missing_sub_question}"))

        if sufficient or missing_sub_question is None:
            break
        sub_questions = [missing_sub_question]

    evidence_block = "\n\n".join(evidence_summaries[:30])
    narrative = chat([{"role": "user", "content": SYNTHESIS_PROMPT.format(question=question, evidence=evidence_block)}])
    trace.append(TraceStep(kind="synthesize", detail="Generated narrative review from gathered evidence"))

    matrix = build_matrix(passages_by_paper)

    return ResearchResult(narrative=narrative, matrix=matrix, trace=trace)
