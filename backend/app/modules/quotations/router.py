"""Quotation HTTP endpoints."""

import uuid
from typing import List
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.responses import success_response
from app.modules.identity.models import User
from app.modules.identity.router import get_current_user
from app.modules.quotations.schemas import (
    QuotationCreateRequest,
    QuotationRevisionRequest,
    QuotationResponse,
)
from app.modules.quotations.service import QuotationService
from app.modules.bookings.schemas import BookingResponse

router = APIRouter(prefix="", tags=["Quotations"])


@router.post("/quotations", status_code=status.HTTP_201_CREATED)
async def create_quotation(
    req: QuotationCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    quotation = await QuotationService.create_quotation(db, req.professional_id, req)
    return success_response(
        data=QuotationResponse.model_validate(quotation).model_dump(mode="json"),
        status_code=status.HTTP_201_CREATED,
    )


@router.post("/quotations/{id}/revisions")
async def revise_quotation(
    id: uuid.UUID,
    req: QuotationRevisionRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    new_quotation = await QuotationService.revise_quotation(db, id, req)
    return success_response(
        data=QuotationResponse.model_validate(new_quotation).model_dump(mode="json")
    )


@router.post("/quotations/{id}/accept")
async def accept_quotation(
    id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    quotation, booking = await QuotationService.accept_quotation(db, id, current_user.id)
    return success_response(
        data={
            "quotation": QuotationResponse.model_validate(quotation).model_dump(mode="json"),
            "booking": BookingResponse.model_validate(booking).model_dump(mode="json"),
        }
    )
