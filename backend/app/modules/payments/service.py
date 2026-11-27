"""Payment service: Razorpay Orders API, idempotency, locking, ledger, refunds, and safe webhooks."""

import contextlib
import hashlib
import hmac
import json
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import settings
from app.core.database import apply_rls_context, register_after_commit
from app.core.exceptions import (
    BusinessRuleViolationException,
    ConflictException,
    ForbiddenException,
    NotFoundException,
)
from app.integrations.notifications.mailer import send_email_notification
from app.modules.bookings.models import Booking
from app.modules.bookings.service import BookingService
from app.modules.identity.models import User
from app.modules.payments.models import Payment, PaymentEvent, PaymentLedgerEntry, Refund
from app.modules.payments.schemas import (
    CreatePaymentOrderRequest,
    CreatePaymentOrderResponse,
    PaymentLedgerEntryResponse,
    PaymentResponse,
    RefundRequest,
    RefundResponse,
    VerifyPaymentRequest,
)
from app.modules.platform.models import AuditLog, IdempotencyRecord
from app.modules.quotations.models import Quotation


def compute_mock_signature(order_id: str, payment_id: str) -> str:
    """Compute deterministic HMAC-SHA256 verification signature for dev/test mock mode."""
    return hmac.new(
        settings.SECRET_KEY.encode("utf-8"),
        f"{order_id}|{payment_id}".encode(),
        hashlib.sha256,
    ).hexdigest()


def _normalize_utc(dt: datetime) -> datetime:
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=UTC)


class PaymentService:
    @staticmethod
    async def _create_razorpay_order(
        *,
        payment_id: uuid.UUID,
        amount_minor: int,
        currency: str,
        booking_id: uuid.UUID,
        payment_type: str,
    ) -> str:
        """Create real order on Razorpay Orders API and return its provider order_id."""
        if not settings.RAZORPAY_KEY_ID or not settings.RAZORPAY_KEY_SECRET:
            raise BusinessRuleViolationException("Razorpay API credentials are not configured.")

        payload = {
            "amount": amount_minor,
            "currency": currency.upper(),
            "receipt": str(payment_id)[:40],
            "notes": {
                "payment_id": str(payment_id),
                "booking_id": str(booking_id),
                "payment_type": payment_type,
            },
        }
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                "https://api.razorpay.com/v1/orders",
                auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET),
                json=payload,
            )
        if resp.status_code not in (200, 201):
            raise BusinessRuleViolationException("Failed to create payment order with Razorpay gateway.")
        data = resp.json()
        order_id = data.get("id")
        if not order_id or not isinstance(order_id, str):
            raise BusinessRuleViolationException("Razorpay gateway returned an invalid order response.")
        return order_id

    @staticmethod
    async def _create_razorpay_refund(provider_payment_id: str, amount_minor: int, reason: str) -> str:
        """Issue refund via Razorpay Refunds API and return provider refund_id."""
        if not settings.RAZORPAY_KEY_ID or not settings.RAZORPAY_KEY_SECRET:
            raise BusinessRuleViolationException("Razorpay API credentials are not configured.")

        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                f"https://api.razorpay.com/v1/payments/{provider_payment_id}/refund",
                auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET),
                json={"amount": amount_minor, "notes": {"reason": reason[:250]}},
            )
        if resp.status_code not in (200, 201):
            raise BusinessRuleViolationException("Failed to process refund with Razorpay gateway.")
        data = resp.json()
        refund_id = data.get("id")
        if not refund_id or not isinstance(refund_id, str):
            raise BusinessRuleViolationException("Razorpay gateway returned an invalid refund response.")
        return refund_id

    @staticmethod
    async def create_order(
        db: AsyncSession,
        current_user: User,
        req: CreatePaymentOrderRequest,
        *,
        idempotency_key: str | None = None,
    ) -> CreatePaymentOrderResponse:
        # 1. Check explicit Idempotency-Key record if supplied
        scoped_key: str | None = None
        if idempotency_key:
            scoped_key = f"payment_order:{current_user.id}:{idempotency_key.strip()}"
            existing_rec = await db.get(IdempotencyRecord, scoped_key)
            if existing_rec and _normalize_utc(existing_rec.expires_at) > datetime.now(UTC):
                payload = dict(existing_rec.response_payload)
                if payload.get("booking_id") != str(req.booking_id) or payload.get("payment_type") != req.payment_type:
                    raise ConflictException("Idempotency-Key already used for a different payment request.")
                return CreatePaymentOrderResponse(
                    payment_id=uuid.UUID(payload["payment_id"]),
                    booking_id=uuid.UUID(payload["booking_id"]),
                    provider=payload["provider"],
                    provider_order_id=payload["provider_order_id"],
                    provider_key_id=payload.get("provider_key_id"),
                    amount_minor=int(payload["amount_minor"]),
                    currency_code=payload["currency_code"],
                    client_secret=None,
                    idempotent_replay=True,
                )

        # 2. Lock Booking FOR UPDATE so balance and pending orders cannot race
        stmt = select(Booking).where(Booking.id == req.booking_id).with_for_update()
        booking = (await db.execute(stmt)).scalar_one_or_none()
        if not booking:
            raise NotFoundException("Booking", req.booking_id)

        if current_user.role != "admin" and booking.customer_id != current_user.id:
            raise ForbiddenException("You do not have permission to initiate payments for this booking.")

        if booking.booking_status in ("cancelled", "completed", "disputed"):
            raise BusinessRuleViolationException(
                f"Cannot create payment order for booking in '{booking.booking_status}' status."
            )

        remaining_balance = max(0, booking.agreed_amount_minor - (booking.paid_amount_minor or 0))
        if remaining_balance <= 0:
            raise BusinessRuleViolationException("Booking has already been fully paid.")

        # 3. Server-side amount computation capped strictly by remaining balance
        if req.payment_type == "advance":
            if booking.quotation_id:
                quot = await db.get(Quotation, booking.quotation_id)
                raw_advance = (
                    quot.advance_amount_minor
                    if quot and quot.advance_amount_minor > 0
                    else (booking.agreed_amount_minor * settings.DEFAULT_ADVANCE_PERCENT) // 100
                )
            else:
                raw_advance = (booking.agreed_amount_minor * settings.DEFAULT_ADVANCE_PERCENT) // 100
            expected_amount = min(remaining_balance, max(1, raw_advance))
        else:
            expected_amount = remaining_balance

        if expected_amount <= 0 or expected_amount > remaining_balance:
            raise BusinessRuleViolationException("Payment order amount exceeds remaining booking balance.")

        provider = settings.PAYMENT_PROVIDER
        if settings.ENVIRONMENT == "production" and provider == "mock":
            raise BusinessRuleViolationException("Mock payment provider is disabled in production.")

        # 4. Prevent duplicate open orders for same (booking_id, payment_type)
        open_stmt = (
            select(Payment)
            .where(
                Payment.booking_id == req.booking_id,
                Payment.payment_type == req.payment_type,
                Payment.payment_status == "pending",
                Payment.provider == provider,
            )
            .order_by(Payment.created_at.desc())
            .with_for_update()
        )
        open_payment = (await db.execute(open_stmt)).scalars().first()
        if open_payment and open_payment.amount_minor == expected_amount and open_payment.provider_order_id:
            return CreatePaymentOrderResponse(
                payment_id=open_payment.id,
                booking_id=open_payment.booking_id,
                provider=open_payment.provider,
                provider_order_id=open_payment.provider_order_id,
                provider_key_id=settings.RAZORPAY_KEY_ID if provider == "razorpay" else None,
                amount_minor=open_payment.amount_minor,
                currency_code=open_payment.currency_code,
                client_secret=None,
                idempotent_replay=True,
            )

        payment_id = uuid.uuid4()
        currency = (booking.currency_code or "INR").upper()
        if provider == "razorpay":
            provider_order_id = await PaymentService._create_razorpay_order(
                payment_id=payment_id,
                amount_minor=expected_amount,
                currency=currency,
                booking_id=req.booking_id,
                payment_type=req.payment_type,
            )
        else:
            provider_order_id = f"order_{provider}_{uuid.uuid4().hex[:12]}"

        payment = Payment(
            id=payment_id,
            booking_id=req.booking_id,
            provider=provider,
            provider_order_id=provider_order_id,
            amount_minor=expected_amount,
            currency_code=currency,
            payment_status="pending",
            payment_type=req.payment_type,
        )
        db.add(payment)
        await db.flush()

        key_id = settings.RAZORPAY_KEY_ID if provider == "razorpay" else None
        if scoped_key:
            db.add(
                IdempotencyRecord(
                    key=scoped_key,
                    action="create_payment_order",
                    response_code=201,
                    response_payload={
                        "payment_id": str(payment.id),
                        "booking_id": str(payment.booking_id),
                        "payment_type": req.payment_type,
                        "provider": provider,
                        "provider_order_id": provider_order_id,
                        "provider_key_id": key_id,
                        "amount_minor": payment.amount_minor,
                        "currency_code": payment.currency_code,
                    },
                    expires_at=datetime.now(UTC) + timedelta(hours=24),
                )
            )
            await db.flush()

        return CreatePaymentOrderResponse(
            payment_id=payment.id,
            booking_id=payment.booking_id,
            provider=provider,
            provider_order_id=provider_order_id,
            provider_key_id=key_id,
            amount_minor=payment.amount_minor,
            currency_code=payment.currency_code,
            client_secret=None,
            idempotent_replay=False,
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
    def _record_capture_ledger(
        db: AsyncSession, booking: Booking, payment: Payment
    ) -> None:
        """Append immutable capture, platform commission, and payable hold ledger entries."""
        commission = (payment.amount_minor * settings.PLATFORM_COMMISSION_BPS) // 10_000
        payable = payment.amount_minor - commission

        db.add(
            PaymentLedgerEntry(
                booking_id=booking.id,
                payment_id=payment.id,
                entry_type="payment_captured",
                direction="credit",
                amount_minor=payment.amount_minor,
                currency_code=payment.currency_code,
                notes=f"Captured {payment.payment_type} payment via {payment.provider}",
            )
        )
        if commission > 0:
            db.add(
                PaymentLedgerEntry(
                    booking_id=booking.id,
                    payment_id=payment.id,
                    entry_type="platform_commission",
                    direction="debit",
                    amount_minor=commission,
                    currency_code=payment.currency_code,
                    notes=f"Platform commission ({settings.PLATFORM_COMMISSION_BPS} bps)",
                )
            )
        if payable > 0:
            db.add(
                PaymentLedgerEntry(
                    booking_id=booking.id,
                    payment_id=payment.id,
                    entry_type="payout_hold",
                    direction="credit",
                    amount_minor=payable,
                    currency_code=payment.currency_code,
                    notes="Held until shoot completion and acceptance",
                )
            )

    @staticmethod
    def _apply_captured_payment(
        db: AsyncSession,
        booking: Booking,
        payment: Payment,
        provider_payment_id: str | None,
        signature: str | None,
    ) -> None:
        """Apply verified payment amount to booking row and ledger (expects rows already locked FOR UPDATE)."""
        if payment.payment_status == "captured":
            return
        if payment.payment_status == "refunded":
            raise BusinessRuleViolationException("Cannot mark a refunded payment as captured.")

        new_paid_total = (booking.paid_amount_minor or 0) + payment.amount_minor
        if new_paid_total > booking.agreed_amount_minor:
            raise BusinessRuleViolationException(
                "Capturing this payment would exceed the agreed booking total."
            )

        payment.payment_status = "captured"
        if provider_payment_id:
            payment.provider_payment_id = provider_payment_id
        if signature:
            payment.signature = signature
        payment.verified_at = datetime.now(UTC)

        booking.paid_amount_minor = new_paid_total
        if booking.booking_status == "pending_payment":
            booking.booking_status = "confirmed"

        PaymentService._record_capture_ledger(db, booking, payment)

    @staticmethod
    async def _persist_failed_payment(db: AsyncSession, payment_id: uuid.UUID) -> None:
        """Release active transaction lock cleanly and persist failed payment status."""
        if not db.bind:
            return
        if db.in_transaction():
            await db.rollback()
        iso_factory = async_sessionmaker(bind=db.bind, class_=AsyncSession, expire_on_commit=False)
        async with iso_factory() as iso_db:
            await apply_rls_context(iso_db, role="system")
            failed_payment = await iso_db.get(Payment, payment_id)
            if failed_payment and failed_payment.payment_status == "pending":
                failed_payment.payment_status = "failed"
                await iso_db.commit()

    @staticmethod
    async def verify_payment(
        db: AsyncSession, current_user: User, req: VerifyPaymentRequest
    ) -> Payment:
        stmt = select(Payment).where(Payment.id == req.payment_id).with_for_update()
        payment = (await db.execute(stmt)).scalar_one_or_none()
        if not payment:
            raise NotFoundException("Payment", req.payment_id)

        b_stmt = select(Booking).where(Booking.id == payment.booking_id).with_for_update()
        booking = (await db.execute(b_stmt)).scalar_one_or_none()
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
                await PaymentService._persist_failed_payment(db, payment.id)
                raise BusinessRuleViolationException("Payment signature verification failed.")
            if req.amount_minor is not None and req.amount_minor != payment.amount_minor:
                await PaymentService._persist_failed_payment(db, payment.id)
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
                await PaymentService._persist_failed_payment(db, payment.id)
                raise BusinessRuleViolationException("Payment signature verification failed.")

            # Confirm exact order_id, amount, currency, and status directly from Razorpay API
            entity = await PaymentService._fetch_razorpay_payment_entity(req.provider_payment_id)
            entity_amount = entity.get("amount")
            entity_currency = str(entity.get("currency", "")).upper()
            entity_order_id = entity.get("order_id")
            if (
                entity_amount != payment.amount_minor
                or entity_currency != payment.currency_code.upper()
                or not entity_order_id
                or entity_order_id != payment.provider_order_id
                or entity.get("status") not in ("captured", "authorized")
            ):
                await PaymentService._persist_failed_payment(db, payment.id)
                raise BusinessRuleViolationException("Gateway payment order, amount, or status mismatch.")
        else:
            raise BusinessRuleViolationException(f"Unsupported payment provider '{payment.provider}'.")

        PaymentService._apply_captured_payment(
            db=db,
            booking=booking,
            payment=payment,
            provider_payment_id=req.provider_payment_id,
            signature=req.provider_signature,
        )
        await db.flush()
        if current_user.email:
            cust_email = current_user.email
            amt_inr = payment.amount_minor / 100
            stage = payment.payment_type

            async def _notify_capture() -> None:
                with contextlib.suppress(Exception):
                    await send_email_notification(
                        recipient=cust_email,
                        subject="MaanCamera Payment Confirmed",
                        body=f"Payment of INR {amt_inr:,.2f} ({stage}) has been confirmed for your booking.",
                        event_type="payment_captured",
                    )

            register_after_commit(db, _notify_capture)
        return payment

    @staticmethod
    async def process_webhook(
        db: AsyncSession,
        provider: str,
        event_id: str | None,
        payload_str: str,
        signature: str | None = None,
    ) -> bool:
        await apply_rls_context(db, role="system")

        # 1. Fail-closed signature check BEFORE trusting any payload field
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

        # Read event strictly from signed body (never default header to payment.captured)
        event_type = raw_payload.get("event")
        if not event_type or not isinstance(event_type, str):
            raise BusinessRuleViolationException("Webhook payload must specify a valid 'event' name.")

        resolved_event_id = event_id or raw_payload.get("id") or f"hash_{payload_hash}"

        stmt = select(PaymentEvent).where(
            PaymentEvent.provider == provider,
            PaymentEvent.provider_event_id == resolved_event_id,
        )
        if (await db.execute(stmt)).scalar_one_or_none():
            return True

        matched_payment_id: uuid.UUID | None = None
        payment_entity = raw_payload.get("payload", {}).get("payment", {}).get("entity", {})
        refund_entity = raw_payload.get("payload", {}).get("refund", {}).get("entity", {})

        if event_type in ("payment.captured", "order.paid", "payment.failed"):
            order_id = payment_entity.get("order_id")
            if order_id:
                p_stmt = select(Payment).where(Payment.provider_order_id == order_id).with_for_update()
                p = (await db.execute(p_stmt)).scalar_one_or_none()
                if p:
                    matched_payment_id = p.id
                    if event_type in ("payment.captured", "order.paid"):
                        if p.payment_status != "captured":
                            captured_amount = payment_entity.get("amount")
                            captured_currency = str(payment_entity.get("currency", p.currency_code)).upper()
                            if captured_amount is None or int(captured_amount) != p.amount_minor:
                                raise BusinessRuleViolationException(
                                    "Webhook payment amount does not match order amount."
                                )
                            if captured_currency != p.currency_code.upper():
                                raise BusinessRuleViolationException(
                                    "Webhook payment currency does not match order currency."
                                )
                            b_stmt = select(Booking).where(Booking.id == p.booking_id).with_for_update()
                            booking = (await db.execute(b_stmt)).scalar_one_or_none()
                            if booking:
                                PaymentService._apply_captured_payment(
                                    db=db,
                                    booking=booking,
                                    payment=p,
                                    provider_payment_id=payment_entity.get("id"),
                                    signature=signature,
                                )
                    elif event_type == "payment.failed" and p.payment_status == "pending":
                        # Out-of-order guard: delayed payment.failed NEVER overwrites captured or refunded
                        p.payment_status = "failed"

        elif event_type == "refund.processed":
            provider_pay_id = refund_entity.get("payment_id") or payment_entity.get("id")
            provider_ref_id = refund_entity.get("id")
            if provider_pay_id:
                p_stmt = select(Payment).where(Payment.provider_payment_id == provider_pay_id).with_for_update()
                p = (await db.execute(p_stmt)).scalar_one_or_none()
                if p:
                    matched_payment_id = p.id
                    b_stmt = select(Booking).where(Booking.id == p.booking_id).with_for_update()
                    booking = (await db.execute(b_stmt)).scalar_one_or_none()
                    refund_amount = int(refund_entity.get("amount") or 0)
                    if booking and refund_amount > 0:
                        existing_ref = None
                        if provider_ref_id:
                            existing_ref = (
                                await db.execute(
                                    select(Refund).where(Refund.provider_refund_id == provider_ref_id)
                                )
                            ).scalar_one_or_none()
                        if not existing_ref:
                            already_refunded = int(
                                (
                                    await db.execute(
                                        select(func.coalesce(func.sum(Refund.amount_minor), 0)).where(
                                            Refund.payment_id == p.id,
                                            Refund.status == "processed",
                                        )
                                    )
                                ).scalar()
                                or 0
                            )
                            if already_refunded + refund_amount <= p.amount_minor:
                                ref_row = Refund(
                                    payment_id=p.id,
                                    amount_minor=refund_amount,
                                    currency_code=p.currency_code,
                                    reason="Gateway refund webhook processed",
                                    status="processed",
                                    provider_refund_id=provider_ref_id,
                                )
                                db.add(ref_row)
                                await db.flush()
                                db.add(
                                    PaymentLedgerEntry(
                                        booking_id=booking.id,
                                        payment_id=p.id,
                                        refund_id=ref_row.id,
                                        entry_type="refund_issued",
                                        direction="debit",
                                        amount_minor=refund_amount,
                                        currency_code=p.currency_code,
                                        notes="Webhook refund processed",
                                    )
                                )
                                booking.paid_amount_minor = max(
                                    0, (booking.paid_amount_minor or 0) - refund_amount
                                )
                                if already_refunded + refund_amount == p.amount_minor:
                                    p.payment_status = "refunded"

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
        try:
            async with db.begin_nested():
                db.add(event)
                await db.flush()
        except IntegrityError:
            return True
        return True

    @staticmethod
    async def create_refund(
        db: AsyncSession,
        payment_id: uuid.UUID,
        current_user: User,
        req: RefundRequest,
    ) -> Refund:
        p_stmt = select(Payment).where(Payment.id == payment_id).with_for_update()
        payment = (await db.execute(p_stmt)).scalar_one_or_none()
        if not payment:
            raise NotFoundException("Payment", payment_id)

        b_stmt = select(Booking).where(Booking.id == payment.booking_id).with_for_update()
        booking = (await db.execute(b_stmt)).scalar_one_or_none()
        if not booking:
            raise NotFoundException("Booking", payment.booking_id)

        if current_user.role != "admin":
            if booking.customer_id != current_user.id:
                raise ForbiddenException("You do not have permission to request a refund for this payment.")
            if booking.booking_status not in ("cancelled", "disputed"):
                raise BusinessRuleViolationException(
                    "Customer refunds are only permitted on cancelled or disputed bookings."
                )

        if payment.payment_status not in ("captured", "refunded"):
            raise BusinessRuleViolationException("Only captured payments can be refunded.")

        already_refunded = int(
            (
                await db.execute(
                    select(func.coalesce(func.sum(Refund.amount_minor), 0)).where(
                        Refund.payment_id == payment.id,
                        Refund.status == "processed",
                    )
                )
            ).scalar()
            or 0
        )
        remaining_refundable = payment.amount_minor - already_refunded
        if req.amount_minor > remaining_refundable:
            raise BusinessRuleViolationException(
                f"Refund amount exceeds remaining refundable balance ({remaining_refundable} minor units)."
            )

        if payment.provider == "razorpay":
            if not payment.provider_payment_id:
                raise BusinessRuleViolationException("Missing Razorpay payment ID for refund.")
            provider_refund_id = await PaymentService._create_razorpay_refund(
                payment.provider_payment_id, req.amount_minor, req.reason
            )
        else:
            provider_refund_id = f"rfnd_{payment.provider}_{uuid.uuid4().hex[:10]}"

        refund = Refund(
            payment_id=payment.id,
            amount_minor=req.amount_minor,
            currency_code=payment.currency_code,
            reason=req.reason,
            status="processed",
            provider_refund_id=provider_refund_id,
        )
        db.add(refund)
        await db.flush()

        db.add(
            PaymentLedgerEntry(
                booking_id=booking.id,
                payment_id=payment.id,
                refund_id=refund.id,
                entry_type="refund_issued",
                direction="debit",
                amount_minor=req.amount_minor,
                currency_code=payment.currency_code,
                notes=req.reason,
            )
        )
        booking.paid_amount_minor = max(0, (booking.paid_amount_minor or 0) - req.amount_minor)
        if already_refunded + req.amount_minor == payment.amount_minor:
            payment.payment_status = "refunded"
        await db.flush()
        return refund

    @staticmethod
    async def get_booking_payment_summary(
        db: AsyncSession, booking_id: uuid.UUID, current_user: User
    ) -> dict[str, Any]:
        booking = await BookingService.get_booking_by_id(db, booking_id, current_user)
        payments = list(
            (
                await db.execute(
                    select(Payment).where(Payment.booking_id == booking.id).order_by(Payment.created_at.desc())
                )
            )
            .scalars()
            .all()
        )
        payment_ids = [p.id for p in payments]
        refunds: list[Refund] = []
        if payment_ids:
            refunds = list(
                (
                    await db.execute(
                        select(Refund).where(Refund.payment_id.in_(payment_ids)).order_by(Refund.created_at.desc())
                    )
                )
                .scalars()
                .all()
            )
        ledger = list(
            (
                await db.execute(
                    select(PaymentLedgerEntry)
                    .where(PaymentLedgerEntry.booking_id == booking.id)
                    .order_by(PaymentLedgerEntry.created_at.asc())
                )
            )
            .scalars()
            .all()
        )
        return {
            "booking_id": str(booking.id),
            "agreed_amount_minor": booking.agreed_amount_minor,
            "paid_amount_minor": booking.paid_amount_minor,
            "remaining_amount_minor": max(0, booking.agreed_amount_minor - (booking.paid_amount_minor or 0)),
            "payments": [PaymentResponse.model_validate(p).model_dump(mode="json") for p in payments],
            "refunds": [RefundResponse.model_validate(r).model_dump(mode="json") for r in refunds],
            "ledger_entries": [
                PaymentLedgerEntryResponse.model_validate(entry).model_dump(mode="json")
                for entry in ledger
            ],
        }

    @staticmethod
    async def capture_mock_payment_dev_only(
        db: AsyncSession, payment_id: uuid.UUID, current_user: User
    ) -> Payment:
        """Complete a mock payment in non-production environments without exposing SECRET_KEY to clients."""
        if settings.ENVIRONMENT == "production":
            raise ForbiddenException("Dev mock payment capture is disabled in production.")

        stmt = select(Payment).where(Payment.id == payment_id).with_for_update()
        payment = (await db.execute(stmt)).scalar_one_or_none()
        if not payment:
            raise NotFoundException("Payment", payment_id)
        if payment.provider != "mock":
            raise BusinessRuleViolationException("Mock capture endpoint only supports mock provider orders.")

        b_stmt = select(Booking).where(Booking.id == payment.booking_id).with_for_update()
        booking = (await db.execute(b_stmt)).scalar_one_or_none()
        if not booking:
            raise NotFoundException("Booking", payment.booking_id)

        if current_user.role != "admin" and booking.customer_id != current_user.id:
            raise ForbiddenException("You do not have permission to capture this payment.")

        if payment.payment_status == "captured":
            return payment

        sim_pay_id = f"pay_mock_{uuid.uuid4().hex[:12]}"
        sig = compute_mock_signature(payment.provider_order_id or "", sim_pay_id)
        PaymentService._apply_captured_payment(
            db=db,
            booking=booking,
            payment=payment,
            provider_payment_id=sim_pay_id,
            signature=sig,
        )
        await db.flush()
        return payment

    @staticmethod
    async def _fetch_razorpay_order_payments(order_id: str) -> list[dict[str, Any]]:
        if not settings.RAZORPAY_KEY_ID or not settings.RAZORPAY_KEY_SECRET:
            raise BusinessRuleViolationException("Razorpay API credentials are not configured.")
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                f"https://api.razorpay.com/v1/orders/{order_id}/payments",
                auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET),
            )
            if resp.status_code != 200:
                raise BusinessRuleViolationException(
                    f"Razorpay order payments lookup failed ({resp.status_code})."
                )
            data = dict(resp.json())
            items = data.get("items") or []
            return [dict(item) for item in items]

    @staticmethod
    async def reconcile_pending_payments(
        db: AsyncSession,
        *,
        admin_user: User | None = None,
        older_than_minutes: int = 15,
        limit: int = 50,
    ) -> dict[str, Any]:
        """Reconcile stale pending Razorpay orders against Razorpay Orders/Payments API."""
        await apply_rls_context(db, role="system")
        cutoff = datetime.now(UTC) - timedelta(minutes=max(0, older_than_minutes))
        stmt = (
            select(Payment)
            .where(
                Payment.provider == "razorpay",
                Payment.payment_status == "pending",
                Payment.provider_order_id.is_not(None),
                Payment.created_at <= cutoff,
            )
            .order_by(Payment.created_at.asc())
            .limit(limit)
        )
        pending = list((await db.execute(stmt)).scalars().all())
        checked = 0
        reconciled_captured = 0
        reconciled_failed = 0
        details: list[dict[str, Any]] = []

        for item in pending:
            checked += 1
            order_id = item.provider_order_id or ""
            try:
                gw_payments = await PaymentService._fetch_razorpay_order_payments(order_id)
            except Exception as exc:
                details.append({"payment_id": str(item.id), "status": "lookup_error", "error": str(exc)})
                continue

            captured_entity = next(
                (
                    gp
                    for gp in gw_payments
                    if gp.get("status") == "captured"
                    and gp.get("amount") == item.amount_minor
                    and str(gp.get("currency", "")).upper() == item.currency_code.upper()
                ),
                None,
            )
            if captured_entity:
                locked_pay = (
                    await db.execute(select(Payment).where(Payment.id == item.id).with_for_update())
                ).scalar_one()
                locked_booking = (
                    await db.execute(
                        select(Booking).where(Booking.id == locked_pay.booking_id).with_for_update()
                    )
                ).scalar_one()
                if locked_pay.payment_status == "pending":
                    PaymentService._apply_captured_payment(
                        db=db,
                        booking=locked_booking,
                        payment=locked_pay,
                        provider_payment_id=str(captured_entity.get("id") or ""),
                        signature="reconciled_api",
                    )
                    db.add(
                        AuditLog(
                            actor_user_id=admin_user.id if admin_user else None,
                            action="payment_reconciled",
                            resource_type="payment",
                            resource_id=locked_pay.id,
                            metadata_payload={
                                "provider_order_id": order_id,
                                "provider_payment_id": captured_entity.get("id"),
                                "new_status": "captured",
                            },
                        )
                    )
                    reconciled_captured += 1
                    details.append({"payment_id": str(item.id), "status": "captured"})
            elif gw_payments and all(gp.get("status") == "failed" for gp in gw_payments):
                locked_pay = (
                    await db.execute(select(Payment).where(Payment.id == item.id).with_for_update())
                ).scalar_one()
                if locked_pay.payment_status == "pending":
                    locked_pay.payment_status = "failed"
                    db.add(
                        AuditLog(
                            actor_user_id=admin_user.id if admin_user else None,
                            action="payment_reconciled",
                            resource_type="payment",
                            resource_id=locked_pay.id,
                            metadata_payload={"provider_order_id": order_id, "new_status": "failed"},
                        )
                    )
                    reconciled_failed += 1
                    details.append({"payment_id": str(item.id), "status": "failed"})

        await db.flush()
        return {
            "checked": checked,
            "reconciled_captured": reconciled_captured,
            "reconciled_failed": reconciled_failed,
            "details": details,
        }
