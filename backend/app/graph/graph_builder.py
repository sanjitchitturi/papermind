import re
from uuid import UUID

from sqlmodel import Session, select

from app.db.models import BibliographyEntry, Entity, Paper, PaperCitation, PaperEntity
from app.graph.entity_extractor import canonical, extract_entities


def build_for_paper(session: Session, paper_id: UUID, text: str) -> dict:
    extracted = extract_entities(text)
    n_entities = 0
    for name, entity_type, mentions in extracted:
        key = canonical(name)
        entity = session.exec(select(Entity).where(Entity.canonical == key, Entity.type == entity_type)).first()
        if entity is None:
            entity = Entity(name=name, canonical=key, type=entity_type)
            session.add(entity)
            session.flush()
        link = session.exec(
            select(PaperEntity).where(PaperEntity.paper_id == paper_id, PaperEntity.entity_id == entity.id)
        ).first()
        if link is None:
            session.add(PaperEntity(paper_id=paper_id, entity_id=entity.id, mentions=mentions))
            n_entities += 1
        else:
            link.mentions = mentions
            session.add(link)
    session.commit()
    n_cites = link_citation_edges(session, paper_id)
    return {"entities": n_entities, "citations": n_cites}


def link_citation_edges(session: Session, paper_id: UUID) -> int:
    papers = session.exec(select(Paper)).all()
    by_arxiv = {p.arxiv_id: p for p in papers if p.arxiv_id}
    entries = session.exec(select(BibliographyEntry).where(BibliographyEntry.paper_id == paper_id)).all()
    linked = 0
    for entry in entries:
        cited = None
        if entry.resolved_arxiv_id and entry.resolved_arxiv_id in by_arxiv:
            cited = by_arxiv[entry.resolved_arxiv_id]
            method = "arxiv_id"
        else:
            cited = _match_by_title(entry.raw_text, papers, paper_id)
            method = "title"
        if cited is None or cited.id == paper_id:
            continue
        existing = session.exec(
            select(PaperCitation).where(
                PaperCitation.citing_paper_id == paper_id, PaperCitation.cited_paper_id == cited.id
            )
        ).first()
        if existing is None:
            session.add(PaperCitation(citing_paper_id=paper_id, cited_paper_id=cited.id, method=method))
            linked += 1
    session.commit()
    return linked


def _match_by_title(raw: str, papers: list[Paper], self_id: UUID) -> Paper | None:
    blob = re.sub(r"\s+", " ", raw.lower())
    best: Paper | None = None
    best_len = 0
    for paper in papers:
        if paper.id == self_id:
            continue
        title = paper.title.lower().strip()
        if len(title) < 18:
            continue
        if title in blob and len(title) > best_len:
            best, best_len = paper, len(title)
    return best
