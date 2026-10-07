"""Read-side queries over the knowledge graph, including the payload the frontend visualization consumes."""

from uuid import UUID

from sqlmodel import Session, select

from app.db.models import Entity, Paper, PaperCitation, PaperEntity


def export_for_visualization(session: Session) -> dict:
    papers = {p.id: p for p in session.exec(select(Paper)).all()}
    entities = {e.id: e for e in session.exec(select(Entity)).all()}
    links = session.exec(select(PaperEntity)).all()
    citations = session.exec(select(PaperCitation)).all()

    paper_nodes = [
        {
            "id": f"paper:{p.id}",
            "kind": "paper",
            "label": p.title,
            "type": "paper",
            "paper_id": str(p.id),
            "year": p.year,
            "arxiv_id": p.arxiv_id,
        }
        for p in papers.values()
    ]
    entity_nodes = [
        {
            "id": f"entity:{e.id}",
            "kind": "entity",
            "label": e.name,
            "type": e.type.value,
            "paper_id": "",
            "mentions": 0,
        }
        for e in entities.values()
    ]
    mention_count: dict[str, int] = {}
    mention_edges = []
    for link in links:
        eid = f"entity:{link.entity_id}"
        mention_count[eid] = mention_count.get(eid, 0) + link.mentions
        mention_edges.append(
            {"source": f"paper:{link.paper_id}", "target": eid, "relation": "mentions", "weight": link.mentions}
        )
    for node in entity_nodes:
        node["mentions"] = mention_count.get(node["id"], 0)

    cite_edges = [
        {"source": f"paper:{c.citing_paper_id}", "target": f"paper:{c.cited_paper_id}", "relation": "cites", "weight": 1}
        for c in citations
    ]
    return {"nodes": paper_nodes + entity_nodes, "edges": mention_edges + cite_edges}


def papers_sharing_entities(session: Session, paper_id: UUID) -> list[Paper]:
    own = session.exec(select(PaperEntity).where(PaperEntity.paper_id == paper_id)).all()
    entity_ids = {link.entity_id for link in own}
    if not entity_ids:
        return []
    other = session.exec(select(PaperEntity).where(PaperEntity.paper_id != paper_id)).all()
    related_ids = {link.paper_id for link in other if link.entity_id in entity_ids}
    if not related_ids:
        return []
    return session.exec(select(Paper).where(Paper.id.in_(related_ids))).all()
