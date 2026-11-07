"""Booking business logic and transition state machine."""

import uuid
from typing import List, Optional
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.bookings.models import Booking
from app.core.exceptions import NotFoundException, BusinessRuleViolationException

# Valid state machine transitions
ALLOWED_TRANSITIONS = {
    "pending_deposit": ["confirmed", "cancelled"],
    "confirmed": ["in_progress", "cancelled"],
    "in_progress": ["completed", "cancelled"],
    "completed": [],
    "cancelled": [],
}


class BookingService:
    @staticmethod
    async def get_booking_by_id(db: AsyncSession, booking_id: uuid.UUID) -> Booking:
        stmt = select(Booking).where(Booking.id == booking_id)
        res = await db.execute(stmt)
        booking = res.scalar_one_or_none()
        if not booking:
            raise NotFoundException("Booking not found.")
        return booking

    @staticmethod
    async def list_user_bookings(db: AsyncSession, user_id: uuid.UUID, is_customer: bool = True) -> List[Booking]:
        if is_customer:
            stmt = select(Booking).where(Booking.customer_id == user_id).order_by(desc(Booking.created_at))
        else:
            stmt = select(Booking).where(Booking.professional_id == user_id).order_by(desc(Booking.created_at))
        res = await db.execute(stmt)
        return list(res.scalars().all())

    @staticmethod
    async def update_status(db: AsyncSession, booking_id: uuid.UUID, new_status: str) -> Booking:
        booking = await BookingService.get_booking_by_id(db, booking_id)
        current = booking.booking_status

        if new_status not in ALLOWED_TRANSITIONS.get(current, []):
            raise BusinessRuleViolationException(
                f"Invalid booking transition from '{current}' to '{new_status}'."
            )

        booking.booking_status = new_status
        await db.commit()
        await db.refresh(booking)
        return booking

    @staticmethod
    async def complete_booking(db: AsyncSession, booking_id: uuid.UUID) -> Booking:
        booking = await BookingService.get_booking_by_id(db, booking_id)
        if booking.booking_status not in ["confirmed", "in_progress"]:
            raise BusinessRuleViolationException("Only confirmed or in-progress bookings can be marked completed.")

        booking.booking_status = "completed"
        booking.completion_status = "accepted"
        await db.commit()
        await db.refresh(booking)
        return booking

    @staticmethod
    async def cancel_booking(db: AsyncSession, booking_id: uuid.UUID, reason: str) -> Booking:
        booking = await BookingService.get_booking_by_id(db, booking_id)
        if booking.booking_status == "completed":
            raise BusinessRuleViolationException("Completed bookings cannot be cancelled.")

        booking.booking_status = "cancelled"
        booking.cancellation_reason = reason
        await db.commit()
        await db.refresh(booking)
        return booking
