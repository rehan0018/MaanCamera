"""Booking HTTP endpoints."""

import uuid
from typing import List
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.responses import success_response
from app.modules.identity.models import User
from app.modules.identity.router import get_current_user
from app.modules.bookings.schemas import (
    BookingResponse,
    BookingStatusUpdate,
    BookingCancelRequest,
)
from app.modules.bookings.service import BookingService

router = APIRouter(prefix="", tags=["Bookings"])


@router.get("/bookings/me")
async def get_my_bookings(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    bookings = await BookingService.list_user_bookings(db, current_user.id, is_customer=True)
    return success_response(
        data=[BookingResponse.model_validate(b).model_dump(mode="json") for b in bookings]
    )


@router.get("/bookings/{id}")
async def get_booking(
    id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    booking = await BookingService.get_booking_by_id(db, id)
    return success_response(data=BookingResponse.model_validate(booking).model_dump(mode="json"))


@router.patch("/bookings/{id}/status")
async def update_booking_status(
    id: uuid.UUID,
    req: BookingStatusUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    booking = await BookingService.update_status(db, id, req.booking_status)
    return success_response(data=BookingResponse.model_validate(booking).model_dump(mode="json"))


@router.post("/bookings/{id}/complete")
async def complete_booking(
    id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    booking = await BookingService.complete_booking(db, id)
    return success_response(data=BookingResponse.model_validate(booking).model_dump(mode="json"))


@router.post("/bookings/{id}/cancel")
async def cancel_booking(
    id: uuid.UUID,
    req: BookingCancelRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    booking = await BookingService.cancel_booking(db, id, req.cancellation_reason)
    return success_response(data=BookingResponse.model_validate(booking).model_dump(mode="json"))
