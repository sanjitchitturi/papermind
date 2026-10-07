"""
FastAPI entrypoint. Wires route modules, runs migrations, recovers jobs
interrupted by a process restart, and warms the local ONNX models so the
first real request isn't a 30-second download.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import (
    routes_chat,
    routes_eval,
    routes_feedback,
    routes_graph,
    routes_health,
    routes_ingest,
    routes_integrity,
    routes_papers,
    routes_research,
)
from app.core.config import get_settings
from app.core.jobs import recover_interrupted_jobs
from app.core.llm import LLMProviderError, LLMUnavailable
from app.core.vector_store import ensure_collection

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("papermind")
settings = get_settings()


def _run_migrations() -> None:
    from alembic import command
    from alembic.config import Config

    cfg = Config("alembic.ini")
    cfg.set_main_option("sqlalchemy.url", settings.database_url)
    command.upgrade(cfg, "head")


def _warm_models() -> None:
    from app.ml.embeddings import get_embedder, get_sparse_encoder
    from app.ml.reranker import get_reranker

    embedder = get_embedder()
    get_sparse_encoder()
    get_reranker()
    embedder.embed_query("warmup")
    logger.info("models ready: embedder=%s dim=%s", embedder.name, embedder.dim)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Keep startup cheap. Render kills a free instance if uvicorn does not
    # bind during lifespan, and loading ONNX here stacked on Alembic is
    # how a 512 MB box gets OOM-killed before /health ever answers.
    try:
        if settings.database_url.startswith("sqlite"):
            from app.db.session import init_db

            init_db()
        else:
            _run_migrations()
    except Exception:
        logger.exception("database init failed")
        raise
    try:
        n = recover_interrupted_jobs()
        if n:
            logger.info("marked %s interrupted jobs as failed", n)
    except Exception:
        logger.exception("job recovery failed")
    try:
        ensure_collection()
    except Exception:
        logger.exception("qdrant collection not ready; retrieval will fail until it is")
    yield


app = FastAPI(title="PaperMind", version=settings.app_version, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_origin_regex=settings.cors_origin_regex,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(routes_health.router)
app.include_router(routes_ingest.router)
app.include_router(routes_papers.router)
app.include_router(routes_chat.router)
app.include_router(routes_integrity.router)
app.include_router(routes_graph.router)
app.include_router(routes_research.router)
app.include_router(routes_eval.router)
app.include_router(routes_feedback.router)


@app.exception_handler(LLMUnavailable)
async def llm_unavailable_handler(request: Request, exc: LLMUnavailable):
    return JSONResponse(status_code=503, content={"detail": str(exc)})


@app.exception_handler(LLMProviderError)
async def llm_provider_handler(request: Request, exc: LLMProviderError):
    return JSONResponse(status_code=502, content={"detail": str(exc)})
