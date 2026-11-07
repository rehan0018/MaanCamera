"""Schemas for AI Operations (Search, Recommendations, Analysis, Review Summaries)."""

import uuid
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class NaturalLanguageSearchRequest(BaseModel):
    query: str = Field(..., min_length=3, max_length=1000)


class ExtractedRequirements(BaseModel):
    category: Optional[List[str]] = None
    location: Optional[Dict[str, str]] = None
    style: Optional[List[str]] = None
    duration_days: Optional[int] = None
    budget: Optional[Dict[str, Any]] = None
    availability_required: bool = False


class RecommendationItemResponse(BaseModel):
    professional_id: uuid.UUID
    display_name: str
    slug: str
    headline: Optional[str]
    profile_image: Optional[str]
    base_city: str
    avg_rating: float
    total_reviews: int
    starting_price_minor: int
    verification_status: str
    relevance_score: float
    ranking_position: int
    match_explanation: str
    relevant_projects: List[str] = []


class RecommendationResponse(BaseModel):
    session_id: uuid.UUID
    query: str
    extracted_requirements: Dict[str, Any]
    total_matches: int
    recommendations: List[RecommendationItemResponse]


class PortfolioAnalysisRequest(BaseModel):
    project_id: uuid.UUID
    asset_id: Optional[uuid.UUID] = None
    media_url: Optional[str] = None


class PortfolioAnalysisResponse(BaseModel):
    detected_categories: List[str]
    suggested_tags: List[str]
    lighting_style: str
    composition: str
    suggested_caption: str


class ReviewSummaryRequest(BaseModel):
    professional_id: uuid.UUID


class ReviewSummaryResponse(BaseModel):
    professional_id: uuid.UUID
    total_reviews_analyzed: int
    sentiment_highlights: List[str]
    strengths_mentioned: List[str]
    areas_for_alignment: List[str]
