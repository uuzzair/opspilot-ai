"""Tests for incident CRUD endpoints."""
from uuid import uuid4

from fastapi.testclient import TestClient

INCIDENTS_URL = "/api/incidents"


def test_create_incident(client: TestClient) -> None:
    """Create an incident."""
    response = client.post(
        INCIDENTS_URL,
        json={
            "title": "API latency",
            "description": "Checkout API latency is above SLO.",
            "severity": "high",
            "affected_service": "checkout-api",
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "API latency"
    assert data["description"] == "Checkout API latency is above SLO."
    assert data["source"] == "manual"
    assert data["severity"] == "high"
    assert data["status"] == "open"
    assert data["affected_service"] == "checkout-api"
    assert data["id"]


def test_list_incidents(client: TestClient) -> None:
    """List incidents."""
    client.post(
        INCIDENTS_URL,
        json={"title": "First", "description": "First incident"},
    )
    client.post(
        INCIDENTS_URL,
        json={"title": "Second", "description": "Second incident"},
    )

    response = client.get(INCIDENTS_URL)

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert {incident["title"] for incident in data} == {"First", "Second"}


def test_get_incident(client: TestClient) -> None:
    """Get an incident by ID."""
    create_response = client.post(
        INCIDENTS_URL,
        json={"title": "Database errors", "description": "Postgres errors increased."},
    )
    incident_id = create_response.json()["id"]

    response = client.get(f"{INCIDENTS_URL}/{incident_id}")

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == incident_id
    assert data["title"] == "Database errors"


def test_update_incident(client: TestClient) -> None:
    """Update an incident."""
    create_response = client.post(
        INCIDENTS_URL,
        json={"title": "Queue backlog", "description": "Worker queue is growing."},
    )
    incident_id = create_response.json()["id"]

    response = client.patch(
        f"{INCIDENTS_URL}/{incident_id}",
        json={"status": "in_progress", "severity": "medium"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == incident_id
    assert data["status"] == "in_progress"
    assert data["severity"] == "medium"


def test_get_missing_incident_returns_404(client: TestClient) -> None:
    """Return 404 for a missing incident."""
    response = client.get(f"{INCIDENTS_URL}/{uuid4()}")

    assert response.status_code == 404
    assert response.json()["detail"] == "Incident not found"


def test_update_missing_incident_returns_404(client: TestClient) -> None:
    """Return 404 when updating a missing incident."""
    response = client.patch(f"{INCIDENTS_URL}/{uuid4()}", json={"status": "closed"})

    assert response.status_code == 404
    assert response.json()["detail"] == "Incident not found"
