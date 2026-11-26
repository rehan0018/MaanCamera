"""Portfolio and Media upload service layer."""

import re
import uuid
from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.exceptions import NotFoundException, ForbiddenException, BusinessRuleViolationException
from app.integrations.storage.s3 import storage_service
from app.modules.portfolios.models import Portfolio, Project, MediaAsset
from app.modules.professionals.models import ProfessionalProfile
from app.modules.identity.models import User
from app.modules.portfolios.schemas import (
    ProjectCreateRequest,
    UploadUrlRequest,
    UploadUrlResponse,
    CompleteMediaUploadRequest,
)


class PortfolioService:
    @staticmethod
    async def get_projects_by_portfolio(db: AsyncSession, portfolio_id: uuid.UUID) -> List[Project]:
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
        # Check portfolio exists and user has authorization
        portfolio = await db.get(Portfolio, req.portfolio_id)
        if not portfolio:
            raise NotFoundException("Portfolio", req.portfolio_id)

        if current_user.role != "admin":
            prof = await db.get(ProfessionalProfile, portfolio.professional_id)
            if not prof or prof.user_id != current_user.id:
                raise ForbiddenException("You do not have permission to add projects to this portfolio.")

        clean_slug_base = re.sub(r"[^a-z0-9]+", "-", req.title.lower()).strip("-")
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
        await db.refresh(project)
        return project

    @staticmethod
    async def generate_upload_url(req: UploadUrlRequest) -> UploadUrlResponse:
        # Sanitize filename
        safe_name = re.sub(r"[^a-zA-Z0-9._-]", "_", req.filename)
        result = await storage_service.generate_presigned_upload_url(
            filename=safe_name,
            content_type=req.mime_type,
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
            if not prof or prof.user_id != current_user.id:
                raise ForbiddenException("You do not have permission to add media to this project.")

        # Compute authentic public URL from storage service
        safe_public_url = storage_service.get_public_url(req.storage_key, is_public=True)

        asset = MediaAsset(
            project_id=req.project_id,
            storage_key=req.storage_key,
            public_url=safe_public_url,
            media_type=req.media_type,
            mime_type=req.mime_type,
            file_size_bytes=req.file_size_bytes,
            checksum=req.checksum,
            width=req.width,
            height=req.height,
            processing_status="completed",
        )
        db.add(asset)
        await db.flush()

        # If project has no cover, set this asset as cover
        if not project.cover_asset_id:
            project.cover_asset_id = asset.id
            await db.flush()

        await db.commit()
        await db.refresh(asset)
        return asset
