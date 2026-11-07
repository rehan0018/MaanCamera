"""Payment HTTP endpoints."""

import uuid
from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.responses import success_response
from app.modules.identity.models import User
from app.modules.identity.router import get_current_user
from app.modules.payments.schemas import (
    CreatePaymentOrderRequest,
    CreatePaymentOrderResponse,
    VerifyPaymentRequest,
    PaymentResponse,
    RefundRequest,
)
from app.modules.payments.service import PaymentService

router = APIRouter(prefix="", tags=["Payments"])


@router.post("/payments/create-order", status_code=status.HTTP_201_CREATED)
async def create_payment_order(
    req: CreatePaymentOrderRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    order = await PaymentService.create_order(db, req)
    return success_response(data=order.model_dump(mode="json"), status_code=status.HTTP_201_CREATED)


@router.post("/payments/verify")
async def verify_payment(
    req: VerifyPaymentRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    payment = await PaymentService.verify_payment(db, req)
    return success_response(data=PaymentResponse.model_validate(payment).model_dump(mode="json"))


@router.post("/payments/webhooks/{provider}")
async def payment_webhook(
    provider: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    body_bytes = await request.body()
    body_str = body_bytes.decode()
    event_id = request.headers.get("X-Razorpay-Event-Id", f"evt_{uuid.uuid4().hex[:12]}")
    event_type = request.headers.get("X-Razorpay-Event-Type", "payment.captured")

    await PaymentService.process_webhook(db, provider, event_id, event_type, body_str)
    return {"status": "ok"}
