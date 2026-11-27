"""Quotation HTTP endpoints."""

import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.responses import success_response
from app.modules.bookings.schemas import BookingResponse
from app.modules.bookings.service import BookingService
from app.modules.identity.models import User
from app.modules.identity.router import get_current_user
from app.modules.quotations.schemas import (
    QuotationCreateRequest,
    QuotationRevisionRequest,
)
from app.modules.quotations.service import QuotationService

router = APIRouter(prefix="", tags=["Quotations"])


@router.get("/quotations/me")
async def get_my_quotations(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    quotations = await QuotationService.list_user_quotations(db, current_user)
    serialized = await QuotationService.serialize_quotations(db, quotations)
    return success_response(data=[q.model_dump(mode="json") for q in serialized])


@router.get("/enquiries/{id}/quotations")
async def get_enquiry_quotations(
    id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    quotations = await QuotationService.list_by_enquiry(db, id, current_user)
    serialized = await QuotationService.serialize_quotations(db, quotations)
    return success_response(data=[q.model_dump(mode="json") for q in serialized])


@router.post("/quotations", status_code=status.HTTP_201_CREATED)
async def create_quotation(
    req: QuotationCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    quotation = await QuotationService.create_quotation(db, current_user, req)
    serialized = await QuotationService.serialize_quotations(db, [quotation])
    return success_response(
        data=serialized[0].model_dump(mode="json"),
        status_code=status.HTTP_201_CREATED,
    )


@router.post("/quotations/{id}/revisions")
async def revise_quotation(
    id: uuid.UUID,
    req: QuotationRevisionRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    new_quotation = await QuotationService.revise_quotation(db, id, current_user, req)
    serialized = await QuotationService.serialize_quotations(db, [new_quotation])
    return success_response(data=serialized[0].model_dump(mode="json"))


@router.post("/quotations/{id}/accept")
async def accept_quotation(
    id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    quotation, booking = await QuotationService.accept_quotation(db, id, current_user.id)
    serialized_quotes = await QuotationService.serialize_quotations(db, [quotation])
    serialized_bookings = await BookingService.serialize_bookings(db, [booking])
    return success_response(
        data={
            "quotation": serialized_quotes[0].model_dump(mode="json"),
            "booking": serialized_bookings[0].model_dump(mode="json") if serialized_bookings else BookingResponse.model_validate(booking).model_dump(mode="json"),
        }
    )
