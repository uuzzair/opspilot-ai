"""Incident API schemas."""
from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


IncidentSeverity = Literal["low", "medium", "high", "critical"]
IncidentStatus = Literal["open", "in_progress", "resolved", "closed"]


class IncidentCreate(BaseModel):
    """Request body for creating an incident."""

    title: str = Field(min_length=1, max_length=255)
    description: str = Field(min_length=1)
    source: str = Field(default="manual", min_length=1, max_length=50)
    severity: IncidentSeverity | None = None
    status: IncidentStatus = "open"
    affected_service: str | None = Field(default=None, max_length=255)
    created_by_id: UUID | None = None
    assigned_to_id: UUID | None = None


class IncidentUpdate(BaseModel):
    """Request body for updating an incident."""

    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, min_length=1)
    source: str | None = Field(default=None, min_length=1, max_length=50)
    severity: IncidentSeverity | None = None
    status: IncidentStatus | None = None
    affected_service: str | None = Field(default=None, max_length=255)
    assigned_to_id: UUID | None = None


class IncidentRead(BaseModel):
    """Response body for an incident."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    description: str
    source: str
    severity: str | None
    status: str
    affected_service: str | None
    created_by_id: UUID | None
    assigned_to_id: UUID | None
    created_at: datetime
    updated_at: datetime
