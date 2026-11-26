"""Enquiry service handling creation and multi-recipient distribution."""

import uuid
from typing import List, Optional
from sqlalchemy import select, desc
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.enquiries.models import Enquiry, EnquiryRecipient
from app.modules.enquiries.schemas import EnquiryCreateRequest
from app.modules.professionals.models import ProfessionalProfile
from app.modules.identity.models import User
from app.core.exceptions import NotFoundException, ForbiddenException


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

        await db.commit()
        await db.refresh(enquiry)
        return enquiry

    @staticmethod
    async def get_enquiry_by_id(
        db: AsyncSession, enquiry_id: uuid.UUID, current_user: Optional[User] = None
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
        if current_user and current_user.role != "admin":
            if enquiry.customer_id != current_user.id:
                # Check if user owns a recipient profile
                prof_stmt = select(ProfessionalProfile.id).where(
                    ProfessionalProfile.user_id == current_user.id
                )
                prof_res = await db.execute(prof_stmt)
                user_prof_ids = set(prof_res.scalars().all())
                recipient_prof_ids = {r.professional_id for r in (enquiry.recipients or [])}
                if not (user_prof_ids & recipient_prof_ids):
                    raise ForbiddenException("You do not have permission to view this enquiry.")

        return enquiry

    @staticmethod
    async def list_customer_enquiries(db: AsyncSession, customer_id: uuid.UUID) -> List[Enquiry]:
        stmt = (
            select(Enquiry)
            .options(selectinload(Enquiry.recipients))
            .where(Enquiry.customer_id == customer_id)
            .order_by(desc(Enquiry.created_at))
        )
        res = await db.execute(stmt)
        return list(res.scalars().all())

    @staticmethod
    async def list_professional_enquiries(db: AsyncSession, user_id: uuid.UUID) -> List[Enquiry]:
        prof_stmt = select(ProfessionalProfile.id).where(ProfessionalProfile.user_id == user_id)
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
