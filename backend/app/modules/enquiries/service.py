"""Enquiry service handling creation and multi-recipient distribution."""

import uuid
from typing import List, Optional
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.enquiries.models import Enquiry, EnquiryRecipient
from app.modules.enquiries.schemas import EnquiryCreateRequest
from app.core.exceptions import NotFoundException


class EnquiryService:
    @staticmethod
    async def create_enquiry(db: AsyncSession, customer_id: uuid.UUID, req: EnquiryCreateRequest) -> Enquiry:
        enquiry = Enquiry(
            customer_id=customer_id,
            category_id=req.category_id,
            title=req.title,
            description=req.description,
            shoot_date=req.shoot_date,
            location=req.location,
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
                recipient_status="pending",
            )
            db.add(recipient)

        await db.commit()
        await db.refresh(enquiry)
        return enquiry

    @staticmethod
    async def get_enquiry_by_id(db: AsyncSession, enquiry_id: uuid.UUID) -> Enquiry:
        stmt = select(Enquiry).where(Enquiry.id == enquiry_id)
        res = await db.execute(stmt)
        enquiry = res.scalar_one_or_none()
        if not enquiry:
            raise NotFoundException("Enquiry not found.")
        return enquiry

    @staticmethod
    async def list_customer_enquiries(db: AsyncSession, customer_id: uuid.UUID) -> List[Enquiry]:
        stmt = select(Enquiry).where(Enquiry.customer_id == customer_id).order_by(desc(Enquiry.created_at))
        res = await db.execute(stmt)
        return list(res.scalars().all())

    @staticmethod
    async def list_professional_enquiries(db: AsyncSession, professional_id: uuid.UUID) -> List[Enquiry]:
        stmt = select(Enquiry).join(EnquiryRecipient).where(
            EnquiryRecipient.professional_id == professional_id
        ).order_by(desc(Enquiry.created_at))
        res = await db.execute(stmt)
        return list(res.scalars().all())
