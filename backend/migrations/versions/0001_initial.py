"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-10-07
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "papers",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("arxiv_id", sa.String(), nullable=True),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("authors", sa.String(), nullable=False),
        sa.Column("first_author_surname", sa.String(), nullable=False),
        sa.Column("year", sa.Integer(), nullable=True),
        sa.Column("abstract", sa.Text(), nullable=False),
        sa.Column("source", sa.String(), nullable=False),
        sa.Column("num_pages", sa.Integer(), nullable=False),
        sa.Column("num_chunks", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_papers_arxiv_id", "papers", ["arxiv_id"])
    op.create_index("ix_papers_first_author_surname", "papers", ["first_author_surname"])

    op.create_table(
        "chunks",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("paper_id", sa.Uuid(), nullable=False),
        sa.Column("point_id", sa.String(), nullable=False),
        sa.Column("section", sa.String(), nullable=False),
        sa.Column("page_start", sa.Integer(), nullable=False),
        sa.Column("page_end", sa.Integer(), nullable=False),
        sa.Column("order_in_paper", sa.Integer(), nullable=False),
        sa.Column("token_count", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["paper_id"], ["papers.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_chunks_paper_id", "chunks", ["paper_id"])
    op.create_index("ix_chunks_point_id", "chunks", ["point_id"])

    op.create_table(
        "bibliography_entries",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("paper_id", sa.Uuid(), nullable=False),
        sa.Column("marker", sa.String(), nullable=False),
        sa.Column("raw_text", sa.Text(), nullable=False),
        sa.Column("resolved_arxiv_id", sa.String(), nullable=True),
        sa.ForeignKeyConstraint(["paper_id"], ["papers.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_bibliography_entries_paper_id", "bibliography_entries", ["paper_id"])

    op.create_table(
        "claims",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("paper_id", sa.Uuid(), nullable=False),
        sa.Column("chunk_id", sa.Uuid(), nullable=True),
        sa.Column("cited_paper_id", sa.Uuid(), nullable=True),
        sa.Column("kind", sa.String(), nullable=False),
        sa.Column("citation_marker", sa.String(), nullable=True),
        sa.Column("context", sa.Text(), nullable=False),
        sa.Column("claim_text", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["paper_id"], ["papers.id"]),
        sa.ForeignKeyConstraint(["chunk_id"], ["chunks.id"]),
        sa.ForeignKeyConstraint(["cited_paper_id"], ["papers.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_claims_paper_id", "claims", ["paper_id"])

    op.create_table(
        "citation_checks",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("claim_id", sa.Uuid(), nullable=False),
        sa.Column("verdict", sa.String(), nullable=False),
        sa.Column("evidence_text", sa.Text(), nullable=False),
        sa.Column("evidence_section", sa.String(), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=False),
        sa.Column("evidence_score", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["claim_id"], ["claims.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_citation_checks_claim_id", "citation_checks", ["claim_id"])

    op.create_table(
        "contradictions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("claim_a_id", sa.Uuid(), nullable=False),
        sa.Column("claim_b_id", sa.Uuid(), nullable=False),
        sa.Column("explanation", sa.Text(), nullable=False),
        sa.Column("similarity", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["claim_a_id"], ["claims.id"]),
        sa.ForeignKeyConstraint(["claim_b_id"], ["claims.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "entities",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("canonical", sa.String(), nullable=False),
        sa.Column("type", sa.String(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_entities_canonical", "entities", ["canonical"])

    op.create_table(
        "paper_entities",
        sa.Column("paper_id", sa.Uuid(), nullable=False),
        sa.Column("entity_id", sa.Uuid(), nullable=False),
        sa.Column("mentions", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["paper_id"], ["papers.id"]),
        sa.ForeignKeyConstraint(["entity_id"], ["entities.id"]),
        sa.PrimaryKeyConstraint("paper_id", "entity_id"),
    )

    op.create_table(
        "paper_citations",
        sa.Column("citing_paper_id", sa.Uuid(), nullable=False),
        sa.Column("cited_paper_id", sa.Uuid(), nullable=False),
        sa.Column("method", sa.String(), nullable=False),
        sa.ForeignKeyConstraint(["citing_paper_id"], ["papers.id"]),
        sa.ForeignKeyConstraint(["cited_paper_id"], ["papers.id"]),
        sa.PrimaryKeyConstraint("citing_paper_id", "cited_paper_id"),
    )

    op.create_table(
        "jobs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("kind", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("stage", sa.String(), nullable=False),
        sa.Column("progress", sa.Float(), nullable=False),
        sa.Column("message", sa.String(), nullable=False),
        sa.Column("error", sa.String(), nullable=True),
        sa.Column("paper_id", sa.Uuid(), nullable=True),
        sa.Column("input_json", sa.Text(), nullable=False),
        sa.Column("result_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["paper_id"], ["papers.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "answers",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("answer", sa.Text(), nullable=False),
        sa.Column("mode", sa.String(), nullable=False),
        sa.Column("paper_id", sa.Uuid(), nullable=True),
        sa.Column("trust_score", sa.Integer(), nullable=False),
        sa.Column("signals_json", sa.Text(), nullable=False),
        sa.Column("abstained", sa.Boolean(), nullable=False),
        sa.Column("latency_ms", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["paper_id"], ["papers.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "feedback",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("answer_id", sa.Uuid(), nullable=False),
        sa.Column("rating", sa.Integer(), nullable=False),
        sa.Column("comment", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["answer_id"], ["answers.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_feedback_answer_id", "feedback", ["answer_id"])

    op.create_table(
        "eval_runs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("suite", sa.String(), nullable=False),
        sa.Column("commit_sha", sa.String(), nullable=False),
        sa.Column("config_json", sa.Text(), nullable=False),
        sa.Column("metrics_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    for table in [
        "eval_runs",
        "feedback",
        "answers",
        "jobs",
        "paper_citations",
        "paper_entities",
        "entities",
        "contradictions",
        "citation_checks",
        "claims",
        "bibliography_entries",
        "chunks",
        "papers",
    ]:
        op.drop_table(table)
