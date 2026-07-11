"""Application middleware."""
from uuid import uuid4

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.request_id import request_id_context

REQUEST_ID_HEADER = "X-Request-ID"


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Attach a request ID to each request and response."""

    async def dispatch(self, request: Request, call_next) -> Response:
        """Set request ID context and response header."""
        request_id = request.headers.get(REQUEST_ID_HEADER) or str(uuid4())
        token = request_id_context.set(request_id)
        request.state.request_id = request_id
        try:
            response = await call_next(request)
            response.headers[REQUEST_ID_HEADER] = request_id
            return response
        finally:
            request_id_context.reset(token)
