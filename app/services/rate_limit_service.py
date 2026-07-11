"""Simple Redis-backed rate limiting."""
from redis import Redis, RedisError

from app.core.logging import get_logger
from app.core.settings import get_settings

logger = get_logger(__name__)


class RateLimitExceeded(Exception):
    """Raised when a request exceeds the configured rate limit."""


def check_auth_rate_limit(identifier: str, action: str) -> None:
    """Check auth endpoint rate limit, falling back open when Redis is unavailable."""
    settings = get_settings()
    if not settings.auth_rate_limit_enabled:
        return

    key = f"rate-limit:auth:{action}:{identifier}"
    try:
        redis_client = Redis.from_url(
            settings.redis_url,
            socket_connect_timeout=0.25,
            socket_timeout=0.25,
            decode_responses=True,
        )
        current = redis_client.incr(key)
        if current == 1:
            redis_client.expire(key, settings.auth_rate_limit_window_seconds)
        if current > settings.auth_rate_limit_max_requests:
            raise RateLimitExceeded
    except RateLimitExceeded:
        raise
    except RedisError as exc:
        logger.warning(
            "Auth rate limiter unavailable; allowing request",
            extra={"error_type": type(exc).__name__},
        )
