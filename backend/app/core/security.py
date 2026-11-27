"""Cryptographic and authentication utilities (Argon2id, Session/OTP Hashing, TOTP, CSRF, PII Masking)."""

import base64
import hashlib
import hmac
import logging
import re
import secrets
import struct
import time
from datetime import UTC, datetime, timedelta
from urllib.parse import quote

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

EMAIL_LOG_PATTERN = re.compile(r"([A-Za-z0-9._%+-])[A-Za-z0-9._%+-]*(@[A-Za-z0-9.-]+\.[A-Za-z]{2,})")
PHONE_LOG_PATTERN = re.compile(r"(?<!\d)(\+?\d{1,3}[- ]?)?(\d{6,8})(\d{2,4})(?!\d)")


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


def generate_one_time_token() -> tuple[str, str]:
    """Return `(plain_token, sha256_hash)` for single-use verification and reset links."""
    plain = secrets.token_urlsafe(32)
    return plain, hashlib.sha256(plain.encode("utf-8")).hexdigest()


def hash_one_time_token(token: str) -> str:
    """Hash a single-use token for constant-time DB lookup."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def generate_otp_code() -> tuple[str, str]:
    """Generate a 6-digit numeric OTP and HMAC-SHA256 hash."""
    code = f"{secrets.randbelow(1_000_000):06d}"
    return code, hash_otp_code(code)


def hash_otp_code(code: str) -> str:
    """Compute HMAC-SHA256 digest of a 6-digit OTP bound to SECRET_KEY."""
    return hmac.new(
        settings.SECRET_KEY.encode("utf-8"),
        code.strip().encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def verify_otp_code(code: str, expected_hash: str) -> bool:
    """Constant-time verification of a 6-digit OTP against stored digest."""
    if not code or not expected_hash:
        return False
    return hmac.compare_digest(hash_otp_code(code), expected_hash)


def generate_totp_secret() -> str:
    """Generate a base32-encoded 160-bit TOTP shared secret (RFC 6238)."""
    return base64.b32encode(secrets.token_bytes(20)).decode("ascii").rstrip("=")


def _totp_at_counter(secret: str, counter: int) -> str:
    padded = secret.upper() + "=" * ((8 - len(secret) % 8) % 8)
    key = base64.b32decode(padded, casefold=True)
    msg = struct.pack(">Q", counter)
    digest = hmac.new(key, msg, hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    code_int = (struct.unpack(">I", digest[offset : offset + 4])[0] & 0x7FFFFFFF) % 1_000_000
    return f"{code_int:06d}"


def generate_totp_code(secret: str, for_time: int | None = None, step_seconds: int = 30) -> str:
    """Generate current 6-digit TOTP code for RFC 6238 authenticator apps."""
    ts = int(time.time()) if for_time is None else int(for_time)
    return _totp_at_counter(secret, ts // step_seconds)


def verify_totp_code(
    secret: str,
    code: str,
    *,
    for_time: int | None = None,
    step_seconds: int = 30,
    window: int = 1,
) -> bool:
    """Verify a 6-digit TOTP code within +/- window time steps."""
    cleaned = code.strip()
    if not secret or not cleaned.isdigit() or len(cleaned) != 6:
        return False
    ts = int(time.time()) if for_time is None else int(for_time)
    counter = ts // step_seconds
    return any(
        hmac.compare_digest(cleaned, _totp_at_counter(secret, counter + offset))
        for offset in range(-window, window + 1)
    )


def build_totp_uri(secret: str, account_name: str, issuer: str = "MaanCamera") -> str:
    """Build standard otpauth:// URI for authenticator QR onboarding."""
    label = quote(f"{issuer}:{account_name}")
    return f"otpauth://totp/{label}?secret={secret}&issuer={quote(issuer)}&digits=6&period=30"


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


def mask_pii_text(value: str) -> str:
    """Scrub email addresses and phone numbers from unstructured log text (DPDP hygiene)."""
    scrubbed = EMAIL_LOG_PATTERN.sub(r"\1***\2", value)
    return PHONE_LOG_PATTERN.sub(r"\1******\3", scrubbed)


class PiiScrubbingFilter(logging.Filter):
    """Logging filter masking emails and phone numbers before log emission."""

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = mask_pii_text(record.msg)
        if record.args:
            if isinstance(record.args, tuple):
                record.args = tuple(
                    mask_pii_text(a) if isinstance(a, str) else a for a in record.args
                )
            elif isinstance(record.args, dict):
                record.args = {
                    k: mask_pii_text(v) if isinstance(v, str) else v for k, v in record.args.items()
                }
        return True
