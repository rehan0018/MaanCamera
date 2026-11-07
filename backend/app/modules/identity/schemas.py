"""Schemas for identity, authentication, and user profiles."""

import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field


class UserRegisterRequest(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=150)
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    phone: Optional[str] = None


class UserLoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: uuid.UUID
    email: Optional[str]
    phone: Optional[str]
    full_name: str
    avatar_url: Optional[str]
    status: str
    is_superuser: bool
    email_verified_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


class AuthResponseData(BaseModel):
    user: UserResponse
    session_token: str
