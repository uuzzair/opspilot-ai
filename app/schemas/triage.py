"""Triage API schemas."""
from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

ApprovalStatus = Literal["pending", "approved", "rejected"]


class TriageReviewRequest(BaseModel):
    """Request body for triage review actions."""

    reviewer_notes: str | None = Field(default=None, max_length=5000)


class TriageResultRead(BaseModel):
    """Response body for a triage result."""

    model_config = ConfigDict(from_attributes=True, protected_namespaces=())

    id: UUID
    incident_id: UUID
    summary: str
    suspected_cause: str | None
    recommended_actions: list[str]
    confidence_score: float | None
    model_name: str | None
    approval_status: ApprovalStatus
    approved_by_id: UUID | None
    reviewer_notes: str | None
    created_at: datetime
    updated_at: datetime
