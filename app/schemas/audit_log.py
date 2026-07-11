"""Audit log API schemas."""
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class AuditLogRead(BaseModel):
    """Response body for an audit log."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    actor_id: UUID | None
    entity_type: str
    entity_id: str
    action: str
    details: dict
    created_at: datetime


class AuditLogFilters(BaseModel):
    """Supported audit log filters."""

    entity_type: str | None = None
    entity_id: str | None = None
    actor_id: UUID | None = None
    action: str | None = None
    limit: int = Field(default=50, ge=1, le=100)
    offset: int = Field(default=0, ge=0)
