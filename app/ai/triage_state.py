"""State definitions for deterministic triage graph."""
from typing import TypedDict
from uuid import UUID


class RetrievedChunk(TypedDict):
    """Runbook chunk metadata used by triage."""

    runbook_id: UUID
    chunk_id: UUID
    chunk_text: str
    chunk_index: int
    service_name: str
    distance: float


class TriageState(TypedDict, total=False):
    """LangGraph state for deterministic incident triage."""

    incident_id: UUID
    title: str
    description: str
    affected_service: str | None
    query: str
    severity: str
    summary: str
    suspected_cause: str
    recommended_actions: list[str]
    confidence_score: float
    retrieved_chunks: list[RetrievedChunk]
