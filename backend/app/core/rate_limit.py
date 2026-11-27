"""Valkey-backed rate limiter setup using slowapi."""

from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.config import settings


def get_user_or_ip_key(request: Request) -> str:
    """Rate limit key preferring authenticated user_id, falling back to client IP."""
    user_id = getattr(request.state, "user_id", None)
    if user_id:
        return f"user:{user_id}"
    return f"ip:{get_remote_address(request)}"


storage_uri = settings.RATE_LIMIT_STORAGE_URI or settings.REDIS_URL

limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=storage_uri,
    enabled=settings.RATE_LIMIT_ENABLED,
    headers_enabled=True,
    in_memory_fallback_enabled=True,
)
