"""Schemas for Portfolios, Projects, and Media Uploads."""

import uuid
from typing import List, Optional
from datetime import date, datetime
from pydantic import BaseModel, Field


class MediaAssetResponse(BaseModel):
    id: uuid.UUID
    storage_key: str
    public_url: Optional[str]
    media_type: str
    mime_type: str
    file_size_bytes: int
    width: Optional[int]
    height: Optional[int]
    display_order: int

    class Config:
        from_attributes = True


class ProjectResponse(BaseModel):
    id: uuid.UUID
    portfolio_id: uuid.UUID
    category_id: uuid.UUID
    title: str
    slug: str
    style: Optional[str]
    location: Optional[str]
    project_date: Optional[date]
    description: Optional[str]
    cover_asset_id: Optional[uuid.UUID]
    cover_url: Optional[str] = None
    publication_status: str
    tags: List[str] = []
    media_assets: List[MediaAssetResponse] = []

    class Config:
        from_attributes = True


class ProjectCreateRequest(BaseModel):
    portfolio_id: uuid.UUID
    category_id: uuid.UUID
    title: str = Field(..., min_length=2, max_length=200)
    style: Optional[str] = None
    location: Optional[str] = None
    project_date: Optional[date] = None
    description: Optional[str] = None
    tags: List[str] = []


class UploadUrlRequest(BaseModel):
    filename: str
    mime_type: str
    file_size_bytes: int
    is_public: bool = True


class UploadUrlResponse(BaseModel):
    upload_url: str
    storage_key: str
    public_url: Optional[str]
    bucket: str
    expires_in_seconds: int


class CompleteMediaUploadRequest(BaseModel):
    project_id: uuid.UUID
    storage_key: str
    public_url: Optional[str] = None
    media_type: str = "image"
    mime_type: str
    file_size_bytes: int
    checksum: str
    width: Optional[int] = None
    height: Optional[int] = None
