"""Database models."""
from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import Boolean, CheckConstraint, DateTime, Float, ForeignKey, JSON, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.db.session import Base
from app.db.types import EmbeddingVector


class BaseModel(Base):
    """Base model with common fields."""

    __abstract__ = True

    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class User(BaseModel):
    """Application user."""

    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    role: Mapped[str] = mapped_column(
        String(50),
        default="engineer",
        server_default="engineer",
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        server_default="true",
        nullable=False,
    )

    created_incidents: Mapped[list["Incident"]] = relationship(
        foreign_keys="Incident.created_by_id",
        back_populates="created_by",
    )
    assigned_incidents: Mapped[list["Incident"]] = relationship(
        foreign_keys="Incident.assigned_to_id",
        back_populates="assigned_to",
    )
    created_runbooks: Mapped[list["Runbook"]] = relationship(
        back_populates="created_by",
    )


class Incident(BaseModel):
    """Incident submitted for triage."""

    __tablename__ = "incidents"

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[str] = mapped_column(
        String(50),
        default="manual",
        server_default="manual",
        nullable=False,
    )
    severity: Mapped[str | None] = mapped_column(String(20), nullable=True)
    status: Mapped[str] = mapped_column(
        String(30),
        default="open",
        server_default="open",
        nullable=False,
    )
    affected_service: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_by_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id"),
        nullable=True,
    )
    assigned_to_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id"),
        nullable=True,
    )

    created_by: Mapped[User | None] = relationship(
        foreign_keys=[created_by_id],
        back_populates="created_incidents",
    )
    assigned_to: Mapped[User | None] = relationship(
        foreign_keys=[assigned_to_id],
        back_populates="assigned_incidents",
    )
    triage_results: Mapped[list["TriageResult"]] = relationship(
        back_populates="incident",
        cascade="all, delete-orphan",
    )


class TriageResult(BaseModel):
    """AI triage result for an incident."""

    __tablename__ = "triage_results"
    __table_args__ = (
        CheckConstraint(
            "approval_status IN ('pending', 'approved', 'rejected')",
            name="ck_triage_results_approval_status",
        ),
    )

    incident_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("incidents.id"),
        nullable=False,
    )
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    suspected_cause: Mapped[str | None] = mapped_column(Text, nullable=True)
    recommended_actions: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    confidence_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    model_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    approval_status: Mapped[str] = mapped_column(
        String(30),
        default="pending",
        server_default="pending",
        nullable=False,
    )
    approved_by_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id"),
        nullable=True,
    )
    reviewer_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    incident: Mapped[Incident] = relationship(back_populates="triage_results")
    approved_by: Mapped[User | None] = relationship()


class TriageJob(BaseModel):
    """Asynchronous triage job."""

    __tablename__ = "triage_jobs"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'running', 'succeeded', 'failed')",
            name="ck_triage_jobs_status",
        ),
    )

    incident_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("incidents.id"),
        nullable=False,
    )
    celery_task_id: Mapped[str | None] = mapped_column(String(255), index=True, nullable=True)
    status: Mapped[str] = mapped_column(
        String(30),
        default="pending",
        server_default="pending",
        nullable=False,
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    triage_result_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("triage_results.id"),
        nullable=True,
    )
    requested_by_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id"),
        nullable=True,
    )

    incident: Mapped[Incident] = relationship()
    triage_result: Mapped[TriageResult | None] = relationship()
    requested_by: Mapped[User | None] = relationship()


class AuditLog(Base):
    """Audit log entry."""

    __tablename__ = "audit_logs"

    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    actor_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id"),
        nullable=True,
    )
    entity_type: Mapped[str] = mapped_column(String(100), nullable=False)
    entity_id: Mapped[str] = mapped_column(String(64), nullable=False)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    details: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    actor: Mapped[User | None] = relationship()


class Runbook(BaseModel):
    """Operational runbook."""

    __tablename__ = "runbooks"

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    service_name: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id"),
        nullable=True,
    )

    created_by: Mapped[User | None] = relationship(back_populates="created_runbooks")
    chunks: Mapped[list["RunbookChunk"]] = relationship(
        back_populates="runbook",
        cascade="all, delete-orphan",
    )


class RunbookChunk(BaseModel):
    """Chunk of runbook content."""

    __tablename__ = "runbook_chunks"

    runbook_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("runbooks.id"),
        nullable=False,
    )
    chunk_text: Mapped[str] = mapped_column(Text, nullable=False)
    chunk_index: Mapped[int] = mapped_column(nullable=False)
    metadata_: Mapped[dict] = mapped_column("metadata", JSON, default=dict, nullable=False)
    embedding: Mapped[list[float] | None] = mapped_column(
        EmbeddingVector(384),
        nullable=True,
    )

    runbook: Mapped[Runbook] = relationship(back_populates="chunks")
