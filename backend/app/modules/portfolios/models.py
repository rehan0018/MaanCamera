"""Portfolio, Project, and MediaAsset database models."""

import uuid
from datetime import UTC, date, datetime

from sqlalchemy import (
    JSON,
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
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, TimestampMixin


class Portfolio(Base, TimestampMixin):
    __tablename__ = "portfolios"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    professional_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("professional_profiles.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(200), default="Primary Portfolio", nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    visibility: Mapped[str] = mapped_column(String(30), default="public", nullable=False)

    projects = relationship("Project", back_populates="portfolio", cascade="all, delete-orphan")

    __table_args__ = (
        CheckConstraint("visibility IN ('public', 'unlisted', 'private')", name="ck_portfolios_visibility"),
    )


class Project(Base, TimestampMixin):
    __tablename__ = "projects"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    portfolio_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("portfolios.id", ondelete="CASCADE"), nullable=False, index=True
    )
    category_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("categories.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[str] = mapped_column(String(220), nullable=False)
    style: Mapped[str | None] = mapped_column(String(100), nullable=True)
    location: Mapped[str | None] = mapped_column(String(150), nullable=True)
    project_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    cover_asset_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("media_assets.id", ondelete="SET NULL", use_alter=True, name="fk_projects_cover_asset"),
        nullable=True,
    )
    publication_status: Mapped[str] = mapped_column(String(30), default="published", nullable=False)
    tags: Mapped[list[str]] = mapped_column(
        ARRAY(String).with_variant(JSON(), "sqlite"), default=list, nullable=False
    )

    portfolio = relationship("Portfolio", back_populates="projects")
    media_assets = relationship(
        "MediaAsset",
        back_populates="project",
        cascade="all, delete-orphan",
        foreign_keys="[MediaAsset.project_id]",
    )

    __table_args__ = (
        UniqueConstraint("portfolio_id", "slug", name="uq_portfolio_project_slug"),
        CheckConstraint(
            "publication_status IN ('draft', 'published', 'archived')",
            name="ck_projects_publication_status",
        ),
    )


class MediaAsset(Base):
    __tablename__ = "media_assets"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    storage_key: Mapped[str] = mapped_column(String(500), nullable=False)
    public_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    visibility: Mapped[str] = mapped_column(String(20), default="public", nullable=False)
    media_type: Mapped[str] = mapped_column(String(20), default="image", nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    width: Mapped[int | None] = mapped_column(Integer, nullable=True)
    height: Mapped[int | None] = mapped_column(Integer, nullable=True)
    duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    checksum: Mapped[str] = mapped_column(String(64), nullable=False)
    processing_status: Mapped[str] = mapped_column(String(30), default="completed", nullable=False)
    copyright_declaration_status: Mapped[str] = mapped_column(String(30), default="declared", nullable=False)
    display_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )

    project = relationship("Project", back_populates="media_assets", foreign_keys=[project_id])

    __table_args__ = (
        CheckConstraint("visibility IN ('public', 'private')", name="ck_media_assets_visibility"),
        CheckConstraint("media_type IN ('image', 'video')", name="ck_media_assets_type"),
        CheckConstraint(
            "processing_status IN ('pending', 'processing', 'completed', 'failed')",
            name="ck_media_assets_processing",
        ),
        CheckConstraint(
            "copyright_declaration_status IN ('declared', 'verified', 'disputed')",
            name="ck_media_assets_copyright",
        ),
    )
