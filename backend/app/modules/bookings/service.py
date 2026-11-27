"""Booking business logic and transition state machine."""

import uuid

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BusinessRuleViolationException, ForbiddenException, NotFoundException
from app.modules.bookings.models import Booking
from app.modules.identity.models import User
from app.modules.professionals.models import ProfessionalProfile

# Valid state machine transitions
ALLOWED_TRANSITIONS = {
    "pending_payment": ["confirmed", "cancelled"],
    "confirmed": ["in_progress", "completed", "cancelled"],
    "in_progress": ["completed", "cancelled"],
    "completed": ["disputed"],
    "cancelled": [],
    "disputed": ["cancelled", "completed"],
}


class BookingService:
    @staticmethod
    async def get_booking_by_id(
        db: AsyncSession, booking_id: uuid.UUID, current_user: User | None = None
    ) -> Booking:
        stmt = select(Booking).where(Booking.id == booking_id)
        res = await db.execute(stmt)
        booking = res.scalar_one_or_none()
        if not booking:
            raise NotFoundException("Booking", booking_id)

        if current_user and current_user.role != "admin" and booking.customer_id != current_user.id:
            # Check if current_user owns the professional profile
            prof_stmt = select(ProfessionalProfile).where(
                ProfessionalProfile.id == booking.professional_id,
                ProfessionalProfile.owner_user_id == current_user.id,
            )
            prof_res = await db.execute(prof_stmt)
            if not prof_res.scalar_one_or_none():
                raise ForbiddenException("You do not have permission to view this booking.")

        return booking

    @staticmethod
    async def list_user_bookings(db: AsyncSession, user: User) -> list[Booking]:
        if user.role == "admin":
            stmt = select(Booking).order_by(desc(Booking.created_at))
        elif user.role == "professional":
            prof_stmt = select(ProfessionalProfile.id).where(ProfessionalProfile.owner_user_id == user.id)
            prof_res = await db.execute(prof_stmt)
            prof_ids = list(prof_res.scalars().all())
            stmt = select(Booking).where(
                (Booking.customer_id == user.id) | (Booking.professional_id.in_(prof_ids))
            ).order_by(desc(Booking.created_at))
        else:
            stmt = select(Booking).where(Booking.customer_id == user.id).order_by(desc(Booking.created_at))

        res = await db.execute(stmt)
        return list(res.scalars().all())

    @staticmethod
    async def update_status(
        db: AsyncSession, booking_id: uuid.UUID, new_status: str, current_user: User
    ) -> Booking:
        booking = await BookingService.get_booking_by_id(db, booking_id, current_user)
        current = booking.booking_status

        if new_status == "completed":
            return await BookingService.complete_booking(db, booking_id, current_user)

        if new_status not in ALLOWED_TRANSITIONS.get(current, []):
            raise BusinessRuleViolationException(
                f"Invalid booking transition from '{current}' to '{new_status}'."
            )

        booking.booking_status = new_status
        await db.commit()
        await db.refresh(booking)
        return booking

    @staticmethod
    async def complete_booking(
        db: AsyncSession, booking_id: uuid.UUID, current_user: User
    ) -> Booking:
        booking = await BookingService.get_booking_by_id(db, booking_id)
        if current_user.role != "admin" and booking.customer_id != current_user.id:
            raise ForbiddenException("Only the booking customer or admin may mark a booking complete.")

        if booking.booking_status not in ["confirmed", "in_progress"]:
            raise BusinessRuleViolationException("Only confirmed or in-progress bookings can be completed.")

        booking.booking_status = "completed"
        booking.completion_status = "customer_accepted"

        # Increment completed bookings count on professional profile
        prof = await db.get(ProfessionalProfile, booking.professional_id)
        if prof:
            prof.completed_bookings_count = (prof.completed_bookings_count or 0) + 1

        await db.commit()
        await db.refresh(booking)
        return booking

    @staticmethod
    async def cancel_booking(
        db: AsyncSession, booking_id: uuid.UUID, reason: str, current_user: User
    ) -> Booking:
        booking = await BookingService.get_booking_by_id(db, booking_id, current_user)
        if booking.booking_status == "completed":
            raise BusinessRuleViolationException("Completed bookings cannot be cancelled.")

        booking.booking_status = "cancelled"
        booking.cancellation_reason = reason
        await db.commit()
        await db.refresh(booking)
        return booking
