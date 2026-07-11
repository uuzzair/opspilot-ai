"""Triage API schemas."""
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


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
    approval_status: str
    approved_by_id: UUID | None
    created_at: datetime
    updated_at: datetime
