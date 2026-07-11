"""Tests for triage approval workflow."""
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.services import triage_service

AUTH_URL = "/api/auth"
INCIDENTS_URL = "/api/incidents"
TRIAGE_URL = "/api/triage"


def auth_headers(client: TestClient, email: str = "reviewer@example.com") -> tuple[dict[str, str], str]:
    """Register and login a test user."""
    password = "correct-horse-battery"
    register_response = client.post(
        f"{AUTH_URL}/register",
        json={"email": email, "password": password, "full_name": "Reviewer"},
    )
    login_response = client.post(
        f"{AUTH_URL}/login",
        json={"email": email, "password": password},
    )
    token = login_response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}, register_response.json()["id"]


@pytest.fixture(autouse=True)
def no_runbook_results(monkeypatch: pytest.MonkeyPatch) -> None:
    """Avoid embedding-backed retrieval in review tests."""
    monkeypatch.setattr(
        triage_service.runbook_service,
        "search_runbook_chunks",
        lambda db, search_in: [],
    )


def create_triage_result(client: TestClient) -> dict:
    """Create a triage result to review."""
    headers, _ = auth_headers(client, "incident-owner@example.com")
    incident_response = client.post(
        INCIDENTS_URL,
        headers=headers,
        json={
            "title": "High latency",
            "description": "p95 latency is high.",
            "affected_service": "payments-api",
        },
    )
    assert incident_response.status_code == 201
    triage_response = client.post(
        f"{INCIDENTS_URL}/{incident_response.json()['id']}/triage",
        headers=headers,
    )
    assert triage_response.status_code == 201
    return triage_response.json()


def test_approve_triage_result(client: TestClient) -> None:
    """Approve a triage result."""
    triage = create_triage_result(client)
    headers, reviewer_id = auth_headers(client, "approver@example.com")

    response = client.post(
        f"{TRIAGE_URL}/{triage['id']}/approve",
        headers=headers,
        json={"reviewer_notes": "Looks correct."},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["approval_status"] == "approved"
    assert data["approved_by_id"] == reviewer_id
    assert data["reviewer_notes"] == "Looks correct."


def test_reject_triage_result(client: TestClient) -> None:
    """Reject a triage result."""
    triage = create_triage_result(client)
    headers, reviewer_id = auth_headers(client, "rejector@example.com")

    response = client.post(
        f"{TRIAGE_URL}/{triage['id']}/reject",
        headers=headers,
        json={"reviewer_notes": "Needs more context."},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["approval_status"] == "rejected"
    assert data["approved_by_id"] == reviewer_id
    assert data["reviewer_notes"] == "Needs more context."


def test_missing_triage_result_returns_404(client: TestClient) -> None:
    """Return 404 for a missing triage result."""
    headers, _ = auth_headers(client)

    response = client.post(
        f"{TRIAGE_URL}/{uuid4()}/approve",
        headers=headers,
        json={"reviewer_notes": "Missing."},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Triage result not found"


def test_unauthenticated_approve_returns_401(client: TestClient) -> None:
    """Require auth for approval."""
    response = client.post(f"{TRIAGE_URL}/{uuid4()}/approve")

    assert response.status_code == 401


def test_unauthenticated_reject_returns_401(client: TestClient) -> None:
    """Require auth for rejection."""
    response = client.post(f"{TRIAGE_URL}/{uuid4()}/reject")

    assert response.status_code == 401


def test_review_without_notes_is_allowed(client: TestClient) -> None:
    """Allow review actions without reviewer notes."""
    triage = create_triage_result(client)
    headers, reviewer_id = auth_headers(client, "no-notes@example.com")

    response = client.post(f"{TRIAGE_URL}/{triage['id']}/approve", headers=headers)

    assert response.status_code == 200
    data = response.json()
    assert data["approval_status"] == "approved"
    assert data["approved_by_id"] == reviewer_id
    assert data["reviewer_notes"] is None
