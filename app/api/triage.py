"""Triage review routes."""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.models import TriageResult, User
from app.db.session import get_db
from app.schemas.triage import TriageResultRead, TriageReviewRequest
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
    return triage_service.approve_triage_result(
        db,
        triage_result,
        current_user.id,
        review_in or TriageReviewRequest(),
    )


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
    return triage_service.reject_triage_result(
        db,
        triage_result,
        current_user.id,
        review_in or TriageReviewRequest(),
    )
