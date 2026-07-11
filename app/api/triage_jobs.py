"""Triage job routes."""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.models import TriageJob
from app.db.session import get_db
from app.schemas.triage_job import TriageJobRead
from app.services import triage_job_service

router = APIRouter(prefix="/triage-jobs", tags=["triage-jobs"])


@router.get("/{job_id}", response_model=TriageJobRead)
def get_triage_job(job_id: UUID, db: Session = Depends(get_db)) -> TriageJob:
    """Get a triage job."""
    job = triage_job_service.get_triage_job(db, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Triage job not found")
    return job
