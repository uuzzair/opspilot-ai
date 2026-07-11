"""Tests for asynchronous triage jobs."""
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from app.api import incidents as incidents_api
from app.db.models import AuditLog, Incident, TriageJob, TriageResult
from app.services import triage_job_service
from app.workers import tasks

AUTH_URL = "/api/auth"
INCIDENTS_URL = "/api/incidents"
TRIAGE_JOBS_URL = "/api/triage-jobs"


class FakeAsyncResult:
    """Minimal Celery AsyncResult stand-in."""

    id = "celery-task-123"


def auth_headers(client: TestClient, email: str = "job-user@example.com") -> dict[str, str]:
    """Register and login a test user."""
    password = "correct-horse-battery"
    client.post(
        f"{AUTH_URL}/register",
        json={"email": email, "password": password, "full_name": "Job User"},
    )
    response = client.post(f"{AUTH_URL}/login", json={"email": email, "password": password})
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def create_incident(client: TestClient) -> dict:
    """Create an incident through the API."""
    response = client.post(
        INCIDENTS_URL,
        headers=auth_headers(client),
        json={
            "title": "Payments API high latency",
            "description": "p95 latency is high for checkout requests.",
            "affected_service": "payments-api",
        },
    )
    assert response.status_code == 201
    return response.json()


def test_authenticated_job_creation_returns_202(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Create a triage job without running triage synchronously."""
    incident = create_incident(client)
    captured = {}

    def fake_delay(job_id: str) -> FakeAsyncResult:
        captured["job_id"] = job_id
        return FakeAsyncResult()

    monkeypatch.setattr(incidents_api.process_triage_job, "delay", fake_delay)

    response = client.post(
        f"{INCIDENTS_URL}/{incident['id']}/triage-jobs",
        headers=auth_headers(client, "job-requester@example.com"),
    )

    assert response.status_code == 202
    data = response.json()
    assert data["incident_id"] == incident["id"]
    assert data["status"] == "pending"
    assert data["celery_task_id"] == "celery-task-123"
    assert captured["job_id"] == data["id"]


def test_unauthenticated_job_creation_returns_401(client: TestClient) -> None:
    """Require auth for triage job creation."""
    response = client.post(f"{INCIDENTS_URL}/{uuid4()}/triage-jobs")

    assert response.status_code == 401


def test_missing_incident_job_creation_returns_404(client: TestClient) -> None:
    """Return 404 when creating a job for a missing incident."""
    response = client.post(
        f"{INCIDENTS_URL}/{uuid4()}/triage-jobs",
        headers=auth_headers(client, "missing-job@example.com"),
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Incident not found"


def test_job_status_endpoint_returns_job_info(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Return triage job status."""
    incident = create_incident(client)
    monkeypatch.setattr(
        incidents_api.process_triage_job,
        "delay",
        lambda job_id: FakeAsyncResult(),
    )
    create_response = client.post(
        f"{INCIDENTS_URL}/{incident['id']}/triage-jobs",
        headers=auth_headers(client, "status-job@example.com"),
    )
    job_id = create_response.json()["id"]

    response = client.get(f"{TRIAGE_JOBS_URL}/{job_id}")

    assert response.status_code == 200
    assert response.json()["id"] == job_id
    assert response.json()["status"] == "pending"


def test_worker_task_updates_job_to_succeeded(
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Worker marks a job succeeded when triage succeeds."""
    incident = Incident(
        title="High latency",
        description="p95 latency is high.",
        affected_service="payments-api",
    )
    db.add(incident)
    db.commit()
    db.refresh(incident)
    job = triage_job_service.create_triage_job(db, incident, None)
    TestingSessionLocal = sessionmaker(bind=db.get_bind())
    monkeypatch.setattr(tasks, "SessionLocal", TestingSessionLocal)

    def fake_create_triage_result(task_db: Session, task_incident: Incident) -> TriageResult:
        triage_result = TriageResult(
            incident_id=task_incident.id,
            summary="High incident for payments-api: High latency",
            suspected_cause="Relevant runbook context was found for this incident.",
            recommended_actions=["Check p95 latency dashboard."],
            confidence_score=0.75,
            model_name="langgraph-deterministic-v1",
        )
        task_db.add(triage_result)
        task_db.commit()
        task_db.refresh(triage_result)
        return triage_result

    monkeypatch.setattr(tasks.triage_service, "create_triage_result", fake_create_triage_result)

    triage_result_id = tasks.process_triage_job(str(job.id))

    db.expire_all()
    updated_job = db.get(TriageJob, job.id)
    assert updated_job is not None
    assert updated_job.status == "succeeded"
    assert str(updated_job.triage_result_id) == triage_result_id
    assert updated_job.error_message is None
    audit_log = (
        db.query(AuditLog)
        .filter_by(entity_type="triage_job", entity_id=str(job.id), action="succeeded")
        .one()
    )
    assert audit_log.actor_id is None
    assert audit_log.details["triage_result_id"] == triage_result_id


def test_worker_task_updates_job_to_failed(
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Worker marks a job failed when triage raises."""
    incident = Incident(
        title="High latency",
        description="p95 latency is high.",
        affected_service="payments-api",
    )
    db.add(incident)
    db.commit()
    db.refresh(incident)
    job = triage_job_service.create_triage_job(db, incident, None)
    TestingSessionLocal = sessionmaker(bind=db.get_bind())
    monkeypatch.setattr(tasks, "SessionLocal", TestingSessionLocal)

    def raise_triage_error(task_db: Session, task_incident: Incident) -> TriageResult:
        raise RuntimeError("triage exploded")

    monkeypatch.setattr(tasks.triage_service, "create_triage_result", raise_triage_error)

    with pytest.raises(RuntimeError, match="triage exploded"):
        tasks.process_triage_job(str(job.id))

    db.expire_all()
    updated_job = db.get(TriageJob, job.id)
    assert updated_job is not None
    assert updated_job.status == "failed"
    assert updated_job.error_message == "triage exploded"
    audit_log = (
        db.query(AuditLog)
        .filter_by(entity_type="triage_job", entity_id=str(job.id), action="failed")
        .one()
    )
    assert audit_log.actor_id is None
    assert audit_log.details["error_type"] == "RuntimeError"
