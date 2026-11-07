"""AI Recommendation Sessions, Items, and Embeddings database models."""

import uuid
from datetime import datetime
from typing import Optional, Any
from sqlalchemy import String, Integer, Numeric, Text, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base, TimestampMixin


class PortfolioEmbedding(Base):
    __tablename__ = "portfolio_embeddings"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    asset_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("media_assets.id", ondelete="CASCADE"), nullable=True)
    embedding_model: Mapped[str] = mapped_column(String(100), default="bge-small-en-v1.5", nullable=False)
    model_version: Mapped[str] = mapped_column(String(50), default="1.0", nullable=False)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)


class RecommendationSession(Base):
    __tablename__ = "recommendation_sessions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    customer_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    query_text: Mapped[str] = mapped_column(Text, nullable=False)
    extracted_requirements: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    ranking_version: Mapped[str] = mapped_column(String(50), default="v1.0-weighted", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)


class RecommendationItem(Base):
    __tablename__ = "recommendation_items"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("recommendation_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    professional_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("professional_profiles.id", ondelete="CASCADE"), nullable=False)
    relevance_score: Mapped[float] = mapped_column(Numeric(5, 4), nullable=False)
    ranking_position: Mapped[int] = mapped_column(Integer, nullable=False)
    explanation_data: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
