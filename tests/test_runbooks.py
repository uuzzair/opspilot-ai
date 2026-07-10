"""Tests for runbook endpoints."""
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.services import runbook_service

RUNBOOKS_URL = "/api/runbooks"
AUTH_URL = "/api/auth"


class FakeEmbeddingService:
    """Deterministic embeddings for tests."""

    def embed_text(self, text: str) -> list[float]:
        lowered = text.lower()
        if "latency" in lowered:
            return [1.0, 0.0, 0.0]
        if "restart" in lowered:
            return [0.0, 1.0, 0.0]
        return [0.0, 0.0, 1.0]


@pytest.fixture(autouse=True)
def fake_embedding_service(monkeypatch: pytest.MonkeyPatch) -> None:
    """Avoid loading sentence-transformers during tests."""
    monkeypatch.setattr(runbook_service, "embedding_service", FakeEmbeddingService())


def auth_headers(client: TestClient, email: str = "runbooker@example.com") -> tuple[dict[str, str], str]:
    """Register and login a test user."""
    password = "correct-horse-battery"
    register_response = client.post(
        f"{AUTH_URL}/register",
        json={"email": email, "password": password, "full_name": "Runbook Author"},
    )
    login_response = client.post(
        f"{AUTH_URL}/login",
        json={"email": email, "password": password},
    )
    token = login_response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}, register_response.json()["id"]


def create_runbook(client: TestClient, email: str = "runbooker@example.com") -> dict:
    """Create a test runbook."""
    headers, _ = auth_headers(client, email)
    response = client.post(
        RUNBOOKS_URL,
        headers=headers,
        json={
            "title": "Restart checkout API",
            "service_name": "checkout-api",
            "description": "Steps to restart checkout safely.",
        },
    )
    assert response.status_code == 201
    return response.json()


def test_create_runbook_sets_created_by(client: TestClient) -> None:
    """Create a runbook as an authenticated user."""
    headers, user_id = auth_headers(client)

    response = client.post(
        RUNBOOKS_URL,
        headers=headers,
        json={"title": "Restart API", "service_name": "api"},
    )

    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Restart API"
    assert data["service_name"] == "api"
    assert data["created_by_id"] == user_id


def test_create_runbook_requires_auth(client: TestClient) -> None:
    """Require auth for runbook creation."""
    response = client.post(
        RUNBOOKS_URL,
        json={"title": "Restart API", "service_name": "api"},
    )

    assert response.status_code == 401


def test_create_runbook_validates_required_text(client: TestClient) -> None:
    """Reject empty title and service name."""
    headers, _ = auth_headers(client)

    response = client.post(
        RUNBOOKS_URL,
        headers=headers,
        json={"title": "", "service_name": ""},
    )

    assert response.status_code == 422


def test_list_runbooks_is_public(client: TestClient) -> None:
    """List runbooks without auth."""
    create_runbook(client, "one@example.com")
    create_runbook(client, "two@example.com")

    response = client.get(RUNBOOKS_URL)

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert {runbook["service_name"] for runbook in data} == {"checkout-api"}


def test_get_runbook_is_public(client: TestClient) -> None:
    """Get a runbook without auth."""
    runbook = create_runbook(client)

    response = client.get(f"{RUNBOOKS_URL}/{runbook['id']}")

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == runbook["id"]
    assert data["title"] == "Restart checkout API"


def test_get_missing_runbook_returns_404(client: TestClient) -> None:
    """Return 404 for missing runbook."""
    response = client.get(f"{RUNBOOKS_URL}/{uuid4()}")

    assert response.status_code == 404
    assert response.json()["detail"] == "Runbook not found"


def test_update_runbook_requires_auth(client: TestClient) -> None:
    """Require auth for runbook updates."""
    response = client.patch(f"{RUNBOOKS_URL}/{uuid4()}", json={"title": "Updated"})

    assert response.status_code == 401


def test_update_runbook(client: TestClient) -> None:
    """Update a runbook."""
    runbook = create_runbook(client)
    headers, _ = auth_headers(client, "editor@example.com")

    response = client.patch(
        f"{RUNBOOKS_URL}/{runbook['id']}",
        headers=headers,
        json={"title": "Updated checkout runbook"},
    )

    assert response.status_code == 200
    assert response.json()["title"] == "Updated checkout runbook"


def test_create_chunk_requires_auth(client: TestClient) -> None:
    """Require auth for chunk creation."""
    runbook = create_runbook(client)

    response = client.post(
        f"{RUNBOOKS_URL}/{runbook['id']}/chunks",
        json={"chunk_text": "Restart the service.", "chunk_index": 0},
    )

    assert response.status_code == 401


def test_create_and_list_chunks(client: TestClient) -> None:
    """Create and list runbook chunks."""
    runbook = create_runbook(client)
    headers, _ = auth_headers(client, "chunker@example.com")

    create_response = client.post(
        f"{RUNBOOKS_URL}/{runbook['id']}/chunks",
        headers=headers,
        json={
            "chunk_text": "Check current error rate.",
            "chunk_index": 0,
            "metadata": {"section": "diagnosis"},
        },
    )

    assert create_response.status_code == 201
    created = create_response.json()
    assert created["runbook_id"] == runbook["id"]
    assert created["chunk_text"] == "Check current error rate."
    assert created["chunk_index"] == 0
    assert created["metadata"] == {"section": "diagnosis"}

    list_response = client.get(f"{RUNBOOKS_URL}/{runbook['id']}/chunks")

    assert list_response.status_code == 200
    data = list_response.json()
    assert len(data) == 1
    assert data[0]["id"] == created["id"]


def test_create_chunk_validates_payload(client: TestClient) -> None:
    """Reject empty chunk text and negative index."""
    runbook = create_runbook(client)
    headers, _ = auth_headers(client, "validator@example.com")

    response = client.post(
        f"{RUNBOOKS_URL}/{runbook['id']}/chunks",
        headers=headers,
        json={"chunk_text": "", "chunk_index": -1},
    )

    assert response.status_code == 422


def test_list_chunks_missing_runbook_returns_404(client: TestClient) -> None:
    """Return 404 when listing chunks for a missing runbook."""
    response = client.get(f"{RUNBOOKS_URL}/{uuid4()}/chunks")

    assert response.status_code == 404
    assert response.json()["detail"] == "Runbook not found"


def test_search_runbook_chunks(client: TestClient) -> None:
    """Search runbook chunks by semantic similarity."""
    runbook = create_runbook(client)
    headers, _ = auth_headers(client, "searcher@example.com")
    client.post(
        f"{RUNBOOKS_URL}/{runbook['id']}/chunks",
        headers=headers,
        json={"chunk_text": "Investigate latency spikes.", "chunk_index": 0},
    )
    client.post(
        f"{RUNBOOKS_URL}/{runbook['id']}/chunks",
        headers=headers,
        json={"chunk_text": "Restart the API service.", "chunk_index": 1},
    )

    response = client.post(
        f"{RUNBOOKS_URL}/search",
        json={"query": "latency is high", "top_k": 1},
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["runbook_id"] == runbook["id"]
    assert data[0]["chunk_text"] == "Investigate latency spikes."
    assert data[0]["service_name"] == "checkout-api"
    assert data[0]["distance"] == 0.0
    assert "score" not in data[0]


def test_search_runbook_chunks_filters_by_service(client: TestClient) -> None:
    """Search can filter chunks by service name."""
    checkout_runbook = create_runbook(client, "checkout-search@example.com")
    headers, _ = auth_headers(client, "payments-search@example.com")
    payments_response = client.post(
        RUNBOOKS_URL,
        headers=headers,
        json={"title": "Payments latency", "service_name": "payments-api"},
    )
    payments_runbook = payments_response.json()

    client.post(
        f"{RUNBOOKS_URL}/{checkout_runbook['id']}/chunks",
        headers=headers,
        json={"chunk_text": "Investigate latency in checkout.", "chunk_index": 0},
    )
    client.post(
        f"{RUNBOOKS_URL}/{payments_runbook['id']}/chunks",
        headers=headers,
        json={"chunk_text": "Investigate latency in payments.", "chunk_index": 0},
    )

    response = client.post(
        f"{RUNBOOKS_URL}/search",
        json={"query": "latency", "service_name": "payments-api", "top_k": 5},
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["runbook_id"] == payments_runbook["id"]
    assert data[0]["service_name"] == "payments-api"


def test_search_runbook_chunks_validates_payload(client: TestClient) -> None:
    """Validate search query and top_k."""
    response = client.post(
        f"{RUNBOOKS_URL}/search",
        json={"query": "", "top_k": 11},
    )

    assert response.status_code == 422
