"""Schemas for Search, Filtering, Comparison, and Ranking."""

import uuid
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class SearchFilterParams(BaseModel):
    category_slug: Optional[str] = None
    city: Optional[str] = None
    budget_min_paise: Optional[int] = None
    budget_max_paise: Optional[int] = None
    style: Optional[str] = None
    verified_only: bool = False
    page: int = Field(1, ge=1)
    limit: int = Field(20, ge=1, le=100)


class SearchCandidateResult(BaseModel):
    id: uuid.UUID
    display_name: str
    slug: str
    headline: Optional[str]
    profile_image: Optional[str]
    cover_image: Optional[str]
    base_city: str
    state: str
    years_experience: int
    avg_rating: float
    total_reviews: int
    starting_price_minor: int
    verification_status: str
    match_score: Optional[float] = None
    match_explanation: Optional[str] = None


class SearchResponse(BaseModel):
    total_results: int
    page: int
    limit: int
    results: List[SearchCandidateResult]


class CompareRequest(BaseModel):
    professional_ids: List[uuid.UUID] = Field(..., min_length=2, max_length=4)


class ComparisonMatrix(BaseModel):
    professionals: List[Dict[str, Any]]
    feature_matrix: Dict[str, List[Any]]
