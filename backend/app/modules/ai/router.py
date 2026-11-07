"""AI HTTP endpoints for Search, Recommendations, Portfolio Analysis, and Review Summaries."""

import uuid
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.responses import success_response
from app.modules.identity.models import User
from app.modules.identity.router import get_current_user
from app.modules.ai.schemas import (
    NaturalLanguageSearchRequest,
    RecommendationResponse,
    PortfolioAnalysisRequest,
    PortfolioAnalysisResponse,
    ReviewSummaryRequest,
    ReviewSummaryResponse,
)
from app.modules.ai.service import AIService

router = APIRouter(prefix="", tags=["AI Intelligence"])


@router.post("/search/ai")
async def natural_language_search(
    req: NaturalLanguageSearchRequest,
    db: AsyncSession = Depends(get_db),
):
    recs = await AIService.get_recommendations(db, req.query)
    return success_response(data=recs.model_dump(mode="json"))


@router.post("/ai/recommendations")
async def get_recommendations(
    req: NaturalLanguageSearchRequest,
    db: AsyncSession = Depends(get_db),
):
    recs = await AIService.get_recommendations(db, req.query)
    return success_response(data=recs.model_dump(mode="json"))


@router.post("/ai/portfolio/analyze")
async def analyze_portfolio(
    req: PortfolioAnalysisRequest,
    db: AsyncSession = Depends(get_db),
):
    analysis = await AIService.analyze_portfolio_asset(req.project_id)
    return success_response(data=analysis.model_dump(mode="json"))


@router.post("/ai/reviews/summarize")
async def summarize_reviews(
    req: ReviewSummaryRequest,
    db: AsyncSession = Depends(get_db),
):
    summary = await AIService.summarize_reviews(db, req.professional_id)
    return success_response(data=summary.model_dump(mode="json"))
