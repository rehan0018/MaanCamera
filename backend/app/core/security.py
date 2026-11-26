"""Cryptographic and authentication utilities (Argon2id, Session Hashing)."""

import hashlib
import secrets
from datetime import datetime, timedelta, timezone
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
        return ph.verify(hashed_password, plain_password)
    except (VerifyMismatchError, Exception):
        return False


def generate_session_token() -> str:
    """Generate a high-entropy URL-safe session token (48 bytes / ~64 chars)."""
    return secrets.token_urlsafe(48)


def hash_session_token(token: str) -> str:
    """Hash session token with SHA-256 before database storage to prevent token compromise."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def calculate_session_expiry() -> datetime:
    """Calculate expiration timestamp for user session."""
    return datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)


def generate_csrf_token() -> str:
    """Generate high-entropy random CSRF token."""
    return secrets.token_hex(32)


def verify_csrf_token(token: str, expected: str) -> bool:
    """Safely verify CSRF token against expected value."""
    if not token or not expected:
        return False
    return secrets.compare_digest(token, expected)
