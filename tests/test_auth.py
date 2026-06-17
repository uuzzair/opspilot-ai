"""Tests for auth endpoints."""
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from fastapi.testclient import TestClient
from jose import jwt
from sqlalchemy.orm import Session

from app.core.settings import get_settings
from app.core.security import verify_password
from app.services.auth_service import get_user_by_email

AUTH_URL = "/api/auth"


def register_user(
    client: TestClient,
    email: str = "user@example.com",
    password: str = "correct-horse-battery",
) -> dict:
    """Register a test user."""
    response = client.post(
        f"{AUTH_URL}/register",
        json={"email": email, "password": password, "full_name": "Example User"},
    )
    assert response.status_code == 201
    return response.json()


def login_user(
    client: TestClient,
    email: str = "user@example.com",
    password: str = "correct-horse-battery",
) -> str:
    """Login a test user and return a token."""
    response = client.post(
        f"{AUTH_URL}/login",
        json={"email": email, "password": password},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["token_type"] == "bearer"
    assert data["access_token"]
    return data["access_token"]


def test_register_user(client: TestClient) -> None:
    """Register a user."""
    data = register_user(client)

    assert data["email"] == "user@example.com"
    assert data["role"] == "engineer"
    assert data["is_active"] is True
    assert "password" not in data
    assert "password_hash" not in data


def test_register_hashes_password(client: TestClient, db: Session) -> None:
    """Store a password hash, not the plain password."""
    password = "correct-horse-battery"
    register_user(client, password=password)

    user = get_user_by_email(db, "user@example.com")

    assert user is not None
    assert user.password_hash != password
    assert verify_password(password, user.password_hash)


def test_register_duplicate_email_returns_409(client: TestClient) -> None:
    """Reject duplicate email registration."""
    register_user(client)

    response = client.post(
        f"{AUTH_URL}/register",
        json={
            "email": "user@example.com",
            "password": "another-password",
            "full_name": "Duplicate User",
        },
    )

    assert response.status_code == 409


def test_login_user(client: TestClient) -> None:
    """Login a user."""
    register_user(client)
    token = login_user(client)

    assert token


def test_login_invalid_credentials_returns_401(client: TestClient) -> None:
    """Reject invalid login credentials."""
    register_user(client)

    response = client.post(
        f"{AUTH_URL}/login",
        json={"email": "user@example.com", "password": "wrong-password"},
    )

    assert response.status_code == 401


def test_me_returns_current_user(client: TestClient) -> None:
    """Return the current authenticated user."""
    user = register_user(client)
    token = login_user(client)

    response = client.get(f"{AUTH_URL}/me", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == user["id"]
    assert data["email"] == "user@example.com"
    assert data["role"] == "engineer"
    assert data["is_active"] is True


def test_me_without_token_returns_401(client: TestClient) -> None:
    """Require auth for /api/auth/me."""
    response = client.get(f"{AUTH_URL}/me")

    assert response.status_code == 401


def test_me_with_invalid_token_returns_401(client: TestClient) -> None:
    """Reject invalid bearer tokens."""
    response = client.get(f"{AUTH_URL}/me", headers={"Authorization": "Bearer invalid-token"})

    assert response.status_code == 401


def test_me_with_expired_token_returns_401(client: TestClient) -> None:
    """Reject expired bearer tokens."""
    settings = get_settings()
    expired_token = jwt.encode(
        {
            "sub": str(uuid4()),
            "exp": datetime.now(timezone.utc) - timedelta(minutes=1),
        },
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )

    response = client.get(f"{AUTH_URL}/me", headers={"Authorization": f"Bearer {expired_token}"})

    assert response.status_code == 401


def test_unauthorized_incident_create_returns_401(client: TestClient) -> None:
    """Require auth for incident creation."""
    response = client.post(
        "/api/incidents",
        json={"title": "Unauthorized", "description": "Should fail."},
    )

    assert response.status_code == 401


def test_unauthorized_incident_update_returns_401(client: TestClient) -> None:
    """Require auth for incident updates."""
    response = client.patch(
        f"/api/incidents/{uuid4()}",
        json={"status": "closed"},
    )

    assert response.status_code == 401


def test_authorized_incident_create_sets_user(client: TestClient) -> None:
    """Create an incident as the authenticated user."""
    user = register_user(client)
    token = login_user(client)

    response = client.post(
        "/api/incidents",
        headers={"Authorization": f"Bearer {token}"},
        json={"title": "Authorized", "description": "Created by a user."},
    )

    assert response.status_code == 201
    data = response.json()
    assert data["created_by_id"] == user["id"]
