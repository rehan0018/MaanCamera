"""Cryptographic and authentication utilities (Argon2id, Session Hashing)."""

import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from passlib.context import CryptContext
from app.core.config import settings

# Argon2id password hashing context
pwd_context = CryptContext(
    schemes=["argon2"],
    deprecated="auto",
    argon2__memory_cost=65536,
    argon2__time_cost=2,
    argon2__parallelism=2,
)


def hash_password(password: str) -> str:
    """Hash password using Argon2id algorithm."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against Argon2id hash."""
    return pwd_context.verify(plain_password, hashed_password)


def generate_session_token() -> str:
    """Generate a high-entropy URL-safe session token (48 bytes / ~64 chars)."""
    return secrets.token_urlsafe(48)


def hash_session_token(token: str) -> str:
    """Hash session token with SHA-256 before database storage to prevent token compromise."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def calculate_session_expiry() -> datetime:
    """Calculate expiration timestamp for user session."""
    return datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
