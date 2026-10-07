"""Endpoints for the knowledge graph: building it per paper, and exporting it for the frontend visualization."""

import uuid

from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from app.db.models import Chunk
from app.db.session import get_session
from app.graph.graph_builder import build_entities_for_paper, link_citation_edges
from app.graph.graph_queries import export_for_visualization, papers_sharing_entities

router = APIRouter(prefix="/graph", tags=["graph"])


@router.post("/papers/{paper_id}/build")
def build_graph_for_paper(paper_id: str, session: Session = Depends(get_session)):
    chunks = session.exec(select(Chunk).where(Chunk.paper_id == uuid.UUID(paper_id))).all()
    full_text = " ".join(c.text for c in chunks)[:8000]  # entity extraction only needs a representative sample
    entities = build_entities_for_paper(session, uuid.UUID(paper_id), full_text)
    edges_linked = link_citation_edges(session, uuid.UUID(paper_id))
    return {"entities_created": len(entities), "citation_edges_linked": edges_linked}


@router.get("")
def get_graph(session: Session = Depends(get_session)):
    return export_for_visualization(session)


@router.get("/papers/{paper_id}/related")
def get_related_papers(paper_id: str, session: Session = Depends(get_session)):
    papers = papers_sharing_entities(session, uuid.UUID(paper_id))
    return [{"id": str(p.id), "title": p.title} for p in papers]
