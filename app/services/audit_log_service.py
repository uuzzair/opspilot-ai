"""Audit log operations."""
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.db.models import AuditLog

logger = get_logger(__name__)


def create_audit_log(
    db: Session,
    entity_type: str,
    entity_id: str | UUID,
    action: str,
    details: dict | None = None,
    actor_id: UUID | None = None,
) -> AuditLog:
    """Create an audit log entry."""
    audit_log = AuditLog(
        actor_id=actor_id,
        entity_type=entity_type,
        entity_id=str(entity_id),
        action=action,
        details=details or {},
    )
    db.add(audit_log)
    db.commit()
    db.refresh(audit_log)
    return audit_log


def safe_create_audit_log(
    db: Session,
    entity_type: str,
    entity_id: str | UUID,
    action: str,
    details: dict | None = None,
    actor_id: UUID | None = None,
) -> AuditLog | None:
    """Create an audit log without failing the primary operation."""
    try:
        return create_audit_log(
            db,
            entity_type=entity_type,
            entity_id=entity_id,
            action=action,
            details=details,
            actor_id=actor_id,
        )
    except Exception as exc:
        db.rollback()
        logger.warning(
            "Audit log creation failed",
            extra={
                "entity_type": entity_type,
                "entity_id": str(entity_id),
                "action": action,
                "error_type": type(exc).__name__,
            },
        )
        return None


def list_audit_logs(
    db: Session,
    entity_type: str | None = None,
    entity_id: str | None = None,
    actor_id: UUID | None = None,
    action: str | None = None,
    limit: int = 50,
) -> list[AuditLog]:
    """List audit logs newest first with optional filters."""
    statement = select(AuditLog)
    if entity_type is not None:
        statement = statement.where(AuditLog.entity_type == entity_type)
    if entity_id is not None:
        statement = statement.where(AuditLog.entity_id == entity_id)
    if actor_id is not None:
        statement = statement.where(AuditLog.actor_id == actor_id)
    if action is not None:
        statement = statement.where(AuditLog.action == action)

    statement = statement.order_by(AuditLog.created_at.desc(), AuditLog.id.desc()).limit(limit)
    return list(db.execute(statement).scalars().all())
