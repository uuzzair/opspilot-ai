"""Add user password hash.

Revision ID: 0003_phase_2b
Revises: 0002_phase_2a
Create Date: 2026-06-18
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0003_phase_2b"
down_revision: str | None = "0002_phase_2a"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add auth fields to users."""
    op.add_column("users", sa.Column("password_hash", sa.String(length=255), nullable=False))


def downgrade() -> None:
    """Remove auth fields from users."""
    op.drop_column("users", "password_hash")
