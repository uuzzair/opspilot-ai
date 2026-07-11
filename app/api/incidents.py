"""Incident routes."""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.models import Incident, TriageResult, User
from app.db.session import get_db
from app.schemas.incident import IncidentCreate, IncidentRead, IncidentUpdate
from app.schemas.triage import TriageResultRead
from app.schemas.triage_job import TriageJobRead
from app.services import audit_log_service
from app.services import incident_service
from app.services import triage_job_service
from app.services import triage_service
from app.workers.tasks import process_triage_job

router = APIRouter(prefix="/incidents", tags=["incidents"])


@router.post("", response_model=IncidentRead, status_code=status.HTTP_201_CREATED)
def create_incident(
    incident_in: IncidentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Incident:
    """Create an incident."""
    incident = incident_service.create_incident(db, incident_in, current_user.id)
    audit_log_service.safe_create_audit_log(
        db,
        entity_type="incident",
        entity_id=incident.id,
        action="created",
        actor_id=current_user.id,
        details={
            "title": incident.title,
            "status": incident.status,
            "severity": incident.severity,
            "affected_service": incident.affected_service,
        },
    )
    return incident


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
    updated_incident = incident_service.update_incident(db, incident, incident_in)
    audit_log_service.safe_create_audit_log(
        db,
        entity_type="incident",
        entity_id=updated_incident.id,
        action="updated",
        actor_id=current_user.id,
        details={
            "title": updated_incident.title,
            "status": updated_incident.status,
            "severity": updated_incident.severity,
            "affected_service": updated_incident.affected_service,
            "updated_fields": list(incident_in.model_dump(exclude_unset=True).keys()),
        },
    )
    return updated_incident


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
    triage_result = triage_service.create_triage_result(db, incident)
    audit_log_service.safe_create_audit_log(
        db,
        entity_type="triage_result",
        entity_id=triage_result.id,
        action="generated",
        actor_id=current_user.id,
        details={
            "incident_id": str(incident.id),
            "severity": incident.severity,
            "model_name": triage_result.model_name,
        },
    )
    return triage_result


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


@router.post(
    "/{incident_id}/triage-jobs",
    response_model=TriageJobRead,
    status_code=status.HTTP_202_ACCEPTED,
)
def create_incident_triage_job(
    incident_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Queue asynchronous triage for an incident."""
    incident = incident_service.get_incident(db, incident_id)
    if incident is None:
        raise HTTPException(status_code=404, detail="Incident not found")
    job = triage_job_service.create_triage_job(db, incident, current_user.id)
    async_result = process_triage_job.delay(str(job.id))
    job = triage_job_service.set_celery_task_id(db, job, async_result.id)
    audit_log_service.safe_create_audit_log(
        db,
        entity_type="triage_job",
        entity_id=job.id,
        action="created",
        actor_id=current_user.id,
        details={
            "incident_id": str(incident.id),
            "status": job.status,
            "celery_task_id": job.celery_task_id,
        },
    )
    return job
