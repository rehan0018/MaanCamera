"""Portfolio and Media upload service layer."""

import uuid
from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.exceptions import NotFoundException
from app.integrations.storage.s3 import storage_service
from app.modules.portfolios.models import Portfolio, Project, MediaAsset
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
    async def create_project(db: AsyncSession, req: ProjectCreateRequest) -> Project:
        slug = f"{req.title.lower().replace(' ', '-')}-{uuid.uuid4().hex[:6]}"
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
        await db.flush()
        return project

    @staticmethod
    async def generate_upload_url(req: UploadUrlRequest) -> UploadUrlResponse:
        result = await storage_service.generate_presigned_upload_url(
            filename=req.filename,
            content_type=req.mime_type,
            is_public=req.is_public,
        )
        return UploadUrlResponse(**result)

    @staticmethod
    async def complete_upload(db: AsyncSession, req: CompleteMediaUploadRequest) -> MediaAsset:
        asset = MediaAsset(
            project_id=req.project_id,
            storage_key=req.storage_key,
            public_url=req.public_url,
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
        project = await db.get(Project, req.project_id)
        if project and not project.cover_asset_id:
            project.cover_asset_id = asset.id
            await db.flush()

        return asset
