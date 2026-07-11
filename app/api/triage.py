"""Triage review routes."""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.models import TriageResult, User
from app.db.session import get_db
from app.schemas.triage import TriageResultRead, TriageReviewRequest
from app.services import audit_log_service
from app.services import triage_service

router = APIRouter(prefix="/triage", tags=["triage"])


@router.post("/{triage_id}/approve", response_model=TriageResultRead)
def approve_triage_result(
    triage_id: UUID,
    review_in: TriageReviewRequest | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TriageResult:
    """Approve a triage result."""
    triage_result = triage_service.get_triage_result(db, triage_id)
    if triage_result is None:
        raise HTTPException(status_code=404, detail="Triage result not found")
    triage_result = triage_service.approve_triage_result(
        db,
        triage_result,
        current_user.id,
        review_in or TriageReviewRequest(),
    )
    audit_log_service.safe_create_audit_log(
        db,
        entity_type="triage_result",
        entity_id=triage_result.id,
        action="approved",
        actor_id=current_user.id,
        details={
            "incident_id": str(triage_result.incident_id),
            "approval_status": triage_result.approval_status,
        },
    )
    return triage_result


@router.post("/{triage_id}/reject", response_model=TriageResultRead)
def reject_triage_result(
    triage_id: UUID,
    review_in: TriageReviewRequest | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TriageResult:
    """Reject a triage result."""
    triage_result = triage_service.get_triage_result(db, triage_id)
    if triage_result is None:
        raise HTTPException(status_code=404, detail="Triage result not found")
    triage_result = triage_service.reject_triage_result(
        db,
        triage_result,
        current_user.id,
        review_in or TriageReviewRequest(),
    )
    audit_log_service.safe_create_audit_log(
        db,
        entity_type="triage_result",
        entity_id=triage_result.id,
        action="rejected",
        actor_id=current_user.id,
        details={
            "incident_id": str(triage_result.incident_id),
            "approval_status": triage_result.approval_status,
        },
    )
    return triage_result
