"""Admin service for professional verification decisions and content report resolution."""

import contextlib
import uuid
from datetime import UTC, datetime

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import register_after_commit
from app.core.exceptions import BusinessRuleViolationException, NotFoundException
from app.integrations.notifications.mailer import send_email_notification
from app.integrations.storage.s3 import storage_service
from app.modules.admin.schemas import (
    AdminReportItemResponse,
    AdminVerificationItemResponse,
    ReportResolutionRequest,
    VerificationDecisionRequest,
)
from app.modules.identity.models import User
from app.modules.platform.models import AuditLog, VerificationRequest
from app.modules.portfolios.models import Project
from app.modules.professionals.models import ProfessionalProfile
from app.modules.reviews.models import ContentReport, Review
from app.modules.reviews.service import _recalculate_professional_ratings


class AdminService:
    @staticmethod
    async def list_verifications(
        db: AsyncSession,
        status_filter: str = "pending",
        limit: int = 100,
    ) -> list[AdminVerificationItemResponse]:
        stmt = (
            select(VerificationRequest, ProfessionalProfile)
            .join(ProfessionalProfile, ProfessionalProfile.id == VerificationRequest.professional_id)
            .where(VerificationRequest.status == status_filter)
            .order_by(desc(VerificationRequest.created_at))
            .limit(limit)
        )
        rows = (await db.execute(stmt)).all()
        items: list[AdminVerificationItemResponse] = []
        for req_row, prof in rows:
            doc_url: str | None = None
            with contextlib.suppress(Exception):
                doc_url = await storage_service.generate_presigned_download_url(
                    req_row.document_storage_key,
                    is_public=False,
                    expires_in=300,
                )
            items.append(
                AdminVerificationItemResponse(
                    id=req_row.id,
                    professional_id=prof.id,
                    professional_name=prof.display_name,
                    base_city=prof.base_city,
                    professional_type=prof.professional_type,
                    document_type=req_row.document_type,
                    document_storage_key=req_row.document_storage_key,
                    document_access_url=doc_url,
                    status=req_row.status,
                    notes=req_row.notes,
                    created_at=req_row.created_at,
                    reviewed_at=req_row.reviewed_at,
                )
            )
        return items

    @staticmethod
    async def decide_verification(
        db: AsyncSession,
        verification_id: uuid.UUID,
        admin_user: User,
        req: VerificationDecisionRequest,
    ) -> VerificationRequest:
        ver = await db.get(VerificationRequest, verification_id)
        if not ver:
            raise NotFoundException("VerificationRequest", verification_id)
        if ver.status != "pending":
            raise BusinessRuleViolationException(
                f"Verification request has already been decided ('{ver.status}')."
            )

        prof = await db.get(ProfessionalProfile, ver.professional_id)
        if not prof:
            raise NotFoundException("ProfessionalProfile", ver.professional_id)

        ver.status = req.decision
        ver.notes = req.notes
        ver.reviewed_by_user_id = admin_user.id
        ver.reviewed_at = datetime.now(UTC)

        prof.verification_status = "verified" if req.decision == "verified" else "rejected"
        db.add(
            AuditLog(
                actor_user_id=admin_user.id,
                action="verification_decided",
                resource_type="verification_request",
                resource_id=ver.id,
                metadata_payload={
                    "professional_id": str(prof.id),
                    "decision": req.decision,
                    "notes": req.notes,
                },
            )
        )
        await db.flush()

        owner = await db.get(User, prof.owner_user_id)
        if owner and owner.email:
            owner_email = owner.email
            studio_name = prof.display_name
            decision = req.decision

            async def _notify_verification() -> None:
                with contextlib.suppress(Exception):
                    await send_email_notification(
                        recipient=owner_email,
                        subject=f"Studio Verification {decision.title()} — {studio_name}",
                        body=f"Your verification request for '{studio_name}' has been marked '{decision}'.",
                        event_type="verification_decided",
                    )

            register_after_commit(db, _notify_verification)

        return ver

    @staticmethod
    async def list_reports(
        db: AsyncSession,
        status_filter: str = "pending",
        limit: int = 100,
    ) -> list[AdminReportItemResponse]:
        stmt = (
            select(ContentReport, User.full_name)
            .outerjoin(User, User.id == ContentReport.reporter_user_id)
            .where(ContentReport.status == status_filter)
            .order_by(desc(ContentReport.created_at))
            .limit(limit)
        )
        rows = (await db.execute(stmt)).all()
        return [
            AdminReportItemResponse(
                id=rep.id,
                reporter_user_id=rep.reporter_user_id,
                reporter_name=rep_name,
                content_type=rep.content_type,
                content_id=rep.content_id,
                reason=rep.reason,
                details=rep.details,
                status=rep.status,
                created_at=rep.created_at,
            )
            for rep, rep_name in rows
        ]

    @staticmethod
    async def resolve_report(
        db: AsyncSession,
        report_id: uuid.UUID,
        admin_user: User,
        req: ReportResolutionRequest,
    ) -> ContentReport:
        report = await db.get(ContentReport, report_id)
        if not report:
            raise NotFoundException("ContentReport", report_id)

        if req.action == "hide_content":
            report.status = "action_taken"
            if report.content_type == "review":
                review = await db.get(Review, report.content_id)
                if review:
                    review.moderation_status = "hidden"
                    await db.flush()
                    await _recalculate_professional_ratings(db, review.professional_id)
            elif report.content_type == "project":
                project = await db.get(Project, report.content_id)
                if project:
                    project.publication_status = "archived"
        else:
            report.status = "dismissed"

        db.add(
            AuditLog(
                actor_user_id=admin_user.id,
                action="content_report_resolved",
                resource_type="content_report",
                resource_id=report.id,
                metadata_payload={
                    "action": req.action,
                    "content_type": report.content_type,
                    "content_id": str(report.content_id),
                    "notes": req.notes,
                },
            )
        )
        await db.flush()
        return report
