"""
SQLModel table definitions.

Design note: the actual vectors live in Qdrant, not here. Postgres holds
everything we need to reason about *relationships* between papers, claims,
and entities: the bibliography graph, citation verifications, contradictions,
and the knowledge graph adjacency. Keeping that relational data in Postgres
(instead of a separate graph database) is a deliberate scope decision so the
whole project runs on free-tier infra without adding another moving part.
"""

import enum
from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlmodel import Field, SQLModel


def utcnow() -> datetime:
    # SQLAlchemy's TIMESTAMP WITH TIME ZONE column type (which SQLModel
    # uses for datetime fields) rejects naive datetimes as of recent
    # versions, datetime.utcnow() returns a naive one even though the name
    # suggests otherwise. This is the timezone-aware equivalent.
    return datetime.now(UTC)


class PaperSource(str, enum.Enum):
    arxiv = "arxiv"
    upload = "upload"


class JobStatus(str, enum.Enum):
    queued = "queued"
    running = "running"
    done = "done"
    failed = "failed"


class CitationVerdict(str, enum.Enum):
    supported = "supported"
    partially_supported = "partially_supported"
    unsupported = "unsupported"
    contradicted = "contradicted"
    unresolved = "unresolved"  # cited work isn't in the corpus and couldn't be fetched


class EntityType(str, enum.Enum):
    method = "method"
    dataset = "dataset"
    metric = "metric"
    model = "model"
    author = "author"
    institution = "institution"


class Paper(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    arxiv_id: str | None = Field(default=None, index=True)
    arxiv_version: str | None = None
    title: str
    authors: str = ""  # comma separated, good enough for display purposes
    abstract: str = ""
    source: PaperSource
    pdf_path: str | None = None
    num_pages: int | None = None
    created_at: datetime = Field(default_factory=utcnow)


class Chunk(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    paper_id: UUID = Field(foreign_key="paper.id", index=True)
    qdrant_point_id: str = Field(index=True)
    section: str = "unknown"
    page: int | None = None
    order_in_paper: int
    text: str


class BibliographyEntry(SQLModel, table=True):
    """One entry from a paper's reference list, e.g. '[12] Vaswani et al., Attention Is All You Need, 2017'."""

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    paper_id: UUID = Field(foreign_key="paper.id", index=True)
    marker: str  # the literal marker used in-text, e.g. "12" or "Vaswani2017"
    raw_text: str
    resolved_arxiv_id: str | None = None
    resolved_paper_id: UUID | None = Field(default=None, foreign_key="paper.id")


class Claim(SQLModel, table=True):
    """An atomic claim extracted from a chunk, optionally attached to a citation marker."""

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    paper_id: UUID = Field(foreign_key="paper.id", index=True)
    chunk_id: UUID = Field(foreign_key="chunk.id")
    bib_entry_id: UUID | None = Field(default=None, foreign_key="bibliographyentry.id")
    claim_text: str
    citation_marker: str | None = None


class CitationVerification(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    claim_id: UUID = Field(foreign_key="claim.id", index=True)
    verdict: CitationVerdict
    evidence_text: str = ""
    judge_rationale: str = ""
    confidence: float = 0.0
    created_at: datetime = Field(default_factory=utcnow)


class Contradiction(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    claim_a_id: UUID = Field(foreign_key="claim.id")
    claim_b_id: UUID = Field(foreign_key="claim.id")
    explanation: str
    confidence: float = 0.0
    created_at: datetime = Field(default_factory=utcnow)


class GraphEntity(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    paper_id: UUID = Field(foreign_key="paper.id", index=True)
    name: str
    type: EntityType


class GraphEdge(SQLModel, table=True):
    """Generic edge, used both for entity relations ('uses dataset') and paper-to-paper citation edges."""

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    source_entity_id: UUID = Field(foreign_key="graphentity.id")
    target_entity_id: UUID = Field(foreign_key="graphentity.id")
    relation: str


class IngestionJob(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    paper_id: UUID | None = Field(default=None, foreign_key="paper.id")
    status: JobStatus = JobStatus.queued
    stage: str = ""
    error: str | None = None
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)


class AnswerRecord(SQLModel, table=True):
    """Every answer we generate, kept so feedback and eval can refer back to it."""

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    question: str
    answer: str
    paper_id: UUID | None = Field(default=None, foreign_key="paper.id")
    trust_score: int = 0
    trust_explanation: str = ""
    abstained: bool = False
    created_at: datetime = Field(default_factory=utcnow)


class Feedback(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    answer_id: UUID = Field(foreign_key="answerrecord.id")
    rating: int  # +1 thumbs up, -1 thumbs down
    comment: str | None = None
    created_at: datetime = Field(default_factory=utcnow)


class EvalRun(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    commit_sha: str = "local"
    pipeline_config: str = "full"  # e.g. "baseline", "hybrid_only", "full"
    metrics_json: str  # json.dumps of the metrics dict, kept simple on purpose
    created_at: datetime = Field(default_factory=utcnow)
