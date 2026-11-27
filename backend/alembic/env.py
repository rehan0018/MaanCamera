"""Alembic migration environment importing all ORM models as single source of truth."""

import os
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool

# Import all module models so Base.metadata registers every table
import app.modules.ai.models  # noqa: F401
import app.modules.bookings.models  # noqa: F401
import app.modules.enquiries.models  # noqa: F401
import app.modules.identity.models  # noqa: F401
import app.modules.payments.models  # noqa: F401
import app.modules.platform.models  # noqa: F401
import app.modules.portfolios.models  # noqa: F401
import app.modules.professionals.models  # noqa: F401
import app.modules.quotations.models  # noqa: F401
import app.modules.reviews.models  # noqa: F401
from alembic import context
from app.core.config import settings
from app.core.database import Base

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

CUSTOM_POSTGRES_INDEXES = {
    "idx_prof_trgm_name",
    "idx_projects_trgm_title",
    "idx_portfolio_embeddings_hnsw",
}


def include_object(object_, name, type_, reflected, compare_to):
    """Ignore custom pg_trgm/hnsw indexes managed via raw SQL in migrations."""
    return not (type_ == "index" and name in CUSTOM_POSTGRES_INDEXES)


def get_sync_database_url() -> str:
    """Resolve synchronous PostgreSQL URL from environment or settings."""
    sync_url = os.environ.get("SYNC_DATABASE_URL") or settings.SYNC_DATABASE_URL
    async_url = os.environ.get("DATABASE_URL")
    if async_url and not os.environ.get("SYNC_DATABASE_URL"):
        sync_url = async_url.replace("postgresql+asyncpg://", "postgresql+psycopg2://")
    elif sync_url.startswith("postgresql://"):
        sync_url = sync_url.replace("postgresql://", "postgresql+psycopg2://", 1)
    return sync_url


def run_migrations_offline() -> None:
    url = get_sync_database_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        include_object=include_object,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = get_sync_database_url()
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            include_object=include_object,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
