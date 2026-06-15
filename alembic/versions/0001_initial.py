"""Initial empty schema.

Revision ID: 0001_initial
Revises:
Create Date: 2026-06-16
"""

from collections.abc import Sequence


revision: str = "0001_initial"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Apply the initial baseline migration."""


def downgrade() -> None:
    """Revert the initial baseline migration."""
