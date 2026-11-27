"""Schemas for professional profiles, skills, equipment, and services."""

import uuid

from pydantic import BaseModel, ConfigDict, Field


class CategoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    slug: str
    description: str | None = None
    icon_name: str | None = None


class SkillResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    skill_name: str
    proficiency_level: str
    years_experience: int
    is_primary: bool


class EquipmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    equipment_type: str
    brand: str
    model: str
    is_primary: bool


class ServicePackageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    package_name: str
    description: str | None
    price_minor: int
    currency_code: str
    estimated_duration: str | None
    deliverables: list[str]
    is_popular: bool


class ServiceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    category_id: uuid.UUID
    name: str
    description: str | None
    pricing_type: str
    starting_price_minor: int
    currency_code: str
    packages: list[ServicePackageResponse] = []


class ServiceCreateRequest(BaseModel):
    category_id: uuid.UUID
    name: str = Field(..., min_length=2, max_length=200)
    description: str | None = None
    pricing_type: str = Field("starting_from", pattern="^(fixed|starting_from|hourly|daily|custom_quote)$")
    starting_price_minor: int = Field(0, ge=0)
    currency_code: str = Field("INR", max_length=3)


class ProfessionalProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    owner_user_id: uuid.UUID
    display_name: str
    slug: str
    headline: str | None
    biography: str | None
    profile_image: str | None
    cover_image: str | None
    professional_type: str
    years_experience: int
    base_city: str
    state: str
    country_code: str
    service_radius_km: int
    travel_available: bool
    verification_status: str
    profile_visibility: str
    onboarding_completed: bool = False
    avg_rating: float
    total_reviews: int
    completed_bookings_count: int
    skills: list[SkillResponse] = []
    equipment_list: list[EquipmentResponse] = []
    services: list[ServiceResponse] = []


class ProfileCreateRequest(BaseModel):
    display_name: str = Field(..., min_length=2, max_length=200)
    headline: str | None = Field(None, max_length=250)
    biography: str | None = None
    professional_type: str = Field("individual", pattern="^(individual|team|studio|crew)$")
    years_experience: int = Field(1, ge=0)
    base_city: str = Field(..., min_length=2, max_length=100)
    state: str = Field(..., min_length=2, max_length=100)
    service_radius_km: int = Field(50, ge=0)
    travel_available: bool = True


class ProfileUpdateRequest(BaseModel):
    display_name: str | None = Field(None, min_length=2, max_length=200)
    headline: str | None = Field(None, max_length=250)
    biography: str | None = None
    professional_type: str | None = Field(None, pattern="^(individual|team|studio|crew)$")
    years_experience: int | None = Field(None, ge=0)
    base_city: str | None = Field(None, min_length=2, max_length=100)
    state: str | None = Field(None, min_length=2, max_length=100)
    service_radius_km: int | None = Field(None, ge=0)
    travel_available: bool | None = None
    profile_visibility: str | None = Field(None, pattern="^(public|unlisted|private)$")
