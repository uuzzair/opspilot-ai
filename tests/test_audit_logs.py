"""Tests for audit logging."""
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.api import incidents as incidents_api
from app.services import triage_service

AUTH_URL = "/api/auth"
AUDIT_LOGS_URL = "/api/audit-logs"
INCIDENTS_URL = "/api/incidents"
RUNBOOKS_URL = "/api/runbooks"
TRIAGE_URL = "/api/triage"


class FakeAsyncResult:
    """Minimal Celery AsyncResult stand-in."""

    id = "audit-celery-task-123"


def auth_headers(client: TestClient, email: str = "audit@example.com") -> dict[str, str]:
    """Register and login a test user."""
    password = "correct-horse-battery"
    client.post(
        f"{AUTH_URL}/register",
        json={"email": email, "password": password, "full_name": "Audit User"},
    )
    response = client.post(f"{AUTH_URL}/login", json={"email": email, "password": password})
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_user_registration_creates_audit_log(client: TestClient) -> None:
    """Audit user registration."""
    email = "registered-audit@example.com"
    register_response = client.post(
        f"{AUTH_URL}/register",
        json={"email": email, "password": "correct-horse-battery"},
    )
    user_id = register_response.json()["id"]
    headers = auth_headers(client, "audit-reader@example.com")

    response = client.get(
        AUDIT_LOGS_URL,
        headers=headers,
        params={"entity_type": "user", "entity_id": user_id, "action": "registered"},
    )

    assert response.status_code == 200
    logs = response.json()
    assert len(logs) == 1
    assert logs[0]["actor_id"] == user_id
    assert logs[0]["details"] == {"email": email, "role": "engineer"}


def test_incident_creation_creates_audit_log(client: TestClient) -> None:
    """Audit incident creation."""
    headers = auth_headers(client, "incident-audit@example.com")
    create_response = client.post(
        INCIDENTS_URL,
        headers=headers,
        json={
            "title": "Payments API high latency",
            "description": "Full incident description should not be audited.",
            "affected_service": "payments-api",
        },
    )
    incident = create_response.json()

    response = client.get(
        AUDIT_LOGS_URL,
        headers=headers,
        params={
            "entity_type": "incident",
            "entity_id": incident["id"],
            "action": "created",
        },
    )

    assert response.status_code == 200
    log = response.json()[0]
    assert log["details"]["title"] == "Payments API high latency"
    assert log["details"]["affected_service"] == "payments-api"
    assert "description" not in log["details"]


def test_runbook_creation_creates_audit_log(client: TestClient) -> None:
    """Audit runbook creation."""
    headers = auth_headers(client, "runbook-audit@example.com")
    create_response = client.post(
        RUNBOOKS_URL,
        headers=headers,
        json={
            "title": "Payments latency runbook",
            "service_name": "payments-api",
            "description": "Runbook description.",
        },
    )
    runbook = create_response.json()

    response = client.get(
        AUDIT_LOGS_URL,
        headers=headers,
        params={"entity_type": "runbook", "entity_id": runbook["id"], "action": "created"},
    )

    assert response.status_code == 200
    assert response.json()[0]["details"] == {
        "title": "Payments latency runbook",
        "service_name": "payments-api",
    }


def test_triage_approval_and_rejection_create_audit_logs(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Audit triage approval and rejection."""
    monkeypatch.setattr(
        triage_service.runbook_service,
        "search_runbook_chunks",
        lambda db, search_in: [
            SimpleNamespace(
                runbook_id=uuid4(),
                chunk_id=uuid4(),
                chunk_text="Check p95 latency dashboard.",
                chunk_index=0,
                service_name="payments-api",
                distance=0.1,
            )
        ],
    )
    headers = auth_headers(client, "triage-audit@example.com")
    incident_response = client.post(
        INCIDENTS_URL,
        headers=headers,
        json={
            "title": "Payments API high latency",
            "description": "p95 latency is high.",
            "affected_service": "payments-api",
        },
    )
    triage_response = client.post(
        f"{INCIDENTS_URL}/{incident_response.json()['id']}/triage",
        headers=headers,
    )
    triage_id = triage_response.json()["id"]

    approve_response = client.post(f"{TRIAGE_URL}/{triage_id}/approve", headers=headers)
    reject_response = client.post(f"{TRIAGE_URL}/{triage_id}/reject", headers=headers)

    assert approve_response.status_code == 200
    assert reject_response.status_code == 200
    approved_logs = client.get(
        AUDIT_LOGS_URL,
        headers=headers,
        params={"entity_type": "triage_result", "entity_id": triage_id, "action": "approved"},
    ).json()
    rejected_logs = client.get(
        AUDIT_LOGS_URL,
        headers=headers,
        params={"entity_type": "triage_result", "entity_id": triage_id, "action": "rejected"},
    ).json()
    assert len(approved_logs) == 1
    assert len(rejected_logs) == 1


def test_triage_job_creation_creates_audit_log(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Audit triage job creation without running Redis."""
    monkeypatch.setattr(
        incidents_api.process_triage_job,
        "delay",
        lambda job_id: FakeAsyncResult(),
    )
    headers = auth_headers(client, "job-audit@example.com")
    incident_response = client.post(
        INCIDENTS_URL,
        headers=headers,
        json={
            "title": "Payments API high latency",
            "description": "p95 latency is high.",
            "affected_service": "payments-api",
        },
    )
    job_response = client.post(
        f"{INCIDENTS_URL}/{incident_response.json()['id']}/triage-jobs",
        headers=headers,
    )
    job = job_response.json()

    response = client.get(
        AUDIT_LOGS_URL,
        headers=headers,
        params={"entity_type": "triage_job", "entity_id": job["id"], "action": "created"},
    )

    assert response.status_code == 200
    log = response.json()[0]
    assert log["details"]["status"] == "pending"
    assert log["details"]["celery_task_id"] == "audit-celery-task-123"


def test_audit_logs_requires_auth(client: TestClient) -> None:
    """Require authentication for audit log listing."""
    response = client.get(AUDIT_LOGS_URL)

    assert response.status_code == 401


def test_audit_log_filters_work(client: TestClient) -> None:
    """Filter audit logs by entity type, action, actor, and limit."""
    headers = auth_headers(client, "filter-audit@example.com")
    incident_response = client.post(
        INCIDENTS_URL,
        headers=headers,
        json={
            "title": "Filter test incident",
            "description": "Description should not appear in audit logs.",
            "affected_service": "payments-api",
        },
    )
    actor_id = incident_response.json()["created_by_id"]

    response = client.get(
        AUDIT_LOGS_URL,
        headers=headers,
        params={
            "entity_type": "incident",
            "action": "created",
            "actor_id": actor_id,
            "limit": 1,
        },
    )

    assert response.status_code == 200
    logs = response.json()
    assert len(logs) == 1
    assert logs[0]["entity_type"] == "incident"
    assert logs[0]["action"] == "created"
    assert logs[0]["actor_id"] == actor_id
