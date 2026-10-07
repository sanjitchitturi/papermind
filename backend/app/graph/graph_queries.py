"""
Read-side queries over the knowledge graph: building a networkx graph
from the Postgres tables, exporting it for the frontend visualization,
and answering "papers related to this one" questions used by both the
Citation Integrity Engine and the agentic Research Mode.
"""

from uuid import UUID

import networkx as nx
from sqlmodel import Session, select

from app.db.models import GraphEdge, GraphEntity, Paper


def load_graph(session: Session) -> nx.DiGraph:
    graph = nx.DiGraph()
    entities = session.exec(select(GraphEntity)).all()
    for entity in entities:
        graph.add_node(str(entity.id), name=entity.name, type=entity.type.value, paper_id=str(entity.paper_id))

    edges = session.exec(select(GraphEdge)).all()
    for edge in edges:
        graph.add_edge(str(edge.source_entity_id), str(edge.target_entity_id), relation=edge.relation)

    return graph


def export_for_visualization(session: Session) -> dict:
    graph = load_graph(session)
    nodes = [
        {"id": node_id, "label": data["name"], "type": data["type"], "paper_id": data["paper_id"]}
        for node_id, data in graph.nodes(data=True)
        if data["name"] != "__self__"  # the synthetic per-paper node is for citation edges, not display
    ]
    edges = [{"source": u, "target": v, "relation": data["relation"]} for u, v, data in graph.edges(data=True)]
    return {"nodes": nodes, "edges": edges}


def papers_sharing_entities(session: Session, paper_id: UUID) -> list[Paper]:
    """Finds other papers that mention at least one of the same named entities, used to suggest related work."""
    entities = session.exec(select(GraphEntity).where(GraphEntity.paper_id == paper_id, GraphEntity.name != "__self__")).all()
    entity_names = {e.name for e in entities}
    if not entity_names:
        return []

    other_entities = session.exec(select(GraphEntity).where(GraphEntity.paper_id != paper_id)).all()
    related_paper_ids = {e.paper_id for e in other_entities if e.name in entity_names}
    if not related_paper_ids:
        return []

    return session.exec(select(Paper).where(Paper.id.in_(related_paper_ids))).all()


def citation_lineage(session: Session, paper_id: UUID, depth: int = 2) -> list[Paper]:
    """Follows outgoing 'cites' edges up to `depth` hops to show what a paper's citation chain looks like."""
    graph = load_graph(session)
    self_node = next((n for n, d in graph.nodes(data=True) if d["paper_id"] == str(paper_id) and d["name"] == "__self__"), None)
    if self_node is None:
        return []

    visited = set()
    frontier = {self_node}
    for _ in range(depth):
        next_frontier = set()
        for node in frontier:
            next_frontier.update(graph.successors(node))
        visited.update(next_frontier)
        frontier = next_frontier

    paper_ids = {UUID(graph.nodes[n]["paper_id"]) for n in visited}
    if not paper_ids:
        return []
    return session.exec(select(Paper).where(Paper.id.in_(paper_ids))).all()
