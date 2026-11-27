"""Schemas for Enquiries and Recipients."""

import uuid
from datetime import date, datetime

from pydantic import BaseModel, Field


class EnquiryCreateRequest(BaseModel):
    category_id: uuid.UUID
    title: str = Field(..., max_length=250)
    description: str
    shoot_date: date | None = None
    duration_days: int = Field(1, ge=1)
    location: str = Field(..., max_length=200)
    city: str = Field(..., max_length=100)
    budget_min_minor: int | None = Field(None, ge=0)
    budget_max_minor: int | None = Field(None, ge=0)
    currency_code: str = Field("INR", max_length=3)
    professional_ids: list[uuid.UUID] = Field(..., min_length=1)


class EnquiryRecipientResponse(BaseModel):
    id: uuid.UUID
    enquiry_id: uuid.UUID
    professional_id: uuid.UUID
    recipient_status: str
    sent_at: datetime
    viewed_at: datetime | None = None

    class Config:
        from_attributes = True


class EnquiryResponse(BaseModel):
    id: uuid.UUID
    customer_id: uuid.UUID
    category_id: uuid.UUID
    title: str
    description: str
    shoot_date: date | None = None
    duration_days: int = 1
    location: str
    city: str
    budget_min_minor: int | None = None
    budget_max_minor: int | None = None
    currency_code: str
    status: str
    created_at: datetime
    recipients: list[EnquiryRecipientResponse] | None = None

    class Config:
        from_attributes = True
