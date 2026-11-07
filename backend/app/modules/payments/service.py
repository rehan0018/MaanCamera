"""Payment service implementing adapter pattern for mock & Razorpay gateways."""

import uuid
import hmac
import hashlib
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.payments.models import Payment, PaymentEvent, Refund
from app.modules.payments.schemas import CreatePaymentOrderRequest, CreatePaymentOrderResponse, VerifyPaymentRequest
from app.modules.bookings.models import Booking
from app.core.config import settings
from app.core.exceptions import NotFoundException, BusinessRuleViolationException


class PaymentService:
    @staticmethod
    async def create_order(db: AsyncSession, req: CreatePaymentOrderRequest) -> CreatePaymentOrderResponse:
        stmt = select(Booking).where(Booking.id == req.booking_id)
        res = await db.execute(stmt)
        booking = res.scalar_one_or_none()
        if not booking:
            raise NotFoundException("Booking not found.")

        provider = settings.PAYMENT_PROVIDER
        provider_order_id = f"order_{provider}_{uuid.uuid4().hex[:12]}"

        payment = Payment(
            booking_id=req.booking_id,
            provider=provider,
            provider_order_id=provider_order_id,
            amount_minor=req.amount_minor,
            currency_code=req.currency_code,
            payment_status="created",
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
            client_secret=f"mock_secret_{payment.id}",
        )

    @staticmethod
    async def verify_payment(db: AsyncSession, req: VerifyPaymentRequest) -> Payment:
        stmt = select(Payment).where(Payment.id == req.payment_id)
        res = await db.execute(stmt)
        payment = res.scalar_one_or_none()
        if not payment:
            raise NotFoundException("Payment record not found.")

        if payment.payment_status == "captured":
            return payment

        # Signature verification (mock accepts all, razorpay verifies HMAC SHA256)
        if payment.provider == "razorpay" and settings.RAZORPAY_KEY_SECRET:
            expected = hmac.new(
                settings.RAZORPAY_KEY_SECRET.encode(),
                f"{payment.provider_order_id}|{req.provider_payment_id}".encode(),
                hashlib.sha256,
            ).hexdigest()
            if req.provider_signature != expected:
                payment.payment_status = "failed"
                await db.commit()
                raise BusinessRuleViolationException("Payment signature verification failed.")

        payment.payment_status = "captured"
        payment.provider_payment_id = req.provider_payment_id
        payment.verified_at = datetime.now(timezone.utc)

        # Update booking status to confirmed if deposit or full payment
        booking_stmt = select(Booking).where(Booking.id == payment.booking_id)
        booking_res = await db.execute(booking_stmt)
        booking = booking_res.scalar_one_or_none()
        if booking and booking.booking_status == "pending_deposit":
            booking.booking_status = "confirmed"

        await db.commit()
        await db.refresh(payment)
        return payment

    @staticmethod
    async def process_webhook(db: AsyncSession, provider: str, event_id: str, event_type: str, payload_str: str) -> bool:
        # Idempotent check
        payload_hash = hashlib.sha256(payload_str.encode()).hexdigest()
        stmt = select(PaymentEvent).where(PaymentEvent.provider_event_id == event_id)
        res = await db.execute(stmt)
        if res.scalar_one_or_none():
            return True  # Already processed

        event = PaymentEvent(
            provider=provider,
            provider_event_id=event_id,
            event_type=event_type,
            payload_hash=payload_hash,
            processed_at=datetime.now(timezone.utc),
        )
        db.add(event)
        await db.commit()
        return True
