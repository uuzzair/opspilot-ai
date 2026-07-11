"""Tests for deterministic incident triage."""
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.services import triage_service

AUTH_URL = "/api/auth"
INCIDENTS_URL = "/api/incidents"


def auth_headers(client: TestClient, email: str = "triage@example.com") -> dict[str, str]:
    """Register and login a test user."""
    password = "correct-horse-battery"
    client.post(
        f"{AUTH_URL}/register",
        json={"email": email, "password": password, "full_name": "Triage User"},
    )
    login_response = client.post(
        f"{AUTH_URL}/login",
        json={"email": email, "password": password},
    )
    token = login_response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def create_incident(
    client: TestClient,
    title: str = "High latency on payments",
    description: str = "p95 latency is high for checkout requests.",
    affected_service: str = "payments-api",
) -> dict:
    """Create a test incident."""
    response = client.post(
        INCIDENTS_URL,
        headers=auth_headers(client),
        json={
            "title": title,
            "description": description,
            "affected_service": affected_service,
        },
    )
    assert response.status_code == 201
    return response.json()


@pytest.fixture
def fake_retrieval(monkeypatch: pytest.MonkeyPatch) -> list[SimpleNamespace]:
    """Mock runbook retrieval for deterministic triage tests."""
    chunks = [
        SimpleNamespace(chunk_text="Check p95 latency dashboard."),
        SimpleNamespace(chunk_text="Review upstream dependency health."),
    ]

    def search_runbook_chunks(db, search_in):
        return chunks

    monkeypatch.setattr(
        triage_service.runbook_service,
        "search_runbook_chunks",
        search_runbook_chunks,
    )
    return chunks


def test_create_triage_requires_auth(client: TestClient) -> None:
    """Require auth for triage creation."""
    response = client.post(f"{INCIDENTS_URL}/{uuid4()}/triage")

    assert response.status_code == 401


def test_create_triage_missing_incident_returns_404(client: TestClient) -> None:
    """Return 404 when triaging a missing incident."""
    response = client.post(
        f"{INCIDENTS_URL}/{uuid4()}/triage",
        headers=auth_headers(client),
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Incident not found"


def test_create_triage_with_runbook_context(client: TestClient, fake_retrieval) -> None:
    """Create triage using retrieved runbook chunks."""
    incident = create_incident(client)

    response = client.post(
        f"{INCIDENTS_URL}/{incident['id']}/triage",
        headers=auth_headers(client, "triager@example.com"),
    )

    assert response.status_code == 201
    data = response.json()
    assert data["incident_id"] == incident["id"]
    assert data["summary"] == "High incident for payments-api: High latency on payments"
    assert data["suspected_cause"] == "Relevant runbook context was found for this incident."
    assert data["recommended_actions"] == [
        "Check p95 latency dashboard.",
        "Review upstream dependency health.",
    ]
    assert data["confidence_score"] == 0.75
    assert data["model_name"] == "deterministic-v1"
    assert data["approval_status"] == "pending"

    incident_response = client.get(f"{INCIDENTS_URL}/{incident['id']}")
    assert incident_response.json()["severity"] == "high"


def test_create_triage_uses_fallback_actions(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    """Use fallback actions when no chunks are retrieved."""
    monkeypatch.setattr(
        triage_service.runbook_service,
        "search_runbook_chunks",
        lambda db, search_in: [],
    )
    incident = create_incident(
        client,
        title="Payment failure",
        description="Payment failure during checkout.",
    )

    response = client.post(
        f"{INCIDENTS_URL}/{incident['id']}/triage",
        headers=auth_headers(client, "fallback@example.com"),
    )

    assert response.status_code == 201
    data = response.json()
    assert data["recommended_actions"] == triage_service.FALLBACK_ACTIONS
    assert data["confidence_score"] == 0.45

    incident_response = client.get(f"{INCIDENTS_URL}/{incident['id']}")
    assert incident_response.json()["severity"] == "critical"


def test_list_triage_is_public(client: TestClient, fake_retrieval) -> None:
    """List triage results without auth."""
    incident = create_incident(client)
    client.post(
        f"{INCIDENTS_URL}/{incident['id']}/triage",
        headers=auth_headers(client, "list-triage@example.com"),
    )

    response = client.get(f"{INCIDENTS_URL}/{incident['id']}/triage")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["incident_id"] == incident["id"]


def test_list_triage_missing_incident_returns_404(client: TestClient) -> None:
    """Return 404 when listing triage for a missing incident."""
    response = client.get(f"{INCIDENTS_URL}/{uuid4()}/triage")

    assert response.status_code == 404
    assert response.json()["detail"] == "Incident not found"


def test_triage_retrieval_uses_incident_text_and_top_five(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Retrieve top 5 chunks using incident text and affected service."""
    captured = {}

    def search_runbook_chunks(db, search_in):
        captured["query"] = search_in.query
        captured["service_name"] = search_in.service_name
        captured["top_k"] = search_in.top_k
        return []

    monkeypatch.setattr(
        triage_service.runbook_service,
        "search_runbook_chunks",
        search_runbook_chunks,
    )
    incident = create_incident(
        client,
        title="Intermittent timeout",
        description="Users report intermittent timeout errors.",
        affected_service="checkout-api",
    )

    response = client.post(
        f"{INCIDENTS_URL}/{incident['id']}/triage",
        headers=auth_headers(client, "capture@example.com"),
    )

    assert response.status_code == 201
    assert "Intermittent timeout" in captured["query"]
    assert "Users report intermittent timeout errors." in captured["query"]
    assert "checkout-api" in captured["query"]
    assert captured["service_name"] == "checkout-api"
    assert captured["top_k"] == 5
