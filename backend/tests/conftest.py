"""Pytest configuration and async test fixtures for MaanCamera."""

import os
import uuid
import pytest
import pytest_asyncio
from typing import AsyncGenerator
from httpx import AsyncClient, ASGITransport
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID, INET
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

# Compilers for SQLite compatibility
@compiles(ARRAY, "sqlite")
def compile_array_sqlite(type_, compiler, **kw):
    return "TEXT"

@compiles(JSONB, "sqlite")
def compile_jsonb_sqlite(type_, compiler, **kw):
    return "JSON"

@compiles(UUID, "sqlite")
def compile_uuid_sqlite(type_, compiler, **kw):
    return "VARCHAR(36)"

@compiles(INET, "sqlite")
def compile_inet_sqlite(type_, compiler, **kw):
    return "VARCHAR(45)"

from app.core.database import Base, get_db
from app.core.security import hash_password
from app.modules.identity.models import User, UserSession
from app.modules.professionals.models import ProfessionalProfile, Category, Service
from app.modules.portfolios.models import Portfolio, Project, MediaAsset
from app.modules.enquiries.models import Enquiry, EnquiryRecipient
from app.modules.quotations.models import Quotation
from app.modules.bookings.models import Booking
from app.modules.payments.models import Payment, PaymentEvent, Refund
from app.modules.reviews.models import Review, ContentReport
from app.modules.ai.models import RecommendationSession, RecommendationItem
from app.main import app

# Directory for test sqlite files inside workspace
TEST_DIR = os.path.join(os.path.dirname(__file__), ".test_db")
os.makedirs(TEST_DIR, exist_ok=True)


@pytest_asyncio.fixture
async def test_engine():
    db_file = os.path.join(TEST_DIR, f"mc_{uuid.uuid4().hex[:8]}.sqlite")
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_file}")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    await engine.dispose()
    if os.path.exists(db_file):
        try:
            os.remove(db_file)
        except Exception:
            pass


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
        yield session


@pytest_asyncio.fixture
async def client(session_factory) -> AsyncGenerator[AsyncClient, None]:
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


@pytest_asyncio.fixture
async def seed_users(db_session: AsyncSession):
    customer = User(
        id=uuid.UUID("00000001-0000-0000-0000-000000000001"),
        email="customer@example.com",
        password_hash=hash_password("CustomerPass@2026!"),
        full_name="Rajesh Patel",
        role="customer",
        status="active",
    )
    prof_user = User(
        id=uuid.UUID("00000001-0000-0000-0000-000000000002"),
        email="pro@example.com",
        password_hash=hash_password("ProPass@2026!"),
        full_name="Aura Studio Lead",
        role="professional",
        status="active",
    )
    admin = User(
        id=uuid.UUID("00000001-0000-0000-0000-000000000003"),
        email="admin@example.com",
        password_hash=hash_password("AdminPass@2026!"),
        full_name="Platform Admin",
        role="admin",
        is_superuser=True,
        status="active",
    )
    db_session.add_all([customer, prof_user, admin])

    cat = Category(
        id=uuid.UUID("c0000001-0000-0000-0000-000000000001"),
        name="Wedding Photography",
        slug="wedding-photography",
        segment="photography",
        description="Wedding and candid shoots",
    )
    db_session.add(cat)

    prof_profile = ProfessionalProfile(
        id=uuid.UUID("b0000001-0000-0000-0000-000000000001"),
        user_id=prof_user.id,
        display_name="Aura Weddings",
        slug="aura-weddings-test",
        headline="Premier Candid Photographer in Pune",
        bio="Specializing in candid and cinematic visual storytelling.",
        account_type="individual",
        base_city="Pune",
        state="Maharashtra",
        years_experience=7,
        avg_rating=4.9,
        total_reviews=25,
        verification_status="verified",
        profile_visibility="public",
        travel_available=True,
    )
    db_session.add(prof_profile)

    serv = Service(
        id=uuid.UUID("s0000001-0000-0000-0000-000000000001"),
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
        id=uuid.UUID("a0000001-0000-0000-0000-000000000001"),
        professional_id=prof_profile.id,
        title="Featured Weddings Portfolio",
        visibility="public",
    )
    db_session.add(port)

    proj = Project(
        id=uuid.UUID("d0000001-0000-0000-0000-000000000001"),
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
