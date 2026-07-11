"""Deterministic incident triage operations."""
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Incident, TriageResult
from app.schemas.runbook import RunbookSearchRequest
from app.services import runbook_service

FALLBACK_ACTIONS = [
    "Check recent deployments",
    "Review application logs",
    "Check database and external dependency health",
    "Escalate if customer impact is high",
]

SEVERITY_KEYWORDS = {
    "critical": ["outage", "down", "unavailable", "data loss", "payment failure"],
    "high": ["high latency", "p95", "error rate", "database cpu", "queue backlog"],
    "medium": ["degraded", "intermittent", "timeout"],
}


def create_triage_result(db: Session, incident: Incident) -> TriageResult:
    """Create a deterministic triage result for an incident."""
    query = build_incident_query(incident)
    severity = classify_severity(query)
    chunks = runbook_service.search_runbook_chunks(
        db,
        RunbookSearchRequest(
            query=query,
            service_name=incident.affected_service,
            top_k=5,
        ),
    )
    recommended_actions = [
        chunk.chunk_text.strip()
        for chunk in chunks
        if chunk.chunk_text.strip()
    ] or FALLBACK_ACTIONS

    incident.severity = severity
    triage_result = TriageResult(
        incident_id=incident.id,
        summary=build_summary(incident, severity),
        suspected_cause=build_suspected_cause(severity, chunks_found=bool(chunks)),
        recommended_actions=recommended_actions,
        confidence_score=0.75 if chunks else 0.45,
        model_name="deterministic-v1",
    )
    db.add(incident)
    db.add(triage_result)
    db.commit()
    db.refresh(triage_result)
    db.refresh(incident)
    return triage_result


def list_triage_results(db: Session, incident_id: UUID) -> list[TriageResult]:
    """List triage results for an incident, newest first."""
    result = db.execute(
        select(TriageResult)
        .where(TriageResult.incident_id == incident_id)
        .order_by(TriageResult.created_at.desc(), TriageResult.id.desc())
    )
    return list(result.scalars().all())


def build_incident_query(incident: Incident) -> str:
    """Build retrieval/classification text from incident fields."""
    parts = [incident.title, incident.description]
    if incident.affected_service:
        parts.append(incident.affected_service)
    return " ".join(parts)


def classify_severity(text: str) -> str:
    """Classify severity using deterministic keyword rules."""
    normalized = text.lower()
    for severity, keywords in SEVERITY_KEYWORDS.items():
        if any(keyword in normalized for keyword in keywords):
            return severity
    return "low"


def build_summary(incident: Incident, severity: str) -> str:
    """Build a concise deterministic summary."""
    service = incident.affected_service or "an unspecified service"
    return f"{severity.title()} incident for {service}: {incident.title}"


def build_suspected_cause(severity: str, chunks_found: bool) -> str:
    """Build a deterministic suspected cause."""
    if chunks_found:
        return "Relevant runbook context was found for this incident."
    return f"No matching runbook context found; classified as {severity} from incident text."
