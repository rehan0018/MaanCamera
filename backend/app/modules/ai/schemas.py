"""Schemas for AI Operations (Search, Recommendations, Analysis, Review Summaries)."""

import uuid
from typing import Any

from pydantic import BaseModel, Field


class NaturalLanguageSearchRequest(BaseModel):
    query: str = Field(..., min_length=3, max_length=1000)


class ExtractedRequirements(BaseModel):
    category: list[str] | None = None
    location: dict[str, str] | None = None
    style: list[str] | None = None
    duration_days: int | None = None
    budget: dict[str, Any] | None = None
    availability_required: bool = False


class RecommendationItemResponse(BaseModel):
    professional_id: uuid.UUID
    display_name: str
    slug: str
    headline: str | None
    profile_image: str | None
    base_city: str
    avg_rating: float
    total_reviews: int
    starting_price_minor: int
    verification_status: str
    relevance_score: float
    ranking_position: int
    match_explanation: str
    relevant_projects: list[str] = []


class RecommendationResponse(BaseModel):
    session_id: uuid.UUID
    query: str
    extracted_requirements: dict[str, Any]
    total_matches: int
    recommendations: list[RecommendationItemResponse]


class PortfolioAnalysisRequest(BaseModel):
    project_id: uuid.UUID
    asset_id: uuid.UUID | None = None
    media_url: str | None = None


class PortfolioAnalysisResponse(BaseModel):
    detected_categories: list[str]
    suggested_tags: list[str]
    lighting_style: str
    composition: str
    suggested_caption: str


class ReviewSummaryRequest(BaseModel):
    professional_id: uuid.UUID


class ReviewSummaryResponse(BaseModel):
    professional_id: uuid.UUID
    total_reviews_analyzed: int
    sentiment_highlights: list[str]
    strengths_mentioned: list[str]
    areas_for_alignment: list[str]
