"""Review service with verified booking requirement, pending moderation, and rating aggregation."""

import uuid

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BusinessRuleViolationException, NotFoundException
from app.modules.bookings.models import Booking
from app.modules.identity.models import User
from app.modules.platform.models import AuditLog
from app.modules.professionals.models import ProfessionalProfile
from app.modules.reviews.models import ContentReport, Review
from app.modules.reviews.schemas import (
    ContentReportRequest,
    ReviewCreateRequest,
    ReviewModerationRequest,
)


async def _recalculate_professional_ratings(db: AsyncSession, professional_id: uuid.UUID) -> None:
    stats_stmt = select(
        func.avg(Review.overall_rating),
        func.count(Review.id),
    ).where(
        Review.professional_id == professional_id,
        Review.moderation_status == "approved",
    )
    avg_r, count_r = (await db.execute(stats_stmt)).one()

    prof = await db.get(ProfessionalProfile, professional_id)
    if prof:
        prof.avg_rating = round(float(avg_r or 0.0), 2)
        prof.total_reviews = int(count_r or 0)


class ReviewService:
    @staticmethod
    async def create_booking_review(
        db: AsyncSession,
        booking_id: uuid.UUID,
        customer_id: uuid.UUID,
        req: ReviewCreateRequest,
    ) -> Review:
        stmt = select(Booking).where(Booking.id == booking_id)
        booking = (await db.execute(stmt)).scalar_one_or_none()
        if not booking:
            raise NotFoundException("Booking", booking_id)

        if booking.customer_id != customer_id:
            raise BusinessRuleViolationException("Only the booking customer may submit a review.")

        if booking.booking_status != "completed" or booking.completion_status != "customer_accepted":
            raise BusinessRuleViolationException(
                "Reviews are only permitted for bookings that have been completed and accepted by the customer."
            )

        rev_stmt = select(Review).where(Review.booking_id == booking_id)
        if (await db.execute(rev_stmt)).scalar_one_or_none():
            raise BusinessRuleViolationException("A review has already been submitted for this booking.")

        # SEC-04: New reviews default to 'pending' moderation before public listing or rating inclusion
        review = Review(
            booking_id=booking_id,
            customer_id=customer_id,
            professional_id=booking.professional_id,
            overall_rating=round(float(req.overall_rating), 1),
            work_quality_rating=round(float(req.work_quality_rating), 1),
            communication_rating=round(float(req.communication_rating), 1),
            punctuality_rating=round(float(req.punctuality_rating), 1),
            value_rating=round(float(req.value_rating), 1),
            review_text=req.review_text,
            moderation_status="pending",
        )
        db.add(review)
        await db.flush()
        return review

    @staticmethod
    async def list_professional_reviews(
        db: AsyncSession,
        professional_id: uuid.UUID,
        limit: int = 50,
    ) -> list[Review]:
        stmt = (
            select(Review)
            .where(
                Review.professional_id == professional_id,
                Review.moderation_status == "approved",
            )
            .order_by(desc(Review.created_at))
            .limit(limit)
        )
        res = await db.execute(stmt)
        return list(res.scalars().all())

    @staticmethod
    async def list_reviews_for_moderation(
        db: AsyncSession,
        moderation_status: str = "pending",
        limit: int = 100,
    ) -> list[Review]:
        stmt = (
            select(Review)
            .where(Review.moderation_status == moderation_status)
            .order_by(desc(Review.created_at))
            .limit(limit)
        )
        res = await db.execute(stmt)
        return list(res.scalars().all())

    @staticmethod
    async def moderate_review(
        db: AsyncSession,
        review_id: uuid.UUID,
        admin_user: User,
        req: ReviewModerationRequest,
    ) -> Review:
        review = await db.get(Review, review_id)
        if not review:
            raise NotFoundException("Review", review_id)

        previous_status = review.moderation_status
        review.moderation_status = req.decision
        db.add(
            AuditLog(
                actor_user_id=admin_user.id,
                action="review_moderated",
                resource_type="review",
                resource_id=review.id,
                metadata_payload={
                    "previous_status": previous_status,
                    "new_status": req.decision,
                    "notes": req.notes,
                },
            )
        )
        await db.flush()
        await _recalculate_professional_ratings(db, review.professional_id)
        await db.flush()
        return review

    @staticmethod
    async def report_review(
        db: AsyncSession,
        review_id: uuid.UUID,
        reporter_user_id: uuid.UUID,
        req: ContentReportRequest,
    ) -> ContentReport:
        review = await db.get(Review, review_id)
        if not review:
            raise NotFoundException("Review", review_id)

        report = ContentReport(
            reporter_user_id=reporter_user_id,
            content_type="review",
            content_id=review_id,
            reason=req.reason,
            details=req.details,
            status="pending",
        )
        db.add(report)
        if review.moderation_status == "approved":
            review.moderation_status = "under_review"
            await db.flush()
            await _recalculate_professional_ratings(db, review.professional_id)
        await db.flush()
        return report
