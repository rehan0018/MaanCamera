"""Schemas for Payments and Refunds."""

import uuid
from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field


class CreatePaymentOrderRequest(BaseModel):
    booking_id: uuid.UUID
    amount_minor: int = Field(..., gt=0)
    currency_code: str = Field("INR", max_length=3)
    payment_type: str = Field("advance_deposit", pattern="^(advance_deposit|full|milestone|balance)$")


class CreatePaymentOrderResponse(BaseModel):
    payment_id: uuid.UUID
    booking_id: uuid.UUID
    provider: str
    provider_order_id: str
    amount_minor: int
    currency_code: str
    client_secret: Optional[str] = None


class VerifyPaymentRequest(BaseModel):
    payment_id: uuid.UUID
    provider_payment_id: str
    provider_signature: Optional[str] = None


class PaymentResponse(BaseModel):
    id: uuid.UUID
    booking_id: uuid.UUID
    provider: str
    provider_order_id: Optional[str] = None
    provider_payment_id: Optional[str] = None
    amount_minor: int
    currency_code: str
    payment_status: str
    payment_type: str
    verified_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


class RefundRequest(BaseModel):
    amount_minor: int = Field(..., gt=0)
    reason: str = Field(..., min_length=5, max_length=500)
