"""AI HTTP endpoints for Search, Recommendations, Portfolio Analysis, and Review Summaries."""

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.rate_limit import get_user_or_ip_key, limiter
from app.core.responses import success_response
from app.modules.ai.schemas import (
    NaturalLanguageSearchRequest,
    PortfolioAnalysisRequest,
    ReviewSummaryRequest,
)
from app.modules.ai.service import AIService
from app.modules.identity.models import User
from app.modules.identity.router import get_current_user

router = APIRouter(prefix="", tags=["AI Intelligence"])


@router.post("/search/ai")
@limiter.limit("10/minute", key_func=get_user_or_ip_key)
async def natural_language_search(
    request: Request,
    response: Response,
    req: NaturalLanguageSearchRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    recs = await AIService.get_recommendations(db, req.query, customer_id=current_user.id)
    return success_response(data=recs.model_dump(mode="json"))


@router.post("/ai/recommendations")
@limiter.limit("10/minute", key_func=get_user_or_ip_key)
async def get_recommendations(
    request: Request,
    response: Response,
    req: NaturalLanguageSearchRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    recs = await AIService.get_recommendations(db, req.query, customer_id=current_user.id)
    return success_response(data=recs.model_dump(mode="json"))


@router.post("/ai/portfolio/analyze")
@limiter.limit("10/minute", key_func=get_user_or_ip_key)
async def analyze_portfolio(
    request: Request,
    response: Response,
    req: PortfolioAnalysisRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    analysis = await AIService.analyze_portfolio_asset(db, req.project_id)
    return success_response(data=analysis.model_dump(mode="json"))


@router.post("/ai/reviews/summarize")
@limiter.limit("10/minute", key_func=get_user_or_ip_key)
async def summarize_reviews(
    request: Request,
    response: Response,
    req: ReviewSummaryRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    summary = await AIService.summarize_reviews(db, req.professional_id)
    return success_response(data=summary.model_dump(mode="json"))
