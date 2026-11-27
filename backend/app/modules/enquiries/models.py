"""Enquiry and EnquiryRecipient database models."""

import uuid
from datetime import UTC, date, datetime

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, TimestampMixin


class Enquiry(Base, TimestampMixin):
    __tablename__ = "enquiries"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    category_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("categories.id", ondelete="RESTRICT"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(250), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    shoot_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    duration_days: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    location: Mapped[str] = mapped_column(String(200), nullable=False)
    city: Mapped[str] = mapped_column(String(100), nullable=False)
    budget_min_minor: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    budget_max_minor: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    currency_code: Mapped[str] = mapped_column(String(3), default="INR", nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="open", nullable=False)

    recipients = relationship("EnquiryRecipient", back_populates="enquiry", cascade="all, delete-orphan")

    __table_args__ = (
        CheckConstraint(
            "status IN ('open', 'responded', 'booked', 'expired', 'cancelled')",
            name="ck_enquiries_status",
        ),
    )


class EnquiryRecipient(Base):
    __tablename__ = "enquiry_recipients"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    enquiry_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("enquiries.id", ondelete="CASCADE"), nullable=False, index=True
    )
    professional_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("professional_profiles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    recipient_status: Mapped[str] = mapped_column(String(30), default="sent", nullable=False)
    sent_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    viewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    enquiry = relationship("Enquiry", back_populates="recipients")

    __table_args__ = (
        UniqueConstraint("enquiry_id", "professional_id", name="uq_enquiry_recipient"),
        CheckConstraint(
            "recipient_status IN ('sent', 'viewed', 'quoted', 'declined')",
            name="ck_enquiry_recipients_status",
        ),
    )
