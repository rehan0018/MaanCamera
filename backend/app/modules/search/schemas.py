"""Schemas for Search, Filtering, Comparison, and Ranking."""

import uuid
from typing import Any

from pydantic import BaseModel, Field


class SearchFilterParams(BaseModel):
    category_slug: str | None = None
    city: str | None = None
    budget_min_paise: int | None = None
    budget_max_paise: int | None = None
    style: str | None = None
    verified_only: bool = False
    page: int = Field(1, ge=1)
    limit: int = Field(20, ge=1, le=100)


class SearchCandidateResult(BaseModel):
    id: uuid.UUID
    display_name: str
    slug: str
    headline: str | None = None
    profile_image: str | None = None
    cover_image: str | None = None
    base_city: str
    state: str
    years_experience: int
    avg_rating: float
    total_reviews: int
    starting_price_minor: int | None = 0
    verification_status: str
    match_score: float | None = None
    match_explanation: str | None = None


class SearchResponse(BaseModel):
    total_results: int
    page: int
    limit: int
    results: list[SearchCandidateResult]


class CompareRequest(BaseModel):
    professional_ids: list[uuid.UUID] = Field(..., min_length=2, max_length=4)


class ComparisonMatrix(BaseModel):
    professionals: list[dict[str, Any]]
    feature_matrix: dict[str, list[Any]]
