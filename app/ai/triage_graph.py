"""LangGraph workflow for deterministic incident triage."""
from collections.abc import Callable

from langgraph.graph import END, StateGraph

from app.ai.llm_provider import DeterministicTriageProvider, TriageProvider
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


def build_triage_graph(retriever: Retriever, provider: TriageProvider | None = None):
    """Build the deterministic triage graph."""
    triage_provider = provider or DeterministicTriageProvider(FALLBACK_ACTIONS)
    graph = StateGraph(TriageState)
    graph.add_node("normalize_incident", normalize_incident)
    graph.add_node("classify_severity", classify_severity)
    graph.add_node("retrieve_runbooks", lambda state: retrieve_runbooks(state, retriever))
    graph.add_node(
        "generate_recommendations",
        lambda state: generate_recommendations(state, triage_provider),
    )
    graph.add_node("validate_output", validate_output)

    graph.set_entry_point("normalize_incident")
    graph.add_edge("normalize_incident", "classify_severity")
    graph.add_edge("classify_severity", "retrieve_runbooks")
    graph.add_edge("retrieve_runbooks", "generate_recommendations")
    graph.add_edge("generate_recommendations", "validate_output")
    graph.add_edge("validate_output", END)
    return graph.compile()


def run_triage_graph(
    state: TriageState,
    retriever: Retriever,
    provider: TriageProvider | None = None,
) -> TriageState:
    """Run the deterministic triage graph."""
    graph = build_triage_graph(retriever, provider)
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


def generate_recommendations(state: TriageState, provider: TriageProvider) -> TriageState:
    """Generate structured output from the configured triage provider."""
    chunks = state.get("retrieved_chunks", [])
    generation = provider.generate_triage(
        incident_text=state.get("query", ""),
        retrieved_chunks=chunks,
        severity=state.get("severity", "low"),
        affected_service=state.get("affected_service"),
        title=state.get("title"),
    )
    return {
        "summary": generation.summary,
        "suspected_cause": generation.suspected_cause,
        "recommended_actions": generation.recommended_actions,
        "confidence_score": generation.confidence_score,
        "model_name": generation.model_name,
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
    confidence_score = state.get("confidence_score")
    if confidence_score is None or not 0 <= confidence_score <= 1:
        raise ValueError("Triage graph produced an invalid confidence score")
    if not state.get("model_name"):
        raise ValueError("Triage graph did not produce a model name")
    return {}
