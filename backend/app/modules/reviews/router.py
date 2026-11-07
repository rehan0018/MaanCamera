"""Review HTTP endpoints."""

import uuid
from typing import List
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.responses import success_response
from app.modules.identity.models import User
from app.modules.identity.router import get_current_user
from app.modules.reviews.schemas import (
    ReviewCreateRequest,
    ReviewResponse,
    ContentReportRequest,
)
from app.modules.reviews.service import ReviewService

router = APIRouter(prefix="", tags=["Reviews"])


@router.post("/bookings/{id}/review", status_code=status.HTTP_201_CREATED)
async def submit_booking_review(
    id: uuid.UUID,
    req: ReviewCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    review = await ReviewService.create_booking_review(db, id, current_user.id, req)
    return success_response(
        data=ReviewResponse.model_validate(review).model_dump(mode="json"),
        status_code=status.HTTP_201_CREATED,
    )


@router.get("/professionals/{id}/reviews")
async def get_professional_reviews(
    id: uuid.UUID,
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    reviews = await ReviewService.list_professional_reviews(db, id, limit=limit)
    return success_response(
        data=[ReviewResponse.model_validate(r).model_dump(mode="json") for r in reviews]
    )


@router.post("/reviews/{id}/report", status_code=status.HTTP_201_CREATED)
async def report_review(
    id: uuid.UUID,
    req: ContentReportRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    report = await ReviewService.report_review(db, id, current_user.id, req)
    return success_response(
        data={"report_id": str(report.id), "status": report.status},
        status_code=status.HTTP_201_CREATED,
    )
