"""Add runbook tables.

Revision ID: 0004_phase_2c
Revises: 0003_phase_2b
Create Date: 2026-07-09
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0004_phase_2c"
down_revision: str | None = "0003_phase_2b"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def uuid_server_default() -> sa.TextClause | None:
    """Use PostgreSQL UUID defaults without breaking SQLite migration checks."""
    if op.get_context().dialect.name == "postgresql":
        return sa.text("gen_random_uuid()")
    return None


def json_object_default() -> sa.TextClause:
    """Return an empty JSON object default for the active dialect."""
    if op.get_context().dialect.name == "postgresql":
        return sa.text("'{}'::json")
    return sa.text("'{}'")


def upgrade() -> None:
    """Create runbook tables."""
    id_default = uuid_server_default()
    if op.get_context().dialect.name == "postgresql":
        op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")

    op.create_table(
        "runbooks",
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("service_name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_by_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("id", sa.Uuid(as_uuid=True), server_default=id_default, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_runbooks_service_name"), "runbooks", ["service_name"])

    op.create_table(
        "runbook_chunks",
        sa.Column("runbook_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("chunk_text", sa.Text(), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("metadata", sa.JSON(), server_default=json_object_default(), nullable=False),
        sa.Column("id", sa.Uuid(as_uuid=True), server_default=id_default, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["runbook_id"], ["runbooks.id"]),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    """Drop runbook tables."""
    op.drop_table("runbook_chunks")
    op.drop_index(op.f("ix_runbooks_service_name"), table_name="runbooks")
    op.drop_table("runbooks")
