"""HTTP endpoints for Portfolio, Projects, and Media Uploads."""

import uuid
from typing import List
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.responses import success_response
from app.modules.identity.models import User
from app.modules.identity.router import get_current_user
from app.modules.portfolios.schemas import (
    ProjectResponse,
    ProjectCreateRequest,
    UploadUrlRequest,
    CompleteMediaUploadRequest,
    MediaAssetResponse,
)
from app.modules.portfolios.service import PortfolioService

router = APIRouter(prefix="", tags=["Portfolios & Media"])


@router.get("/portfolios/{portfolio_id}/projects")
async def get_projects(portfolio_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    projects = await PortfolioService.get_projects_by_portfolio(db, portfolio_id)
    return success_response(
        data=[ProjectResponse.model_validate(p).model_dump(mode="json") for p in projects]
    )


@router.get("/projects/{project_id}")
async def get_project(project_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    project = await PortfolioService.get_project_by_id(db, project_id)
    return success_response(
        data=ProjectResponse.model_validate(project).model_dump(mode="json")
    )


@router.post("/projects", status_code=status.HTTP_201_CREATED)
async def create_project(
    req: ProjectCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    project = await PortfolioService.create_project(db, req)
    return success_response(
        data=ProjectResponse.model_validate(project).model_dump(mode="json"),
        status_code=status.HTTP_201_CREATED,
    )


@router.post("/media/upload-url")
async def generate_upload_url(
    req: UploadUrlRequest,
    current_user: User = Depends(get_current_user),
):
    url_res = await PortfolioService.generate_upload_url(req)
    return success_response(data=url_res.model_dump(mode="json"))


@router.post("/media/complete")
async def complete_upload(
    req: CompleteMediaUploadRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    asset = await PortfolioService.complete_upload(db, req)
    return success_response(
        data=MediaAssetResponse.model_validate(asset).model_dump(mode="json")
    )
