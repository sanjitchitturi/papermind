"""
FastAPI application entrypoint. Wires up all the route modules and does
the one-time startup work: creating tables and making sure the Qdrant
collection exists.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import (
    routes_chat,
    routes_eval,
    routes_feedback,
    routes_graph,
    routes_ingest,
    routes_integrity,
    routes_research,
)
from app.core.config import get_settings
from app.core.vector_store import ensure_collection
from app.db.session import init_db

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    ensure_collection()
    yield


app = FastAPI(title="PaperMind", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(routes_ingest.router)
app.include_router(routes_chat.router)
app.include_router(routes_integrity.router)
app.include_router(routes_graph.router)
app.include_router(routes_research.router)
app.include_router(routes_eval.router)
app.include_router(routes_feedback.router)


@app.get("/health")
def health():
    return {"status": "ok"}
