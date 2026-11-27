"""Cryptographic and authentication utilities (Argon2id, Session Hashing, Double-Submit CSRF)."""

import hashlib
import hmac
import secrets
from datetime import UTC, datetime, timedelta

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

from app.core.config import settings

# Argon2id password hasher context (OWASP recommended parameters)
ph = PasswordHasher(
    time_cost=2,
    memory_cost=65536,
    parallelism=2,
    hash_len=32,
    salt_len=16,
)


def hash_password(password: str) -> str:
    """Hash password using Argon2id algorithm."""
    return ph.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against Argon2id hash."""
    try:
        return bool(ph.verify(hashed_password, plain_password))
    except VerifyMismatchError:
        return False


def generate_session_token() -> str:
    """Generate a high-entropy URL-safe session token (48 bytes / ~64 chars)."""
    return secrets.token_urlsafe(48)


def hash_session_token(token: str) -> str:
    """Hash session token with SHA-256 before database storage to prevent token compromise."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def calculate_session_expiry() -> datetime:
    """Calculate expiration timestamp for user session."""
    return datetime.now(UTC) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)


def generate_csrf_token() -> str:
    """Generate HMAC-signed double-submit CSRF token bound to CSRF_SECRET."""
    nonce = secrets.token_hex(24)
    sig = hmac.new(
        settings.CSRF_SECRET.encode("utf-8"),
        nonce.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return f"{nonce}.{sig}"


def verify_csrf_token(token_from_cookie: str, token_from_header: str) -> bool:
    """Constant-time double-submit comparison plus HMAC signature verification."""
    if not token_from_cookie or not token_from_header:
        return False
    if not hmac.compare_digest(token_from_cookie, token_from_header):
        return False
    if "." not in token_from_cookie:
        return False
    nonce, provided_sig = token_from_cookie.split(".", 1)
    expected_sig = hmac.new(
        settings.CSRF_SECRET.encode("utf-8"),
        nonce.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(provided_sig, expected_sig)
