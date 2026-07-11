"""Runbook routes."""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.models import Runbook, RunbookChunk, User
from app.db.session import get_db
from app.schemas.runbook import (
    RunbookChunkCreate,
    RunbookChunkRead,
    RunbookChunkSearchResult,
    RunbookCreate,
    RunbookRead,
    RunbookSearchRequest,
    RunbookUpdate,
)
from app.services import audit_log_service
from app.services import runbook_service

router = APIRouter(prefix="/runbooks", tags=["runbooks"])


@router.post("", response_model=RunbookRead, status_code=status.HTTP_201_CREATED)
def create_runbook(
    runbook_in: RunbookCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Runbook:
    """Create a runbook."""
    runbook = runbook_service.create_runbook(db, runbook_in, current_user.id)
    audit_log_service.safe_create_audit_log(
        db,
        entity_type="runbook",
        entity_id=runbook.id,
        action="created",
        actor_id=current_user.id,
        details={
            "title": runbook.title,
            "service_name": runbook.service_name,
        },
    )
    return runbook


@router.get("", response_model=list[RunbookRead])
def list_runbooks(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> list[Runbook]:
    """List runbooks."""
    return runbook_service.list_runbooks(db, limit=limit, offset=offset)


@router.post("/search", response_model=list[RunbookChunkSearchResult])
def search_runbooks(
    search_in: RunbookSearchRequest,
    db: Session = Depends(get_db),
) -> list[RunbookChunkSearchResult]:
    """Search runbook chunks."""
    return runbook_service.search_runbook_chunks(db, search_in)


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
    updated_runbook = runbook_service.update_runbook(db, runbook, runbook_in)
    audit_log_service.safe_create_audit_log(
        db,
        entity_type="runbook",
        entity_id=updated_runbook.id,
        action="updated",
        actor_id=current_user.id,
        details={
            "title": updated_runbook.title,
            "service_name": updated_runbook.service_name,
            "updated_fields": list(runbook_in.model_dump(exclude_unset=True).keys()),
        },
    )
    return updated_runbook


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
    chunk = runbook_service.create_runbook_chunk(db, runbook, chunk_in)
    audit_log_service.safe_create_audit_log(
        db,
        entity_type="runbook_chunk",
        entity_id=chunk.id,
        action="created",
        actor_id=current_user.id,
        details={
            "runbook_id": str(runbook.id),
            "service_name": runbook.service_name,
            "chunk_index": chunk.chunk_index,
        },
    )
    return chunk


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
