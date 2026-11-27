"""Schemas for identity, authentication, verification, 2FA, sessions, and DPDP compliance."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator


class UserRegisterRequest(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=150)
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    phone: str | None = Field(default=None, max_length=20)
    role: str = Field("customer", pattern="^(customer|professional)$")
    accept_terms: bool = True
    accept_privacy: bool = True
    marketing_opt_in: bool = False
    terms_version: str | None = None
    privacy_version: str | None = None

    @model_validator(mode="after")
    def validate_consent(self) -> "UserRegisterRequest":
        if not self.accept_terms or not self.accept_privacy:
            raise ValueError("Terms of Service and Privacy Policy must be accepted to register.")
        return self


class UserLoginRequest(BaseModel):
    email: EmailStr
    password: str
    totp_code: str | None = Field(default=None, min_length=6, max_length=6)


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str | None
    phone: str | None
    full_name: str
    role: str = "customer"
    avatar_url: str | None
    status: str
    is_superuser: bool
    email_verified_at: datetime | None
    phone_verified_at: datetime | None = None
    totp_enabled: bool = False
    terms_version: str | None = None
    privacy_version: str | None = None
    created_at: datetime


class AuthResponseData(BaseModel):
    user: UserResponse
    session_token: str


class EmailVerifyConfirmRequest(BaseModel):
    token: str = Field(..., min_length=16, max_length=256)


class PhoneOtpRequest(BaseModel):
    phone: str | None = Field(default=None, min_length=8, max_length=20)


class PhoneOtpConfirmRequest(BaseModel):
    phone: str | None = Field(default=None, min_length=8, max_length=20)
    code: str = Field(..., pattern=r"^\d{6}$")


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetConfirmRequest(BaseModel):
    token: str = Field(..., min_length=16, max_length=256)
    new_password: str = Field(..., min_length=8, max_length=128)


class TotpCodeRequest(BaseModel):
    code: str = Field(..., pattern=r"^\d{6}$")


class UserSessionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_agent: str | None
    ip_address: str | None
    created_at: datetime
    last_used_at: datetime
    expires_at: datetime
    revoked_at: datetime | None
    is_current: bool = False


class ConsentRecordResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    consent_type: str
    policy_version: str
    granted: bool
    recorded_at: datetime


class DeleteAccountRequest(BaseModel):
    password: str | None = None
    confirm_phrase: str = Field("DELETE", pattern="^DELETE$")
