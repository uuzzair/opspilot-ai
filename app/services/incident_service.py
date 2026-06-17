"""Incident business operations."""
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Incident
from app.schemas.incident import IncidentCreate, IncidentUpdate


def create_incident(
    db: Session,
    incident_in: IncidentCreate,
    created_by_id: UUID,
) -> Incident:
    """Create an incident."""
    incident = Incident(**incident_in.model_dump(), created_by_id=created_by_id)
    db.add(incident)
    db.commit()
    db.refresh(incident)
    return incident


def list_incidents(db: Session) -> list[Incident]:
    """List incidents ordered by creation time."""
    result = db.execute(select(Incident).order_by(Incident.created_at.desc()))
    return list(result.scalars().all())


def get_incident(db: Session, incident_id: UUID) -> Incident | None:
    """Get an incident by ID."""
    return db.get(Incident, incident_id)


def update_incident(
    db: Session,
    incident: Incident,
    incident_in: IncidentUpdate,
) -> Incident:
    """Update an incident."""
    update_data = incident_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(incident, field, value)

    db.add(incident)
    db.commit()
    db.refresh(incident)
    return incident
