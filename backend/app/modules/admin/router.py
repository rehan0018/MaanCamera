"""Admin HTTP endpoints for verification queue and content report moderation."""

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.permissions import require_admin
from app.core.responses import success_response
from app.modules.admin.schemas import ReportResolutionRequest, VerificationDecisionRequest
from app.modules.admin.service import AdminService
from app.modules.identity.models import User

router = APIRouter(prefix="", tags=["Admin Moderation & Trust"])


@router.get("/admin/verifications")
async def list_verification_requests(
    verification_status: str = Query("pending", pattern="^(pending|verified|rejected)$"),
    limit: int = Query(100, ge=1, le=200),
    admin_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    items = await AdminService.list_verifications(db, status_filter=verification_status, limit=limit)
    return success_response(data=[item.model_dump(mode="json") for item in items])


@router.post("/admin/verifications/{id}/decision")
async def decide_verification_request(
    id: uuid.UUID,
    req: VerificationDecisionRequest,
    admin_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    ver = await AdminService.decide_verification(db, id, admin_user, req)
    return success_response(
        data={
            "id": str(ver.id),
            "professional_id": str(ver.professional_id),
            "status": ver.status,
            "reviewed_at": ver.reviewed_at.isoformat() if ver.reviewed_at else None,
        }
    )


@router.get("/admin/reports")
async def list_content_reports(
    report_status: str = Query("pending", pattern="^(pending|dismissed|action_taken)$"),
    limit: int = Query(100, ge=1, le=200),
    admin_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    items = await AdminService.list_reports(db, status_filter=report_status, limit=limit)
    return success_response(data=[item.model_dump(mode="json") for item in items])


@router.post("/admin/reports/{id}/resolve")
async def resolve_content_report(
    id: uuid.UUID,
    req: ReportResolutionRequest,
    admin_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    report = await AdminService.resolve_report(db, id, admin_user, req)
    return success_response(data={"id": str(report.id), "status": report.status})
