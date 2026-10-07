"""Question answering: retrieve, rerank, generate or extract, verify, score."""

import json
import time

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from app.api.deps import SessionDep, rate_limit
from app.api.schemas import ChatRequest, ChatResponse, SourceOut, TrustSignalsOut
from app.db.models import AnswerRecord
from app.generation.answer_generator import generate_answer
from app.generation.citation_verifier import pass_rate, verify_citations
from app.retrieval.hybrid_search import retrieve
from app.trust.trust_score import compute_self_consistency, compute_trust

router = APIRouter(prefix="/chat", tags=["chat"])


def _run_chat(request: ChatRequest, session: SessionDep) -> ChatResponse:
    t0 = time.perf_counter()
    paper_ids = [request.paper_id] if request.paper_id else None
    passages = retrieve(request.question, paper_ids=paper_ids)
    generated = generate_answer(request.question, passages)
    checks = verify_citations(generated)
    citation_rate = pass_rate(checks)
    consistency = (
        compute_self_consistency(request.question, passages, generated.answer)
        if generated.mode == "generative"
        else 0.7
    )
    trust = compute_trust(passages, generated, citation_rate, consistency)
    answer = generated.answer
    if trust.should_abstain and generated.mode == "generative":
        answer = (
            "I don't have enough confidence in the available evidence to answer this well. "
            f"({trust.explanation}) Here is the best attempt, treat it with caution:\n\n{generated.answer}"
        )
    latency = int((time.perf_counter() - t0) * 1000)
    record = AnswerRecord(
        question=request.question,
        answer=answer,
        mode=generated.mode,
        paper_id=request.paper_id,
        trust_score=trust.score,
        signals_json=json.dumps(trust.as_json()["signals"]),
        abstained=trust.should_abstain,
        latency_ms=latency,
    )
    session.add(record)
    session.commit()
    return ChatResponse(
        answer_id=str(record.id),
        answer=answer,
        mode=generated.mode,
        sources=[
            SourceOut(
                index=s.index,
                paper_id=s.paper_id,
                paper_title=s.paper_title,
                section=s.section,
                page=s.page,
                text=s.text,
            )
            for s in generated.sources
        ],
        trust_score=trust.score,
        trust_explanation=trust.explanation,
        trust_signals=TrustSignalsOut(**trust.as_json()["signals"]),
        abstained=trust.should_abstain,
        latency_ms=latency,
    )


@router.post("", response_model=ChatResponse)
def chat_endpoint(request: ChatRequest, session: SessionDep, _: None = Depends(rate_limit)):
    return _run_chat(request, session)


@router.post("/stream")
def chat_stream(request: ChatRequest, session: SessionDep, _: None = Depends(rate_limit)):
    def events():
        yield _sse({"stage": "retrieving", "detail": "Dense + BM25 search, then cross-encoder rerank"})
        yield _sse({"stage": "complete", "result": _run_chat(request, session).model_dump()})

    return StreamingResponse(events(), media_type="text/event-stream")


def _sse(payload: dict) -> str:
    import json as _json

    return f"data: {_json.dumps(payload)}\n\n"
