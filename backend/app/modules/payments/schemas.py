"""Schemas for Payments and Refunds."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class CreatePaymentOrderRequest(BaseModel):
    booking_id: uuid.UUID
    currency_code: str = Field("INR", max_length=3)
    payment_type: str = Field("advance", pattern="^(advance|balance|full)$")


class CreatePaymentOrderResponse(BaseModel):
    payment_id: uuid.UUID
    booking_id: uuid.UUID
    provider: str
    provider_order_id: str
    amount_minor: int
    currency_code: str
    client_secret: str | None = None


class VerifyPaymentRequest(BaseModel):
    payment_id: uuid.UUID
    provider_payment_id: str
    provider_signature: str = Field(..., min_length=16, max_length=256)
    amount_minor: int | None = Field(None, gt=0)


class PaymentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    booking_id: uuid.UUID
    provider: str
    provider_order_id: str | None = None
    provider_payment_id: str | None = None
    amount_minor: int
    currency_code: str
    payment_status: str
    payment_type: str
    verified_at: datetime | None = None
    created_at: datetime


class RefundRequest(BaseModel):
    amount_minor: int = Field(..., gt=0)
    reason: str = Field(..., min_length=5, max_length=500)
