"""Celery tasks for asynchronous triage."""
from uuid import UUID

from app.core.logging import get_logger
from app.db.models import Incident
from app.db.session import SessionLocal
from app.services import audit_log_service
from app.services import triage_job_service, triage_service
from app.workers.celery_app import celery_app

logger = get_logger(__name__)


@celery_app.task(name="app.workers.tasks.process_triage_job")
def process_triage_job(job_id: str) -> str:
    """Run triage generation for a queued job."""
    db = SessionLocal()
    try:
        job = triage_job_service.get_triage_job(db, UUID(job_id))
        if job is None:
            raise ValueError("Triage job not found")

        triage_job_service.mark_running(db, job)
        incident = db.get(Incident, job.incident_id)
        if incident is None:
            raise ValueError("Incident not found")

        triage_result = triage_service.create_triage_result(db, incident)
        triage_job_service.mark_succeeded(db, job, triage_result)
        audit_log_service.safe_create_audit_log(
            db,
            entity_type="triage_job",
            entity_id=job.id,
            action="succeeded",
            details={
                "incident_id": str(incident.id),
                "triage_result_id": str(triage_result.id),
                "status": "succeeded",
            },
        )
        return str(triage_result.id)
    except Exception as exc:
        logger.exception(
            "Triage job failed",
            extra={"job_id": job_id, "error_type": type(exc).__name__},
        )
        try:
            job = triage_job_service.get_triage_job(db, UUID(job_id))
            if job is not None:
                triage_job_service.mark_failed(db, job, str(exc))
                audit_log_service.safe_create_audit_log(
                    db,
                    entity_type="triage_job",
                    entity_id=job.id,
                    action="failed",
                    details={
                        "incident_id": str(job.incident_id),
                        "status": "failed",
                        "error_type": type(exc).__name__,
                    },
                )
        finally:
            raise
    finally:
        db.close()
