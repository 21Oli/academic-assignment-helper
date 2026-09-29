"""Initial schema — all tables + pgvector HNSW index

Revision ID: 0001
Revises:
Create Date: 2024-01-01 00:00:00
"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from alembic import op

try:
    from pgvector.sqlalchemy import Vector
except ImportError:
    Vector = None

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Enable pgvector extension
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # ------------------------------------------------------------------
    # students
    # ------------------------------------------------------------------
    op.create_table(
        "students",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("email", sa.String(), nullable=False, unique=True, index=True),
        sa.Column("password_hash", sa.String(), nullable=False),
        sa.Column("full_name", sa.String(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
        ),
    )

    # ------------------------------------------------------------------
    # assignments
    # ------------------------------------------------------------------
    op.create_table(
        "assignments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("student_id", sa.Integer(), sa.ForeignKey("students.id", ondelete="CASCADE"), nullable=False),
        sa.Column("filename", sa.String(), nullable=True),
        sa.Column("file_path", sa.String(), nullable=True),
        sa.Column("original_text", sa.Text(), nullable=True),
        sa.Column("topic", sa.String(), nullable=True),
        sa.Column("academic_level", sa.String(), nullable=True),
        sa.Column("word_count", sa.Integer(), nullable=True),
        sa.Column(
            "uploaded_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
        ),
    )
    op.create_index("ix_assignments_student_id", "assignments", ["student_id"])

    # ------------------------------------------------------------------
    # analysis_results
    # ------------------------------------------------------------------
    op.create_table(
        "analysis_results",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("assignment_id", sa.Integer(), sa.ForeignKey("assignments.id", ondelete="CASCADE")),
        sa.Column("suggested_sources", postgresql.JSONB(), nullable=True),
        sa.Column("plagiarism_score", sa.Float(), nullable=True),
        sa.Column("flagged_sections", postgresql.JSONB(), nullable=True),
        sa.Column("research_suggestions", sa.Text(), nullable=True),
        sa.Column("citation_recommendations", sa.Text(), nullable=True),
        sa.Column("confidence_score", sa.Float(), nullable=True),
        sa.Column(
            "analyzed_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
        ),
    )
    op.create_index("ix_analysis_results_assignment_id", "analysis_results", ["assignment_id"])

    # ------------------------------------------------------------------
    # academic_sources
    # ------------------------------------------------------------------
    op.create_table(
        "academic_sources",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("title", sa.Text(), nullable=True),
        sa.Column("authors", sa.Text(), nullable=True),
        sa.Column("publication_year", sa.Integer(), nullable=True),
        sa.Column("abstract", sa.Text(), nullable=True),
        sa.Column("full_text", sa.Text(), nullable=True),
        sa.Column("source_type", sa.String(), nullable=True),
        # pgvector column — 1536 dims for OpenAI text-embedding-3-small
        sa.Column("embedding", sa.Text(), nullable=True),  # placeholder; altered below
    )

    # Replace the placeholder Text column with the real vector(1536) type
    op.execute("ALTER TABLE academic_sources ALTER COLUMN embedding TYPE vector(1536) USING NULL::vector(1536)")

    # ------------------------------------------------------------------
    # HNSW index for fast cosine-distance nearest-neighbour search
    # Dramatically faster than a sequential scan for large source tables.
    # ------------------------------------------------------------------
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_academic_sources_embedding_hnsw "
        "ON academic_sources USING hnsw (embedding vector_cosine_ops) "
        "WITH (m = 16, ef_construction = 64)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_academic_sources_embedding_hnsw")
    op.drop_table("academic_sources")
    op.drop_table("analysis_results")
    op.drop_table("assignments")
    op.drop_table("students")
    op.execute("DROP EXTENSION IF EXISTS vector")
