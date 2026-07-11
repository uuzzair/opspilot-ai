"""Tests for LangGraph deterministic triage workflow."""
from uuid import uuid4

import pytest

from app.ai.triage_graph import FALLBACK_ACTIONS, run_triage_graph
from app.ai.triage_state import TriageState


def no_chunks(state: TriageState) -> list:
    """Return no chunks from retrieval."""
    return []


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("payments outage", "critical"),
        ("p95 high latency", "high"),
        ("intermittent timeout", "medium"),
        ("minor cosmetic issue", "low"),
    ],
)
def test_graph_classifies_severity(text: str, expected: str) -> None:
    """Classify severity in the graph."""
    output = run_triage_graph(
        {
            "incident_id": uuid4(),
            "title": text,
            "description": "Incident description",
            "affected_service": "payments-api",
        },
        no_chunks,
    )

    assert output["severity"] == expected


def test_graph_returns_fallback_actions_when_no_chunks() -> None:
    """Use fallback actions when retrieval returns no chunks."""
    output = run_triage_graph(
        {
            "incident_id": uuid4(),
            "title": "Payment failure",
            "description": "Payment failure at checkout.",
            "affected_service": "payments-api",
        },
        no_chunks,
    )

    assert output["recommended_actions"] == FALLBACK_ACTIONS
    assert output["confidence_score"] == 0.45
    assert output["retrieved_chunks"] == []


def test_graph_uses_retrieved_chunks_for_actions() -> None:
    """Convert retrieved runbook chunks into action strings."""
    chunk_id = uuid4()
    runbook_id = uuid4()

    def retrieve_chunks(state: TriageState) -> list:
        return [
            {
                "runbook_id": runbook_id,
                "chunk_id": chunk_id,
                "chunk_text": "Check latency dashboard.",
                "chunk_index": 0,
                "service_name": "payments-api",
                "distance": 0.1,
            }
        ]

    output = run_triage_graph(
        {
            "incident_id": uuid4(),
            "title": "High latency",
            "description": "p95 latency is high.",
            "affected_service": "payments-api",
        },
        retrieve_chunks,
    )

    assert output["recommended_actions"] == ["Check latency dashboard."]
    assert output["confidence_score"] == 0.75
    assert output["retrieved_chunks"][0]["chunk_id"] == chunk_id
