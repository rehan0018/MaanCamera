"""Initial relational, vector, and RLS schema derived from ORM models.

Revision ID: 20261126_0001
Revises:
Create Date: 2026-11-26 08:40:00+00:00
"""

from collections.abc import Sequence

import pgvector.sqlalchemy
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "20261126_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    is_postgres = bind.dialect.name == "postgresql"

    if is_postgres:
        op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')
        op.execute('CREATE EXTENSION IF NOT EXISTS "pgcrypto"')
        op.execute('CREATE EXTENSION IF NOT EXISTS "vector"')
        op.execute('CREATE EXTENSION IF NOT EXISTS "pg_trgm"')

    op.create_table(
        "categories",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("parent_id", sa.UUID(), nullable=True),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("slug", sa.String(length=120), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("icon_name", sa.String(length=50), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("display_order", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["parent_id"], ["categories.id"], name=op.f("fk_categories_parent_id_categories"), ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_categories")),
    )
    op.create_index(op.f("ix_categories_slug"), "categories", ["slug"], unique=True)

    op.create_table(
        "idempotency_records",
        sa.Column("key", sa.String(length=256), nullable=False),
        sa.Column("action", sa.String(length=100), nullable=False),
        sa.Column("response_code", sa.Integer(), nullable=False),
        sa.Column("response_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("key", name=op.f("pk_idempotency_records")),
    )

    op.create_table(
        "organizations",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("slug", sa.String(length=220), nullable=False),
        sa.Column("organization_type", sa.String(length=50), nullable=False),
        sa.Column("registration_country", sa.String(length=2), nullable=False),
        sa.Column("gstin", sa.String(length=20), nullable=True),
        sa.Column("logo_url", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "organization_type IN ('studio', 'agency', 'production_house', 'collective')",
            name=op.f("ck_organizations_type"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_organizations")),
        sa.UniqueConstraint("slug", name=op.f("uq_organizations_slug")),
    )

    op.create_table(
        "subscription_plans",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=50), nullable=False),
        sa.Column("slug", sa.String(length=60), nullable=False),
        sa.Column("price_minor", sa.BigInteger(), nullable=False),
        sa.Column("currency_code", sa.String(length=3), nullable=False),
        sa.Column("billing_period", sa.String(length=20), nullable=False),
        sa.Column("features", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("max_projects", sa.Integer(), nullable=False),
        sa.Column("max_storage_gb", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.CheckConstraint("billing_period IN ('monthly', 'yearly')", name=op.f("ck_sub_plans_period")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_subscription_plans")),
        sa.UniqueConstraint("name", name=op.f("uq_subscription_plans_name")),
        sa.UniqueConstraint("slug", name=op.f("uq_subscription_plans_slug")),
    )

    op.create_table(
        "users",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("phone", sa.String(length=20), nullable=True),
        sa.Column("password_hash", sa.Text(), nullable=True),
        sa.Column("full_name", sa.String(length=150), nullable=False),
        sa.Column("role", sa.String(length=30), nullable=False),
        sa.Column("avatar_url", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("is_superuser", sa.Boolean(), nullable=False),
        sa.Column("email_verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("phone_verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("role IN ('customer', 'professional', 'admin')", name=op.f("ck_users_role")),
        sa.CheckConstraint(
            "status IN ('active', 'suspended', 'pending_verification', 'deactivated')",
            name=op.f("ck_users_status"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_users")),
    )
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)
    op.create_index(op.f("ix_users_phone"), "users", ["phone"], unique=True)

    op.create_table(
        "audit_logs",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("actor_user_id", sa.UUID(), nullable=True),
        sa.Column("action", sa.String(length=100), nullable=False),
        sa.Column("resource_type", sa.String(length=100), nullable=False),
        sa.Column("resource_id", sa.UUID(), nullable=True),
        sa.Column("ip_address", postgresql.INET(), nullable=True),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["actor_user_id"], ["users.id"], name=op.f("fk_audit_logs_actor_user_id_users"), ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_audit_logs")),
    )

    op.create_table(
        "content_reports",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("reporter_user_id", sa.UUID(), nullable=False),
        sa.Column("content_type", sa.String(length=50), nullable=False),
        sa.Column("content_id", sa.UUID(), nullable=False),
        sa.Column("reason", sa.String(length=100), nullable=False),
        sa.Column("details", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["reporter_user_id"],
            ["users.id"],
            name=op.f("fk_content_reports_reporter_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_content_reports")),
    )

    op.create_table(
        "enquiries",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("customer_id", sa.UUID(), nullable=False),
        sa.Column("category_id", sa.UUID(), nullable=False),
        sa.Column("title", sa.String(length=250), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("shoot_date", sa.Date(), nullable=True),
        sa.Column("duration_days", sa.Integer(), nullable=False),
        sa.Column("location", sa.String(length=200), nullable=False),
        sa.Column("city", sa.String(length=100), nullable=False),
        sa.Column("budget_min_minor", sa.BigInteger(), nullable=True),
        sa.Column("budget_max_minor", sa.BigInteger(), nullable=True),
        sa.Column("currency_code", sa.String(length=3), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "status IN ('open', 'responded', 'booked', 'expired', 'cancelled')", name=op.f("ck_enquiries_status")
        ),
        sa.ForeignKeyConstraint(
            ["category_id"], ["categories.id"], name=op.f("fk_enquiries_category_id_categories"), ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["customer_id"], ["users.id"], name=op.f("fk_enquiries_customer_id_users"), ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_enquiries")),
    )
    op.create_index(op.f("ix_enquiries_customer_id"), "enquiries", ["customer_id"], unique=False)

    op.create_table(
        "organization_members",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("organization_id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("role", sa.String(length=30), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("joined_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "role IN ('owner', 'admin', 'manager', 'professional', 'editor', 'viewer', 'member')",
            name=op.f("ck_org_members_role"),
        ),
        sa.CheckConstraint("status IN ('active', 'invited', 'suspended')", name=op.f("ck_org_members_status")),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name=op.f("fk_organization_members_organization_id_organizations"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_organization_members_user_id_users"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_organization_members")),
        sa.UniqueConstraint("organization_id", "user_id", name="uq_org_user"),
    )

    op.create_table(
        "professional_profiles",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("owner_user_id", sa.UUID(), nullable=False),
        sa.Column("organization_id", sa.UUID(), nullable=True),
        sa.Column("display_name", sa.String(length=200), nullable=False),
        sa.Column("slug", sa.String(length=220), nullable=False),
        sa.Column("headline", sa.String(length=250), nullable=True),
        sa.Column("biography", sa.Text(), nullable=True),
        sa.Column("profile_image", sa.Text(), nullable=True),
        sa.Column("cover_image", sa.Text(), nullable=True),
        sa.Column("professional_type", sa.String(length=50), nullable=False),
        sa.Column("years_experience", sa.Integer(), nullable=False),
        sa.Column("base_city", sa.String(length=100), nullable=False),
        sa.Column("state", sa.String(length=100), nullable=False),
        sa.Column("country_code", sa.String(length=2), nullable=False),
        sa.Column("latitude", sa.Numeric(precision=10, scale=7), nullable=True),
        sa.Column("longitude", sa.Numeric(precision=10, scale=7), nullable=True),
        sa.Column("service_radius_km", sa.Integer(), nullable=False),
        sa.Column("travel_available", sa.Boolean(), nullable=False),
        sa.Column("verification_status", sa.String(length=30), nullable=False),
        sa.Column("profile_visibility", sa.String(length=30), nullable=False),
        sa.Column("avg_rating", sa.Numeric(precision=3, scale=2), nullable=False),
        sa.Column("total_reviews", sa.Integer(), nullable=False),
        sa.Column("completed_bookings_count", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "professional_type IN ('individual', 'team', 'studio', 'crew')", name=op.f("ck_prof_profiles_type")
        ),
        sa.CheckConstraint(
            "profile_visibility IN ('public', 'unlisted', 'private')", name=op.f("ck_prof_profiles_visibility")
        ),
        sa.CheckConstraint(
            "verification_status IN ('unverified', 'pending', 'verified', 'rejected')",
            name=op.f("ck_prof_profiles_verification"),
        ),
        sa.CheckConstraint("years_experience >= 0", name=op.f("ck_prof_profiles_years")),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name=op.f("fk_professional_profiles_organization_id_organizations"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["owner_user_id"],
            ["users.id"],
            name=op.f("fk_professional_profiles_owner_user_id_users"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_professional_profiles")),
    )
    op.create_index(op.f("ix_professional_profiles_base_city"), "professional_profiles", ["base_city"], unique=False)
    op.create_index(
        op.f("ix_professional_profiles_owner_user_id"), "professional_profiles", ["owner_user_id"], unique=False
    )
    op.create_index(op.f("ix_professional_profiles_slug"), "professional_profiles", ["slug"], unique=True)

    op.create_table(
        "recommendation_sessions",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("customer_id", sa.UUID(), nullable=True),
        sa.Column("query_text", sa.Text(), nullable=False),
        sa.Column("extracted_requirements", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("ranking_version", sa.String(length=50), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["customer_id"],
            ["users.id"],
            name=op.f("fk_recommendation_sessions_customer_id_users"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_recommendation_sessions")),
    )

    op.create_table(
        "subscriptions",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=True),
        sa.Column("organization_id", sa.UUID(), nullable=True),
        sa.Column("plan_id", sa.UUID(), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("current_period_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("current_period_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "status IN ('active', 'past_due', 'cancelled', 'trialing')", name=op.f("ck_subscriptions_status")
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name=op.f("fk_subscriptions_organization_id_organizations"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["plan_id"],
            ["subscription_plans.id"],
            name=op.f("fk_subscriptions_plan_id_subscription_plans"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_subscriptions_user_id_users"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_subscriptions")),
    )

    op.create_table(
        "user_sessions",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("session_token_hash", sa.String(length=128), nullable=False),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column("ip_address", postgresql.INET(), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_user_sessions_user_id_users"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_user_sessions")),
    )
    op.create_index(op.f("ix_user_sessions_session_token_hash"), "user_sessions", ["session_token_hash"], unique=True)
    op.create_index(op.f("ix_user_sessions_user_id"), "user_sessions", ["user_id"], unique=False)

    op.create_table(
        "enquiry_recipients",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("enquiry_id", sa.UUID(), nullable=False),
        sa.Column("professional_id", sa.UUID(), nullable=False),
        sa.Column("recipient_status", sa.String(length=30), nullable=False),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("viewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "recipient_status IN ('sent', 'viewed', 'quoted', 'declined')",
            name=op.f("ck_enquiry_recipients_status"),
        ),
        sa.ForeignKeyConstraint(
            ["enquiry_id"], ["enquiries.id"], name=op.f("fk_enquiry_recipients_enquiry_id_enquiries"), ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["professional_id"],
            ["professional_profiles.id"],
            name=op.f("fk_enquiry_recipients_professional_id_professional_profiles"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_enquiry_recipients")),
        sa.UniqueConstraint("enquiry_id", "professional_id", name="uq_enquiry_recipient"),
    )
    op.create_index(op.f("ix_enquiry_recipients_enquiry_id"), "enquiry_recipients", ["enquiry_id"], unique=False)
    op.create_index(
        op.f("ix_enquiry_recipients_professional_id"), "enquiry_recipients", ["professional_id"], unique=False
    )

    op.create_table(
        "equipment",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("professional_id", sa.UUID(), nullable=False),
        sa.Column("equipment_type", sa.String(length=50), nullable=False),
        sa.Column("brand", sa.String(length=100), nullable=False),
        sa.Column("model", sa.String(length=150), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_primary", sa.Boolean(), nullable=False),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "equipment_type IN ('camera', 'lens', 'drone', 'lighting', 'audio', 'stabilizer', 'workstation', 'other')",
            name=op.f("ck_equipment_type"),
        ),
        sa.ForeignKeyConstraint(
            ["professional_id"],
            ["professional_profiles.id"],
            name=op.f("fk_equipment_professional_id_professional_profiles"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_equipment")),
    )

    op.create_table(
        "portfolios",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("professional_id", sa.UUID(), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("visibility", sa.String(length=30), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("visibility IN ('public', 'unlisted', 'private')", name=op.f("ck_portfolios_visibility")),
        sa.ForeignKeyConstraint(
            ["professional_id"],
            ["professional_profiles.id"],
            name=op.f("fk_portfolios_professional_id_professional_profiles"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_portfolios")),
    )

    op.create_table(
        "professional_skills",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("professional_id", sa.UUID(), nullable=False),
        sa.Column("category_id", sa.UUID(), nullable=False),
        sa.Column("skill_name", sa.String(length=100), nullable=False),
        sa.Column("proficiency_level", sa.String(length=30), nullable=False),
        sa.Column("years_experience", sa.Integer(), nullable=False),
        sa.Column("is_primary", sa.Boolean(), nullable=False),
        sa.CheckConstraint(
            "proficiency_level IN ('beginner', 'intermediate', 'advanced', 'master')",
            name=op.f("ck_prof_skills_level"),
        ),
        sa.ForeignKeyConstraint(
            ["category_id"],
            ["categories.id"],
            name=op.f("fk_professional_skills_category_id_categories"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["professional_id"],
            ["professional_profiles.id"],
            name=op.f("fk_professional_skills_professional_id_professional_profiles"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_professional_skills")),
        sa.UniqueConstraint("professional_id", "category_id", "skill_name", name="uq_prof_skill_category"),
    )
    op.create_index(op.f("ix_professional_skills_category_id"), "professional_skills", ["category_id"], unique=False)
    op.create_index(
        op.f("ix_professional_skills_professional_id"), "professional_skills", ["professional_id"], unique=False
    )

    op.create_table(
        "quotations",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("enquiry_id", sa.UUID(), nullable=False),
        sa.Column("professional_id", sa.UUID(), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("total_amount_minor", sa.BigInteger(), nullable=False),
        sa.Column("currency_code", sa.String(length=3), nullable=False),
        sa.Column("advance_amount_minor", sa.BigInteger(), nullable=False),
        sa.Column("scope_of_work", sa.Text(), nullable=False),
        sa.Column("deliverables", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("terms", sa.Text(), nullable=True),
        sa.Column("valid_until", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "status IN ('draft', 'sent', 'revised', 'accepted', 'rejected', 'expired')",
            name=op.f("ck_quotations_status"),
        ),
        sa.ForeignKeyConstraint(
            ["enquiry_id"], ["enquiries.id"], name=op.f("fk_quotations_enquiry_id_enquiries"), ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["professional_id"],
            ["professional_profiles.id"],
            name=op.f("fk_quotations_professional_id_professional_profiles"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_quotations")),
        sa.UniqueConstraint("enquiry_id", "professional_id", "version_number", name="uq_quotation_version"),
    )
    op.create_index(op.f("ix_quotations_enquiry_id"), "quotations", ["enquiry_id"], unique=False)
    op.create_index(op.f("ix_quotations_professional_id"), "quotations", ["professional_id"], unique=False)

    op.create_table(
        "recommendation_items",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("session_id", sa.UUID(), nullable=False),
        sa.Column("professional_id", sa.UUID(), nullable=False),
        sa.Column("relevance_score", sa.Numeric(precision=5, scale=4), nullable=False),
        sa.Column("ranking_position", sa.Integer(), nullable=False),
        sa.Column("explanation_data", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["professional_id"],
            ["professional_profiles.id"],
            name=op.f("fk_recommendation_items_professional_id_professional_profiles"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["session_id"],
            ["recommendation_sessions.id"],
            name=op.f("fk_recommendation_items_session_id_recommendation_sessions"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_recommendation_items")),
    )
    op.create_index(op.f("ix_recommendation_items_session_id"), "recommendation_items", ["session_id"], unique=False)

    op.create_table(
        "services",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("professional_id", sa.UUID(), nullable=False),
        sa.Column("category_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("pricing_type", sa.String(length=30), nullable=False),
        sa.Column("starting_price_minor", sa.BigInteger(), nullable=False),
        sa.Column("currency_code", sa.String(length=3), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "pricing_type IN ('fixed', 'starting_from', 'hourly', 'daily', 'custom_quote')",
            name=op.f("ck_services_pricing_type"),
        ),
        sa.ForeignKeyConstraint(
            ["category_id"], ["categories.id"], name=op.f("fk_services_category_id_categories"), ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["professional_id"],
            ["professional_profiles.id"],
            name=op.f("fk_services_professional_id_professional_profiles"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_services")),
    )

    op.create_table(
        "verification_requests",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("professional_id", sa.UUID(), nullable=False),
        sa.Column("document_type", sa.String(length=50), nullable=False),
        sa.Column("document_storage_key", sa.String(length=500), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("reviewed_by_user_id", sa.UUID(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "document_type IN ('government_id', 'business_license', 'gst_certificate', 'equipment_invoice')",
            name=op.f("ck_verification_doc_type"),
        ),
        sa.CheckConstraint("status IN ('pending', 'verified', 'rejected')", name=op.f("ck_verification_status")),
        sa.ForeignKeyConstraint(
            ["professional_id"],
            ["professional_profiles.id"],
            name=op.f("fk_verification_requests_professional_id_professional_profiles"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["reviewed_by_user_id"],
            ["users.id"],
            name=op.f("fk_verification_requests_reviewed_by_user_id_users"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_verification_requests")),
    )

    op.create_table(
        "bookings",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("enquiry_id", sa.UUID(), nullable=True),
        sa.Column("quotation_id", sa.UUID(), nullable=True),
        sa.Column("customer_id", sa.UUID(), nullable=False),
        sa.Column("professional_id", sa.UUID(), nullable=False),
        sa.Column("shoot_date", sa.Date(), nullable=False),
        sa.Column("location", sa.String(length=250), nullable=False),
        sa.Column("agreed_amount_minor", sa.BigInteger(), nullable=False),
        sa.Column("paid_amount_minor", sa.BigInteger(), nullable=False),
        sa.Column("currency_code", sa.String(length=3), nullable=False),
        sa.Column("booking_status", sa.String(length=30), nullable=False),
        sa.Column("completion_status", sa.String(length=30), nullable=False),
        sa.Column("cancellation_reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "booking_status IN ('pending_payment', 'confirmed', 'in_progress', 'completed', 'cancelled', 'disputed')",
            name=op.f("ck_bookings_status"),
        ),
        sa.CheckConstraint(
            "completion_status IN ('pending', 'delivered', 'customer_accepted')",
            name=op.f("ck_bookings_completion_status"),
        ),
        sa.ForeignKeyConstraint(
            ["customer_id"], ["users.id"], name=op.f("fk_bookings_customer_id_users"), ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["enquiry_id"], ["enquiries.id"], name=op.f("fk_bookings_enquiry_id_enquiries"), ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["professional_id"],
            ["professional_profiles.id"],
            name=op.f("fk_bookings_professional_id_professional_profiles"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["quotation_id"], ["quotations.id"], name=op.f("fk_bookings_quotation_id_quotations"), ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_bookings")),
        sa.UniqueConstraint("quotation_id", name=op.f("uq_bookings_quotation_id")),
    )
    op.create_index(op.f("ix_bookings_customer_id"), "bookings", ["customer_id"], unique=False)
    op.create_index(op.f("ix_bookings_enquiry_id"), "bookings", ["enquiry_id"], unique=False)
    op.create_index(op.f("ix_bookings_professional_id"), "bookings", ["professional_id"], unique=False)

    op.create_table(
        "projects",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("portfolio_id", sa.UUID(), nullable=False),
        sa.Column("category_id", sa.UUID(), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("slug", sa.String(length=220), nullable=False),
        sa.Column("style", sa.String(length=100), nullable=True),
        sa.Column("location", sa.String(length=150), nullable=True),
        sa.Column("project_date", sa.Date(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("cover_asset_id", sa.UUID(), nullable=True),
        sa.Column("publication_status", sa.String(length=30), nullable=False),
        sa.Column("tags", postgresql.ARRAY(sa.String()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "publication_status IN ('draft', 'published', 'archived')", name=op.f("ck_projects_publication_status")
        ),
        sa.ForeignKeyConstraint(
            ["category_id"], ["categories.id"], name=op.f("fk_projects_category_id_categories"), ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["portfolio_id"], ["portfolios.id"], name=op.f("fk_projects_portfolio_id_portfolios"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_projects")),
        sa.UniqueConstraint("portfolio_id", "slug", name="uq_portfolio_project_slug"),
    )
    op.create_index(op.f("ix_projects_category_id"), "projects", ["category_id"], unique=False)
    op.create_index(op.f("ix_projects_portfolio_id"), "projects", ["portfolio_id"], unique=False)

    op.create_table(
        "service_packages",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("service_id", sa.UUID(), nullable=False),
        sa.Column("package_name", sa.String(length=150), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("price_minor", sa.BigInteger(), nullable=False),
        sa.Column("currency_code", sa.String(length=3), nullable=False),
        sa.Column("estimated_duration", sa.String(length=100), nullable=True),
        sa.Column("deliverables", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("terms", sa.Text(), nullable=True),
        sa.Column("is_popular", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["service_id"], ["services.id"], name=op.f("fk_service_packages_service_id_services"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_service_packages")),
    )

    op.create_table(
        "conversations",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("enquiry_id", sa.UUID(), nullable=True),
        sa.Column("booking_id", sa.UUID(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["booking_id"], ["bookings.id"], name=op.f("fk_conversations_booking_id_bookings"), ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["enquiry_id"], ["enquiries.id"], name=op.f("fk_conversations_enquiry_id_enquiries"), ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_conversations")),
    )

    op.create_table(
        "media_assets",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("project_id", sa.UUID(), nullable=False),
        sa.Column("storage_key", sa.String(length=500), nullable=False),
        sa.Column("public_url", sa.Text(), nullable=True),
        sa.Column("media_type", sa.String(length=20), nullable=False),
        sa.Column("mime_type", sa.String(length=100), nullable=False),
        sa.Column("file_size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("width", sa.Integer(), nullable=True),
        sa.Column("height", sa.Integer(), nullable=True),
        sa.Column("duration_seconds", sa.Integer(), nullable=True),
        sa.Column("checksum", sa.String(length=64), nullable=False),
        sa.Column("processing_status", sa.String(length=30), nullable=False),
        sa.Column("copyright_declaration_status", sa.String(length=30), nullable=False),
        sa.Column("display_order", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "copyright_declaration_status IN ('declared', 'verified', 'disputed')",
            name=op.f("ck_media_assets_copyright"),
        ),
        sa.CheckConstraint("media_type IN ('image', 'video')", name=op.f("ck_media_assets_type")),
        sa.CheckConstraint(
            "processing_status IN ('pending', 'processing', 'completed', 'failed')",
            name=op.f("ck_media_assets_processing"),
        ),
        sa.ForeignKeyConstraint(
            ["project_id"], ["projects.id"], name=op.f("fk_media_assets_project_id_projects"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_media_assets")),
    )
    op.create_index(op.f("ix_media_assets_project_id"), "media_assets", ["project_id"], unique=False)

    op.create_foreign_key(
        "fk_projects_cover_asset",
        "projects",
        "media_assets",
        ["cover_asset_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.create_table(
        "payments",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("booking_id", sa.UUID(), nullable=False),
        sa.Column("provider", sa.String(length=50), nullable=False),
        sa.Column("provider_order_id", sa.String(length=100), nullable=True),
        sa.Column("provider_payment_id", sa.String(length=100), nullable=True),
        sa.Column("amount_minor", sa.BigInteger(), nullable=False),
        sa.Column("currency_code", sa.String(length=3), nullable=False),
        sa.Column("payment_status", sa.String(length=30), nullable=False),
        sa.Column("payment_type", sa.String(length=30), nullable=False),
        sa.Column("signature", sa.String(length=256), nullable=True),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "payment_status IN ('pending', 'captured', 'failed', 'refunded')", name=op.f("ck_payments_status")
        ),
        sa.CheckConstraint("payment_type IN ('advance', 'balance', 'full')", name=op.f("ck_payments_type")),
        sa.CheckConstraint("provider IN ('mock', 'razorpay', 'bank_transfer')", name=op.f("ck_payments_provider")),
        sa.ForeignKeyConstraint(
            ["booking_id"], ["bookings.id"], name=op.f("fk_payments_booking_id_bookings"), ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_payments")),
    )
    op.create_index(op.f("ix_payments_booking_id"), "payments", ["booking_id"], unique=False)
    op.create_index(op.f("ix_payments_provider_payment_id"), "payments", ["provider_payment_id"], unique=False)

    op.create_table(
        "reviews",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("booking_id", sa.UUID(), nullable=False),
        sa.Column("customer_id", sa.UUID(), nullable=False),
        sa.Column("professional_id", sa.UUID(), nullable=False),
        sa.Column("overall_rating", sa.Numeric(precision=2, scale=1), nullable=False),
        sa.Column("work_quality_rating", sa.Numeric(precision=2, scale=1), nullable=False),
        sa.Column("communication_rating", sa.Numeric(precision=2, scale=1), nullable=False),
        sa.Column("punctuality_rating", sa.Numeric(precision=2, scale=1), nullable=False),
        sa.Column("value_rating", sa.Numeric(precision=2, scale=1), nullable=False),
        sa.Column("review_text", sa.Text(), nullable=False),
        sa.Column("moderation_status", sa.String(length=30), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "moderation_status IN ('pending', 'approved', 'flagged', 'hidden')",
            name=op.f("ck_reviews_moderation_status"),
        ),
        sa.CheckConstraint(
            "communication_rating >= 1.0 AND communication_rating <= 5.0", name=op.f("ck_reviews_communication")
        ),
        sa.CheckConstraint(
            "overall_rating >= 1.0 AND overall_rating <= 5.0", name=op.f("ck_reviews_overall_rating")
        ),
        sa.CheckConstraint(
            "punctuality_rating >= 1.0 AND punctuality_rating <= 5.0", name=op.f("ck_reviews_punctuality")
        ),
        sa.CheckConstraint("value_rating >= 1.0 AND value_rating <= 5.0", name=op.f("ck_reviews_value")),
        sa.CheckConstraint(
            "work_quality_rating >= 1.0 AND work_quality_rating <= 5.0", name=op.f("ck_reviews_work_quality")
        ),
        sa.ForeignKeyConstraint(
            ["booking_id"], ["bookings.id"], name=op.f("fk_reviews_booking_id_bookings"), ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["customer_id"], ["users.id"], name=op.f("fk_reviews_customer_id_users"), ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["professional_id"],
            ["professional_profiles.id"],
            name=op.f("fk_reviews_professional_id_professional_profiles"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_reviews")),
    )
    op.create_index(op.f("ix_reviews_booking_id"), "reviews", ["booking_id"], unique=True)
    op.create_index(op.f("ix_reviews_customer_id"), "reviews", ["customer_id"], unique=False)
    op.create_index(op.f("ix_reviews_professional_id"), "reviews", ["professional_id"], unique=False)

    op.create_table(
        "conversation_participants",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("conversation_id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("participant_role", sa.String(length=30), nullable=False),
        sa.CheckConstraint(
            "participant_role IN ('customer', 'professional', 'admin')", name=op.f("ck_conv_participant_role")
        ),
        sa.ForeignKeyConstraint(
            ["conversation_id"],
            ["conversations.id"],
            name=op.f("fk_conversation_participants_conversation_id_conversations"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_conversation_participants_user_id_users"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_conversation_participants")),
        sa.UniqueConstraint("conversation_id", "user_id", name="uq_conv_participant"),
    )

    op.create_table(
        "messages",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("conversation_id", sa.UUID(), nullable=False),
        sa.Column("sender_id", sa.UUID(), nullable=False),
        sa.Column("message_type", sa.String(length=30), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("attachment_id", sa.UUID(), nullable=True),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "message_type IN ('text', 'image', 'quotation', 'booking_update', 'system')",
            name=op.f("ck_messages_type"),
        ),
        sa.ForeignKeyConstraint(
            ["attachment_id"], ["media_assets.id"], name=op.f("fk_messages_attachment_id_media_assets"), ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["conversation_id"],
            ["conversations.id"],
            name=op.f("fk_messages_conversation_id_conversations"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["sender_id"], ["users.id"], name=op.f("fk_messages_sender_id_users"), ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_messages")),
    )

    op.create_table(
        "payment_events",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("payment_id", sa.UUID(), nullable=True),
        sa.Column("provider", sa.String(length=50), nullable=False),
        sa.Column("provider_event_id", sa.String(length=150), nullable=True),
        sa.Column("event_type", sa.String(length=100), nullable=False),
        sa.Column("payload_hash", sa.String(length=64), nullable=False),
        sa.Column("raw_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["payment_id"], ["payments.id"], name=op.f("fk_payment_events_payment_id_payments"), ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_payment_events")),
        sa.UniqueConstraint("provider", "provider_event_id", name="uq_payment_events_provider_event"),
    )

    op.create_table(
        "portfolio_embeddings",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("project_id", sa.UUID(), nullable=True),
        sa.Column("asset_id", sa.UUID(), nullable=True),
        sa.Column("embedding_type", sa.String(length=20), nullable=False),
        sa.Column("embedding_model", sa.String(length=100), nullable=False),
        sa.Column("model_version", sa.String(length=50), nullable=False),
        sa.Column("embedding", pgvector.sqlalchemy.vector.VECTOR(dim=512), nullable=True),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "embedding_type IN ('visual_clip', 'text_project')", name=op.f("ck_portfolio_embeddings_type")
        ),
        sa.ForeignKeyConstraint(
            ["asset_id"],
            ["media_assets.id"],
            name=op.f("fk_portfolio_embeddings_asset_id_media_assets"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["projects.id"],
            name=op.f("fk_portfolio_embeddings_project_id_projects"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_portfolio_embeddings")),
    )
    op.create_index(op.f("ix_portfolio_embeddings_project_id"), "portfolio_embeddings", ["project_id"], unique=False)

    op.create_table(
        "refunds",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("payment_id", sa.UUID(), nullable=False),
        sa.Column("amount_minor", sa.BigInteger(), nullable=False),
        sa.Column("currency_code", sa.String(length=3), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("provider_refund_id", sa.String(length=100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("status IN ('pending', 'processed', 'failed')", name=op.f("ck_refunds_status")),
        sa.ForeignKeyConstraint(
            ["payment_id"], ["payments.id"], name=op.f("fk_refunds_payment_id_payments"), ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_refunds")),
    )
    op.create_index(op.f("ix_refunds_payment_id"), "refunds", ["payment_id"], unique=False)

    if is_postgres:
        # Performance trigram and pgvector HNSW indexes
        op.execute(
            "CREATE INDEX IF NOT EXISTS idx_prof_trgm_name "
            "ON professional_profiles USING gin (display_name gin_trgm_ops)"
        )
        op.execute(
            "CREATE INDEX IF NOT EXISTS idx_projects_trgm_title "
            "ON projects USING gin (title gin_trgm_ops)"
        )
        op.execute(
            "CREATE INDEX IF NOT EXISTS idx_portfolio_embeddings_hnsw "
            "ON portfolio_embeddings USING hnsw (embedding vector_cosine_ops) "
            "WITH (m = 16, ef_construction = 64)"
        )

        # Row-Level Security (RLS) policies on sensitive transactional tables
        op.execute("ALTER TABLE bookings ENABLE ROW LEVEL SECURITY")
        op.execute("ALTER TABLE enquiries ENABLE ROW LEVEL SECURITY")
        op.execute("ALTER TABLE payments ENABLE ROW LEVEL SECURITY")

        op.execute(
            """
            CREATE POLICY bookings_participant_isolation ON bookings
            USING (
                NULLIF(current_setting('app.current_user_id', true), '') IS NULL
                OR current_setting('app.current_user_role', true) IN ('admin', 'system')
                OR customer_id::text = current_setting('app.current_user_id', true)
                OR professional_id IN (
                    SELECT id FROM professional_profiles
                    WHERE owner_user_id::text = current_setting('app.current_user_id', true)
                )
            )
            """
        )
        op.execute(
            """
            CREATE POLICY enquiries_participant_isolation ON enquiries
            USING (
                NULLIF(current_setting('app.current_user_id', true), '') IS NULL
                OR current_setting('app.current_user_role', true) IN ('admin', 'system')
                OR customer_id::text = current_setting('app.current_user_id', true)
                OR id IN (
                    SELECT er.enquiry_id FROM enquiry_recipients er
                    JOIN professional_profiles pp ON pp.id = er.professional_id
                    WHERE pp.owner_user_id::text = current_setting('app.current_user_id', true)
                )
            )
            """
        )
        op.execute(
            """
            CREATE POLICY payments_participant_isolation ON payments
            USING (
                NULLIF(current_setting('app.current_user_id', true), '') IS NULL
                OR current_setting('app.current_user_role', true) IN ('admin', 'system')
                OR booking_id IN (
                    SELECT b.id FROM bookings b
                    WHERE b.customer_id::text = current_setting('app.current_user_id', true)
                       OR b.professional_id IN (
                           SELECT pp.id FROM professional_profiles pp
                           WHERE pp.owner_user_id::text = current_setting('app.current_user_id', true)
                       )
                )
            )
            """
        )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("DROP POLICY IF EXISTS payments_participant_isolation ON payments")
        op.execute("DROP POLICY IF EXISTS enquiries_participant_isolation ON enquiries")
        op.execute("DROP POLICY IF EXISTS bookings_participant_isolation ON bookings")
        op.execute("ALTER TABLE payments DISABLE ROW LEVEL SECURITY")
        op.execute("ALTER TABLE enquiries DISABLE ROW LEVEL SECURITY")
        op.execute("ALTER TABLE bookings DISABLE ROW LEVEL SECURITY")
        op.execute("DROP INDEX IF EXISTS idx_portfolio_embeddings_hnsw")
        op.execute("DROP INDEX IF EXISTS idx_projects_trgm_title")
        op.execute("DROP INDEX IF EXISTS idx_prof_trgm_name")

    op.drop_index(op.f("ix_refunds_payment_id"), table_name="refunds")
    op.drop_table("refunds")
    op.drop_index(op.f("ix_portfolio_embeddings_project_id"), table_name="portfolio_embeddings")
    op.drop_table("portfolio_embeddings")
    op.drop_table("payment_events")
    op.drop_table("messages")
    op.drop_table("conversation_participants")
    op.drop_index(op.f("ix_reviews_professional_id"), table_name="reviews")
    op.drop_index(op.f("ix_reviews_customer_id"), table_name="reviews")
    op.drop_index(op.f("ix_reviews_booking_id"), table_name="reviews")
    op.drop_table("reviews")
    op.drop_index(op.f("ix_payments_provider_payment_id"), table_name="payments")
    op.drop_index(op.f("ix_payments_booking_id"), table_name="payments")
    op.drop_table("payments")
    op.drop_constraint("fk_projects_cover_asset", "projects", type_="foreignkey")
    op.drop_index(op.f("ix_media_assets_project_id"), table_name="media_assets")
    op.drop_table("media_assets")
    op.drop_table("conversations")
    op.drop_table("service_packages")
    op.drop_index(op.f("ix_projects_portfolio_id"), table_name="projects")
    op.drop_index(op.f("ix_projects_category_id"), table_name="projects")
    op.drop_table("projects")
    op.drop_index(op.f("ix_bookings_professional_id"), table_name="bookings")
    op.drop_index(op.f("ix_bookings_enquiry_id"), table_name="bookings")
    op.drop_index(op.f("ix_bookings_customer_id"), table_name="bookings")
    op.drop_table("bookings")
    op.drop_table("verification_requests")
    op.drop_table("services")
    op.drop_index(op.f("ix_recommendation_items_session_id"), table_name="recommendation_items")
    op.drop_table("recommendation_items")
    op.drop_index(op.f("ix_quotations_professional_id"), table_name="quotations")
    op.drop_index(op.f("ix_quotations_enquiry_id"), table_name="quotations")
    op.drop_table("quotations")
    op.drop_index(op.f("ix_professional_skills_professional_id"), table_name="professional_skills")
    op.drop_index(op.f("ix_professional_skills_category_id"), table_name="professional_skills")
    op.drop_table("professional_skills")
    op.drop_table("portfolios")
    op.drop_table("equipment")
    op.drop_index(op.f("ix_enquiry_recipients_professional_id"), table_name="enquiry_recipients")
    op.drop_index(op.f("ix_enquiry_recipients_enquiry_id"), table_name="enquiry_recipients")
    op.drop_table("enquiry_recipients")
    op.drop_index(op.f("ix_user_sessions_user_id"), table_name="user_sessions")
    op.drop_index(op.f("ix_user_sessions_session_token_hash"), table_name="user_sessions")
    op.drop_table("user_sessions")
    op.drop_table("subscriptions")
    op.drop_table("recommendation_sessions")
    op.drop_index(op.f("ix_professional_profiles_slug"), table_name="professional_profiles")
    op.drop_index(op.f("ix_professional_profiles_owner_user_id"), table_name="professional_profiles")
    op.drop_index(op.f("ix_professional_profiles_base_city"), table_name="professional_profiles")
    op.drop_table("professional_profiles")
    op.drop_table("organization_members")
    op.drop_index(op.f("ix_enquiries_customer_id"), table_name="enquiries")
    op.drop_table("enquiries")
    op.drop_table("content_reports")
    op.drop_table("audit_logs")
    op.drop_index(op.f("ix_users_phone"), table_name="users")
    op.drop_index(op.f("ix_users_email"), table_name="users")
    op.drop_table("users")
    op.drop_table("subscription_plans")
    op.drop_table("organizations")
    op.drop_table("idempotency_records")
    op.drop_index(op.f("ix_categories_slug"), table_name="categories")
    op.drop_table("categories")
