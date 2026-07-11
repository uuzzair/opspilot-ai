"""LangGraph workflow for deterministic incident triage."""
from collections.abc import Callable

from langgraph.graph import END, StateGraph

from app.ai.triage_state import RetrievedChunk, TriageState

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

Retriever = Callable[[TriageState], list[RetrievedChunk]]


def classify_severity_from_text(text: str) -> str:
    """Classify severity using deterministic keyword rules."""
    normalized = text.lower()
    for severity, keywords in SEVERITY_KEYWORDS.items():
        if any(keyword in normalized for keyword in keywords):
            return severity
    return "low"


def build_triage_graph(retriever: Retriever):
    """Build the deterministic triage graph."""
    graph = StateGraph(TriageState)
    graph.add_node("normalize_incident", normalize_incident)
    graph.add_node("classify_severity", classify_severity)
    graph.add_node("retrieve_runbooks", lambda state: retrieve_runbooks(state, retriever))
    graph.add_node("generate_recommendations", generate_recommendations)
    graph.add_node("validate_output", validate_output)

    graph.set_entry_point("normalize_incident")
    graph.add_edge("normalize_incident", "classify_severity")
    graph.add_edge("classify_severity", "retrieve_runbooks")
    graph.add_edge("retrieve_runbooks", "generate_recommendations")
    graph.add_edge("generate_recommendations", "validate_output")
    graph.add_edge("validate_output", END)
    return graph.compile()


def run_triage_graph(state: TriageState, retriever: Retriever) -> TriageState:
    """Run the deterministic triage graph."""
    graph = build_triage_graph(retriever)
    return graph.invoke(state)


def normalize_incident(state: TriageState) -> TriageState:
    """Normalize incident fields into a retrieval/classification query."""
    parts = [state.get("title", ""), state.get("description", "")]
    affected_service = state.get("affected_service")
    if affected_service:
        parts.append(affected_service)
    return {"query": " ".join(part for part in parts if part).strip()}


def classify_severity(state: TriageState) -> TriageState:
    """Classify incident severity."""
    return {"severity": classify_severity_from_text(state.get("query", ""))}


def retrieve_runbooks(state: TriageState, retriever: Retriever) -> TriageState:
    """Retrieve runbook chunks for the incident query."""
    return {"retrieved_chunks": retriever(state)}


def generate_recommendations(state: TriageState) -> TriageState:
    """Generate deterministic output from incident and retrieved chunks."""
    chunks = state.get("retrieved_chunks", [])
    actions = [
        chunk["chunk_text"].strip()
        for chunk in chunks
        if chunk["chunk_text"].strip()
    ] or FALLBACK_ACTIONS
    severity = state.get("severity", "low")
    service = state.get("affected_service") or "an unspecified service"
    chunks_found = bool(chunks)
    return {
        "summary": f"{severity.title()} incident for {service}: {state.get('title', '')}",
        "suspected_cause": (
            "Relevant runbook context was found for this incident."
            if chunks_found
            else f"No matching runbook context found; classified as {severity} from incident text."
        ),
        "recommended_actions": actions,
        "confidence_score": 0.75 if chunks_found else 0.45,
    }


def validate_output(state: TriageState) -> TriageState:
    """Validate graph output has required fields and allowed values."""
    severity = state.get("severity")
    if severity not in {"critical", "high", "medium", "low"}:
        raise ValueError("Invalid severity from triage graph")
    if not state.get("summary"):
        raise ValueError("Triage graph did not produce a summary")
    if not state.get("recommended_actions"):
        raise ValueError("Triage graph did not produce recommended actions")
    return {}
