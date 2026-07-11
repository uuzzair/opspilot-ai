"""Main FastAPI application."""
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.settings import get_settings
from app.core.logging import setup_logging, get_logger
from app.core.middleware import RequestIDMiddleware
from app.api.auth import router as auth_router
from app.api.audit_logs import router as audit_logs_router
from app.api.health import router as health_router
from app.api.incidents import router as incidents_router
from app.api.runbooks import router as runbooks_router
from app.api.triage import router as triage_router
from app.api.triage_jobs import router as triage_jobs_router

# Setup logging
settings = get_settings()
setup_logging(debug=settings.debug)
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Run application startup and shutdown hooks."""
    logger.info(f"Starting {settings.app_name} v{settings.app_version}")
    logger.info(f"Debug mode: {settings.debug}")
    yield
    logger.info(f"Shutting down {settings.app_name}")


def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        debug=settings.debug,
        lifespan=lifespan,
    )

    app.add_middleware(RequestIDMiddleware)

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"] if settings.debug else [],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include routers
    app.include_router(auth_router, prefix="/api")
    app.include_router(audit_logs_router, prefix="/api")
    app.include_router(health_router)
    app.include_router(incidents_router, prefix="/api")
    app.include_router(runbooks_router, prefix="/api")
    app.include_router(triage_router, prefix="/api")
    app.include_router(triage_jobs_router, prefix="/api")

    return app


app = create_app()
