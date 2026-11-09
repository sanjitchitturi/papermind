"""PaperMind API and optional built frontend, served from one origin."""

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.api import (
    routes_chat,
    routes_demo,
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
from app.core.request_security import RequestSecurityMiddleware
from app.db.session import init_db

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    recover_interrupted_jobs()
    yield


app = FastAPI(title="PaperMind", version=settings.app_version, lifespan=lifespan)
app.add_middleware(
    RequestSecurityMiddleware,
    allowed_origins=settings.cors_origins,
    max_bytes=(settings.max_upload_mb + 1) * 1024 * 1024,
)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.allowed_hosts)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["Content-Type"],
)
for module in (
    routes_health,
    routes_ingest,
    routes_papers,
    routes_chat,
    routes_integrity,
    routes_graph,
    routes_research,
    routes_eval,
    routes_feedback,
    routes_demo,
):
    app.include_router(module.router, prefix="/api")
    app.include_router(module.router, include_in_schema=False)


@app.exception_handler(LLMUnavailable)
async def llm_unavailable_handler(request: Request, exc: LLMUnavailable):
    return JSONResponse(status_code=503, content={"detail": str(exc)})


@app.exception_handler(LLMProviderError)
async def llm_provider_handler(request: Request, exc: LLMProviderError):
    return JSONResponse(status_code=502, content={"detail": str(exc)})


frontend = Path(__file__).resolve().parents[2] / "frontend" / "dist"
if (frontend / "assets").is_dir():
    app.mount("/assets", StaticFiles(directory=frontend / "assets"), name="assets")


@app.get("/{path:path}", include_in_schema=False)
def frontend_page(path: str):
    if path.startswith("api/") or path == "api":
        raise HTTPException(status_code=404, detail="API endpoint not found.")
    if not (frontend / "index.html").is_file():
        if not path:
            return {"name": "PaperMind", "docs": "/docs", "detail": "Build the frontend or run its development server."}
        raise HTTPException(status_code=404, detail="Page not found.")
    asset = (frontend / path).resolve()
    if asset.is_relative_to(frontend.resolve()) and asset.is_file():
        return FileResponse(asset)
    return FileResponse(frontend / "index.html")
