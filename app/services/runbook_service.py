"""Runbook business operations."""
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Runbook, RunbookChunk
from app.schemas.runbook import RunbookChunkCreate, RunbookCreate, RunbookUpdate


def create_runbook(
    db: Session,
    runbook_in: RunbookCreate,
    created_by_id: UUID,
) -> Runbook:
    """Create a runbook."""
    runbook = Runbook(**runbook_in.model_dump(), created_by_id=created_by_id)
    db.add(runbook)
    db.commit()
    db.refresh(runbook)
    return runbook


def list_runbooks(db: Session) -> list[Runbook]:
    """List runbooks ordered by creation time."""
    result = db.execute(select(Runbook).order_by(Runbook.created_at.desc()))
    return list(result.scalars().all())


def get_runbook(db: Session, runbook_id: UUID) -> Runbook | None:
    """Get a runbook by ID."""
    return db.get(Runbook, runbook_id)


def update_runbook(
    db: Session,
    runbook: Runbook,
    runbook_in: RunbookUpdate,
) -> Runbook:
    """Update a runbook."""
    update_data = runbook_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(runbook, field, value)

    db.add(runbook)
    db.commit()
    db.refresh(runbook)
    return runbook


def create_runbook_chunk(
    db: Session,
    runbook: Runbook,
    chunk_in: RunbookChunkCreate,
) -> RunbookChunk:
    """Create a runbook chunk."""
    chunk = RunbookChunk(
        runbook_id=runbook.id,
        chunk_text=chunk_in.chunk_text,
        chunk_index=chunk_in.chunk_index,
        metadata_=chunk_in.metadata,
    )
    db.add(chunk)
    db.commit()
    db.refresh(chunk)
    return chunk


def list_runbook_chunks(db: Session, runbook_id: UUID) -> list[RunbookChunk]:
    """List chunks for a runbook ordered by chunk index."""
    result = db.execute(
        select(RunbookChunk)
        .where(RunbookChunk.runbook_id == runbook_id)
        .order_by(RunbookChunk.chunk_index.asc())
    )
    return list(result.scalars().all())
