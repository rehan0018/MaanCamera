"""Payment service implementing fail-closed verification, row locking, and idempotent webhooks."""

import hashlib
import hmac
import json
import uuid
from datetime import UTC, datetime
from typing import Any

import httpx
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import (
    BusinessRuleViolationException,
    ForbiddenException,
    NotFoundException,
)
from app.modules.bookings.models import Booking
from app.modules.identity.models import User
from app.modules.payments.models import Payment, PaymentEvent
from app.modules.payments.schemas import (
    CreatePaymentOrderRequest,
    CreatePaymentOrderResponse,
    VerifyPaymentRequest,
)
from app.modules.quotations.models import Quotation


def compute_mock_signature(order_id: str, payment_id: str) -> str:
    """Compute deterministic HMAC-SHA256 verification signature for dev/test mock mode."""
    return hmac.new(
        settings.SECRET_KEY.encode("utf-8"),
        f"{order_id}|{payment_id}".encode(),
        hashlib.sha256,
    ).hexdigest()


class PaymentService:
    @staticmethod
    async def create_order(
        db: AsyncSession, current_user: User, req: CreatePaymentOrderRequest
    ) -> CreatePaymentOrderResponse:
        stmt = select(Booking).where(Booking.id == req.booking_id)
        res = await db.execute(stmt)
        booking = res.scalar_one_or_none()
        if not booking:
            raise NotFoundException("Booking", req.booking_id)

        if current_user.role != "admin" and booking.customer_id != current_user.id:
            raise ForbiddenException("You do not have permission to initiate payments for this booking.")

        # Server-side amount computation (disregards any client-supplied amount)
        if req.payment_type == "advance":
            if booking.quotation_id:
                quot = await db.get(Quotation, booking.quotation_id)
                expected_amount = (
                    quot.advance_amount_minor
                    if quot and quot.advance_amount_minor > 0
                    else booking.agreed_amount_minor
                )
            else:
                expected_amount = booking.agreed_amount_minor
        else:
            expected_amount = max(0, booking.agreed_amount_minor - booking.paid_amount_minor)

        if expected_amount <= 0:
            raise BusinessRuleViolationException("Booking has already been fully paid.")

        provider = settings.PAYMENT_PROVIDER
        if settings.ENVIRONMENT == "production" and provider == "mock":
            raise BusinessRuleViolationException("Mock payment provider is disabled in production.")

        provider_order_id = f"order_{provider}_{uuid.uuid4().hex[:12]}"

        payment = Payment(
            booking_id=req.booking_id,
            provider=provider,
            provider_order_id=provider_order_id,
            amount_minor=expected_amount,
            currency_code=booking.currency_code or "INR",
            payment_status="pending",
            payment_type=req.payment_type,
        )
        db.add(payment)
        await db.commit()
        await db.refresh(payment)

        return CreatePaymentOrderResponse(
            payment_id=payment.id,
            booking_id=payment.booking_id,
            provider=provider,
            provider_order_id=provider_order_id,
            amount_minor=payment.amount_minor,
            currency_code=payment.currency_code,
            client_secret=None,
        )

    @staticmethod
    async def _fetch_razorpay_payment_entity(provider_payment_id: str) -> dict[str, Any]:
        """Confirm captured amount and currency directly from Razorpay API."""
        if not settings.RAZORPAY_KEY_ID or not settings.RAZORPAY_KEY_SECRET:
            raise BusinessRuleViolationException("Razorpay API credentials are not configured.")

        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                f"https://api.razorpay.com/v1/payments/{provider_payment_id}",
                auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET),
            )
            if resp.status_code != 200:
                raise BusinessRuleViolationException("Failed to verify payment details with Razorpay gateway.")
            return dict(resp.json())

    @staticmethod
    def _apply_captured_payment(booking: Booking, payment: Payment, provider_payment_id: str | None, signature: str | None) -> None:
        """Apply verified payment amount to booking row (expects rows already locked FOR UPDATE)."""
        if payment.payment_status == "captured":
            return

        payment.payment_status = "captured"
        if provider_payment_id:
            payment.provider_payment_id = provider_payment_id
        if signature:
            payment.signature = signature
        payment.verified_at = datetime.now(UTC)

        booking.paid_amount_minor = (booking.paid_amount_minor or 0) + payment.amount_minor
        if booking.booking_status == "pending_payment":
            booking.booking_status = "confirmed"

    @staticmethod
    async def verify_payment(
        db: AsyncSession, current_user: User, req: VerifyPaymentRequest
    ) -> Payment:
        # Lock payment row FOR UPDATE to prevent race conditions
        stmt = select(Payment).where(Payment.id == req.payment_id).with_for_update()
        res = await db.execute(stmt)
        payment = res.scalar_one_or_none()
        if not payment:
            raise NotFoundException("Payment", req.payment_id)

        # Lock booking row FOR UPDATE before modifying paid_amount_minor or booking_status
        b_stmt = select(Booking).where(Booking.id == payment.booking_id).with_for_update()
        b_res = await db.execute(b_stmt)
        booking = b_res.scalar_one_or_none()
        if not booking:
            raise NotFoundException("Booking", payment.booking_id)

        if current_user.role != "admin" and booking.customer_id != current_user.id:
            raise ForbiddenException("You do not have permission to verify payments for this booking.")

        if payment.payment_status == "captured":
            return payment

        if not req.provider_signature:
            raise BusinessRuleViolationException("Payment signature is required for verification.")

        if payment.provider == "mock":
            if settings.ENVIRONMENT == "production":
                raise BusinessRuleViolationException("Mock payment verification is disabled in production.")
            expected_mock = compute_mock_signature(payment.provider_order_id or "", req.provider_payment_id)
            if not hmac.compare_digest(req.provider_signature, expected_mock):
                payment.payment_status = "failed"
                await db.commit()
                raise BusinessRuleViolationException("Payment signature verification failed.")
            if req.amount_minor is not None and req.amount_minor != payment.amount_minor:
                payment.payment_status = "failed"
                await db.commit()
                raise BusinessRuleViolationException("Verified payment amount mismatch.")

        elif payment.provider == "razorpay":
            if not settings.RAZORPAY_KEY_SECRET:
                raise BusinessRuleViolationException("Razorpay key secret is not configured.")
            expected = hmac.new(
                settings.RAZORPAY_KEY_SECRET.encode("utf-8"),
                f"{payment.provider_order_id}|{req.provider_payment_id}".encode(),
                hashlib.sha256,
            ).hexdigest()
            if not hmac.compare_digest(req.provider_signature, expected):
                payment.payment_status = "failed"
                await db.commit()
                raise BusinessRuleViolationException("Payment signature verification failed.")

            # Confirm amount & currency from Razorpay gateway payload rather than trusting client
            entity = await PaymentService._fetch_razorpay_payment_entity(req.provider_payment_id)
            entity_amount = entity.get("amount")
            entity_currency = str(entity.get("currency", "")).upper()
            entity_order_id = entity.get("order_id")
            if (
                entity_amount != payment.amount_minor
                or entity_currency != payment.currency_code.upper()
                or (entity_order_id and entity_order_id != payment.provider_order_id)
                or entity.get("status") not in ("captured", "authorized")
            ):
                payment.payment_status = "failed"
                await db.commit()
                raise BusinessRuleViolationException("Gateway payment amount or status mismatch.")
        else:
            raise BusinessRuleViolationException(f"Unsupported payment provider '{payment.provider}'.")

        PaymentService._apply_captured_payment(
            booking=booking,
            payment=payment,
            provider_payment_id=req.provider_payment_id,
            signature=req.provider_signature,
        )
        await db.commit()
        await db.refresh(payment)
        return payment

    @staticmethod
    async def process_webhook(
        db: AsyncSession,
        provider: str,
        event_id: str | None,
        event_type: str,
        payload_str: str,
        signature: str | None = None,
    ) -> bool:
        if db.bind and db.bind.dialect.name == "postgresql":
            await db.execute(text("SELECT set_config('app.current_user_role', 'system', true)"))

        # Always fail closed when webhook secret or signature is missing
        if provider == "razorpay":
            if not settings.RAZORPAY_WEBHOOK_SECRET:
                raise BusinessRuleViolationException("Razorpay webhook secret is not configured.")
            if not signature:
                raise BusinessRuleViolationException("Webhook signature missing.")
            expected = hmac.new(
                settings.RAZORPAY_WEBHOOK_SECRET.encode("utf-8"),
                payload_str.encode("utf-8"),
                hashlib.sha256,
            ).hexdigest()
            if not hmac.compare_digest(signature, expected):
                raise BusinessRuleViolationException("Invalid webhook signature.")
        elif provider == "mock":
            if settings.ENVIRONMENT == "production":
                raise BusinessRuleViolationException("Mock payment webhooks are disabled in production.")
            if not signature:
                raise BusinessRuleViolationException("Mock webhook signature missing.")
            expected_mock = hmac.new(
                settings.SECRET_KEY.encode("utf-8"),
                payload_str.encode("utf-8"),
                hashlib.sha256,
            ).hexdigest()
            if not hmac.compare_digest(signature, expected_mock):
                raise BusinessRuleViolationException("Invalid webhook signature.")
        else:
            raise BusinessRuleViolationException(f"Unsupported webhook provider '{provider}'.")

        payload_hash = hashlib.sha256(payload_str.encode("utf-8")).hexdigest()
        try:
            raw_payload = json.loads(payload_str)
        except Exception as exc:
            raise BusinessRuleViolationException("Invalid JSON webhook payload.") from exc

        resolved_event_id = event_id or raw_payload.get("id") or f"hash_{payload_hash}"

        # Idempotency check on (provider, provider_event_id)
        stmt = select(PaymentEvent).where(
            PaymentEvent.provider == provider,
            PaymentEvent.provider_event_id == resolved_event_id,
        )
        res = await db.execute(stmt)
        if res.scalar_one_or_none():
            return True

        matched_payment_id = None
        payment_entity = raw_payload.get("payload", {}).get("payment", {}).get("entity", {})
        order_id = payment_entity.get("order_id")
        if order_id:
            p_stmt = select(Payment).where(Payment.provider_order_id == order_id).with_for_update()
            p_res = await db.execute(p_stmt)
            p = p_res.scalar_one_or_none()
            if p:
                matched_payment_id = p.id
                if event_type in ("payment.captured", "order.paid") and p.payment_status != "captured":
                    captured_amount = payment_entity.get("amount")
                    captured_currency = str(payment_entity.get("currency", p.currency_code)).upper()
                    if captured_amount is None or int(captured_amount) != p.amount_minor:
                        raise BusinessRuleViolationException("Webhook payment amount does not match order amount.")
                    if captured_currency != p.currency_code.upper():
                        raise BusinessRuleViolationException("Webhook payment currency does not match order currency.")

                    b_stmt = select(Booking).where(Booking.id == p.booking_id).with_for_update()
                    b_res = await db.execute(b_stmt)
                    booking = b_res.scalar_one_or_none()
                    if booking:
                        PaymentService._apply_captured_payment(
                            booking=booking,
                            payment=p,
                            provider_payment_id=payment_entity.get("id"),
                            signature=signature,
                        )

        event = PaymentEvent(
            payment_id=matched_payment_id,
            provider=provider,
            provider_event_id=resolved_event_id,
            event_type=event_type,
            payload_hash=payload_hash,
            raw_payload=raw_payload,
            received_at=datetime.now(UTC),
            processed_at=datetime.now(UTC),
        )
        db.add(event)
        try:
            await db.commit()
        except IntegrityError:
            await db.rollback()
            return True
        return True
