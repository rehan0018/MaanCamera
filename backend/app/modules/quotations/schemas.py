"""Schemas for Quotations."""

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class QuotationCreateRequest(BaseModel):
    enquiry_id: uuid.UUID
    professional_id: uuid.UUID | None = None
    total_amount_minor: int = Field(..., gt=0)
    currency_code: str = Field("INR", max_length=3)
    advance_amount_minor: int = Field(0, ge=0)
    scope_of_work: str
    deliverables: Any | None = None
    terms: str | None = None
    valid_until: datetime | None = None


class QuotationRevisionRequest(BaseModel):
    total_amount_minor: int = Field(..., gt=0)
    advance_amount_minor: int = Field(0, ge=0)
    scope_of_work: str
    deliverables: Any | None = None
    terms: str | None = None
    valid_until: datetime | None = None


class QuotationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    enquiry_id: uuid.UUID
    professional_id: uuid.UUID
    professional_name: str | None = None
    enquiry_title: str | None = None
    version_number: int
    total_amount_minor: int
    currency_code: str
    advance_amount_minor: int
    scope_of_work: str
    deliverables: Any | None = None
    terms: str | None = None
    valid_until: datetime | None = None
    status: str
    created_at: datetime
    updated_at: datetime
