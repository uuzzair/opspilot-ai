"""Runbook routes."""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.models import Runbook, RunbookChunk, User
from app.db.session import get_db
from app.schemas.runbook import (
    RunbookChunkCreate,
    RunbookChunkRead,
    RunbookCreate,
    RunbookRead,
    RunbookUpdate,
)
from app.services import runbook_service

router = APIRouter(prefix="/runbooks", tags=["runbooks"])


@router.post("", response_model=RunbookRead, status_code=status.HTTP_201_CREATED)
def create_runbook(
    runbook_in: RunbookCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Runbook:
    """Create a runbook."""
    return runbook_service.create_runbook(db, runbook_in, current_user.id)


@router.get("", response_model=list[RunbookRead])
def list_runbooks(db: Session = Depends(get_db)) -> list[Runbook]:
    """List runbooks."""
    return runbook_service.list_runbooks(db)


@router.get("/{runbook_id}", response_model=RunbookRead)
def get_runbook(
    runbook_id: UUID,
    db: Session = Depends(get_db),
) -> Runbook:
    """Get a runbook."""
    runbook = runbook_service.get_runbook(db, runbook_id)
    if runbook is None:
        raise HTTPException(status_code=404, detail="Runbook not found")
    return runbook


@router.patch("/{runbook_id}", response_model=RunbookRead)
def update_runbook(
    runbook_id: UUID,
    runbook_in: RunbookUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Runbook:
    """Update a runbook."""
    runbook = runbook_service.get_runbook(db, runbook_id)
    if runbook is None:
        raise HTTPException(status_code=404, detail="Runbook not found")
    return runbook_service.update_runbook(db, runbook, runbook_in)


@router.post(
    "/{runbook_id}/chunks",
    response_model=RunbookChunkRead,
    status_code=status.HTTP_201_CREATED,
)
def create_runbook_chunk(
    runbook_id: UUID,
    chunk_in: RunbookChunkCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> RunbookChunk:
    """Create a runbook chunk."""
    runbook = runbook_service.get_runbook(db, runbook_id)
    if runbook is None:
        raise HTTPException(status_code=404, detail="Runbook not found")
    return runbook_service.create_runbook_chunk(db, runbook, chunk_in)


@router.get("/{runbook_id}/chunks", response_model=list[RunbookChunkRead])
def list_runbook_chunks(
    runbook_id: UUID,
    db: Session = Depends(get_db),
) -> list[RunbookChunk]:
    """List runbook chunks."""
    runbook = runbook_service.get_runbook(db, runbook_id)
    if runbook is None:
        raise HTTPException(status_code=404, detail="Runbook not found")
    return runbook_service.list_runbook_chunks(db, runbook_id)
