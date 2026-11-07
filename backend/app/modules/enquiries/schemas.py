"""Schemas for Enquiries and Recipients."""

import uuid
from datetime import date, datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class EnquiryCreateRequest(BaseModel):
    category_id: uuid.UUID
    title: str = Field(..., max_length=200)
    description: str
    shoot_date: Optional[date] = None
    location: Optional[str] = Field(None, max_length=200)
    budget_min_minor: Optional[int] = Field(None, ge=0)
    budget_max_minor: Optional[int] = Field(None, ge=0)
    currency_code: str = Field("INR", max_length=3)
    professional_ids: List[uuid.UUID] = Field(..., min_length=1)


class EnquiryRecipientResponse(BaseModel):
    id: uuid.UUID
    enquiry_id: uuid.UUID
    professional_id: uuid.UUID
    recipient_status: str
    sent_at: datetime
    viewed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class EnquiryResponse(BaseModel):
    id: uuid.UUID
    customer_id: uuid.UUID
    category_id: uuid.UUID
    title: str
    description: str
    shoot_date: Optional[date] = None
    location: Optional[str] = None
    budget_min_minor: Optional[int] = None
    budget_max_minor: Optional[int] = None
    currency_code: str
    status: str
    created_at: datetime
    recipients: Optional[List[EnquiryRecipientResponse]] = None

    class Config:
        from_attributes = True
