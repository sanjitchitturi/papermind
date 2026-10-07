"""
Builds the knowledge graph for a paper: extracts entities, deduplicates
them against entities already seen for that paper, and records citation
edges from the bibliography parser's resolved arXiv ids.

The graph is stored as plain rows in Postgres (GraphEntity, GraphEdge)
rather than in a dedicated graph database. For the size of corpus this
project targets (dozens to low hundreds of papers), adjacency queries in
Postgres plus in-process traversal with networkx are plenty fast, and it
avoids running a second database just for this.
"""

from uuid import UUID

from sqlmodel import Session, select

from app.db.models import BibliographyEntry, GraphEdge, GraphEntity, Paper
from app.graph.entity_extractor import extract_entities


def build_entities_for_paper(session: Session, paper_id: UUID, text: str) -> list[GraphEntity]:
    extracted = extract_entities(text)
    created = []
    for name, entity_type in extracted:
        existing = session.exec(
            select(GraphEntity).where(
                GraphEntity.paper_id == paper_id,
                GraphEntity.name == name,
                GraphEntity.type == entity_type,
            )
        ).first()
        if existing:
            continue
        entity = GraphEntity(paper_id=paper_id, name=name, type=entity_type)
        session.add(entity)
        created.append(entity)
    session.commit()
    return created


def link_citation_edges(session: Session, paper_id: UUID) -> int:
    """
    For every bibliography entry we managed to resolve to an arXiv id that
    is also in our corpus, record a citation edge between the two papers'
    "self" entities (one synthetic entity per paper representing the
    paper itself, so edges can connect papers directly, not just
    sub-entities within them).
    """
    citing_self = _get_or_create_self_entity(session, paper_id)

    entries = session.exec(select(BibliographyEntry).where(BibliographyEntry.paper_id == paper_id)).all()
    linked = 0
    for entry in entries:
        if not entry.resolved_arxiv_id:
            continue
        cited_paper = session.exec(select(Paper).where(Paper.arxiv_id == entry.resolved_arxiv_id)).first()
        if not cited_paper:
            continue
        cited_self = _get_or_create_self_entity(session, cited_paper.id)
        session.add(GraphEdge(source_entity_id=citing_self.id, target_entity_id=cited_self.id, relation="cites"))
        linked += 1
    session.commit()
    return linked


def _get_or_create_self_entity(session: Session, paper_id: UUID) -> GraphEntity:
    from app.db.models import EntityType

    existing = session.exec(
        select(GraphEntity).where(GraphEntity.paper_id == paper_id, GraphEntity.type == EntityType.model, GraphEntity.name == "__self__")
    ).first()
    if existing:
        return existing
    entity = GraphEntity(paper_id=paper_id, name="__self__", type=EntityType.model)
    session.add(entity)
    session.commit()
    return entity
