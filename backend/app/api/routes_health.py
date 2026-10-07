from fastapi import APIRouter
from sqlmodel import select

from app.api.deps import SessionDep
from app.core.config import get_settings
from app.core.llm import llm_available, provider_host
from app.core.vector_store import count_points
from app.core.vector_store import healthy as qdrant_healthy
from app.db.models import Paper
from app.ml.registry import DENSE_MODELS, RERANKERS

router = APIRouter(tags=["meta"])


@router.get("/health")
def health():
    settings = get_settings()
    db_ok = True
    try:
        from sqlalchemy import text

        from app.db.session import engine

        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception:  # noqa: BLE001
        db_ok = False
    return {
        "status": "ok" if db_ok else "degraded",
        "version": settings.app_version,
        "commit": settings.git_commit_sha,
        "postgres": db_ok,
        "qdrant": qdrant_healthy(),
        "llm": llm_available(),
    }


@router.get("/capabilities")
def capabilities(session: SessionDep):
    settings = get_settings()
    n_papers = len(session.exec(select(Paper)).all())
    embed_spec = DENSE_MODELS.get(settings.embedding_model)
    rerank_spec = RERANKERS.get(settings.reranker_model)
    return {
        "embedding_model": settings.embedding_model,
        "embedding_description": embed_spec.description if embed_spec else settings.embedding_model,
        "embedding_dim": embed_spec.dim if embed_spec else None,
        "reranker_model": settings.reranker_model,
        "reranker_description": rerank_spec.description if rerank_spec else settings.reranker_model,
        "llm_configured": llm_available(),
        "llm_model": settings.llm_model if llm_available() else None,
        "llm_host": provider_host() if llm_available() else None,
        "papers": n_papers,
        "max_papers": settings.max_papers,
        "chunks_indexed": count_points() if qdrant_healthy() else 0,
    }
