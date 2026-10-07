"""
The main question-answering endpoint: retrieve, rerank, generate, verify
citations, compute a trust score, and decide whether to answer or abstain.
This is the request path that ties together most of the core RAG pipeline.
"""

from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.api.schemas import ChatRequest, ChatResponse, SourceOut
from app.db.models import AnswerRecord
from app.db.session import get_session
from app.generation.answer_generator import generate_answer
from app.generation.citation_verifier import pass_rate, verify_citations
from app.retrieval.hybrid_search import retrieve
from app.retrieval.reranker import rerank
from app.trust.trust_score import TrustSignals, compute_retrieval_margin, compute_self_consistency, compute_trust

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
def chat(request: ChatRequest, session: Session = Depends(get_session)):
    candidates = retrieve(request.question, paper_id=request.paper_id)

    if not candidates:
        answer_record = AnswerRecord(
            question=request.question,
            answer="I could not find any relevant passages in the corpus to answer this.",
            paper_id=request.paper_id,
            trust_score=0,
            trust_explanation="No retrieval results, nothing to ground an answer in.",
            abstained=True,
        )
        session.add(answer_record)
        session.commit()
        return ChatResponse(
            answer_id=str(answer_record.id),
            answer=answer_record.answer,
            sources=[],
            trust_score=0,
            trust_explanation=answer_record.trust_explanation,
            abstained=True,
        )

    top_passages = rerank(request.question, candidates)
    generated = generate_answer(request.question, top_passages)

    checks = verify_citations(generated)
    citation_rate = pass_rate(checks)

    retrieval_scores = [c["score"] for c in candidates]
    passage_block = "\n\n".join(f"[{s.index}] {s.text}" for s in generated.sources)
    self_consistency = compute_self_consistency(request.question, passage_block, generated.answer)

    trust = compute_trust(
        TrustSignals(
            retrieval_margin=compute_retrieval_margin(retrieval_scores),
            citation_pass_rate=citation_rate,
            self_consistency=self_consistency,
        )
    )

    final_answer = generated.answer
    if trust.should_abstain:
        final_answer = (
            "I don't have enough confidence in the available evidence to answer this well. "
            f"({trust.explanation}) Here is my best attempt, treat it with caution:\n\n{generated.answer}"
        )

    answer_record = AnswerRecord(
        question=request.question,
        answer=final_answer,
        paper_id=request.paper_id,
        trust_score=trust.score,
        trust_explanation=trust.explanation,
        abstained=trust.should_abstain,
    )
    session.add(answer_record)
    session.commit()

    return ChatResponse(
        answer_id=str(answer_record.id),
        answer=final_answer,
        sources=[
            SourceOut(index=s.index, paper_id=s.paper_id, paper_title=s.paper_title, section=s.section, text=s.text)
            for s in generated.sources
        ],
        trust_score=trust.score,
        trust_explanation=trust.explanation,
        abstained=trust.should_abstain,
    )
