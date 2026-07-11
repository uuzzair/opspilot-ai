"""Audit log routes."""
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.models import AuditLog, User
from app.db.session import get_db
from app.schemas.audit_log import AuditLogRead
from app.services import audit_log_service

router = APIRouter(prefix="/audit-logs", tags=["audit-logs"])


@router.get("", response_model=list[AuditLogRead])
def list_audit_logs(
    entity_type: str | None = None,
    entity_id: str | None = None,
    actor_id: UUID | None = None,
    action: str | None = None,
    limit: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[AuditLog]:
    """List audit logs."""
    return audit_log_service.list_audit_logs(
        db,
        entity_type=entity_type,
        entity_id=entity_id,
        actor_id=actor_id,
        action=action,
        limit=limit,
    )
