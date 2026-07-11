"""Deterministic incident triage operations."""
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.llm_provider import get_triage_provider
from app.ai.triage_graph import FALLBACK_ACTIONS, classify_severity_from_text, run_triage_graph
from app.ai.triage_state import RetrievedChunk, TriageState
from app.db.models import Incident, TriageResult
from app.schemas.runbook import RunbookSearchRequest
from app.schemas.triage import TriageReviewRequest
from app.services import runbook_service

APPROVED_STATUS = "approved"
REJECTED_STATUS = "rejected"


def create_triage_result(db: Session, incident: Incident) -> TriageResult:
    """Create a LangGraph-orchestrated deterministic triage result."""
    graph_output = run_triage_graph(
        build_initial_triage_state(incident),
        lambda state: retrieve_runbook_chunks(db, state),
        get_triage_provider(FALLBACK_ACTIONS),
    )
    severity = graph_output["severity"]
    incident.severity = severity
    triage_result = TriageResult(
        incident_id=incident.id,
        summary=graph_output["summary"],
        suspected_cause=graph_output["suspected_cause"],
        recommended_actions=graph_output["recommended_actions"],
        confidence_score=graph_output["confidence_score"],
        model_name=graph_output["model_name"],
    )
    db.add(incident)
    db.add(triage_result)
    db.commit()
    db.refresh(triage_result)
    db.refresh(incident)
    return triage_result


def build_initial_triage_state(incident: Incident) -> TriageState:
    """Build graph input state from an incident."""
    return {
        "incident_id": incident.id,
        "title": incident.title,
        "description": incident.description,
        "affected_service": incident.affected_service,
    }


def retrieve_runbook_chunks(db: Session, state: TriageState) -> list[RetrievedChunk]:
    """Retrieve top 5 runbook chunks for graph state."""
    chunks = runbook_service.search_runbook_chunks(
        db,
        RunbookSearchRequest(
            query=state["query"],
            service_name=state.get("affected_service"),
            top_k=5,
        ),
    )
    return [
        {
            "runbook_id": chunk.runbook_id,
            "chunk_id": chunk.chunk_id,
            "chunk_text": chunk.chunk_text,
            "chunk_index": chunk.chunk_index,
            "service_name": chunk.service_name,
            "distance": chunk.distance,
        }
        for chunk in chunks
    ]


def list_triage_results(db: Session, incident_id: UUID) -> list[TriageResult]:
    """List triage results for an incident, newest first."""
    result = db.execute(
        select(TriageResult)
        .where(TriageResult.incident_id == incident_id)
        .order_by(TriageResult.created_at.desc(), TriageResult.id.desc())
    )
    return list(result.scalars().all())


def get_triage_result(db: Session, triage_id: UUID) -> TriageResult | None:
    """Get a triage result by ID."""
    return db.get(TriageResult, triage_id)


def approve_triage_result(
    db: Session,
    triage_result: TriageResult,
    reviewer_id: UUID,
    review_in: TriageReviewRequest,
) -> TriageResult:
    """Approve a triage result."""
    return review_triage_result(
        db,
        triage_result,
        reviewer_id,
        review_in,
        APPROVED_STATUS,
    )


def reject_triage_result(
    db: Session,
    triage_result: TriageResult,
    reviewer_id: UUID,
    review_in: TriageReviewRequest,
) -> TriageResult:
    """Reject a triage result."""
    return review_triage_result(
        db,
        triage_result,
        reviewer_id,
        review_in,
        REJECTED_STATUS,
    )


def review_triage_result(
    db: Session,
    triage_result: TriageResult,
    reviewer_id: UUID,
    review_in: TriageReviewRequest,
    approval_status: str,
) -> TriageResult:
    """Persist a human review decision for a triage result."""
    triage_result.approval_status = approval_status
    triage_result.approved_by_id = reviewer_id
    triage_result.reviewer_notes = review_in.reviewer_notes
    db.add(triage_result)
    db.commit()
    db.refresh(triage_result)
    return triage_result


def build_incident_query(incident: Incident) -> str:
    """Build retrieval/classification text from incident fields."""
    parts = [incident.title, incident.description]
    if incident.affected_service:
        parts.append(incident.affected_service)
    return " ".join(parts)


def classify_severity(text: str) -> str:
    """Classify severity using deterministic keyword rules."""
    return classify_severity_from_text(text)


def build_summary(incident: Incident, severity: str) -> str:
    """Build a concise deterministic summary."""
    service = incident.affected_service or "an unspecified service"
    return f"{severity.title()} incident for {service}: {incident.title}"


def build_suspected_cause(severity: str, chunks_found: bool) -> str:
    """Build a deterministic suspected cause."""
    if chunks_found:
        return "Relevant runbook context was found for this incident."
    return f"No matching runbook context found; classified as {severity} from incident text."
