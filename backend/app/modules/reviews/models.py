"""Review and ContentReport database models."""

import uuid

from sqlalchemy import CheckConstraint, ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, TimestampMixin


class Review(Base, TimestampMixin):
    __tablename__ = "reviews"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    booking_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("bookings.id", ondelete="RESTRICT"), unique=True, nullable=False, index=True
    )
    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    professional_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("professional_profiles.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    overall_rating: Mapped[float] = mapped_column(Numeric(2, 1), nullable=False)
    work_quality_rating: Mapped[float] = mapped_column(Numeric(2, 1), nullable=False)
    communication_rating: Mapped[float] = mapped_column(Numeric(2, 1), nullable=False)
    punctuality_rating: Mapped[float] = mapped_column(Numeric(2, 1), nullable=False)
    value_rating: Mapped[float] = mapped_column(Numeric(2, 1), nullable=False)
    review_text: Mapped[str] = mapped_column(Text, nullable=False)
    moderation_status: Mapped[str] = mapped_column(String(30), default="pending", nullable=False)

    __table_args__ = (
        CheckConstraint("overall_rating >= 1.0 AND overall_rating <= 5.0", name="ck_reviews_overall_rating"),
        CheckConstraint("work_quality_rating >= 1.0 AND work_quality_rating <= 5.0", name="ck_reviews_work_quality"),
        CheckConstraint("communication_rating >= 1.0 AND communication_rating <= 5.0", name="ck_reviews_communication"),
        CheckConstraint("punctuality_rating >= 1.0 AND punctuality_rating <= 5.0", name="ck_reviews_punctuality"),
        CheckConstraint("value_rating >= 1.0 AND value_rating <= 5.0", name="ck_reviews_value"),
        CheckConstraint(
            "moderation_status IN ('pending', 'approved', 'rejected', 'under_review', 'flagged', 'hidden')",
            name="ck_reviews_moderation_status",
        ),
    )


class ContentReport(Base, TimestampMixin):
    __tablename__ = "content_reports"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    reporter_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    content_type: Mapped[str] = mapped_column(String(50), nullable=False)
    content_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    reason: Mapped[str] = mapped_column(String(100), nullable=False)
    details: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="pending", nullable=False)
