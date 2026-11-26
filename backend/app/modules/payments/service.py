"""Payment service implementing adapter pattern for mock & Razorpay gateways."""

import json
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
from app.modules.quotations.models import Quotation
from app.modules.identity.models import User
from app.core.config import settings
from app.core.exceptions import NotFoundException, BusinessRuleViolationException, ForbiddenException


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

        # IDOR check: Only booking customer or admin can create order
        if current_user.role != "admin" and booking.customer_id != current_user.id:
            raise ForbiddenException("You do not have permission to initiate payments for this booking.")

        # Server-side amount computation (disregards client-tampered amount)
        if req.payment_type == "advance":
            if booking.quotation_id:
                quot = await db.get(Quotation, booking.quotation_id)
                expected_amount = quot.advance_amount_minor if quot and quot.advance_amount_minor > 0 else booking.agreed_amount_minor
            else:
                expected_amount = booking.agreed_amount_minor
        elif req.payment_type == "balance":
            expected_amount = max(0, booking.agreed_amount_minor - booking.paid_amount_minor)
        else:  # full
            expected_amount = max(0, booking.agreed_amount_minor - booking.paid_amount_minor)

        if expected_amount <= 0:
            raise BusinessRuleViolationException("Booking has already been fully paid.")

        provider = settings.PAYMENT_PROVIDER
        provider_order_id = f"order_{provider}_{uuid.uuid4().hex[:12]}"

        payment = Payment(
            booking_id=req.booking_id,
            provider=provider,
            provider_order_id=provider_order_id,
            amount_minor=expected_amount,
            currency_code=req.currency_code or "INR",
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
            client_secret=f"mock_secret_{payment.id}",
        )

    @staticmethod
    async def verify_payment(
        db: AsyncSession, current_user: User, req: VerifyPaymentRequest
    ) -> Payment:
        stmt = select(Payment).where(Payment.id == req.payment_id)
        res = await db.execute(stmt)
        payment = res.scalar_one_or_none()
        if not payment:
            raise NotFoundException("Payment", req.payment_id)

        # Verify booking ownership
        booking = await db.get(Booking, payment.booking_id)
        if not booking:
            raise NotFoundException("Booking", payment.booking_id)

        if current_user.role != "admin" and booking.customer_id != current_user.id:
            raise ForbiddenException("You do not have permission to verify payments for this booking.")

        if payment.payment_status == "captured":
            return payment

        # Signature verification (mock accepts all with test signature; razorpay verifies HMAC SHA256)
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
        payment.signature = req.provider_signature
        payment.verified_at = datetime.now(timezone.utc)

        # Update booking paid amount and confirm booking if pending_payment
        booking.paid_amount_minor = (booking.paid_amount_minor or 0) + payment.amount_minor
        if booking.booking_status == "pending_payment":
            booking.booking_status = "confirmed"

        await db.commit()
        await db.refresh(payment)
        return payment

    @staticmethod
    async def process_webhook(
        db: AsyncSession,
        provider: str,
        event_id: Optional[str],
        event_type: str,
        payload_str: str,
        signature: Optional[str] = None,
    ) -> bool:
        # Signature check for Razorpay webhooks
        if provider == "razorpay" and settings.RAZORPAY_WEBHOOK_SECRET:
            if not signature:
                raise BusinessRuleViolationException("Webhook signature missing.")
            expected = hmac.new(
                settings.RAZORPAY_WEBHOOK_SECRET.encode(),
                payload_str.encode(),
                hashlib.sha256,
            ).hexdigest()
            if not hmac.compare_digest(signature, expected):
                raise BusinessRuleViolationException("Invalid webhook signature.")

        payload_hash = hashlib.sha256(payload_str.encode()).hexdigest()
        raw_payload = {}
        try:
            raw_payload = json.loads(payload_str)
        except Exception:
            raw_payload = {"raw": payload_str}

        # Idempotency check
        stmt = select(PaymentEvent).where(PaymentEvent.payload_hash == payload_hash)
        res = await db.execute(stmt)
        if res.scalar_one_or_none():
            return True  # Already processed

        # Look up associated payment if order/payment id present
        matched_payment_id = None
        order_id = raw_payload.get("payload", {}).get("payment", {}).get("entity", {}).get("order_id")
        if order_id:
            p_stmt = select(Payment).where(Payment.provider_order_id == order_id)
            p_res = await db.execute(p_stmt)
            p = p_res.scalar_one_or_none()
            if p:
                matched_payment_id = p.id
                if event_type in ["payment.captured", "order.paid"] and p.payment_status != "captured":
                    p.payment_status = "captured"
                    p.verified_at = datetime.now(timezone.utc)
                    booking = await db.get(Booking, p.booking_id)
                    if booking:
                        booking.paid_amount_minor = (booking.paid_amount_minor or 0) + p.amount_minor
                        if booking.booking_status == "pending_payment":
                            booking.booking_status = "confirmed"

        event = PaymentEvent(
            payment_id=matched_payment_id,
            provider=provider,
            provider_event_id=event_id or f"evt_{uuid.uuid4().hex[:12]}",
            event_type=event_type,
            payload_hash=payload_hash,
            raw_payload=raw_payload,
            received_at=datetime.now(timezone.utc),
            processed_at=datetime.now(timezone.utc),
        )
        db.add(event)
        await db.commit()
        return True
