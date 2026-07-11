"""Add triage reviewer notes.

Revision ID: 0006_phase_3c
Revises: 0005_phase_3a
Create Date: 2026-07-11
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0006_phase_3c"
down_revision: str | None = "0005_phase_3a"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add reviewer notes to triage results."""
    op.add_column("triage_results", sa.Column("reviewer_notes", sa.Text(), nullable=True))
    if op.get_context().dialect.name == "postgresql":
        op.create_check_constraint(
            "ck_triage_results_approval_status",
            "triage_results",
            "approval_status IN ('pending', 'approved', 'rejected')",
        )


def downgrade() -> None:
    """Remove reviewer notes from triage results."""
    if op.get_context().dialect.name == "postgresql":
        op.drop_constraint(
            "ck_triage_results_approval_status",
            "triage_results",
            type_="check",
        )
    op.drop_column("triage_results", "reviewer_notes")
