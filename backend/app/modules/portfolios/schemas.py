"""Schemas for Portfolios, Projects, and Media Uploads."""

import os
import uuid
from datetime import date

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.core.config import settings

ALLOWED_MIME_EXTENSIONS: dict[str, set[str]] = {
    "image/jpeg": {".jpg", ".jpeg"},
    "image/png": {".png"},
    "image/webp": {".webp"},
}


class MediaAssetResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    storage_key: str
    public_url: str | None = None
    visibility: str = "public"
    media_type: str
    mime_type: str
    file_size_bytes: int
    width: int | None = None
    height: int | None = None
    processing_status: str
    display_order: int


class MediaReadUrlResponse(BaseModel):
    asset_id: uuid.UUID
    url: str
    visibility: str
    expires_in_seconds: int | None = None


class ProjectResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    portfolio_id: uuid.UUID
    category_id: uuid.UUID
    title: str
    slug: str
    style: str | None = None
    location: str | None = None
    project_date: date | None = None
    description: str | None = None
    cover_asset_id: uuid.UUID | None = None
    cover_url: str | None = None
    publication_status: str
    tags: list[str] = []
    media_assets: list[MediaAssetResponse] = []


class ProjectCreateRequest(BaseModel):
    portfolio_id: uuid.UUID
    category_id: uuid.UUID
    title: str = Field(..., min_length=2, max_length=200)
    style: str | None = None
    location: str | None = None
    project_date: date | None = None
    description: str | None = None
    tags: list[str] = []


class UploadUrlRequest(BaseModel):
    filename: str = Field(..., min_length=1, max_length=255)
    mime_type: str = Field(..., pattern=r"^image/(jpeg|png|webp)$")
    file_size_bytes: int = Field(..., gt=0, le=settings.MAX_UPLOAD_SIZE_BYTES)
    is_public: bool = True

    @model_validator(mode="after")
    def validate_extension_matches_mime(self) -> "UploadUrlRequest":
        _, ext = os.path.splitext(self.filename.strip().lower())
        allowed_exts = ALLOWED_MIME_EXTENSIONS.get(self.mime_type, set())
        if ext not in allowed_exts:
            raise ValueError(
                f"File extension '{ext or 'none'}' does not match MIME type '{self.mime_type}'. "
                f"Allowed extensions: {', '.join(sorted(allowed_exts))}."
            )
        return self


class UploadUrlResponse(BaseModel):
    upload_url: str
    storage_key: str
    public_url: str | None = None
    bucket: str
    expires_in_seconds: int
    max_content_length_bytes: int


class CompleteMediaUploadRequest(BaseModel):
    project_id: uuid.UUID
    storage_key: str = Field(..., min_length=5, max_length=500)
    visibility: str | None = Field(default=None, pattern="^(public|private)$")
    media_type: str = Field("image", pattern=r"^image$")
    mime_type: str = Field(..., pattern=r"^image/(jpeg|png|webp)$")
    file_size_bytes: int = Field(..., gt=0, le=settings.MAX_UPLOAD_SIZE_BYTES)
    checksum: str = Field(..., min_length=16, max_length=64)
    width: int | None = Field(None, gt=0)
    height: int | None = Field(None, gt=0)
