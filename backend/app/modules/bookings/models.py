"""Booking database model."""

import uuid
from datetime import date

from sqlalchemy import BigInteger, CheckConstraint, Date, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, TimestampMixin


class Booking(Base, TimestampMixin):
    __tablename__ = "bookings"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    enquiry_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("enquiries.id", ondelete="SET NULL"), nullable=True, index=True
    )
    quotation_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("quotations.id", ondelete="RESTRICT"), unique=True, nullable=True
    )
    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    professional_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("professional_profiles.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    shoot_date: Mapped[date] = mapped_column(Date, nullable=False)
    location: Mapped[str] = mapped_column(String(250), nullable=False)
    agreed_amount_minor: Mapped[int] = mapped_column(BigInteger, nullable=False)
    paid_amount_minor: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    currency_code: Mapped[str] = mapped_column(String(3), default="INR", nullable=False)
    booking_status: Mapped[str] = mapped_column(String(30), default="pending_payment", nullable=False)
    completion_status: Mapped[str] = mapped_column(String(30), default="pending", nullable=False)
    cancellation_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        CheckConstraint(
            "booking_status IN ('pending_payment', 'confirmed', 'in_progress', 'completed', 'cancelled', 'disputed')",
            name="ck_bookings_status",
        ),
        CheckConstraint(
            "completion_status IN ('pending', 'delivered', 'customer_accepted')",
            name="ck_bookings_completion_status",
        ),
    )
