"""Portfolio and Media upload service layer enforcing visibility and ownership isolation."""

import contextlib
import os
import re
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import register_after_commit
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
    MediaReadUrlResponse,
    PortfolioResponse,
    ProjectCreateRequest,
    ProjectResponse,
    ProjectUpdateRequest,
    UploadUrlRequest,
    UploadUrlResponse,
)
from app.modules.professionals.models import ProfessionalProfile
from app.workers.celery_app import process_uploaded_media


async def _is_portfolio_owner_or_admin(
    db: AsyncSession, portfolio: Portfolio, current_user: User | None
) -> bool:
    if not current_user:
        return False
    if current_user.role == "admin":
        return True
    prof = await db.get(ProfessionalProfile, portfolio.professional_id)
    return bool(prof and prof.owner_user_id == current_user.id)


def _to_project_response(project: Project, is_privileged: bool) -> ProjectResponse:
    """Serialize a Project ORM object without mutating tracked relationship collections."""
    resp = ProjectResponse.model_validate(project)
    if not is_privileged:
        resp.media_assets = [asset for asset in resp.media_assets if asset.visibility == "public"]
    return resp


class PortfolioService:
    @staticmethod
    async def get_projects_by_portfolio(
        db: AsyncSession,
        portfolio_id: uuid.UUID,
        current_user: User | None = None,
    ) -> list[ProjectResponse]:
        portfolio = await db.get(Portfolio, portfolio_id)
        if not portfolio:
            raise NotFoundException("Portfolio", portfolio_id)

        is_privileged = await _is_portfolio_owner_or_admin(db, portfolio, current_user)
        if not is_privileged and portfolio.visibility == "private":
            raise ForbiddenException("You do not have permission to view this private portfolio.")

        stmt = (
            select(Project)
            .options(selectinload(Project.media_assets))
            .where(Project.portfolio_id == portfolio_id)
            .order_by(Project.created_at.desc())
        )
        if not is_privileged:
            stmt = stmt.where(Project.publication_status == "published")

        res = await db.execute(stmt)
        projects = list(res.scalars().all())
        return [_to_project_response(proj, is_privileged) for proj in projects]

    @staticmethod
    async def get_project_by_id(
        db: AsyncSession,
        project_id: uuid.UUID,
        current_user: User | None = None,
    ) -> ProjectResponse:
        stmt = (
            select(Project)
            .options(selectinload(Project.media_assets), selectinload(Project.portfolio))
            .where(Project.id == project_id)
        )
        res = await db.execute(stmt)
        proj = res.scalar_one_or_none()
        if not proj:
            raise NotFoundException("Project", project_id)

        is_privileged = await _is_portfolio_owner_or_admin(db, proj.portfolio, current_user)
        if not is_privileged:
            if proj.portfolio.visibility == "private":
                raise ForbiddenException("This portfolio is private.")
            if proj.publication_status != "published":
                raise ForbiddenException("This project is not publicly published.")

        return _to_project_response(proj, is_privileged)

    @staticmethod
    async def create_project(
        db: AsyncSession, current_user: User, req: ProjectCreateRequest
    ) -> ProjectResponse:
        portfolio = await db.get(Portfolio, req.portfolio_id)
        if not portfolio:
            raise NotFoundException("Portfolio", req.portfolio_id)

        if current_user.role != "admin":
            prof = await db.get(ProfessionalProfile, portfolio.professional_id)
            if not prof or prof.owner_user_id != current_user.id:
                raise ForbiddenException("You do not have permission to add projects to this portfolio.")

        if req.publication_status == "published":
            raise BusinessRuleViolationException(
                "Upload at least one public media asset to a draft project before publishing."
            )

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
            publication_status=req.publication_status,
        )
        db.add(project)
        await db.flush()
        return await PortfolioService.get_project_by_id(db, project.id, current_user=current_user)

    @staticmethod
    async def get_my_portfolios(db: AsyncSession, current_user: User) -> list[PortfolioResponse]:
        prof = (
            await db.execute(
                select(ProfessionalProfile).where(ProfessionalProfile.owner_user_id == current_user.id)
            )
        ).scalar_one_or_none()
        if not prof:
            return []

        portfolios = list(
            (
                await db.execute(
                    select(Portfolio)
                    .where(Portfolio.professional_id == prof.id)
                    .order_by(Portfolio.created_at.asc())
                )
            )
            .scalars()
            .all()
        )
        if not portfolios:
            default_port = Portfolio(
                professional_id=prof.id,
                title="Featured Portfolio",
                visibility="public",
            )
            db.add(default_port)
            await db.flush()
            portfolios = [default_port]
        return [PortfolioResponse.model_validate(p) for p in portfolios]

    @staticmethod
    async def get_portfolios_by_professional(
        db: AsyncSession, professional_id: uuid.UUID, current_user: User | None = None
    ) -> list[PortfolioResponse]:
        prof = await db.get(ProfessionalProfile, professional_id)
        if not prof:
            raise NotFoundException("ProfessionalProfile", professional_id)

        is_privileged = bool(
            current_user and (current_user.role == "admin" or prof.owner_user_id == current_user.id)
        )
        if prof.profile_visibility == "private" and not is_privileged:
            raise ForbiddenException("This professional profile is currently private.")

        stmt = select(Portfolio).where(Portfolio.professional_id == professional_id)
        if not is_privileged:
            stmt = stmt.where(Portfolio.visibility == "public")
        stmt = stmt.order_by(Portfolio.created_at.asc())
        portfolios = list((await db.execute(stmt)).scalars().all())
        return [PortfolioResponse.model_validate(p) for p in portfolios]

    @staticmethod
    async def update_project(
        db: AsyncSession, project_id: uuid.UUID, current_user: User, req: ProjectUpdateRequest
    ) -> ProjectResponse:
        stmt = (
            select(Project)
            .options(selectinload(Project.media_assets), selectinload(Project.portfolio))
            .where(Project.id == project_id)
        )
        project = (await db.execute(stmt)).scalar_one_or_none()
        if not project:
            raise NotFoundException("Project", project_id)

        if not await _is_portfolio_owner_or_admin(db, project.portfolio, current_user):
            raise ForbiddenException("You do not have permission to update this project.")

        updates = req.model_dump(exclude_unset=True)
        if updates.get("publication_status") == "published":
            has_public_asset = any(a.visibility == "public" for a in (project.media_assets or []))
            if not has_public_asset:
                raise BusinessRuleViolationException(
                    "Upload at least one public media asset before publishing this project."
                )

        for field, value in updates.items():
            setattr(project, field, value)

        await db.flush()
        return await PortfolioService.get_project_by_id(db, project.id, current_user=current_user)

    @staticmethod
    async def delete_project(
        db: AsyncSession, project_id: uuid.UUID, current_user: User
    ) -> bool:
        stmt = select(Project).options(selectinload(Project.portfolio)).where(Project.id == project_id)
        project = (await db.execute(stmt)).scalar_one_or_none()
        if not project:
            raise NotFoundException("Project", project_id)

        if not await _is_portfolio_owner_or_admin(db, project.portfolio, current_user):
            raise ForbiddenException("You do not have permission to delete this project.")

        project.cover_asset_id = None
        await db.flush()
        await db.delete(project)
        await db.flush()
        return True

    @staticmethod
    async def delete_media_asset(
        db: AsyncSession, asset_id: uuid.UUID, current_user: User
    ) -> bool:
        asset = await db.get(MediaAsset, asset_id)
        if not asset:
            raise NotFoundException("MediaAsset", asset_id)
        project = await db.get(Project, asset.project_id)
        if not project:
            raise NotFoundException("Project", asset.project_id)
        portfolio = await db.get(Portfolio, project.portfolio_id)
        if not portfolio:
            raise NotFoundException("Portfolio", project.portfolio_id)

        if not await _is_portfolio_owner_or_admin(db, portfolio, current_user):
            raise ForbiddenException("You do not have permission to delete this media asset.")

        if project.cover_asset_id == asset.id:
            project.cover_asset_id = None
            await db.flush()

        await db.delete(asset)
        await db.flush()
        return True

    @staticmethod
    async def generate_upload_url(current_user: User, req: UploadUrlRequest) -> UploadUrlResponse:
        if current_user.role not in ("professional", "admin"):
            raise ForbiddenException("Only professionals may generate portfolio media upload URLs.")
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

        portfolio = await db.get(Portfolio, project.portfolio_id)
        if not portfolio:
            raise NotFoundException("Portfolio", project.portfolio_id)

        if current_user.role != "admin":
            prof = await db.get(ProfessionalProfile, portfolio.professional_id)
            if not prof or prof.owner_user_id != current_user.id:
                raise ForbiddenException("You do not have permission to add media to this project.")

            expected_public_prefix = f"public/{current_user.id}/"
            expected_private_prefix = f"private/{current_user.id}/"
            if not (
                req.storage_key.startswith(expected_public_prefix)
                or req.storage_key.startswith(expected_private_prefix)
            ):
                raise BusinessRuleViolationException("Invalid upload storage key ownership prefix.")

        if req.storage_key.startswith("private/"):
            resolved_visibility = "private"
        elif req.storage_key.startswith("public/"):
            resolved_visibility = "public"
        else:
            raise BusinessRuleViolationException("Upload storage key must reside under public/ or private/ prefix.")

        if req.visibility and req.visibility != resolved_visibility:
            raise BusinessRuleViolationException(
                "Declared asset visibility does not match storage key prefix."
            )

        asset = MediaAsset(
            project_id=req.project_id,
            storage_key=req.storage_key,
            public_url=None,  # Worker publishes public WebP URL strictly for public assets after sanitization
            visibility=resolved_visibility,
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

        if resolved_visibility == "public" and not project.cover_asset_id:
            project.cover_asset_id = asset.id
            await db.flush()

        # Enqueue async Pillow validation + EXIF stripping + visibility-aware WebP storage after commit
        asset_id_str = str(asset.id)
        asset_storage_key = asset.storage_key

        def _dispatch_media_job() -> None:
            with contextlib.suppress(Exception):
                process_uploaded_media.delay(asset_id_str, asset_storage_key)

        register_after_commit(db, _dispatch_media_job)

        return asset

    @staticmethod
    async def get_authorized_media_url(
        db: AsyncSession, asset_id: uuid.UUID, current_user: User
    ) -> MediaReadUrlResponse:
        asset = await db.get(MediaAsset, asset_id)
        if not asset:
            raise NotFoundException("MediaAsset", asset_id)

        project = await db.get(Project, asset.project_id)
        if not project:
            raise NotFoundException("Project", asset.project_id)

        portfolio = await db.get(Portfolio, project.portfolio_id)
        if not portfolio:
            raise NotFoundException("Portfolio", project.portfolio_id)

        is_privileged = await _is_portfolio_owner_or_admin(db, portfolio, current_user)
        if asset.visibility == "private" and not is_privileged:
            raise ForbiddenException("You do not have permission to access this private media asset.")

        if asset.visibility == "public":
            if not is_privileged and (
                portfolio.visibility == "private" or project.publication_status != "published"
            ):
                raise ForbiddenException("This media asset is not publicly available.")
            if asset.public_url:
                return MediaReadUrlResponse(
                    asset_id=asset.id,
                    url=asset.public_url,
                    visibility="public",
                    expires_in_seconds=None,
                )

        expires_in = 300
        signed_url = await storage_service.generate_presigned_download_url(
            asset.storage_key,
            is_public=(asset.visibility == "public"),
            expires_in=expires_in,
        )
        return MediaReadUrlResponse(
            asset_id=asset.id,
            url=signed_url,
            visibility=asset.visibility,
            expires_in_seconds=expires_in,
        )
