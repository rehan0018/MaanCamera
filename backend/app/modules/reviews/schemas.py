"""Schemas for Reviews and Reports."""

import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class ReviewCreateRequest(BaseModel):
    overall_rating: int = Field(..., ge=1, le=5)
    work_quality_rating: int = Field(..., ge=1, le=5)
    communication_rating: int = Field(..., ge=1, le=5)
    punctuality_rating: int = Field(..., ge=1, le=5)
    value_rating: int = Field(..., ge=1, le=5)
    review_text: str = Field(..., min_length=10, max_length=2000)


class ReviewResponse(BaseModel):
    id: uuid.UUID
    booking_id: uuid.UUID
    customer_id: uuid.UUID
    professional_id: uuid.UUID
    overall_rating: int
    work_quality_rating: int
    communication_rating: int
    punctuality_rating: int
    value_rating: int
    review_text: str
    moderation_status: str
    created_at: datetime

    class Config:
        from_attributes = True


class ContentReportRequest(BaseModel):
    reason: str = Field(..., min_length=3, max_length=100)
    details: Optional[str] = Field(None, max_length=1000)
