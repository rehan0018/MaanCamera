"""Quotation service with versioning and booking creation on acceptance."""

import uuid
from datetime import UTC, date, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BusinessRuleViolationException, ForbiddenException, NotFoundException
from app.modules.bookings.models import Booking
from app.modules.enquiries.models import Enquiry, EnquiryRecipient
from app.modules.identity.models import User
from app.modules.professionals.models import ProfessionalProfile
from app.modules.quotations.models import Quotation
from app.modules.quotations.schemas import QuotationCreateRequest, QuotationRevisionRequest


class QuotationService:
    @staticmethod
    async def create_quotation(
        db: AsyncSession, current_user: User, req: QuotationCreateRequest
    ) -> Quotation:
        # Check enquiry exists
        stmt = select(Enquiry).where(Enquiry.id == req.enquiry_id)
        res = await db.execute(stmt)
        enquiry = res.scalar_one_or_none()
        if not enquiry:
            raise NotFoundException("Enquiry", req.enquiry_id)

        # Resolve quoting professional profile for current_user
        prof_stmt = select(ProfessionalProfile).where(ProfessionalProfile.owner_user_id == current_user.id)
        if req.professional_id and current_user.role == "admin":
            prof_stmt = select(ProfessionalProfile).where(ProfessionalProfile.id == req.professional_id)
        elif req.professional_id:
            prof_stmt = prof_stmt.where(ProfessionalProfile.id == req.professional_id)

        prof_res = await db.execute(prof_stmt)
        prof = prof_res.scalar_one_or_none()
        if not prof:
            raise ForbiddenException("You must have a professional profile to create quotations.")

        # Business Rule: advance <= total
        if req.advance_amount_minor > req.total_amount_minor:
            raise BusinessRuleViolationException("Advance amount cannot exceed total agreed amount.")

        # Verify professional was an intended recipient of the enquiry
        recip_stmt = select(EnquiryRecipient).where(
            EnquiryRecipient.enquiry_id == enquiry.id,
            EnquiryRecipient.professional_id == prof.id,
        )
        recip_res = await db.execute(recip_stmt)
        recipient = recip_res.scalar_one_or_none()
        if not recipient and current_user.role != "admin":
            raise BusinessRuleViolationException("You were not invited to quote on this enquiry.")

        valid_until = req.valid_until or (datetime.now(UTC) + timedelta(days=7))
        if valid_until <= datetime.now(UTC):
            raise BusinessRuleViolationException("Quotation expiration date must be in the future.")

        quotation = Quotation(
            enquiry_id=req.enquiry_id,
            professional_id=prof.id,
            version_number=1,
            total_amount_minor=req.total_amount_minor,
            currency_code=req.currency_code or "INR",
            advance_amount_minor=req.advance_amount_minor,
            scope_of_work=req.scope_of_work,
            deliverables=req.deliverables if isinstance(req.deliverables, list) else ([req.deliverables] if req.deliverables else []),
            terms=req.terms,
            valid_until=valid_until,
            status="sent",
        )
        db.add(quotation)

        if recipient and recipient.recipient_status == "sent":
            recipient.recipient_status = "quoted"

        await db.flush()
        return quotation

    @staticmethod
    async def revise_quotation(
        db: AsyncSession, quotation_id: uuid.UUID, current_user: User, req: QuotationRevisionRequest
    ) -> Quotation:
        stmt = select(Quotation).where(Quotation.id == quotation_id)
        res = await db.execute(stmt)
        old_quotation = res.scalar_one_or_none()
        if not old_quotation:
            raise NotFoundException("Quotation", quotation_id)

        # Check ownership
        if current_user.role != "admin":
            prof_stmt = select(ProfessionalProfile).where(
                ProfessionalProfile.id == old_quotation.professional_id,
                ProfessionalProfile.owner_user_id == current_user.id,
            )
            prof_res = await db.execute(prof_stmt)
            if not prof_res.scalar_one_or_none():
                raise ForbiddenException("You do not have permission to revise this quotation.")

        if old_quotation.status in ["accepted", "rejected", "expired"]:
            raise BusinessRuleViolationException(f"Cannot revise quotation in '{old_quotation.status}' status.")

        if req.advance_amount_minor > req.total_amount_minor:
            raise BusinessRuleViolationException("Advance amount cannot exceed total agreed amount.")

        valid_until = req.valid_until or old_quotation.valid_until
        if valid_until <= datetime.now(UTC):
            raise BusinessRuleViolationException("Quotation expiration date must be in the future.")

        # Mark previous version revised (matching schema check constraint!)
        old_quotation.status = "revised"

        # Create new revision
        new_quotation = Quotation(
            enquiry_id=old_quotation.enquiry_id,
            professional_id=old_quotation.professional_id,
            version_number=old_quotation.version_number + 1,
            total_amount_minor=req.total_amount_minor,
            currency_code=old_quotation.currency_code,
            advance_amount_minor=req.advance_amount_minor,
            scope_of_work=req.scope_of_work,
            deliverables=req.deliverables if isinstance(req.deliverables, list) else ([req.deliverables] if req.deliverables else old_quotation.deliverables),
            terms=req.terms or old_quotation.terms,
            valid_until=valid_until,
            status="sent",
        )
        db.add(new_quotation)
        await db.flush()
        return new_quotation

    @staticmethod
    async def accept_quotation(
        db: AsyncSession, quotation_id: uuid.UUID, customer_id: uuid.UUID
    ) -> tuple[Quotation, Booking]:
        stmt = select(Quotation).where(Quotation.id == quotation_id)
        res = await db.execute(stmt)
        quotation = res.scalar_one_or_none()
        if not quotation:
            raise NotFoundException("Quotation", quotation_id)

        if quotation.status != "sent":
            raise BusinessRuleViolationException(f"Quotation cannot be accepted from state '{quotation.status}'.")

        # Get enquiry
        enquiry_stmt = select(Enquiry).where(Enquiry.id == quotation.enquiry_id)
        enquiry_res = await db.execute(enquiry_stmt)
        enquiry = enquiry_res.scalar_one_or_none()
        if not enquiry or (enquiry.customer_id != customer_id):
            raise ForbiddenException("Only the enquiry customer may accept this quotation.")

        quotation.status = "accepted"
        enquiry.status = "booked"

        initial_booking_status = "pending_payment" if quotation.advance_amount_minor > 0 else "confirmed"

        booking = Booking(
            enquiry_id=quotation.enquiry_id,
            quotation_id=quotation.id,
            customer_id=customer_id,
            professional_id=quotation.professional_id,
            shoot_date=enquiry.shoot_date or date.today(),
            location=enquiry.location or "Client Designated Venue",
            agreed_amount_minor=quotation.total_amount_minor,
            paid_amount_minor=0,
            currency_code=quotation.currency_code,
            booking_status=initial_booking_status,
            completion_status="pending",
        )
        db.add(booking)
        await db.flush()
        return quotation, booking
