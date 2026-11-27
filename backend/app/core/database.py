"""Database connection, single-transaction session lifecycle, and RLS context propagation."""

import inspect
from collections.abc import AsyncGenerator, Callable
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import DateTime, MetaData, event, text
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

from app.core.config import settings

# Explicit naming conventions for constraints and indexes
convention = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

metadata = MetaData(naming_convention=convention)


class Base(DeclarativeBase):
    """Base model class with metadata naming conventions."""

    metadata = metadata


class TimestampMixin:
    """Standardized timestamp mixin using UTC with timezone."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )


# Asynchronous database engine
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
)

# Async session factory
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


@event.listens_for(Session, "after_begin")
def _apply_rls_context_on_begin(session: Session, transaction: Any, connection: Connection) -> None:
    """Apply Postgres RLS GUCs at the beginning of every transaction (including after commits)."""
    if connection.dialect.name != "postgresql":
        return
    uid = str(session.info.get("rls_user_id") or "")
    role = str(session.info.get("rls_user_role") or "")
    connection.execute(
        text(
            "SELECT set_config('app.current_user_id', :uid, true), "
            "set_config('app.current_user_role', :role, true)"
        ),
        {"uid": uid, "role": role},
    )


async def apply_rls_context(
    db: AsyncSession,
    *,
    user_id: str | None = None,
    role: str | None = None,
) -> None:
    """Bind RLS identity to session.info and current active transaction if present."""
    uid_val = user_id or ""
    role_val = role or ""
    db.sync_session.info["rls_user_id"] = uid_val
    db.sync_session.info["rls_user_role"] = role_val
    if db.bind and db.bind.dialect.name == "postgresql" and db.in_transaction():
        await db.execute(
            text(
                "SELECT set_config('app.current_user_id', :uid, true), "
                "set_config('app.current_user_role', :role, true)"
            ),
            {"uid": uid_val, "role": role_val},
        )


def register_after_commit(db: AsyncSession, callback: Callable[[], Any]) -> None:
    """Queue a post-commit side effect (such as Celery dispatch or notifications) for request commit."""
    callbacks = db.sync_session.info.setdefault("after_commit_callbacks", [])
    callbacks.append(callback)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency enforcing one transaction per request with auto-commit/rollback."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            if session.in_transaction():
                await session.commit()
            callbacks = session.sync_session.info.pop("after_commit_callbacks", [])
            for cb in callbacks:
                res = cb()
                if inspect.isawaitable(res):
                    await res
        except Exception:
            session.sync_session.info.pop("after_commit_callbacks", None)
            if session.in_transaction():
                await session.rollback()
            raise
        finally:
            session.sync_session.info.pop("rls_user_id", None)
            session.sync_session.info.pop("rls_user_role", None)
            await session.close()
