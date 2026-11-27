"""Valkey-backed rate limiter setup with trusted proxy forwarding support."""

from ipaddress import ip_address, ip_network

from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.config import settings


def _is_trusted_proxy(peer_ip: str | None) -> bool:
    if not peer_ip:
        return False
    if "*" in settings.TRUSTED_PROXY_IPS:
        return True
    try:
        peer = ip_address(peer_ip)
    except ValueError:
        return peer_ip in settings.TRUSTED_PROXY_IPS

    for entry in settings.TRUSTED_PROXY_IPS:
        try:
            if "/" in entry:
                if peer in ip_network(entry, strict=False):
                    return True
            elif peer == ip_address(entry):
                return True
        except ValueError:
            if peer_ip == entry:
                return True
    return False


def get_client_ip(request: Request) -> str:
    """Resolve real client IP, honoring X-Forwarded-For only from trusted proxies."""
    peer_ip = request.client.host if request.client else None
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded and _is_trusted_proxy(peer_ip):
        # Walk right-to-left skipping known trusted proxy hops; fallback to left-most client IP
        hops = [h.strip() for h in forwarded.split(",") if h.strip()]
        for hop in reversed(hops):
            if not _is_trusted_proxy(hop):
                return hop
        if hops:
            return hops[0]
    return peer_ip or get_remote_address(request)


def get_user_or_ip_key(request: Request) -> str:
    """Rate limit key preferring authenticated user_id, falling back to client IP."""
    user_id = getattr(request.state, "user_id", None)
    if user_id:
        return f"user:{user_id}"
    return f"ip:{get_client_ip(request)}"


storage_uri = settings.RATE_LIMIT_STORAGE_URI or settings.REDIS_URL
_allow_memory_fallback = settings.ENVIRONMENT != "production" or not settings.RATE_LIMIT_FAIL_CLOSED

limiter = Limiter(
    key_func=get_client_ip,
    storage_uri=storage_uri,
    enabled=settings.RATE_LIMIT_ENABLED,
    headers_enabled=True,
    in_memory_fallback_enabled=_allow_memory_fallback,
)
