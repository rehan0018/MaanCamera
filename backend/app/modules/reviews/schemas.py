"""Schemas for Reviews and Reports."""

import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class ReviewCreateRequest(BaseModel):
    overall_rating: float = Field(..., ge=1.0, le=5.0)
    work_quality_rating: float = Field(..., ge=1.0, le=5.0)
    communication_rating: float = Field(..., ge=1.0, le=5.0)
    punctuality_rating: float = Field(..., ge=1.0, le=5.0)
    value_rating: float = Field(..., ge=1.0, le=5.0)
    review_text: str = Field(..., min_length=10, max_length=2000)


class ReviewResponse(BaseModel):
    id: uuid.UUID
    booking_id: uuid.UUID
    customer_id: uuid.UUID
    professional_id: uuid.UUID
    overall_rating: float
    work_quality_rating: float
    communication_rating: float
    punctuality_rating: float
    value_rating: float
    review_text: str
    moderation_status: str
    created_at: datetime

    class Config:
        from_attributes = True


class ContentReportRequest(BaseModel):
    reason: str = Field(..., min_length=3, max_length=100)
    details: Optional[str] = Field(None, max_length=1000)
