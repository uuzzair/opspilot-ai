"""Health check routes."""
import logging

from fastapi import APIRouter
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/health", tags=["health"])


class HealthResponse(BaseModel):
    """Health check response."""

    status: str = "healthy"


@router.get("", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Health check endpoint."""
    logger.info("Health check called")
    return HealthResponse(status="healthy")
