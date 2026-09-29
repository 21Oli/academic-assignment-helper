"""Make embedding column dimension configurable (1536 → env-driven)

Run this migration ONLY if you changed EMBEDDING_DIM from 1536 (OpenAI) to
1024 (NVIDIA nv-embedqa-e5-v5). You must also clear the academic_sources table
and re-seed, since existing vectors will have the wrong dimension.

Revision ID: 0002
Revises: 0001
Create Date: 2024-06-01 00:00:00
"""
import os
from typing import Sequence, Union
from alembic import op

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Read the target dimension from the environment (same variable the app uses)
TARGET_DIM = int(os.getenv("EMBEDDING_DIM", "1536"))
PREV_DIM = 1536  # dimension set in migration 0001


def upgrade() -> None:
    if TARGET_DIM == PREV_DIM:
        print(f"EMBEDDING_DIM={TARGET_DIM} matches existing column — no change needed.")
        return

    print(f"Resizing embedding column: {PREV_DIM} → {TARGET_DIM} dims")

    # Drop the HNSW index first (can't alter column type with an index on it)
    op.execute("DROP INDEX IF EXISTS ix_academic_sources_embedding_hnsw")

    # Clear existing embeddings (they have wrong dimensions and must be re-seeded)
    op.execute("TRUNCATE TABLE academic_sources")

    # Resize the column
    op.execute(
        f"ALTER TABLE academic_sources "
        f"ALTER COLUMN embedding TYPE vector({TARGET_DIM}) "
        f"USING NULL::vector({TARGET_DIM})"
    )

    # Recreate the HNSW index for the new dimension
    op.execute(
        f"CREATE INDEX ix_academic_sources_embedding_hnsw "
        f"ON academic_sources USING hnsw (embedding vector_cosine_ops) "
        f"WITH (m = 16, ef_construction = 64)"
    )
    print(f"Done. Re-seed academic sources by restarting the backend.")


def downgrade() -> None:
    # Revert to 1536-dim (OpenAI default)
    op.execute("DROP INDEX IF EXISTS ix_academic_sources_embedding_hnsw")
    op.execute("TRUNCATE TABLE academic_sources")
    op.execute(
        f"ALTER TABLE academic_sources "
        f"ALTER COLUMN embedding TYPE vector({PREV_DIM}) "
        f"USING NULL::vector({PREV_DIM})"
    )
    op.execute(
        f"CREATE INDEX ix_academic_sources_embedding_hnsw "
        f"ON academic_sources USING hnsw (embedding vector_cosine_ops) "
        f"WITH (m = 16, ef_construction = 64)"
    )
