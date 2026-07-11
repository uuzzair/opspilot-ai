"""Asynchronous triage job operations."""
from uuid import UUID

from sqlalchemy.orm import Session

from app.db.models import Incident, TriageJob, TriageResult

PENDING_STATUS = "pending"
RUNNING_STATUS = "running"
SUCCEEDED_STATUS = "succeeded"
FAILED_STATUS = "failed"
MAX_ERROR_LENGTH = 2000


def create_triage_job(
    db: Session,
    incident: Incident,
    requested_by_id: UUID | None,
) -> TriageJob:
    """Create a pending triage job."""
    job = TriageJob(
        incident_id=incident.id,
        requested_by_id=requested_by_id,
        status=PENDING_STATUS,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def get_triage_job(db: Session, job_id: UUID) -> TriageJob | None:
    """Get a triage job by ID."""
    return db.get(TriageJob, job_id)


def set_celery_task_id(db: Session, job: TriageJob, celery_task_id: str | None) -> TriageJob:
    """Persist the Celery task ID for a job."""
    job.celery_task_id = celery_task_id
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def mark_running(db: Session, job: TriageJob) -> TriageJob:
    """Mark a triage job as running."""
    job.status = RUNNING_STATUS
    job.error_message = None
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def mark_succeeded(db: Session, job: TriageJob, triage_result: TriageResult) -> TriageJob:
    """Mark a triage job as succeeded."""
    job.status = SUCCEEDED_STATUS
    job.triage_result_id = triage_result.id
    job.error_message = None
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def mark_failed(db: Session, job: TriageJob, error_message: str) -> TriageJob:
    """Mark a triage job as failed."""
    job.status = FAILED_STATUS
    job.error_message = error_message[:MAX_ERROR_LENGTH]
    db.add(job)
    db.commit()
    db.refresh(job)
    return job
