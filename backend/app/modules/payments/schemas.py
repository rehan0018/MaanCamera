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
    provider_key_id: str | None = None
    amount_minor: int
    currency_code: str
    client_secret: str | None = None
    idempotent_replay: bool = False


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


class RefundResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    payment_id: uuid.UUID
    amount_minor: int
    currency_code: str
    reason: str
    status: str
    provider_refund_id: str | None = None
    created_at: datetime


class PaymentLedgerEntryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    booking_id: uuid.UUID
    payment_id: uuid.UUID | None = None
    refund_id: uuid.UUID | None = None
    entry_type: str
    direction: str
    amount_minor: int
    currency_code: str
    notes: str | None = None
    created_at: datetime
