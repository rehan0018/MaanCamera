"""HTTP endpoints for Portfolio, Projects, and Media Uploads."""

import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.permissions import require_professional
from app.core.responses import success_response
from app.modules.identity.models import User
from app.modules.identity.router import get_current_user, get_optional_current_user
from app.modules.portfolios.schemas import (
    CompleteMediaUploadRequest,
    MediaAssetResponse,
    ProjectCreateRequest,
    ProjectUpdateRequest,
    UploadUrlRequest,
)
from app.modules.portfolios.service import PortfolioService

router = APIRouter(prefix="", tags=["Portfolios & Media"])


@router.get("/portfolios/me")
async def get_my_portfolios(
    current_user: User = Depends(require_professional),
    db: AsyncSession = Depends(get_db),
):
    portfolios = await PortfolioService.get_my_portfolios(db, current_user)
    return success_response(data=[p.model_dump(mode="json") for p in portfolios])


@router.get("/professionals/{id}/portfolios")
async def get_professional_portfolios(
    id: uuid.UUID,
    current_user: User | None = Depends(get_optional_current_user),
    db: AsyncSession = Depends(get_db),
):
    portfolios = await PortfolioService.get_portfolios_by_professional(db, id, current_user=current_user)
    return success_response(data=[p.model_dump(mode="json") for p in portfolios])


@router.get("/portfolios/{portfolio_id}/projects")
async def get_projects(
    portfolio_id: uuid.UUID,
    current_user: User | None = Depends(get_optional_current_user),
    db: AsyncSession = Depends(get_db),
):
    projects = await PortfolioService.get_projects_by_portfolio(
        db, portfolio_id, current_user=current_user
    )
    return success_response(data=[p.model_dump(mode="json") for p in projects])


@router.get("/projects/{project_id}")
async def get_project(
    project_id: uuid.UUID,
    current_user: User | None = Depends(get_optional_current_user),
    db: AsyncSession = Depends(get_db),
):
    project = await PortfolioService.get_project_by_id(db, project_id, current_user=current_user)
    return success_response(data=project.model_dump(mode="json"))


@router.post("/projects", status_code=status.HTTP_201_CREATED)
async def create_project(
    req: ProjectCreateRequest,
    current_user: User = Depends(require_professional),
    db: AsyncSession = Depends(get_db),
):
    project = await PortfolioService.create_project(db, current_user, req)
    return success_response(
        data=project.model_dump(mode="json"),
        status_code=status.HTTP_201_CREATED,
    )


@router.patch("/projects/{project_id}")
async def update_project(
    project_id: uuid.UUID,
    req: ProjectUpdateRequest,
    current_user: User = Depends(require_professional),
    db: AsyncSession = Depends(get_db),
):
    project = await PortfolioService.update_project(db, project_id, current_user, req)
    return success_response(data=project.model_dump(mode="json"))


@router.delete("/projects/{project_id}")
async def delete_project(
    project_id: uuid.UUID,
    current_user: User = Depends(require_professional),
    db: AsyncSession = Depends(get_db),
):
    await PortfolioService.delete_project(db, project_id, current_user)
    return success_response(data={"deleted": True})


@router.post("/media/upload-url")
async def generate_upload_url(
    req: UploadUrlRequest,
    current_user: User = Depends(get_current_user),
):
    url_res = await PortfolioService.generate_upload_url(current_user, req)
    return success_response(data=url_res.model_dump(mode="json"))


@router.post("/media/complete")
async def complete_upload(
    req: CompleteMediaUploadRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    asset = await PortfolioService.complete_upload(db, current_user, req)
    return success_response(
        data=MediaAssetResponse.model_validate(asset).model_dump(mode="json")
    )


@router.get("/media/{asset_id}/url")
async def get_media_access_url(
    asset_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    res = await PortfolioService.get_authorized_media_url(db, asset_id, current_user)
    return success_response(data=res.model_dump(mode="json"))


@router.delete("/media/{asset_id}")
async def delete_media_asset(
    asset_id: uuid.UUID,
    current_user: User = Depends(require_professional),
    db: AsyncSession = Depends(get_db),
):
    await PortfolioService.delete_media_asset(db, asset_id, current_user)
    return success_response(data={"deleted": True})
