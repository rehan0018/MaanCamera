"""Quotation service with versioning and booking creation on acceptance."""

import uuid
from datetime import date
from typing import List, Optional, Tuple
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.quotations.models import Quotation
from app.modules.quotations.schemas import QuotationCreateRequest, QuotationRevisionRequest
from app.modules.enquiries.models import Enquiry
from app.modules.bookings.models import Booking
from app.core.exceptions import NotFoundException, BusinessRuleViolationException


class QuotationService:
    @staticmethod
    async def create_quotation(db: AsyncSession, professional_id: uuid.UUID, req: QuotationCreateRequest) -> Quotation:
        # Check enquiry exists
        stmt = select(Enquiry).where(Enquiry.id == req.enquiry_id)
        res = await db.execute(stmt)
        enquiry = res.scalar_one_or_none()
        if not enquiry:
            raise NotFoundException("Enquiry not found.")

        quotation = Quotation(
            enquiry_id=req.enquiry_id,
            professional_id=professional_id,
            version_number=1,
            total_amount_minor=req.total_amount_minor,
            currency_code=req.currency_code,
            advance_amount_minor=req.advance_amount_minor,
            scope_of_work=req.scope_of_work,
            deliverables=req.deliverables,
            terms=req.terms,
            valid_until=req.valid_until,
            status="sent",
        )
        db.add(quotation)
        await db.commit()
        await db.refresh(quotation)
        return quotation

    @staticmethod
    async def revise_quotation(
        db: AsyncSession, quotation_id: uuid.UUID, req: QuotationRevisionRequest
    ) -> Quotation:
        stmt = select(Quotation).where(Quotation.id == quotation_id)
        res = await db.execute(stmt)
        old_quotation = res.scalar_one_or_none()
        if not old_quotation:
            raise NotFoundException("Original quotation not found.")

        if old_quotation.status in ["accepted", "rejected"]:
            raise BusinessRuleViolationException("Cannot revise an accepted or rejected quotation.")

        # Supersede old
        old_quotation.status = "superseded"

        # Create new revision
        new_quotation = Quotation(
            enquiry_id=old_quotation.enquiry_id,
            professional_id=old_quotation.professional_id,
            version_number=old_quotation.version_number + 1,
            total_amount_minor=req.total_amount_minor,
            currency_code=old_quotation.currency_code,
            advance_amount_minor=req.advance_amount_minor,
            scope_of_work=req.scope_of_work,
            deliverables=req.deliverables,
            terms=req.terms,
            valid_until=req.valid_until,
            status="sent",
        )
        db.add(new_quotation)
        await db.commit()
        await db.refresh(new_quotation)
        return new_quotation

    @staticmethod
    async def accept_quotation(db: AsyncSession, quotation_id: uuid.UUID, customer_id: uuid.UUID) -> Tuple[Quotation, Booking]:
        stmt = select(Quotation).where(Quotation.id == quotation_id)
        res = await db.execute(stmt)
        quotation = res.scalar_one_or_none()
        if not quotation:
            raise NotFoundException("Quotation not found.")

        if quotation.status != "sent":
            raise BusinessRuleViolationException(f"Quotation cannot be accepted from state '{quotation.status}'.")

        # Get enquiry
        enquiry_stmt = select(Enquiry).where(Enquiry.id == quotation.enquiry_id)
        enquiry_res = await db.execute(enquiry_stmt)
        enquiry = enquiry_res.scalar_one_or_none()
        if not enquiry or enquiry.customer_id != customer_id:
            raise BusinessRuleViolationException("Only the enquiry customer may accept this quotation.")

        quotation.status = "accepted"

        initial_booking_status = "pending_deposit" if quotation.advance_amount_minor > 0 else "confirmed"

        booking = Booking(
            enquiry_id=quotation.enquiry_id,
            quotation_id=quotation.id,
            customer_id=customer_id,
            professional_id=quotation.professional_id,
            shoot_date=enquiry.shoot_date or date.today(),
            location=enquiry.location or "Client Designated Venue",
            agreed_amount_minor=quotation.total_amount_minor,
            currency_code=quotation.currency_code,
            booking_status=initial_booking_status,
            completion_status="pending",
        )
        db.add(booking)
        await db.commit()
        await db.refresh(quotation)
        await db.refresh(booking)
        return quotation, booking
