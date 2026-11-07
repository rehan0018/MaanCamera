"""Schemas for professional profiles, skills, equipment, and services."""

import uuid
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class CategoryResponse(BaseModel):
    id: uuid.UUID
    name: str
    slug: str
    description: Optional[str] = None
    icon_name: Optional[str] = None

    class Config:
        from_attributes = True


class SkillResponse(BaseModel):
    id: uuid.UUID
    skill_name: str
    proficiency_level: str
    years_experience: int
    is_primary: bool

    class Config:
        from_attributes = True


class EquipmentResponse(BaseModel):
    id: uuid.UUID
    equipment_type: str
    brand: str
    model: str
    is_primary: bool

    class Config:
        from_attributes = True


class ServicePackageResponse(BaseModel):
    id: uuid.UUID
    package_name: str
    description: Optional[str]
    price_minor: int
    currency_code: str
    estimated_duration: Optional[str]
    deliverables: List[str]
    is_popular: bool

    class Config:
        from_attributes = True


class ServiceResponse(BaseModel):
    id: uuid.UUID
    name: str
    description: Optional[str]
    pricing_type: str
    starting_price_minor: int
    currency_code: str
    packages: List[ServicePackageResponse] = []

    class Config:
        from_attributes = True


class ProfessionalProfileResponse(BaseModel):
    id: uuid.UUID
    display_name: str
    slug: str
    headline: Optional[str]
    biography: Optional[str]
    profile_image: Optional[str]
    cover_image: Optional[str]
    professional_type: str
    years_experience: int
    base_city: str
    state: str
    country_code: str
    service_radius_km: int
    travel_available: bool
    verification_status: str
    avg_rating: float
    total_reviews: int
    completed_bookings_count: int
    skills: List[SkillResponse] = []
    equipment_list: List[EquipmentResponse] = []
    services: List[ServiceResponse] = []

    class Config:
        from_attributes = True


class ProfileCreateRequest(BaseModel):
    display_name: str = Field(..., min_length=2, max_length=200)
    headline: Optional[str] = None
    biography: Optional[str] = None
    professional_type: str = "individual"
    years_experience: int = Field(1, ge=0)
    base_city: str
    state: str
    service_radius_km: int = 50
    travel_available: bool = True
