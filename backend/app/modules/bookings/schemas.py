"""Schemas for Bookings."""

import uuid
from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel, Field


class BookingStatusUpdate(BaseModel):
    booking_status: str = Field(..., pattern="^(pending_deposit|confirmed|in_progress|completed|cancelled)$")


class BookingCancelRequest(BaseModel):
    cancellation_reason: str = Field(..., min_length=5, max_length=1000)


class BookingResponse(BaseModel):
    id: uuid.UUID
    enquiry_id: uuid.UUID
    quotation_id: uuid.UUID
    customer_id: uuid.UUID
    professional_id: uuid.UUID
    shoot_date: date
    location: str
    agreed_amount_minor: int
    currency_code: str
    booking_status: str
    completion_status: str
    cancellation_reason: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
