"""Portfolio and Media upload service layer."""

import contextlib
import os
import re
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import (
    BusinessRuleViolationException,
    ForbiddenException,
    NotFoundException,
)
from app.integrations.storage.s3 import storage_service
from app.modules.identity.models import User
from app.modules.portfolios.models import MediaAsset, Portfolio, Project
from app.modules.portfolios.schemas import (
    CompleteMediaUploadRequest,
    ProjectCreateRequest,
    UploadUrlRequest,
    UploadUrlResponse,
)
from app.modules.professionals.models import ProfessionalProfile
from app.workers.celery_app import process_uploaded_media


class PortfolioService:
    @staticmethod
    async def get_projects_by_portfolio(db: AsyncSession, portfolio_id: uuid.UUID) -> list[Project]:
        stmt = (
            select(Project)
            .options(selectinload(Project.media_assets))
            .where(Project.portfolio_id == portfolio_id)
            .order_by(Project.created_at.desc())
        )
        res = await db.execute(stmt)
        return list(res.scalars().all())

    @staticmethod
    async def get_project_by_id(db: AsyncSession, project_id: uuid.UUID) -> Project:
        stmt = (
            select(Project)
            .options(selectinload(Project.media_assets))
            .where(Project.id == project_id)
        )
        res = await db.execute(stmt)
        proj = res.scalar_one_or_none()
        if not proj:
            raise NotFoundException("Project", project_id)
        return proj

    @staticmethod
    async def create_project(db: AsyncSession, current_user: User, req: ProjectCreateRequest) -> Project:
        portfolio = await db.get(Portfolio, req.portfolio_id)
        if not portfolio:
            raise NotFoundException("Portfolio", req.portfolio_id)

        if current_user.role != "admin":
            prof = await db.get(ProfessionalProfile, portfolio.professional_id)
            if not prof or prof.owner_user_id != current_user.id:
                raise ForbiddenException("You do not have permission to add projects to this portfolio.")

        clean_slug_base = re.sub(r"[^a-z0-9]+", "-", req.title.lower()).strip("-") or "project"
        slug = f"{clean_slug_base}-{uuid.uuid4().hex[:6]}"

        project = Project(
            portfolio_id=req.portfolio_id,
            category_id=req.category_id,
            title=req.title,
            slug=slug,
            style=req.style,
            location=req.location,
            project_date=req.project_date,
            description=req.description,
            tags=req.tags,
            publication_status="published",
        )
        db.add(project)
        await db.commit()
        return await PortfolioService.get_project_by_id(db, project.id)

    @staticmethod
    async def generate_upload_url(current_user: User, req: UploadUrlRequest) -> UploadUrlResponse:
        _, ext = os.path.splitext(req.filename.strip().lower())
        result = await storage_service.generate_presigned_upload_url(
            owner_user_id=current_user.id,
            extension=ext,
            content_type=req.mime_type,
            file_size_bytes=req.file_size_bytes,
            is_public=req.is_public,
        )
        return UploadUrlResponse(**result)

    @staticmethod
    async def complete_upload(
        db: AsyncSession, current_user: User, req: CompleteMediaUploadRequest
    ) -> MediaAsset:
        project = await db.get(Project, req.project_id)
        if not project:
            raise NotFoundException("Project", req.project_id)

        if current_user.role != "admin":
            portfolio = await db.get(Portfolio, project.portfolio_id)
            prof = await db.get(ProfessionalProfile, portfolio.professional_id) if portfolio else None
            if not prof or prof.owner_user_id != current_user.id:
                raise ForbiddenException("You do not have permission to add media to this project.")

            expected_public_prefix = f"public/{current_user.id}/"
            expected_private_prefix = f"private/{current_user.id}/"
            if not (
                req.storage_key.startswith(expected_public_prefix)
                or req.storage_key.startswith(expected_private_prefix)
            ):
                raise BusinessRuleViolationException("Invalid upload storage key ownership prefix.")

        asset = MediaAsset(
            project_id=req.project_id,
            storage_key=req.storage_key,
            public_url=None,  # Worker publishes public WebP URL after Pillow verification & EXIF stripping
            media_type=req.media_type,
            mime_type=req.mime_type,
            file_size_bytes=req.file_size_bytes,
            checksum=req.checksum,
            width=req.width,
            height=req.height,
            processing_status="pending",
        )
        db.add(asset)
        await db.flush()

        if not project.cover_asset_id:
            project.cover_asset_id = asset.id
            await db.flush()

        await db.commit()
        await db.refresh(asset)

        # Enqueue async Pillow validation + EXIF stripping + WebP generation
        with contextlib.suppress(Exception):
            process_uploaded_media.delay(str(asset.id), asset.storage_key)

        return asset
