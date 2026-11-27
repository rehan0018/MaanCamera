"""Pytest configuration and async fixtures supporting PostgreSQL (CI) and SQLite (local fallback)."""

import contextlib
import os
import uuid
from collections.abc import AsyncGenerator
from typing import Any

# Default rate-limit storage to in-memory for local unit tests unless CI/env provides Valkey URI
os.environ.setdefault("RATE_LIMIT_STORAGE_URI", os.environ.get("TEST_REDIS_URL", "memory://"))
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from pgvector.sqlalchemy import Vector
from sqlalchemy import text
from sqlalchemy.dialects.postgresql import ARRAY, INET, JSONB, UUID
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.ext.compiler import compiles


# SQLite compilation shims for local offline test runs when TEST_DATABASE_URL is not Postgres
@compiles(ARRAY, "sqlite")
def compile_array_sqlite(type_: Any, compiler: Any, **kw: Any) -> str:
    return "TEXT"


@compiles(JSONB, "sqlite")
def compile_jsonb_sqlite(type_: Any, compiler: Any, **kw: Any) -> str:
    return "JSON"


@compiles(UUID, "sqlite")
def compile_uuid_sqlite(type_: Any, compiler: Any, **kw: Any) -> str:
    return "VARCHAR(36)"


@compiles(INET, "sqlite")
def compile_inet_sqlite(type_: Any, compiler: Any, **kw: Any) -> str:
    return "VARCHAR(45)"


@compiles(Vector, "sqlite")
def compile_vector_sqlite(type_: Any, compiler: Any, **kw: Any) -> str:
    return "TEXT"


import app.modules.ai.models  # noqa: E402, F401
import app.modules.bookings.models  # noqa: E402, F401
import app.modules.enquiries.models  # noqa: E402, F401
import app.modules.payments.models  # noqa: E402, F401
import app.modules.platform.models  # noqa: E402, F401
import app.modules.quotations.models  # noqa: E402, F401
import app.modules.reviews.models  # noqa: E402, F401
from app.core.database import Base, get_db  # noqa: E402
from app.core.rate_limit import limiter  # noqa: E402
from app.core.security import hash_password  # noqa: E402
from app.main import app  # noqa: E402
from app.modules.identity.models import User  # noqa: E402
from app.modules.portfolios.models import Portfolio, Project  # noqa: E402
from app.modules.professionals.models import Category, ProfessionalProfile, Service  # noqa: E402

TEST_NS = uuid.uuid5(uuid.NAMESPACE_DNS, "test.maancamera.com")
TEST_DIR = os.path.join(os.path.dirname(__file__), ".test_db")


def test_uuid(key: str) -> uuid.UUID:
    return uuid.uuid5(TEST_NS, key)


def csrf_headers(client: AsyncClient, extra: dict[str, str] | None = None) -> dict[str, str]:
    """Attach X-CSRF-Token header matching mc_csrf cookie for cookie-authenticated mutations."""
    headers = dict(extra or {})
    csrf_tok = client.cookies.get("mc_csrf")
    if csrf_tok:
        headers["X-CSRF-Token"] = csrf_tok
    return headers


@pytest_asyncio.fixture
async def test_engine():
    db_url = os.environ.get("TEST_DATABASE_URL", "").strip()
    is_sqlite = False
    sqlite_path = ""

    if not db_url:
        is_sqlite = True
        os.makedirs(TEST_DIR, exist_ok=True)
        sqlite_path = os.path.join(TEST_DIR, f"mc_{uuid.uuid4().hex[:8]}.sqlite")
        posix_path = sqlite_path.replace("\\", "/")
        db_url = f"sqlite+aiosqlite:///{posix_path}"

    engine = create_async_engine(db_url)
    if is_sqlite:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    else:
        # Clean all tables between tests when running against Alembic-migrated PostgreSQL
        async with engine.begin() as conn:
            await conn.execute(text("SELECT set_config('app.current_user_role', 'system', true)"))
            table_names = ", ".join(f'"{t.name}"' for t in reversed(Base.metadata.sorted_tables))
            if table_names:
                await conn.execute(text(f"TRUNCATE TABLE {table_names} RESTART IDENTITY CASCADE"))

    yield engine

    await engine.dispose()
    if is_sqlite and sqlite_path and os.path.exists(sqlite_path):
        with contextlib.suppress(OSError):
            os.remove(sqlite_path)


@pytest_asyncio.fixture
async def session_factory(test_engine):
    return async_sessionmaker(
        bind=test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )


@pytest_asyncio.fixture
async def db_session(session_factory) -> AsyncGenerator[AsyncSession, None]:
    async with session_factory() as session:
        if session.bind and session.bind.dialect.name == "postgresql":
            await session.execute(text("SELECT set_config('app.current_user_role', 'system', true)"))
        yield session


@pytest_asyncio.fixture
async def client(session_factory) -> AsyncGenerator[AsyncClient, None]:
    # Keep generic test suite deterministic even without Valkey or >5 login calls
    limiter.enabled = False

    async def override_get_db():
        async with session_factory() as session:
            try:
                yield session
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver/api/v1") as ac:
        yield ac
    app.dependency_overrides.clear()
    limiter.enabled = True


@pytest_asyncio.fixture
async def seed_users(db_session: AsyncSession) -> dict[str, Any]:
    customer = User(
        id=test_uuid("user:customer"),
        email="customer@example.com",
        password_hash=hash_password("CustomerPass@2026!"),
        full_name="Rajesh Patel",
        role="customer",
        status="active",
    )
    prof_user = User(
        id=test_uuid("user:pro"),
        email="pro@example.com",
        password_hash=hash_password("ProPass@2026!"),
        full_name="Aura Studio Lead",
        role="professional",
        status="active",
    )
    admin = User(
        id=test_uuid("user:admin"),
        email="admin@example.com",
        password_hash=hash_password("AdminPass@2026!"),
        full_name="Platform Admin",
        role="admin",
        is_superuser=True,
        status="active",
    )
    db_session.add_all([customer, prof_user, admin])

    cat = Category(
        id=test_uuid("category:wedding"),
        name="Wedding Photography",
        slug="wedding-photography",
        description="Wedding and candid shoots",
    )
    db_session.add(cat)
    await db_session.flush()

    prof_profile = ProfessionalProfile(
        id=test_uuid("prof:aura"),
        owner_user_id=prof_user.id,
        display_name="Aura Weddings",
        slug="aura-weddings-test",
        headline="Premier Candid Photographer in Pune",
        biography="Specializing in candid and cinematic visual storytelling.",
        professional_type="individual",
        years_experience=7,
        base_city="Pune",
        state="Maharashtra",
        avg_rating=4.9,
        total_reviews=25,
        verification_status="verified",
        profile_visibility="public",
        travel_available=True,
    )
    db_session.add(prof_profile)
    await db_session.flush()

    serv = Service(
        id=test_uuid("service:wedding-full"),
        professional_id=prof_profile.id,
        category_id=cat.id,
        name="Full Day Wedding Photography",
        description="Comprehensive candid and traditional wedding coverage.",
        starting_price_minor=4500000,
        currency_code="INR",
        is_active=True,
    )
    db_session.add(serv)

    port = Portfolio(
        id=test_uuid("portfolio:aura"),
        professional_id=prof_profile.id,
        title="Featured Weddings Portfolio",
        visibility="public",
    )
    db_session.add(port)
    await db_session.flush()

    proj = Project(
        id=test_uuid("project:royal-palace"),
        portfolio_id=port.id,
        category_id=cat.id,
        title="Royal Palace Wedding",
        slug="royal-palace-wedding-test",
        style="Candid & Cinematic",
        location="Pune",
        publication_status="published",
    )
    db_session.add(proj)

    await db_session.commit()
    return {
        "customer": customer,
        "professional_user": prof_user,
        "professional_profile": prof_profile,
        "admin": admin,
        "category": cat,
        "service": serv,
        "portfolio": port,
        "project": proj,
    }
