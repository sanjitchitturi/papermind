from fastapi import APIRouter
from sqlmodel import select

from app.api.deps import SessionDep, paper_or_404, paper_out
from app.db.models import Chunk
from app.graph.graph_builder import build_for_paper
from app.graph.graph_queries import export_for_visualization, papers_sharing_entities

router = APIRouter(prefix="/graph", tags=["graph"])


@router.post("/papers/{paper_id}/build")
def build(paper_id: str, session: SessionDep):
    paper = paper_or_404(session, paper_id)
    chunks = session.exec(select(Chunk).where(Chunk.paper_id == paper.id)).all()
    text = " ".join(c.text for c in chunks)
    return build_for_paper(session, paper.id, text)


@router.get("")
def get_graph(session: SessionDep):
    return export_for_visualization(session)


@router.get("/papers/{paper_id}/related")
def related(paper_id: str, session: SessionDep):
    paper = paper_or_404(session, paper_id)
    return [paper_out(p) for p in papers_sharing_entities(session, paper.id)]
