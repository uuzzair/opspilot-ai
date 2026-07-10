"""Runbook API schemas."""
from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class RunbookCreate(BaseModel):
    """Request body for creating a runbook."""

    title: str = Field(min_length=1, max_length=255)
    service_name: str = Field(min_length=1, max_length=255)
    description: str | None = None


class RunbookUpdate(BaseModel):
    """Request body for updating a runbook."""

    title: str | None = Field(default=None, min_length=1, max_length=255)
    service_name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None


class RunbookRead(BaseModel):
    """Response body for a runbook."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    service_name: str
    description: str | None
    created_by_id: UUID | None
    created_at: datetime
    updated_at: datetime


class RunbookChunkCreate(BaseModel):
    """Request body for creating a runbook chunk."""

    chunk_text: str = Field(min_length=1)
    chunk_index: int = Field(ge=0)
    metadata: dict[str, Any] = Field(default_factory=dict)


class RunbookChunkRead(BaseModel):
    """Response body for a runbook chunk."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    runbook_id: UUID
    chunk_text: str
    chunk_index: int
    metadata: dict[str, Any] = Field(validation_alias="metadata_")
    created_at: datetime
    updated_at: datetime


class RunbookSearchRequest(BaseModel):
    """Request body for searching runbook chunks."""

    query: str = Field(min_length=1)
    service_name: str | None = Field(default=None, min_length=1, max_length=255)
    top_k: int = Field(default=5, ge=1, le=10)


class RunbookChunkSearchResult(BaseModel):
    """Search result for a matching runbook chunk."""

    runbook_id: UUID
    chunk_id: UUID
    chunk_text: str
    chunk_index: int
    service_name: str
    distance: float
