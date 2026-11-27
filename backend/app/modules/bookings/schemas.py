"""Schemas for Bookings."""

import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class BookingStatusUpdate(BaseModel):
    booking_status: str = Field(..., pattern="^(pending_payment|confirmed|in_progress|completed|cancelled|disputed)$")


class BookingCancelRequest(BaseModel):
    cancellation_reason: str = Field(..., min_length=5, max_length=1000)


class BookingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    enquiry_id: uuid.UUID | None = None
    quotation_id: uuid.UUID | None = None
    customer_id: uuid.UUID
    professional_id: uuid.UUID
    professional_name: str | None = None
    customer_name: str | None = None
    shoot_date: date
    location: str
    agreed_amount_minor: int
    paid_amount_minor: int = 0
    currency_code: str
    booking_status: str
    completion_status: str
    cancellation_reason: str | None = None
    created_at: datetime
    updated_at: datetime
