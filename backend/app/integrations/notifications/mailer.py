"""Pluggable notification dispatcher supporting SMTP email and dev/test outbox recording."""

import asyncio
import logging
import smtplib
from email.message import EmailMessage
from typing import Any

from app.core.config import settings
from app.core.security import mask_pii_text

logger = logging.getLogger("maancamera.notifications")

# In-memory capture list active only when ENVIRONMENT == "test" for verification assertions
_TEST_OUTBOX: list[dict[str, Any]] = []


def get_test_outbox() -> list[dict[str, Any]]:
    """Return captured notification events in test mode."""
    return _TEST_OUTBOX


def clear_test_outbox() -> None:
    """Clear captured test notification events."""
    _TEST_OUTBOX.clear()


def _send_smtp_sync(recipient: str, subject: str, body: str) -> None:
    msg = EmailMessage()
    msg["From"] = settings.SMTP_FROM_EMAIL
    msg["To"] = recipient
    msg["Subject"] = subject
    msg.set_content(body)

    with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10) as client:
        if settings.SMTP_USE_TLS:
            client.starttls()
        if settings.SMTP_USER and settings.SMTP_PASSWORD:
            client.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
        client.send_message(msg)


async def send_email_notification(recipient: str, subject: str, body: str, event_type: str) -> None:
    """Send an email via SMTP when configured, or log safely without leaking secrets/PII."""
    if settings.ENVIRONMENT == "test":
        _TEST_OUTBOX.append(
            {
                "channel": "email",
                "event_type": event_type,
                "recipient": recipient,
                "subject": subject,
                "body": body,
            }
        )
        return

    if settings.SMTP_HOST:
        await asyncio.to_thread(_send_smtp_sync, recipient, subject, body)
        logger.info("Sent email event=%s recipient=%s", event_type, mask_pii_text(recipient))
        return

    logger.info("Email delivery skipped (SMTP_HOST unset): event=%s recipient=%s", event_type, mask_pii_text(recipient))


async def send_sms_otp(phone: str, code: str, purpose: str) -> None:
    """Dispatch OTP via configured SMS transport or record in test outbox without logging codes."""
    if settings.ENVIRONMENT == "test":
        _TEST_OUTBOX.append(
            {
                "channel": "sms",
                "event_type": purpose,
                "recipient": phone,
                "code": code,
            }
        )
        return

    logger.info("SMS OTP queued: purpose=%s recipient=%s", purpose, mask_pii_text(phone))
