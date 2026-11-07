"""Schemas for Quotations."""

import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class QuotationCreateRequest(BaseModel):
    enquiry_id: uuid.UUID
    professional_id: uuid.UUID
    total_amount_minor: int = Field(..., gt=0)
    currency_code: str = Field("INR", max_length=3)
    advance_amount_minor: int = Field(0, ge=0)
    scope_of_work: str
    deliverables: Optional[str] = None
    terms: Optional[str] = None
    valid_until: Optional[datetime] = None


class QuotationRevisionRequest(BaseModel):
    total_amount_minor: int = Field(..., gt=0)
    advance_amount_minor: int = Field(0, ge=0)
    scope_of_work: str
    deliverables: Optional[str] = None
    terms: Optional[str] = None
    valid_until: Optional[datetime] = None


class QuotationResponse(BaseModel):
    id: uuid.UUID
    enquiry_id: uuid.UUID
    professional_id: uuid.UUID
    version_number: int
    total_amount_minor: int
    currency_code: str
    advance_amount_minor: int
    scope_of_work: str
    deliverables: Optional[str] = None
    terms: Optional[str] = None
    valid_until: Optional[datetime] = None
    status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
