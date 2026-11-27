"""Quotation service with versioning and booking creation on acceptance."""

import contextlib
import uuid
from datetime import UTC, date, datetime, timedelta

from sqlalchemy import desc, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import register_after_commit
from app.core.exceptions import BusinessRuleViolationException, ForbiddenException, NotFoundException
from app.integrations.notifications.mailer import send_email_notification
from app.modules.bookings.models import Booking
from app.modules.enquiries.models import Enquiry, EnquiryRecipient
from app.modules.enquiries.service import EnquiryService
from app.modules.identity.models import User
from app.modules.professionals.models import ProfessionalProfile
from app.modules.quotations.models import Quotation
from app.modules.quotations.schemas import QuotationCreateRequest, QuotationResponse, QuotationRevisionRequest


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
        customer = await db.get(User, enquiry.customer_id)
        if customer and customer.email:
            cust_email = customer.email
            studio_name = prof.display_name
            enq_title = enquiry.title

            async def _notify_quote() -> None:
                with contextlib.suppress(Exception):
                    await send_email_notification(
                        recipient=cust_email,
                        subject=f"New Quotation from {studio_name}",
                        body=f"{studio_name} sent a quotation for '{enq_title}'. Log in to review deliverables and accept.",
                        event_type="quotation_received",
                    )

            register_after_commit(db, _notify_quote)
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
        prof_obj = await db.get(ProfessionalProfile, quotation.professional_id)
        if prof_obj:
            pro_owner = await db.get(User, prof_obj.owner_user_id)
            if pro_owner and pro_owner.email:
                pro_email = pro_owner.email
                enq_title = enquiry.title

                async def _notify_accept() -> None:
                    with contextlib.suppress(Exception):
                        await send_email_notification(
                            recipient=pro_email,
                            subject=f"Quotation Accepted: {enq_title}",
                            body=f"Your quotation for '{enq_title}' was accepted and a booking has been created.",
                            event_type="quotation_accepted",
                        )

                register_after_commit(db, _notify_accept)
        return quotation, booking

    @staticmethod
    async def list_by_enquiry(
        db: AsyncSession, enquiry_id: uuid.UUID, current_user: User
    ) -> list[Quotation]:
        enquiry = await EnquiryService.get_enquiry_by_id(db, enquiry_id, current_user)
        stmt = select(Quotation).where(Quotation.enquiry_id == enquiry.id)
        if current_user.role == "professional":
            prof_ids = list(
                (
                    await db.execute(
                        select(ProfessionalProfile.id).where(
                            ProfessionalProfile.owner_user_id == current_user.id
                        )
                    )
                )
                .scalars()
                .all()
            )
            if enquiry.customer_id != current_user.id:
                stmt = stmt.where(Quotation.professional_id.in_(prof_ids))
        stmt = stmt.order_by(desc(Quotation.created_at), desc(Quotation.version_number))
        return list((await db.execute(stmt)).scalars().all())

    @staticmethod
    async def list_user_quotations(db: AsyncSession, current_user: User) -> list[Quotation]:
        if current_user.role == "admin":
            stmt = select(Quotation).order_by(desc(Quotation.created_at))
        elif current_user.role == "professional":
            prof_ids = list(
                (
                    await db.execute(
                        select(ProfessionalProfile.id).where(
                            ProfessionalProfile.owner_user_id == current_user.id
                        )
                    )
                )
                .scalars()
                .all()
            )
            enq_ids = list(
                (
                    await db.execute(
                        select(Enquiry.id).where(Enquiry.customer_id == current_user.id)
                    )
                )
                .scalars()
                .all()
            )
            clauses = []
            if prof_ids:
                clauses.append(Quotation.professional_id.in_(prof_ids))
            if enq_ids:
                clauses.append(Quotation.enquiry_id.in_(enq_ids))
            if not clauses:
                return []
            stmt = select(Quotation).where(or_(*clauses)).order_by(desc(Quotation.created_at))
        else:
            stmt = (
                select(Quotation)
                .join(Enquiry, Enquiry.id == Quotation.enquiry_id)
                .where(Enquiry.customer_id == current_user.id)
                .order_by(desc(Quotation.created_at))
            )
        return list((await db.execute(stmt)).scalars().all())

    @staticmethod
    async def serialize_quotations(
        db: AsyncSession, quotations: list[Quotation]
    ) -> list[QuotationResponse]:
        if not quotations:
            return []
        prof_ids = {q.professional_id for q in quotations}
        enq_ids = {q.enquiry_id for q in quotations}
        profs = dict(
            (
                await db.execute(
                    select(ProfessionalProfile.id, ProfessionalProfile.display_name).where(
                        ProfessionalProfile.id.in_(prof_ids)
                    )
                )
            ).all()
        )
        enqs = dict(
            (await db.execute(select(Enquiry.id, Enquiry.title).where(Enquiry.id.in_(enq_ids)))).all()
        )
        result: list[QuotationResponse] = []
        for q in quotations:
            dto = QuotationResponse.model_validate(q)
            dto.professional_name = profs.get(q.professional_id)
            dto.enquiry_title = enqs.get(q.enquiry_id)
            result.append(dto)
        return result
