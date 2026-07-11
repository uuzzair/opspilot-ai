"""Triage job API schemas."""
from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict

TriageJobStatus = Literal["pending", "running", "succeeded", "failed"]


class TriageJobRead(BaseModel):
    """Response body for an asynchronous triage job."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    incident_id: UUID
    celery_task_id: str | None
    status: TriageJobStatus
    error_message: str | None
    triage_result_id: UUID | None
    requested_by_id: UUID | None
    created_at: datetime
    updated_at: datetime
