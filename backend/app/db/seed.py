"""Deterministic development database seeder using uuid5 and Argon2id hashes."""

import asyncio
import uuid
from datetime import UTC, date, datetime, timedelta
from typing import Any

from sqlalchemy import select

from app.core.database import AsyncSessionLocal, apply_rls_context
from app.core.security import hash_password
from app.modules.bookings.models import Booking
from app.modules.enquiries.models import Enquiry, EnquiryRecipient
from app.modules.identity.models import User
from app.modules.platform.models import SubscriptionPlan
from app.modules.portfolios.models import MediaAsset, Portfolio, Project
from app.modules.professionals.models import (
    Category,
    Equipment,
    ProfessionalProfile,
    ProfessionalSkill,
    Service,
    ServicePackage,
)
from app.modules.quotations.models import Quotation
from app.modules.reviews.models import Review

SEED_NAMESPACE = uuid.uuid5(uuid.NAMESPACE_DNS, "maancamera.com")


def seed_uuid(key: str) -> uuid.UUID:
    """Return deterministic UUIDv5 derived from a semantic key."""
    return uuid.uuid5(SEED_NAMESPACE, key)


async def seed_database() -> None:
    """Populate idempotent development seed data aligned with README credentials."""
    async with AsyncSessionLocal() as db:
        await apply_rls_context(db, role="system")
        # 1. Subscription Plans
        plans_data = [
            {
                "id": seed_uuid("plan:free"),
                "name": "Free Starter",
                "slug": "free",
                "price_minor": 0,
                "currency_code": "INR",
                "billing_period": "monthly",
                "features": {"enquiries": True, "portfolio_limit": 5, "ai_search_eligible": True, "verified_badge": False},
                "max_projects": 5,
                "max_storage_gb": 2,
            },
            {
                "id": seed_uuid("plan:creator"),
                "name": "Creator Pro",
                "slug": "creator",
                "price_minor": 99900,
                "currency_code": "INR",
                "billing_period": "monthly",
                "features": {"enquiries": True, "portfolio_limit": 20, "ai_search_eligible": True, "verified_badge": True, "analytics": True},
                "max_projects": 20,
                "max_storage_gb": 15,
            },
            {
                "id": seed_uuid("plan:studio"),
                "name": "Studio Master",
                "slug": "studio",
                "price_minor": 249900,
                "currency_code": "INR",
                "billing_period": "monthly",
                "features": {"enquiries": True, "portfolio_limit": 100, "ai_search_eligible": True, "verified_badge": True, "team_members": 5},
                "max_projects": 100,
                "max_storage_gb": 100,
            },
        ]
        for plan in plans_data:
            if not await db.get(SubscriptionPlan, plan["id"]):
                res = await db.execute(select(SubscriptionPlan).where(SubscriptionPlan.slug == plan["slug"]))
                if not res.scalar_one_or_none():
                    db.add(SubscriptionPlan(**plan, is_active=True))

        # 2. Categories
        categories_data = [
            ("wedding-photography", "Wedding Photography", "Candid, traditional, and destination wedding photography", "Camera", 1),
            ("videography", "Cinematic Videography", "Wedding cinema, music videos, documentaries, and commercials", "Video", 2),
            ("aerial-drone", "Drone & Aerial", "High-altitude 4K aerial photography and cinematic drone piloting", "Plane", 3),
            ("fashion-editorial", "Fashion & Editorial", "High fashion, model portfolios, lookbooks, and magazine editorials", "Sparkles", 4),
            ("product-ecommerce", "Product & E-Commerce", "Product catalog, jewelry, FMCG, and studio photography", "Package", 5),
            ("food-hospitality", "Food & Hospitality", "Gastronomy, restaurant menus, culinary styling, and cafe lifestyle", "Utensils", 6),
            ("portrait-headshots", "Portrait & Headshots", "Executive corporate headshots, studio portraits, and family memories", "User", 7),
            ("architecture-interiors", "Architecture & Interiors", "Architectural geometry, luxury interior design, and real estate tours", "Home", 8),
        ]
        cat_ids: dict[str, uuid.UUID] = {}
        for slug, name, desc, icon, order in categories_data:
            cid = seed_uuid(f"category:{slug}")
            res = await db.execute(select(Category).where(Category.slug == slug))
            existing_cat = res.scalar_one_or_none()
            if existing_cat:
                cat_ids[slug] = existing_cat.id
            else:
                db.add(Category(id=cid, name=name, slug=slug, description=desc, icon_name=icon, is_active=True, display_order=order))
                cat_ids[slug] = cid

        # 3. Users (Real Argon2id password hashes matching README dev accounts)
        dev_pass_hash = hash_password("DevPass@2026!")
        admin_pass_hash = hash_password("DevAdmin@2026!")
        now = datetime.now(UTC)

        users_data = [
            ("admin@maancamera.com", "+919876543210", admin_pass_hash, "MaanCamera Administrator", "admin", True),
            ("arjun.mehta@example.com", "+919800011122", dev_pass_hash, "Arjun Mehta", "customer", False),
            ("priya.sharma@example.com", "+919811122233", dev_pass_hash, "Priya Sharma", "customer", False),
            ("contact@auraweddings.com", "+919822233344", dev_pass_hash, "Rohan Kulkarni", "professional", False),
            ("studio@drishtivisuals.com", "+919833344455", dev_pass_hash, "Ananya Sen", "professional", False),
            ("vikram.singh@example.com", "+919844455566", dev_pass_hash, "Vikram Singh", "professional", False),
        ]
        user_ids: dict[str, uuid.UUID] = {}
        for email, phone, p_hash, full_name, role, is_super in users_data:
            uid = seed_uuid(f"user:{email}")
            res = await db.execute(select(User).where(User.email == email))
            existing_user = res.scalar_one_or_none()
            if existing_user:
                user_ids[email] = existing_user.id
            else:
                db.add(
                    User(
                        id=uid,
                        email=email,
                        phone=phone,
                        password_hash=p_hash,
                        full_name=full_name,
                        role=role,
                        status="active",
                        is_superuser=is_super,
                        email_verified_at=now,
                    )
                )
                user_ids[email] = uid

        await db.flush()

        # 4. Professional Profiles
        profs_data: list[dict[str, Any]] = [
            {
                "id": seed_uuid("prof:aura-weddings"),
                "owner_user_id": user_ids["contact@auraweddings.com"],
                "display_name": "Aura Weddings & Films",
                "slug": "aura-weddings",
                "headline": "Award-winning Candid Wedding Photographer & Cinematic Storyteller",
                "biography": "Capturing authentic emotions and timeless wedding stories across Pune, Mumbai, and destination locations across India for over 8 years.",
                "professional_type": "studio",
                "years_experience": 8,
                "base_city": "Pune",
                "state": "Maharashtra",
                "service_radius_km": 100,
                "travel_available": True,
                "verification_status": "verified",
                "profile_visibility": "public",
                "avg_rating": 4.95,
                "total_reviews": 38,
                "completed_bookings_count": 45,
            },
            {
                "id": seed_uuid("prof:drishti-visuals"),
                "owner_user_id": user_ids["studio@drishtivisuals.com"],
                "display_name": "Drishti Visuals Studio",
                "slug": "drishti-visuals",
                "headline": "High Fashion, Editorial & Luxury Lookbooks",
                "biography": "Mumbai-based fashion and advertising photographer working with Indian apparel designers, beauty brands, and modeling talent.",
                "professional_type": "studio",
                "years_experience": 6,
                "base_city": "Mumbai",
                "state": "Maharashtra",
                "service_radius_km": 60,
                "travel_available": True,
                "verification_status": "verified",
                "profile_visibility": "public",
                "avg_rating": 4.88,
                "total_reviews": 24,
                "completed_bookings_count": 31,
            },
            {
                "id": seed_uuid("prof:vikram-aerocinematics"),
                "owner_user_id": user_ids["vikram.singh@example.com"],
                "display_name": "Vikram Singh AeroCinematics",
                "slug": "vikram-aerocinematics",
                "headline": "Cinematographer & DGCA-Certified Drone Pilot",
                "biography": "Cinematic drone operator, music video cinematographer, and corporate brand film director.",
                "professional_type": "team",
                "years_experience": 7,
                "base_city": "Bengaluru",
                "state": "Karnataka",
                "service_radius_km": 150,
                "travel_available": True,
                "verification_status": "verified",
                "profile_visibility": "public",
                "avg_rating": 4.92,
                "total_reviews": 19,
                "completed_bookings_count": 27,
            },
        ]
        prof_ids: dict[str, uuid.UUID] = {}
        for p in profs_data:
            res = await db.execute(select(ProfessionalProfile).where(ProfessionalProfile.slug == p["slug"]))
            existing_prof = res.scalar_one_or_none()
            if existing_prof:
                prof_ids[p["slug"]] = existing_prof.id
            else:
                db.add(ProfessionalProfile(**p))
                prof_ids[p["slug"]] = p["id"]

        await db.flush()

        # 5. Services, Portfolios, Projects, Skills & Equipment
        svc_id_1 = seed_uuid("service:aura-wedding-full")
        if not await db.get(Service, svc_id_1):
            svc1 = Service(
                id=svc_id_1,
                professional_id=prof_ids["aura-weddings"],
                category_id=cat_ids["wedding-photography"],
                name="2-Day Complete Wedding Photo & Cinema",
                description="Full coverage of Sangeet, Wedding Ceremony, and Reception.",
                pricing_type="starting_from",
                starting_price_minor=7500000,
                currency_code="INR",
                is_active=True,
            )
            svc2 = Service(
                id=seed_uuid("service:drishti-fashion"),
                professional_id=prof_ids["drishti-visuals"],
                category_id=cat_ids["fashion-editorial"],
                name="Designer Fashion Lookbook & Campaign",
                description="Full-day studio and location fashion campaign.",
                pricing_type="fixed",
                starting_price_minor=5000000,
                currency_code="INR",
                is_active=True,
            )
            svc3 = Service(
                id=seed_uuid("service:vikram-aerial"),
                professional_id=prof_ids["vikram-aerocinematics"],
                category_id=cat_ids["aerial-drone"],
                name="Cinematic 4K Aerial Drone Coverage",
                description="Licensed aerial piloting for events and commercials.",
                pricing_type="daily",
                starting_price_minor=2500000,
                currency_code="INR",
                is_active=True,
            )
            db.add_all([svc1, svc2, svc3])
            db.add(
                ServicePackage(
                    id=seed_uuid("pkg:aura-signature"),
                    service_id=svc_id_1,
                    package_name="Signature Candid + Cinema",
                    description="2 Senior Candid Photographers + 2 Cinematographers with drone teaser",
                    price_minor=8500000,
                    currency_code="INR",
                    estimated_duration="2 Days",
                    deliverables=["500+ Edited Photos", "3-5 min Cinematic Teaser"],
                    is_popular=True,
                )
            )
            db.add(
                ProfessionalSkill(
                    id=seed_uuid("skill:aura-candid"),
                    professional_id=prof_ids["aura-weddings"],
                    category_id=cat_ids["wedding-photography"],
                    skill_name="Candid Wedding Photography",
                    proficiency_level="master",
                    years_experience=8,
                    is_primary=True,
                )
            )
            db.add(
                Equipment(
                    id=seed_uuid("equip:aura-sony-a7iv"),
                    professional_id=prof_ids["aura-weddings"],
                    equipment_type="camera",
                    brand="Sony",
                    model="Alpha 7 IV",
                    description="Dual body mirrorless full-frame kit",
                    is_primary=True,
                    verified_at=now,
                )
            )

        # Portfolios & Sample Project
        port_id = seed_uuid("portfolio:aura-weddings")
        if not await db.get(Portfolio, port_id):
            db.add(
                Portfolio(
                    id=port_id,
                    professional_id=prof_ids["aura-weddings"],
                    title="Weddings & Celebrations",
                    description="Real celebrations captured with candid warmth.",
                    visibility="public",
                )
            )
            await db.flush()
            proj_id = seed_uuid("project:aniket-sneha")
            asset_id = seed_uuid("asset:aniket-sneha-01")
            db.add(
                Project(
                    id=proj_id,
                    portfolio_id=port_id,
                    category_id=cat_ids["wedding-photography"],
                    title="The Royal Maharashtrian Wedding of Aniket & Sneha",
                    slug="aniket-sneha-pune-wedding",
                    style="Candid Documentary",
                    location="Pune, Maharashtra",
                    project_date=date(2026, 2, 14),
                    description="2-day traditional wedding celebration in Pune.",
                    publication_status="published",
                    tags=["candid", "wedding", "pune"],
                )
            )
            await db.flush()
            db.add(
                MediaAsset(
                    id=asset_id,
                    project_id=proj_id,
                    storage_key="public/seed/aniket_sneha_01.webp",
                    public_url="https://images.unsplash.com/photo-1519741497674-611481863552?auto=format&fit=crop&w=1200&q=80",
                    media_type="image",
                    mime_type="image/webp",
                    file_size_bytes=245000,
                    width=1920,
                    height=1280,
                    checksum="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
                    display_order=1,
                )
            )
            await db.flush()
            proj_res = await db.get(Project, proj_id)
            if proj_res:
                proj_res.cover_asset_id = asset_id

        # Sample Enquiry, Quotation, Booking, Review
        enq_id = seed_uuid("enquiry:demo-1")
        if not await db.get(Enquiry, enq_id):
            db.add(
                Enquiry(
                    id=enq_id,
                    customer_id=user_ids["arjun.mehta@example.com"],
                    category_id=cat_ids["wedding-photography"],
                    title="Candid Wedding Photographer in Pune for 2 Days",
                    description="Looking for candid wedding coverage in Koregaon Park, Pune.",
                    shoot_date=date(2026, 3, 20),
                    duration_days=2,
                    location="Koregaon Park, Pune",
                    city="Pune",
                    budget_min_minor=6000000,
                    budget_max_minor=9000000,
                    currency_code="INR",
                    status="booked",
                )
            )
            await db.flush()
            db.add(
                EnquiryRecipient(
                    id=seed_uuid("enq_recip:demo-1"),
                    enquiry_id=enq_id,
                    professional_id=prof_ids["aura-weddings"],
                    recipient_status="quoted",
                )
            )
            quot_id = seed_uuid("quotation:demo-1")
            db.add(
                Quotation(
                    id=quot_id,
                    enquiry_id=enq_id,
                    professional_id=prof_ids["aura-weddings"],
                    version_number=1,
                    total_amount_minor=8000000,
                    advance_amount_minor=2000000,
                    currency_code="INR",
                    scope_of_work="2 Days Candid Photography + Cinematic Wedding Highlights",
                    deliverables=["500 edited candid photos", "Cinematic highlight reel"],
                    valid_until=now + timedelta(days=14),
                    status="accepted",
                )
            )
            await db.flush()
            bk_id = seed_uuid("booking:demo-1")
            db.add(
                Booking(
                    id=bk_id,
                    enquiry_id=enq_id,
                    quotation_id=quot_id,
                    customer_id=user_ids["arjun.mehta@example.com"],
                    professional_id=prof_ids["aura-weddings"],
                    shoot_date=date(2026, 3, 20),
                    location="Koregaon Park, Pune",
                    agreed_amount_minor=8000000,
                    paid_amount_minor=8000000,
                    currency_code="INR",
                    booking_status="completed",
                    completion_status="customer_accepted",
                )
            )
            await db.flush()
            db.add(
                Review(
                    id=seed_uuid("review:demo-1"),
                    booking_id=bk_id,
                    customer_id=user_ids["arjun.mehta@example.com"],
                    professional_id=prof_ids["aura-weddings"],
                    overall_rating=5.0,
                    work_quality_rating=5.0,
                    communication_rating=5.0,
                    punctuality_rating=5.0,
                    value_rating=4.8,
                    review_text="Rohan and his crew were spectacular! Unobtrusive candid moments and timely delivery.",
                    moderation_status="approved",
                )
            )

        await db.commit()
        print("MaanCamera seed completed successfully (deterministic uuid5 + Argon2id).")


if __name__ == "__main__":
    asyncio.run(seed_database())
