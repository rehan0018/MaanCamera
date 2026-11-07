"""Search and Comparison HTTP endpoints."""

from typing import List
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.responses import success_response
from app.modules.search.schemas import (
    SearchFilterParams,
    SearchResponse,
    CompareRequest,
    ComparisonMatrix,
)
from app.modules.search.service import SearchService

router = APIRouter(prefix="", tags=["Search & Comparison"])


@router.get("/search/professionals")
async def search_professionals(
    category_slug: str = Query(None, description="Category filter (e.g. wedding-photography)"),
    city: str = Query(None, description="City name (e.g. Pune, Mumbai)"),
    verified_only: bool = Query(False, description="Filter only verified profiles"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    params = SearchFilterParams(
        category_slug=category_slug,
        city=city,
        verified_only=verified_only,
        page=page,
        limit=limit,
    )
    result = await SearchService.search_professionals(db, params)
    return success_response(data=result.model_dump(mode="json"))


@router.post("/search/compare")
async def compare_professionals(
    req: CompareRequest,
    db: AsyncSession = Depends(get_db),
):
    result = await SearchService.compare_professionals(db, req.professional_ids)
    return success_response(data=result.model_dump(mode="json"))
