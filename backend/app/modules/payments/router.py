"""Payment HTTP endpoints."""

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.responses import success_response
from app.modules.identity.models import User
from app.modules.identity.router import get_current_user
from app.modules.payments.schemas import (
    CreatePaymentOrderRequest,
    PaymentResponse,
    VerifyPaymentRequest,
)
from app.modules.payments.service import PaymentService

router = APIRouter(prefix="", tags=["Payments"])


@router.post("/payments/create-order", status_code=status.HTTP_201_CREATED)
async def create_payment_order(
    req: CreatePaymentOrderRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    order = await PaymentService.create_order(db, current_user, req)
    return success_response(data=order.model_dump(mode="json"), status_code=status.HTTP_201_CREATED)


@router.post("/payments/verify")
async def verify_payment(
    req: VerifyPaymentRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    payment = await PaymentService.verify_payment(db, current_user, req)
    return success_response(data=PaymentResponse.model_validate(payment).model_dump(mode="json"))


@router.post("/payments/webhooks/{provider}")
async def payment_webhook(
    provider: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    body_bytes = await request.body()
    body_str = body_bytes.decode("utf-8")
    event_id = request.headers.get("X-Razorpay-Event-Id") or request.headers.get("X-Event-Id")
    event_type = request.headers.get("X-Razorpay-Event-Type") or "payment.captured"
    signature = request.headers.get("X-Razorpay-Signature") or request.headers.get("X-Mock-Signature")

    await PaymentService.process_webhook(
        db, provider, event_id, event_type, body_str, signature=signature
    )
    return {"status": "ok"}
