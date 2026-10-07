"""
SQLModel table definitions.

Vectors live in Qdrant. Postgres holds everything needed to reason about
relationships between papers, claims and entities: the bibliography,
citation checks, contradictions, and the knowledge graph adjacency. Keeping
the graph as plain tables (instead of a separate graph database) is a
deliberate scope decision, the corpus sizes this targets are small enough
that adjacency queries plus in-process traversal are plenty fast.

Schema changes go through Alembic migrations in backend/migrations.
"""

import enum
from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import Column, Text
from sqlmodel import Field, SQLModel


def utcnow() -> datetime:
    # TIMESTAMP WITH TIME ZONE columns reject naive datetimes, and
    # datetime.utcnow() returns a naive one despite the name.
    return datetime.now(UTC)


class PaperSource(str, enum.Enum):
    arxiv = "arxiv"
    upload = "upload"


class JobKind(str, enum.Enum):
    ingest = "ingest"
    integrity = "integrity"
    contradictions = "contradictions"
    eval = "eval"


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
    unresolved = "unresolved"


class EntityType(str, enum.Enum):
    method = "method"
    dataset = "dataset"
    metric = "metric"
    model = "model"
    task = "task"


class Paper(SQLModel, table=True):
    __tablename__ = "papers"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    arxiv_id: str | None = Field(default=None, index=True)
    title: str
    authors: str = ""  # comma separated, display only
    first_author_surname: str = Field(default="", index=True)
    year: int | None = None
    abstract: str = Field(default="", sa_column=Column(Text, nullable=False, default=""))
    source: PaperSource
    num_pages: int = 0
    num_chunks: int = 0
    created_at: datetime = Field(default_factory=utcnow)


class Chunk(SQLModel, table=True):
    __tablename__ = "chunks"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    paper_id: UUID = Field(foreign_key="papers.id", index=True)
    point_id: str = Field(index=True)
    section: str = "body"
    page_start: int = 1
    page_end: int = 1
    order_in_paper: int
    token_count: int = 0
    text: str = Field(sa_column=Column(Text, nullable=False))


class BibliographyEntry(SQLModel, table=True):
    """One entry from a paper's reference list."""

    __tablename__ = "bibliography_entries"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    paper_id: UUID = Field(foreign_key="papers.id", index=True)
    marker: str  # the in-text marker, "12" or "RWC+19"
    raw_text: str = Field(sa_column=Column(Text, nullable=False))
    resolved_arxiv_id: str | None = None


class Claim(SQLModel, table=True):
    """A checkable claim. Either attributed to a citation, or an atomic claim used for contradiction search."""

    __tablename__ = "claims"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    paper_id: UUID = Field(foreign_key="papers.id", index=True)
    chunk_id: UUID | None = Field(default=None, foreign_key="chunks.id")
    cited_paper_id: UUID | None = Field(default=None, foreign_key="papers.id")
    kind: str = "citation"  # "citation" | "atomic"
    citation_marker: str | None = None
    context: str = Field(default="", sa_column=Column(Text, nullable=False, default=""))
    claim_text: str = Field(sa_column=Column(Text, nullable=False))


class CitationCheck(SQLModel, table=True):
    __tablename__ = "citation_checks"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    claim_id: UUID = Field(foreign_key="claims.id", index=True)
    verdict: CitationVerdict
    evidence_text: str = Field(default="", sa_column=Column(Text, nullable=False, default=""))
    evidence_section: str = ""
    rationale: str = Field(default="", sa_column=Column(Text, nullable=False, default=""))
    evidence_score: float = 0.0
    created_at: datetime = Field(default_factory=utcnow)


class Contradiction(SQLModel, table=True):
    __tablename__ = "contradictions"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    claim_a_id: UUID = Field(foreign_key="claims.id")
    claim_b_id: UUID = Field(foreign_key="claims.id")
    explanation: str = Field(sa_column=Column(Text, nullable=False))
    similarity: float = 0.0
    created_at: datetime = Field(default_factory=utcnow)


class Entity(SQLModel, table=True):
    """A canonical entity shared across papers, e.g. one "SQuAD" node no matter how many papers use it."""

    __tablename__ = "entities"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    name: str
    canonical: str = Field(index=True)
    type: EntityType


class PaperEntity(SQLModel, table=True):
    __tablename__ = "paper_entities"

    paper_id: UUID = Field(foreign_key="papers.id", primary_key=True)
    entity_id: UUID = Field(foreign_key="entities.id", primary_key=True)
    mentions: int = 1


class PaperCitation(SQLModel, table=True):
    """Citation edge between two papers that are both in the corpus."""

    __tablename__ = "paper_citations"

    citing_paper_id: UUID = Field(foreign_key="papers.id", primary_key=True)
    cited_paper_id: UUID = Field(foreign_key="papers.id", primary_key=True)
    method: str = "title"  # how it was resolved: "arxiv_id" | "title"


class Job(SQLModel, table=True):
    __tablename__ = "jobs"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    kind: JobKind
    status: JobStatus = JobStatus.queued
    stage: str = "queued"
    progress: float = 0.0
    message: str = ""
    error: str | None = None
    paper_id: UUID | None = Field(default=None, foreign_key="papers.id")
    input_json: str = Field(default="{}", sa_column=Column(Text, nullable=False, default="{}"))
    result_json: str = Field(default="{}", sa_column=Column(Text, nullable=False, default="{}"))
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)


class AnswerRecord(SQLModel, table=True):
    """Every answer served, kept so feedback and calibration can refer back to it."""

    __tablename__ = "answers"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    question: str = Field(sa_column=Column(Text, nullable=False))
    answer: str = Field(sa_column=Column(Text, nullable=False))
    mode: str = "generative"  # "generative" | "extractive"
    paper_id: UUID | None = Field(default=None, foreign_key="papers.id")
    trust_score: int = 0
    signals_json: str = Field(default="{}", sa_column=Column(Text, nullable=False, default="{}"))
    abstained: bool = False
    latency_ms: int = 0
    created_at: datetime = Field(default_factory=utcnow)


class Feedback(SQLModel, table=True):
    __tablename__ = "feedback"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    answer_id: UUID = Field(foreign_key="answers.id", index=True)
    rating: int  # +1 or -1
    comment: str | None = None
    created_at: datetime = Field(default_factory=utcnow)


class EvalRun(SQLModel, table=True):
    __tablename__ = "eval_runs"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    suite: str = "retrieval"  # "retrieval" | "generation"
    commit_sha: str = "local"
    config_json: str = Field(default="{}", sa_column=Column(Text, nullable=False, default="{}"))
    metrics_json: str = Field(sa_column=Column(Text, nullable=False))
    created_at: datetime = Field(default_factory=utcnow)
