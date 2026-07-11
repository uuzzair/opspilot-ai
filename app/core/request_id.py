"""Request ID context helpers."""
from contextvars import ContextVar

request_id_context: ContextVar[str | None] = ContextVar("request_id", default=None)


def get_request_id() -> str | None:
    """Return the current request ID."""
    return request_id_context.get()
