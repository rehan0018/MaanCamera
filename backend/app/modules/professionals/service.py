"""Service layer for professional profile retrieval, creation, updates, and services."""

import re
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import (
    BusinessRuleViolationException,
    ConflictException,
    ForbiddenException,
    NotFoundException,
)
from app.modules.identity.models import User
from app.modules.professionals.models import Category, ProfessionalProfile, Service
from app.modules.professionals.schemas import (
    ProfileCreateRequest,
    ProfileUpdateRequest,
    ServiceCreateRequest,
)


class ProfessionalService:
    @staticmethod
    async def get_by_id_or_slug(
        db: AsyncSession,
        identifier: str,
        current_user: User | None = None,
    ) -> ProfessionalProfile:
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
        if prof.profile_visibility == "private" and (
            not current_user or (current_user.role != "admin" and prof.owner_user_id != current_user.id)
        ):
            raise ForbiddenException("This professional profile is currently private.")
        return prof

    @staticmethod
    async def get_by_user_id(db: AsyncSession, user_id: uuid.UUID) -> ProfessionalProfile | None:
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
    async def get_categories(db: AsyncSession) -> list[Category]:
        stmt = select(Category).where(Category.is_active.is_(True)).order_by(Category.display_order.asc())
        res = await db.execute(stmt)
        return list(res.scalars().all())

    @staticmethod
    async def create_profile(
        db: AsyncSession, user_id: uuid.UUID, req: ProfileCreateRequest
    ) -> ProfessionalProfile:
        existing = await ProfessionalService.get_by_user_id(db, user_id)
        if existing:
            raise ConflictException("A professional profile already exists for this user.")

        slug_base = re.sub(r"[^a-z0-9]+", "-", req.display_name.lower()).strip("-") or "professional"
        unique_slug = f"{slug_base}-{uuid.uuid4().hex[:6]}"
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
            profile_visibility="private",
            onboarding_completed=False,
        )
        db.add(profile)
        await db.flush()
        return await ProfessionalService.get_by_id_or_slug(
            db, str(profile.id), current_user=await db.get(User, user_id)
        )

    @staticmethod
    async def update_profile(
        db: AsyncSession,
        profile_id: uuid.UUID,
        current_user: User,
        req: ProfileUpdateRequest,
    ) -> ProfessionalProfile:
        stmt = select(ProfessionalProfile).where(ProfessionalProfile.id == profile_id)
        res = await db.execute(stmt)
        profile = res.scalar_one_or_none()
        if not profile:
            raise NotFoundException("ProfessionalProfile", profile_id)

        if current_user.role != "admin" and profile.owner_user_id != current_user.id:
            raise ForbiddenException("You do not have permission to update this professional profile.")

        updates = req.model_dump(exclude_unset=True)
        if updates.get("profile_visibility") == "public" and not profile.onboarding_completed:
            raise BusinessRuleViolationException(
                "Add at least one active service before making your profile public."
            )
        for field, value in updates.items():
            setattr(profile, field, value)

        await db.flush()
        return await ProfessionalService.get_by_id_or_slug(db, str(profile.id), current_user=current_user)

    @staticmethod
    async def delete_profile(
        db: AsyncSession,
        profile_id: uuid.UUID,
        current_user: User,
    ) -> bool:
        stmt = select(ProfessionalProfile).where(ProfessionalProfile.id == profile_id)
        res = await db.execute(stmt)
        profile = res.scalar_one_or_none()
        if not profile:
            raise NotFoundException("ProfessionalProfile", profile_id)

        if current_user.role != "admin" and profile.owner_user_id != current_user.id:
            raise ForbiddenException("You do not have permission to delete this professional profile.")

        await db.delete(profile)
        await db.flush()
        return True

    @staticmethod
    async def create_service(
        db: AsyncSession,
        current_user: User,
        req: ServiceCreateRequest,
    ) -> Service:
        profile = await ProfessionalService.get_by_user_id(db, current_user.id)
        if not profile:
            raise ForbiddenException("You must create a professional profile before adding services.")

        cat = await db.get(Category, req.category_id)
        if not cat:
            raise NotFoundException("Category", req.category_id)

        service = Service(
            professional_id=profile.id,
            category_id=req.category_id,
            name=req.name,
            description=req.description,
            pricing_type=req.pricing_type,
            starting_price_minor=req.starting_price_minor,
            currency_code=req.currency_code,
            is_active=True,
        )
        db.add(service)
        if not profile.onboarding_completed:
            profile.onboarding_completed = True
            if profile.profile_visibility == "private":
                profile.profile_visibility = "public"
        await db.flush()
        stmt = select(Service).options(selectinload(Service.packages)).where(Service.id == service.id)
        res = await db.execute(stmt)
        return res.scalar_one()
