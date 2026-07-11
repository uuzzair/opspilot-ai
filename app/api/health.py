"""Health check routes."""
import logging

from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict
from redis import Redis, RedisError
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.core.settings import get_settings
from app.db.session import SessionLocal

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/health", tags=["health"])


class HealthResponse(BaseModel):
    """Health check response."""

    status: str = "healthy"


class ReadyResponse(BaseModel):
    """Readiness check response."""

    model_config = ConfigDict(extra="forbid")

    status: str
    checks: dict[str, str]


@router.get("", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Health check endpoint."""
    logger.info("Health check called")
    return HealthResponse(status="healthy")


@router.get("/ready", response_model=ReadyResponse)
def readiness_check() -> ReadyResponse:
    """Readiness check for required backing services."""
    checks = {
        "database": check_database(),
        "redis": check_redis(),
    }
    status = "ready" if all(value == "ok" for value in checks.values()) else "not_ready"
    return ReadyResponse(status=status, checks=checks)


def check_database() -> str:
    """Check database connectivity."""
    try:
        with SessionLocal() as db:
            db.execute(text("SELECT 1"))
        return "ok"
    except SQLAlchemyError:
        logger.exception("Database readiness check failed")
        return "error"


def check_redis() -> str:
    """Check Redis connectivity when configured."""
    settings = get_settings()
    if not settings.redis_url:
        return "not_configured"
    try:
        Redis.from_url(
            settings.redis_url,
            socket_connect_timeout=0.5,
            socket_timeout=0.5,
        ).ping()
        return "ok"
    except RedisError:
        logger.exception("Redis readiness check failed")
        return "error"
