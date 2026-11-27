"""Booking business logic, actor-enforced state machine, and audit logging."""

import contextlib
import uuid

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import register_after_commit
from app.core.exceptions import BusinessRuleViolationException, ForbiddenException, NotFoundException
from app.integrations.notifications.mailer import send_email_notification
from app.modules.bookings.models import Booking
from app.modules.bookings.schemas import BookingResponse
from app.modules.identity.models import User
from app.modules.platform.models import AuditLog
from app.modules.professionals.models import ProfessionalProfile
from app.modules.quotations.models import Quotation

# Allowed transitions keyed by (current_status, target_status) -> allowed booking actor roles
TRANSITION_ROLES: dict[tuple[str, str], set[str]] = {
    ("pending_payment", "confirmed"): {"admin"},  # Normally confirmed via payment capture/webhook
    ("pending_payment", "cancelled"): {"customer", "professional", "admin"},
    ("confirmed", "in_progress"): {"professional", "admin"},
    ("confirmed", "cancelled"): {"customer", "professional", "admin"},
    ("confirmed", "disputed"): {"customer", "professional", "admin"},
    ("in_progress", "completed"): {"customer", "admin"},
    ("in_progress", "cancelled"): {"customer", "professional", "admin"},
    ("in_progress", "disputed"): {"customer", "professional", "admin"},
    ("completed", "disputed"): {"customer", "professional", "admin"},
    ("disputed", "completed"): {"admin"},
    ("disputed", "cancelled"): {"admin"},
}


async def _resolve_booking_actor(db: AsyncSession, booking: Booking, user: User) -> str:
    """Resolve user's exact authority on this booking ('admin', 'customer', 'professional')."""
    if user.role == "admin":
        return "admin"
    if booking.customer_id == user.id:
        return "customer"
    prof_stmt = select(ProfessionalProfile.id).where(
        ProfessionalProfile.id == booking.professional_id,
        ProfessionalProfile.owner_user_id == user.id,
    )
    if (await db.execute(prof_stmt)).scalar_one_or_none():
        return "professional"
    raise ForbiddenException("You do not have permission to access or modify this booking.")


class BookingService:
    @staticmethod
    async def get_booking_by_id(
        db: AsyncSession, booking_id: uuid.UUID, current_user: User | None = None
    ) -> Booking:
        stmt = select(Booking).where(Booking.id == booking_id)
        booking = (await db.execute(stmt)).scalar_one_or_none()
        if not booking:
            raise NotFoundException("Booking", booking_id)

        if current_user:
            await _resolve_booking_actor(db, booking, current_user)
        return booking

    @staticmethod
    async def list_user_bookings(db: AsyncSession, user: User) -> list[Booking]:
        if user.role == "admin":
            stmt = select(Booking).order_by(desc(Booking.created_at))
        elif user.role == "professional":
            prof_stmt = select(ProfessionalProfile.id).where(ProfessionalProfile.owner_user_id == user.id)
            prof_ids = list((await db.execute(prof_stmt)).scalars().all())
            stmt = (
                select(Booking)
                .where((Booking.customer_id == user.id) | (Booking.professional_id.in_(prof_ids)))
                .order_by(desc(Booking.created_at))
            )
        else:
            stmt = select(Booking).where(Booking.customer_id == user.id).order_by(desc(Booking.created_at))

        return list((await db.execute(stmt)).scalars().all())

    @staticmethod
    async def _check_payment_preconditions(db: AsyncSession, booking: Booking) -> None:
        if booking.quotation_id:
            quot = await db.get(Quotation, booking.quotation_id)
            if quot and quot.advance_amount_minor > 0 and (booking.paid_amount_minor or 0) < quot.advance_amount_minor:
                raise BusinessRuleViolationException(
                    "Required advance payment must be captured before starting or completing this booking."
                )

    @staticmethod
    async def update_status(
        db: AsyncSession, booking_id: uuid.UUID, new_status: str, current_user: User
    ) -> Booking:
        if new_status == "completed":
            return await BookingService.complete_booking(db, booking_id, current_user)

        stmt = select(Booking).where(Booking.id == booking_id).with_for_update()
        booking = (await db.execute(stmt)).scalar_one_or_none()
        if not booking:
            raise NotFoundException("Booking", booking_id)

        actor = await _resolve_booking_actor(db, booking, current_user)
        current = booking.booking_status
        allowed_actors = TRANSITION_ROLES.get((current, new_status))
        if not allowed_actors:
            raise BusinessRuleViolationException(
                f"Invalid booking transition from '{current}' to '{new_status}'."
            )
        if actor not in allowed_actors:
            raise ForbiddenException(
                f"Role '{actor}' is not permitted to transition booking from '{current}' to '{new_status}'."
            )

        if new_status == "in_progress":
            await BookingService._check_payment_preconditions(db, booking)

        booking.booking_status = new_status
        db.add(
            AuditLog(
                actor_user_id=current_user.id,
                action="booking_status_changed",
                resource_type="booking",
                resource_id=booking.id,
                metadata_payload={"from": current, "to": new_status, "actor": actor},
            )
        )
        await db.flush()
        return booking

    @staticmethod
    async def complete_booking(
        db: AsyncSession, booking_id: uuid.UUID, current_user: User
    ) -> Booking:
        stmt = select(Booking).where(Booking.id == booking_id).with_for_update()
        booking = (await db.execute(stmt)).scalar_one_or_none()
        if not booking:
            raise NotFoundException("Booking", booking_id)

        actor = await _resolve_booking_actor(db, booking, current_user)
        if actor not in {"customer", "admin"}:
            raise ForbiddenException("Only the booking customer or admin may mark a booking complete.")

        previous_status = booking.booking_status
        if previous_status not in ["confirmed", "in_progress"]:
            raise BusinessRuleViolationException("Only confirmed or in-progress bookings can be completed.")

        await BookingService._check_payment_preconditions(db, booking)

        booking.booking_status = "completed"
        booking.completion_status = "customer_accepted"

        prof = await db.get(ProfessionalProfile, booking.professional_id)
        if prof:
            prof.completed_bookings_count = (prof.completed_bookings_count or 0) + 1

        db.add(
            AuditLog(
                actor_user_id=current_user.id,
                action="booking_completed",
                resource_type="booking",
                resource_id=booking.id,
                metadata_payload={"from": previous_status, "to": "completed", "actor": actor},
            )
        )
        await db.flush()
        if prof:
            pro_owner = await db.get(User, prof.owner_user_id)
            if pro_owner and pro_owner.email:
                pro_email = pro_owner.email
                studio_name = prof.display_name

                async def _notify_complete() -> None:
                    with contextlib.suppress(Exception):
                        await send_email_notification(
                            recipient=pro_email,
                            subject=f"Booking Completed — {studio_name}",
                            body="Customer accepted delivery and marked the booking completed.",
                            event_type="booking_completed",
                        )

                register_after_commit(db, _notify_complete)
        return booking

    @staticmethod
    async def cancel_booking(
        db: AsyncSession, booking_id: uuid.UUID, reason: str, current_user: User
    ) -> Booking:
        stmt = select(Booking).where(Booking.id == booking_id).with_for_update()
        booking = (await db.execute(stmt)).scalar_one_or_none()
        if not booking:
            raise NotFoundException("Booking", booking_id)

        actor = await _resolve_booking_actor(db, booking, current_user)
        previous_status = booking.booking_status
        allowed_actors = TRANSITION_ROLES.get((previous_status, "cancelled"))
        if not allowed_actors:
            raise BusinessRuleViolationException(
                f"Bookings in status '{previous_status}' cannot be cancelled."
            )
        if actor not in allowed_actors:
            raise ForbiddenException("You do not have permission to cancel this booking.")

        booking.booking_status = "cancelled"
        booking.cancellation_reason = reason
        db.add(
            AuditLog(
                actor_user_id=current_user.id,
                action="booking_cancelled",
                resource_type="booking",
                resource_id=booking.id,
                metadata_payload={
                    "from": previous_status,
                    "to": "cancelled",
                    "actor": actor,
                    "reason": reason,
                },
            )
        )
        await db.flush()
        cust = await db.get(User, booking.customer_id)
        if cust and cust.email:
            cust_email = cust.email
            reason_copy = reason

            async def _notify_cancel() -> None:
                with contextlib.suppress(Exception):
                    await send_email_notification(
                        recipient=cust_email,
                        subject="MaanCamera Booking Cancelled",
                        body=f"Your booking has been cancelled. Reason: {reason_copy}",
                        event_type="booking_cancelled",
                    )

            register_after_commit(db, _notify_cancel)
        return booking

    @staticmethod
    async def serialize_bookings(db: AsyncSession, bookings: list[Booking]) -> list[BookingResponse]:
        if not bookings:
            return []
        prof_ids = {b.professional_id for b in bookings}
        cust_ids = {b.customer_id for b in bookings}
        profs = dict(
            (
                await db.execute(
                    select(ProfessionalProfile.id, ProfessionalProfile.display_name).where(
                        ProfessionalProfile.id.in_(prof_ids)
                    )
                )
            ).all()
        )
        custs = dict(
            (await db.execute(select(User.id, User.full_name).where(User.id.in_(cust_ids)))).all()
        )
        result: list[BookingResponse] = []
        for b in bookings:
            dto = BookingResponse.model_validate(b)
            dto.professional_name = profs.get(b.professional_id)
            dto.customer_name = custs.get(b.customer_id)
            result.append(dto)
        return result
