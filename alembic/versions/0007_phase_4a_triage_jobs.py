"""Add asynchronous triage jobs.

Revision ID: 0007_phase_4a
Revises: 0006_phase_3c
Create Date: 2026-07-11
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0007_phase_4a"
down_revision: str | None = "0006_phase_3c"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create triage jobs table."""
    op.create_table(
        "triage_jobs",
        sa.Column("incident_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("celery_task_id", sa.String(length=255), nullable=True),
        sa.Column("status", sa.String(length=30), server_default="pending", nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("triage_result_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("requested_by_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "status IN ('pending', 'running', 'succeeded', 'failed')",
            name="ck_triage_jobs_status",
        ),
        sa.ForeignKeyConstraint(["incident_id"], ["incidents.id"]),
        sa.ForeignKeyConstraint(["requested_by_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["triage_result_id"], ["triage_results.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_triage_jobs_celery_task_id"),
        "triage_jobs",
        ["celery_task_id"],
        unique=False,
    )


def downgrade() -> None:
    """Drop triage jobs table."""
    op.drop_index(op.f("ix_triage_jobs_celery_task_id"), table_name="triage_jobs")
    op.drop_table("triage_jobs")
