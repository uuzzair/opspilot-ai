"""Incident routes."""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.models import Incident, TriageResult, User
from app.db.session import get_db
from app.schemas.incident import IncidentCreate, IncidentRead, IncidentUpdate
from app.schemas.triage import TriageResultRead
from app.services import incident_service
from app.services import triage_service

router = APIRouter(prefix="/incidents", tags=["incidents"])


@router.post("", response_model=IncidentRead, status_code=status.HTTP_201_CREATED)
def create_incident(
    incident_in: IncidentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Incident:
    """Create an incident."""
    return incident_service.create_incident(db, incident_in, current_user.id)


@router.get("", response_model=list[IncidentRead])
def list_incidents(db: Session = Depends(get_db)) -> list[Incident]:
    """List incidents."""
    return incident_service.list_incidents(db)


@router.get("/{incident_id}", response_model=IncidentRead)
def get_incident(
    incident_id: UUID,
    db: Session = Depends(get_db),
) -> Incident:
    """Get an incident."""
    incident = incident_service.get_incident(db, incident_id)
    if incident is None:
        raise HTTPException(status_code=404, detail="Incident not found")
    return incident


@router.patch("/{incident_id}", response_model=IncidentRead)
def update_incident(
    incident_id: UUID,
    incident_in: IncidentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Incident:
    """Update an incident."""
    incident = incident_service.get_incident(db, incident_id)
    if incident is None:
        raise HTTPException(status_code=404, detail="Incident not found")
    return incident_service.update_incident(db, incident, incident_in)


@router.post("/{incident_id}/triage", response_model=TriageResultRead, status_code=status.HTTP_201_CREATED)
def create_incident_triage(
    incident_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TriageResult:
    """Create deterministic triage for an incident."""
    incident = incident_service.get_incident(db, incident_id)
    if incident is None:
        raise HTTPException(status_code=404, detail="Incident not found")
    return triage_service.create_triage_result(db, incident)


@router.get("/{incident_id}/triage", response_model=list[TriageResultRead])
def list_incident_triage(
    incident_id: UUID,
    db: Session = Depends(get_db),
) -> list[TriageResult]:
    """List triage results for an incident."""
    incident = incident_service.get_incident(db, incident_id)
    if incident is None:
        raise HTTPException(status_code=404, detail="Incident not found")
    return triage_service.list_triage_results(db, incident_id)
