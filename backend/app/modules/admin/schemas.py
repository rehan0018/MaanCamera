"""Schemas for admin verification and content report moderation."""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class VerificationDecisionRequest(BaseModel):
    decision: str = Field(..., pattern="^(verified|rejected)$")
    notes: str | None = Field(None, max_length=1000)


class AdminVerificationItemResponse(BaseModel):
    id: uuid.UUID
    professional_id: uuid.UUID
    professional_name: str
    base_city: str
    professional_type: str
    document_type: str
    document_storage_key: str
    document_access_url: str | None = None
    status: str
    notes: str | None = None
    created_at: datetime
    reviewed_at: datetime | None = None


class ReportResolutionRequest(BaseModel):
    action: str = Field(..., pattern="^(dismiss|hide_content)$")
    notes: str | None = Field(None, max_length=1000)


class AdminReportItemResponse(BaseModel):
    id: uuid.UUID
    reporter_user_id: uuid.UUID
    reporter_name: str | None = None
    content_type: str
    content_id: uuid.UUID
    reason: str
    details: str | None = None
    status: str
    created_at: datetime
