"""HTTP endpoints for professionals, categories, and services."""

import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import NotFoundException
from app.core.permissions import require_professional
from app.core.responses import success_response
from app.modules.identity.models import User
from app.modules.identity.router import get_current_user
from app.modules.professionals.schemas import (
    CategoryResponse,
    ProfessionalProfileResponse,
    ProfileCreateRequest,
    ProfileUpdateRequest,
    ServiceCreateRequest,
    ServiceResponse,
)
from app.modules.professionals.service import ProfessionalService

router = APIRouter(prefix="", tags=["Professionals & Marketplace"])


@router.get("/categories")
async def get_categories(db: AsyncSession = Depends(get_db)):
    cats = await ProfessionalService.get_categories(db)
    return success_response(
        data=[CategoryResponse.model_validate(c).model_dump(mode="json") for c in cats]
    )


@router.get("/professionals/me")
async def get_my_profile(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    profile = await ProfessionalService.get_by_user_id(db, current_user.id)
    if not profile:
        return success_response(data=None)
    return success_response(
        data=ProfessionalProfileResponse.model_validate(profile).model_dump(mode="json")
    )


@router.patch("/professionals/me")
async def update_my_profile(
    req: ProfileUpdateRequest,
    current_user: User = Depends(require_professional),
    db: AsyncSession = Depends(get_db),
):
    profile = await ProfessionalService.get_by_user_id(db, current_user.id)
    if not profile:
        raise NotFoundException("ProfessionalProfile", current_user.id)
    updated = await ProfessionalService.update_profile(db, profile.id, current_user, req)
    return success_response(
        data=ProfessionalProfileResponse.model_validate(updated).model_dump(mode="json")
    )


@router.post("/professionals/me/services", status_code=status.HTTP_201_CREATED)
async def create_my_service(
    req: ServiceCreateRequest,
    current_user: User = Depends(require_professional),
    db: AsyncSession = Depends(get_db),
):
    service = await ProfessionalService.create_service(db, current_user, req)
    return success_response(
        data=ServiceResponse.model_validate(service).model_dump(mode="json"),
        status_code=status.HTTP_201_CREATED,
    )


@router.get("/professionals/{id}")
async def get_professional(id: str, db: AsyncSession = Depends(get_db)):
    profile = await ProfessionalService.get_by_id_or_slug(db, id)
    return success_response(
        data=ProfessionalProfileResponse.model_validate(profile).model_dump(mode="json")
    )


@router.post("/professionals", status_code=status.HTTP_201_CREATED)
async def create_professional_profile(
    req: ProfileCreateRequest,
    current_user: User = Depends(require_professional),
    db: AsyncSession = Depends(get_db),
):
    profile = await ProfessionalService.create_profile(db, current_user.id, req)
    return success_response(
        data=ProfessionalProfileResponse.model_validate(profile).model_dump(mode="json"),
        status_code=status.HTTP_201_CREATED,
    )


@router.patch("/professionals/{id}")
async def update_professional_profile(
    id: uuid.UUID,
    req: ProfileUpdateRequest,
    current_user: User = Depends(require_professional),
    db: AsyncSession = Depends(get_db),
):
    updated = await ProfessionalService.update_profile(db, id, current_user, req)
    return success_response(
        data=ProfessionalProfileResponse.model_validate(updated).model_dump(mode="json")
    )


@router.delete("/professionals/{id}")
async def delete_professional_profile(
    id: uuid.UUID,
    current_user: User = Depends(require_professional),
    db: AsyncSession = Depends(get_db),
):
    await ProfessionalService.delete_profile(db, id, current_user)
    return success_response(data={"deleted": True})
