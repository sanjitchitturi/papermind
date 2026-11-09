from fastapi import APIRouter
from sqlalchemy import func, text
from sqlmodel import select

from app.api.deps import SessionDep
from app.core.config import get_settings
from app.core.llm import llm_available, provider_host
from app.db.models import Chunk, Paper
from app.db.session import engine

router = APIRouter(tags=["meta"])


@router.get("/health")
def health():
    settings = get_settings()
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        database_ok = True
    except Exception:
        database_ok = False
    return {
        "status": "ok" if database_ok else "degraded",
        "version": settings.app_version,
        "commit": settings.git_commit_sha,
        "database": database_ok,
        "storage": database_ok,
        "llm": llm_available(),
    }


@router.get("/capabilities")
def capabilities(session: SessionDep):
    settings = get_settings()
    return {
        "search_mode": "bm25",
        "embedding_model": "none",
        "embedding_description": "Local BM25 keyword retrieval; no model downloads",
        "embedding_dim": None,
        "reranker_model": "none",
        "reranker_description": "No neural reranker",
        "llm_configured": llm_available(),
        "llm_model": settings.llm_model if llm_available() else None,
        "llm_host": provider_host() if llm_available() else None,
        "papers": session.exec(select(func.count(Paper.id))).one(),
        "max_papers": settings.max_papers,
        "chunks_indexed": session.exec(select(func.count(Chunk.id))).one(),
    }
