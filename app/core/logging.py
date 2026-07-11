"""Logging configuration."""
import logging
import sys
from pythonjsonlogger import jsonlogger

from app.core.request_id import get_request_id


class RequestIDFilter(logging.Filter):
    """Attach request_id to log records when available."""

    def filter(self, record: logging.LogRecord) -> bool:
        """Add request_id to each log record."""
        record.request_id = get_request_id()
        return True


def setup_logging(debug: bool = False) -> None:
    """Configure structured JSON logging."""
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG if debug else logging.INFO)

    # Remove default handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # JSON formatter
    formatter = jsonlogger.JsonFormatter("%(message)s %(levelname)s %(name)s %(request_id)s")

    # Console handler with JSON formatting
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.addFilter(RequestIDFilter())
    root_logger.addHandler(console_handler)

    # Set third-party loggers
    logging.getLogger("uvicorn").setLevel(logging.INFO)
    logging.getLogger("sqlalchemy").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance."""
    return logging.getLogger(name)
