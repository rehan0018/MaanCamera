"""Enquiry service handling creation and multi-recipient distribution."""

import contextlib
import uuid

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import register_after_commit
from app.core.exceptions import ForbiddenException, NotFoundException
from app.integrations.notifications.mailer import send_email_notification
from app.modules.enquiries.models import Enquiry, EnquiryRecipient
from app.modules.enquiries.schemas import EnquiryCreateRequest, EnquiryResponse
from app.modules.identity.models import User
from app.modules.professionals.models import Category, ProfessionalProfile
from app.modules.quotations.models import Quotation


class EnquiryService:
    @staticmethod
    async def create_enquiry(db: AsyncSession, customer_id: uuid.UUID, req: EnquiryCreateRequest) -> Enquiry:
        enquiry = Enquiry(
            customer_id=customer_id,
            category_id=req.category_id,
            title=req.title,
            description=req.description,
            shoot_date=req.shoot_date,
            duration_days=req.duration_days,
            location=req.location,
            city=req.city,
            budget_min_minor=req.budget_min_minor,
            budget_max_minor=req.budget_max_minor,
            currency_code=req.currency_code,
            status="open",
        )
        db.add(enquiry)
        await db.flush()

        for prof_id in req.professional_ids:
            recipient = EnquiryRecipient(
                enquiry_id=enquiry.id,
                professional_id=prof_id,
                recipient_status="sent",
            )
            db.add(recipient)

        await db.flush()
        loaded = await EnquiryService.get_enquiry_by_id(db, enquiry.id)

        owner_emails_raw = list(
            (
                await db.execute(
                    select(User.email)
                    .join(ProfessionalProfile, ProfessionalProfile.owner_user_id == User.id)
                    .where(ProfessionalProfile.id.in_(req.professional_ids), User.email.is_not(None))
                )
            )
            .scalars()
            .all()
        )
        owner_emails = [email for email in owner_emails_raw if email]
        enquiry_title = loaded.title
        enquiry_city = loaded.city

        async def _notify_recipients() -> None:
            for email in owner_emails:
                with contextlib.suppress(Exception):
                    await send_email_notification(
                        recipient=email,
                        subject=f"New MaanCamera Enquiry: {enquiry_title}",
                        body=f"You received a new shoot enquiry '{enquiry_title}' in {enquiry_city}. Log in to review and send a quotation.",
                        event_type="enquiry_received",
                    )

        if owner_emails:
            register_after_commit(db, _notify_recipients)

        return loaded

    @staticmethod
    async def get_enquiry_by_id(
        db: AsyncSession, enquiry_id: uuid.UUID, current_user: User | None = None
    ) -> Enquiry:
        stmt = (
            select(Enquiry)
            .options(selectinload(Enquiry.recipients))
            .where(Enquiry.id == enquiry_id)
        )
        res = await db.execute(stmt)
        enquiry = res.scalar_one_or_none()
        if not enquiry:
            raise NotFoundException("Enquiry", enquiry_id)

        # IDOR protection: only customer who created it, a recipient professional, or admin
        if current_user and current_user.role != "admin" and enquiry.customer_id != current_user.id:
            # Check if user owns a recipient profile
            prof_stmt = select(ProfessionalProfile.id).where(
                ProfessionalProfile.owner_user_id == current_user.id
            )
            prof_res = await db.execute(prof_stmt)
            user_prof_ids = set(prof_res.scalars().all())
            recipient_prof_ids = {r.professional_id for r in (enquiry.recipients or [])}
            if not (user_prof_ids & recipient_prof_ids):
                raise ForbiddenException("You do not have permission to view this enquiry.")

        return enquiry

    @staticmethod
    async def list_customer_enquiries(db: AsyncSession, customer_id: uuid.UUID) -> list[Enquiry]:
        stmt = (
            select(Enquiry)
            .options(selectinload(Enquiry.recipients))
            .where(Enquiry.customer_id == customer_id)
            .order_by(desc(Enquiry.created_at))
        )
        res = await db.execute(stmt)
        return list(res.scalars().all())

    @staticmethod
    async def list_professional_enquiries(db: AsyncSession, user_id: uuid.UUID) -> list[Enquiry]:
        prof_stmt = select(ProfessionalProfile.id).where(ProfessionalProfile.owner_user_id == user_id)
        prof_res = await db.execute(prof_stmt)
        prof_ids = list(prof_res.scalars().all())
        if not prof_ids:
            return []

        stmt = (
            select(Enquiry)
            .options(selectinload(Enquiry.recipients))
            .join(EnquiryRecipient, EnquiryRecipient.enquiry_id == Enquiry.id)
            .where(EnquiryRecipient.professional_id.in_(prof_ids))
            .order_by(desc(Enquiry.created_at))
        )
        res = await db.execute(stmt)
        return list(res.scalars().all())

    @staticmethod
    async def serialize_enquiries(db: AsyncSession, enquiries: list[Enquiry]) -> list[EnquiryResponse]:
        if not enquiries:
            return []
        cat_ids = {e.category_id for e in enquiries}
        cust_ids = {e.customer_id for e in enquiries}
        enq_ids = [e.id for e in enquiries]

        cats = dict(
            (await db.execute(select(Category.id, Category.name).where(Category.id.in_(cat_ids)))).all()
        )
        customers = dict(
            (await db.execute(select(User.id, User.full_name).where(User.id.in_(cust_ids)))).all()
        )
        quote_counts = dict(
            (
                await db.execute(
                    select(Quotation.enquiry_id, func.count(Quotation.id))
                    .where(Quotation.enquiry_id.in_(enq_ids), Quotation.status != "revised")
                    .group_by(Quotation.enquiry_id)
                )
            ).all()
        )

        result: list[EnquiryResponse] = []
        for e in enquiries:
            dto = EnquiryResponse.model_validate(e)
            dto.category_name = cats.get(e.category_id)
            dto.customer_name = customers.get(e.customer_id)
            dto.quotations_count = int(quote_counts.get(e.id, 0))
            result.append(dto)
        return result
