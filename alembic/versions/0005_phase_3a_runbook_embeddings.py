"""Add runbook chunk embeddings.

Revision ID: 0005_phase_3a
Revises: 0004_phase_2c
Create Date: 2026-07-11
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0005_phase_3a"
down_revision: str | None = "0004_phase_2c"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def embedding_column_type() -> sa.types.TypeEngine:
    """Use pgvector in PostgreSQL and JSON elsewhere."""
    if op.get_context().dialect.name == "postgresql":
        from pgvector.sqlalchemy import Vector

        return Vector(384)
    return sa.JSON()


def upgrade() -> None:
    """Add embedding storage for runbook chunks."""
    if op.get_context().dialect.name == "postgresql":
        op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.add_column(
        "runbook_chunks",
        sa.Column("embedding", embedding_column_type(), nullable=True),
    )


def downgrade() -> None:
    """Remove embedding storage for runbook chunks."""
    op.drop_column("runbook_chunks", "embedding")
