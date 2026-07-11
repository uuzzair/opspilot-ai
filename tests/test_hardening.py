"""Tests for production hardening behavior."""
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from app.api import health
from app.services import rate_limit_service

AUTH_URL = "/api/auth"
INCIDENTS_URL = "/api/incidents"
RUNBOOKS_URL = "/api/runbooks"
AUDIT_LOGS_URL = "/api/audit-logs"


def auth_headers(client: TestClient, email: str = "hardening@example.com") -> dict[str, str]:
    """Register and login a test user."""
    password = "correct-horse-battery"
    client.post(
        f"{AUTH_URL}/register",
        json={"email": email, "password": password, "full_name": "Hardening User"},
    )
    response = client.post(f"{AUTH_URL}/login", json={"email": email, "password": password})
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_request_id_header_is_preserved(client: TestClient) -> None:
    """Use caller-provided request ID."""
    response = client.get("/health", headers={"X-Request-ID": "request-123"})

    assert response.headers["X-Request-ID"] == "request-123"


def test_request_id_header_is_generated(client: TestClient) -> None:
    """Generate request ID when none is provided."""
    response = client.get("/health")

    request_id = response.headers["X-Request-ID"]
    assert UUID(request_id)


def test_readiness_returns_clear_status(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Readiness reports dependency status without secrets."""
    monkeypatch.setattr(health, "check_database", lambda: "ok")
    monkeypatch.setattr(health, "check_redis", lambda: "ok")

    response = client.get("/health/ready")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ready",
        "checks": {"database": "ok", "redis": "ok"},
    }


def test_auth_rate_limit_returns_429(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Auth endpoints return 429 when the limiter rejects a request."""
    monkeypatch.setattr(
        rate_limit_service,
        "check_auth_rate_limit",
        lambda identifier, action: (_ for _ in ()).throw(rate_limit_service.RateLimitExceeded()),
    )
    monkeypatch.setattr("app.api.auth.check_auth_rate_limit", rate_limit_service.check_auth_rate_limit)

    response = client.post(
        f"{AUTH_URL}/login",
        json={"email": "missing@example.com", "password": "bad-password"},
    )

    assert response.status_code == 429
    assert response.json()["detail"] == "Too many requests"


def test_incident_list_supports_pagination(client: TestClient) -> None:
    """Incident list supports limit and offset."""
    headers = auth_headers(client, "incident-page@example.com")
    for index in range(3):
        response = client.post(
            INCIDENTS_URL,
            headers=headers,
            json={
                "title": f"Incident {index}",
                "description": "Pagination test incident.",
                "affected_service": "payments-api",
            },
        )
        assert response.status_code == 201

    response = client.get(f"{INCIDENTS_URL}?limit=2&offset=1")

    assert response.status_code == 200
    assert len(response.json()) == 2


def test_runbook_list_supports_pagination(client: TestClient) -> None:
    """Runbook list supports limit and offset."""
    headers = auth_headers(client, "runbook-page@example.com")
    for index in range(3):
        response = client.post(
            RUNBOOKS_URL,
            headers=headers,
            json={
                "title": f"Runbook {index}",
                "service_name": f"service-{index}",
            },
        )
        assert response.status_code == 201

    response = client.get(f"{RUNBOOKS_URL}?limit=2&offset=1")

    assert response.status_code == 200
    assert len(response.json()) == 2


def test_audit_log_list_supports_offset(client: TestClient) -> None:
    """Audit log list supports offset."""
    headers = auth_headers(client, "audit-page@example.com")
    for index in range(2):
        response = client.post(
            INCIDENTS_URL,
            headers=headers,
            json={
                "title": f"Audited incident {index}",
                "description": "Audit pagination test incident.",
                "affected_service": "payments-api",
            },
        )
        assert response.status_code == 201

    response = client.get(
        f"{AUDIT_LOGS_URL}?entity_type=incident&action=created&limit=1&offset=1",
        headers=headers,
    )

    assert response.status_code == 200
    assert len(response.json()) == 1
