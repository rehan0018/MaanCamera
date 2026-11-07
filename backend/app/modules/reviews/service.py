"""Review service with verified booking requirement and rating aggregation."""

import uuid
from typing import List
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.reviews.models import Review, ContentReport
from app.modules.reviews.schemas import ReviewCreateRequest, ContentReportRequest
from app.modules.bookings.models import Booking
from app.modules.professionals.models import ProfessionalProfile
from app.core.exceptions import NotFoundException, BusinessRuleViolationException


class ReviewService:
    @staticmethod
    async def create_booking_review(
        db: AsyncSession,
        booking_id: uuid.UUID,
        customer_id: uuid.UUID,
        req: ReviewCreateRequest,
    ) -> Review:
        # 1. Booking must exist and belong to customer
        stmt = select(Booking).where(Booking.id == booking_id)
        res = await db.execute(stmt)
        booking = res.scalar_one_or_none()
        if not booking:
            raise NotFoundException("Booking not found.")

        if booking.customer_id != customer_id:
            raise BusinessRuleViolationException("Only the booking customer may submit a review.")

        # 2. Acceptance Criteria MC-012: Only eligible completed bookings can receive reviews
        if booking.booking_status != "completed":
            raise BusinessRuleViolationException("Reviews are only permitted for completed bookings.")

        # 3. Check duplicate review
        rev_stmt = select(Review).where(Review.booking_id == booking_id)
        rev_res = await db.execute(rev_stmt)
        if rev_res.scalar_one_or_none():
            raise BusinessRuleViolationException("A review has already been submitted for this booking.")

        review = Review(
            booking_id=booking_id,
            customer_id=customer_id,
            professional_id=booking.professional_id,
            overall_rating=req.overall_rating,
            work_quality_rating=req.work_quality_rating,
            communication_rating=req.communication_rating,
            punctuality_rating=req.punctuality_rating,
            value_rating=req.value_rating,
            review_text=req.review_text,
            moderation_status="approved",
        )
        db.add(review)
        await db.flush()

        # 4. Recalculate average rating & total reviews
        stats_stmt = select(
            func.avg(Review.overall_rating),
            func.count(Review.id),
        ).where(
            Review.professional_id == booking.professional_id,
            Review.moderation_status == "approved",
        )
        stats_res = await db.execute(stats_stmt)
        avg_r, count_r = stats_res.one()

        prof_stmt = select(ProfessionalProfile).where(ProfessionalProfile.id == booking.professional_id)
        prof_res = await db.execute(prof_stmt)
        prof = prof_res.scalar_one_or_none()
        if prof:
            prof.avg_rating = round(float(avg_r or 0.0), 2)
            prof.total_reviews = int(count_r or 0)
            prof.completed_bookings_count += 1

        await db.commit()
        await db.refresh(review)
        return review

    @staticmethod
    async def list_professional_reviews(
        db: AsyncSession,
        professional_id: uuid.UUID,
        limit: int = 50,
    ) -> List[Review]:
        stmt = select(Review).where(
            Review.professional_id == professional_id,
            Review.moderation_status == "approved",
        ).order_by(desc(Review.created_at)).limit(limit)
        res = await db.execute(stmt)
        return list(res.scalars().all())

    @staticmethod
    async def report_review(
        db: AsyncSession,
        review_id: uuid.UUID,
        reporter_user_id: uuid.UUID,
        req: ContentReportRequest,
    ) -> ContentReport:
        report = ContentReport(
            reporter_user_id=reporter_user_id,
            content_type="review",
            content_id=review_id,
            reason=req.reason,
            details=req.details,
            status="pending",
        )
        db.add(report)
        await db.commit()
        await db.refresh(report)
        return report
