"""Service layer for professional profile retrieval, creation, and services."""

import uuid
from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.exceptions import NotFoundException
from app.modules.professionals.models import (
    ProfessionalProfile,
    Category,
    Service,
)
from app.modules.professionals.schemas import ProfileCreateRequest


class ProfessionalService:
    @staticmethod
    async def get_by_id_or_slug(db: AsyncSession, identifier: str) -> ProfessionalProfile:
        stmt = (
            select(ProfessionalProfile)
            .options(
                selectinload(ProfessionalProfile.skills),
                selectinload(ProfessionalProfile.equipment_list),
                selectinload(ProfessionalProfile.services).selectinload(Service.packages),
            )
        )
        try:
            val_uuid = uuid.UUID(identifier)
            stmt = stmt.where(ProfessionalProfile.id == val_uuid)
        except ValueError:
            stmt = stmt.where(ProfessionalProfile.slug == identifier)

        res = await db.execute(stmt)
        prof = res.scalar_one_or_none()
        if not prof:
            raise NotFoundException("ProfessionalProfile", identifier)
        return prof

    @staticmethod
    async def get_by_user_id(db: AsyncSession, user_id: uuid.UUID) -> Optional[ProfessionalProfile]:
        stmt = (
            select(ProfessionalProfile)
            .options(
                selectinload(ProfessionalProfile.skills),
                selectinload(ProfessionalProfile.equipment_list),
                selectinload(ProfessionalProfile.services).selectinload(Service.packages),
            )
            .where(ProfessionalProfile.owner_user_id == user_id)
        )
        res = await db.execute(stmt)
        return res.scalar_one_or_none()

    @staticmethod
    async def get_categories(db: AsyncSession) -> List[Category]:
        stmt = select(Category).where(Category.is_active.is_(True)).order_by(Category.display_order.asc())
        res = await db.execute(stmt)
        return list(res.scalars().all())

    @staticmethod
    async def create_profile(db: AsyncSession, user_id: uuid.UUID, req: ProfileCreateRequest) -> ProfessionalProfile:
        slug = req.display_name.lower().replace(" ", "-").replace("&", "and")
        # Ensure unique slug
        unique_slug = f"{slug}-{uuid.uuid4().hex[:6]}"
        profile = ProfessionalProfile(
            owner_user_id=user_id,
            display_name=req.display_name,
            slug=unique_slug,
            headline=req.headline,
            biography=req.biography,
            professional_type=req.professional_type,
            years_experience=req.years_experience,
            base_city=req.base_city,
            state=req.state,
            service_radius_km=req.service_radius_km,
            travel_available=req.travel_available,
        )
        db.add(profile)
        await db.flush()
        return await ProfessionalService.get_by_id_or_slug(db, str(profile.id))
