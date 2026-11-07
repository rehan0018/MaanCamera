-- ==============================================================================
-- MAANCAMERA — Master Relational & Vector Database Schema
-- Document ID: MC-DB-001 | Version: 2.0
-- Dialect: PostgreSQL 16+ with pgvector & pg_trgm
-- ==============================================================================

-- Enable required core PostgreSQL extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "vector";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- ------------------------------------------------------------------------------
-- A. IDENTITY SCHEMA GROUP
-- ------------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE,
    phone VARCHAR(20) UNIQUE,
    password_hash TEXT,
    full_name VARCHAR(150) NOT NULL,
    avatar_url TEXT,
    status VARCHAR(30) NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'suspended', 'pending_verification', 'deactivated')),
    is_superuser BOOLEAN NOT NULL DEFAULT FALSE,
    email_verified_at TIMESTAMPTZ,
    phone_verified_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS user_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    session_token_hash VARCHAR(128) NOT NULL UNIQUE,
    user_agent TEXT,
    ip_address INET,
    expires_at TIMESTAMPTZ NOT NULL,
    revoked_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_used_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ------------------------------------------------------------------------------
-- B. ORGANIZATION SCHEMA GROUP (Studio Multi-Tenancy)
-- ------------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS organizations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(200) NOT NULL,
    slug VARCHAR(220) NOT NULL UNIQUE,
    organization_type VARCHAR(50) NOT NULL DEFAULT 'studio' CHECK (organization_type IN ('studio', 'agency', 'production_house', 'collective')),
    registration_country VARCHAR(2) NOT NULL DEFAULT 'IN',
    gstin VARCHAR(20),
    logo_url TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS organization_members (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role VARCHAR(30) NOT NULL DEFAULT 'member' CHECK (role IN ('owner', 'admin', 'manager', 'professional', 'editor', 'viewer')),
    status VARCHAR(30) NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'invited', 'suspended')),
    joined_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_org_user UNIQUE (organization_id, user_id)
);

-- ------------------------------------------------------------------------------
-- C. CATEGORIES & TAXONOMY
-- ------------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS categories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    parent_id UUID REFERENCES categories(id) ON DELETE SET NULL,
    name VARCHAR(100) NOT NULL,
    slug VARCHAR(120) NOT NULL UNIQUE,
    description TEXT,
    icon_name VARCHAR(50),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    display_order INT NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ------------------------------------------------------------------------------
-- D. PROFESSIONAL PROFILES & SPECIALIZATIONS
-- ------------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS professional_profiles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_user_id UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    organization_id UUID REFERENCES organizations(id) ON DELETE SET NULL,
    display_name VARCHAR(200) NOT NULL,
    slug VARCHAR(220) NOT NULL UNIQUE,
    headline VARCHAR(250),
    biography TEXT,
    profile_image TEXT,
    cover_image TEXT,
    professional_type VARCHAR(50) NOT NULL DEFAULT 'individual' CHECK (professional_type IN ('individual', 'team', 'studio', 'crew')),
    years_experience INT NOT NULL DEFAULT 1 CHECK (years_experience >= 0),
    base_city VARCHAR(100) NOT NULL,
    state VARCHAR(100) NOT NULL,
    country_code VARCHAR(2) NOT NULL DEFAULT 'IN',
    latitude NUMERIC(10, 7),
    longitude NUMERIC(10, 7),
    service_radius_km INT NOT NULL DEFAULT 50,
    travel_available BOOLEAN NOT NULL DEFAULT TRUE,
    verification_status VARCHAR(30) NOT NULL DEFAULT 'unverified' CHECK (verification_status IN ('unverified', 'pending', 'verified', 'rejected')),
    profile_visibility VARCHAR(30) NOT NULL DEFAULT 'public' CHECK (profile_visibility IN ('public', 'unlisted', 'private')),
    avg_rating NUMERIC(3, 2) NOT NULL DEFAULT 0.00,
    total_reviews INT NOT NULL DEFAULT 0,
    completed_bookings_count INT NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS professional_skills (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    professional_id UUID NOT NULL REFERENCES professional_profiles(id) ON DELETE CASCADE,
    category_id UUID NOT NULL REFERENCES categories(id) ON DELETE CASCADE,
    skill_name VARCHAR(100) NOT NULL,
    proficiency_level VARCHAR(30) NOT NULL DEFAULT 'advanced' CHECK (proficiency_level IN ('beginner', 'intermediate', 'advanced', 'master')),
    years_experience INT NOT NULL DEFAULT 1,
    is_primary BOOLEAN NOT NULL DEFAULT FALSE,
    CONSTRAINT uq_prof_skill_category UNIQUE (professional_id, category_id, skill_name)
);

CREATE TABLE IF NOT EXISTS equipment (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    professional_id UUID NOT NULL REFERENCES professional_profiles(id) ON DELETE CASCADE,
    equipment_type VARCHAR(50) NOT NULL CHECK (equipment_type IN ('camera', 'lens', 'drone', 'lighting', 'audio', 'stabilizer', 'workstation', 'other')),
    brand VARCHAR(100) NOT NULL,
    model VARCHAR(150) NOT NULL,
    description TEXT,
    is_primary BOOLEAN NOT NULL DEFAULT FALSE,
    verified_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ------------------------------------------------------------------------------
-- E. SERVICES & PACKAGES
-- ------------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS services (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    professional_id UUID NOT NULL REFERENCES professional_profiles(id) ON DELETE CASCADE,
    category_id UUID NOT NULL REFERENCES categories(id) ON DELETE RESTRICT,
    name VARCHAR(200) NOT NULL,
    description TEXT,
    pricing_type VARCHAR(30) NOT NULL DEFAULT 'starting_from' CHECK (pricing_type IN ('fixed', 'starting_from', 'hourly', 'daily', 'custom_quote')),
    starting_price_minor BIGINT NOT NULL DEFAULT 0, -- Minor units (e.g. Paise in INR: 5000000 = Rs 50,000)
    currency_code VARCHAR(3) NOT NULL DEFAULT 'INR',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS service_packages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    service_id UUID NOT NULL REFERENCES services(id) ON DELETE CASCADE,
    package_name VARCHAR(150) NOT NULL,
    description TEXT,
    price_minor BIGINT NOT NULL,
    currency_code VARCHAR(3) NOT NULL DEFAULT 'INR',
    estimated_duration VARCHAR(100), -- e.g. "8 Hours Shoot"
    deliverables JSONB NOT NULL DEFAULT '[]'::jsonb, -- e.g. ["300 Edited Photos", "1 Cinematic Teaser"]
    terms TEXT,
    is_popular BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ------------------------------------------------------------------------------
-- F. PORTFOLIOS, PROJECTS & MEDIA ASSETS
-- ------------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS portfolios (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    professional_id UUID NOT NULL REFERENCES professional_profiles(id) ON DELETE CASCADE,
    title VARCHAR(200) NOT NULL DEFAULT 'Primary Portfolio',
    description TEXT,
    visibility VARCHAR(30) NOT NULL DEFAULT 'public' CHECK (visibility IN ('public', 'unlisted', 'private')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS projects (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    portfolio_id UUID NOT NULL REFERENCES portfolios(id) ON DELETE CASCADE,
    category_id UUID NOT NULL REFERENCES categories(id) ON DELETE RESTRICT,
    title VARCHAR(200) NOT NULL,
    slug VARCHAR(220) NOT NULL,
    style VARCHAR(100), -- e.g. "Candid", "Cinematic", "Fine Art", "Editorial"
    location VARCHAR(150),
    project_date DATE,
    description TEXT,
    cover_asset_id UUID,
    publication_status VARCHAR(30) NOT NULL DEFAULT 'published' CHECK (publication_status IN ('draft', 'published', 'archived')),
    tags TEXT[] NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_portfolio_project_slug UNIQUE (portfolio_id, slug)
);

CREATE TABLE IF NOT EXISTS media_assets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    storage_key VARCHAR(500) NOT NULL,
    public_url TEXT,
    media_type VARCHAR(20) NOT NULL CHECK (media_type IN ('image', 'video')),
    mime_type VARCHAR(100) NOT NULL,
    file_size_bytes BIGINT NOT NULL,
    width INT,
    height INT,
    duration_seconds INT,
    checksum VARCHAR(64) NOT NULL,
    processing_status VARCHAR(30) NOT NULL DEFAULT 'completed' CHECK (processing_status IN ('pending', 'processing', 'completed', 'failed')),
    copyright_declaration_status VARCHAR(30) NOT NULL DEFAULT 'declared' CHECK (copyright_declaration_status IN ('declared', 'verified', 'disputed')),
    display_order INT NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Circular foreign key for project cover asset
ALTER TABLE projects ADD CONSTRAINT fk_projects_cover_asset FOREIGN KEY (cover_asset_id) REFERENCES media_assets(id) ON DELETE SET NULL;

-- ------------------------------------------------------------------------------
-- G. ENQUIRIES, QUOTATIONS & BOOKINGS
-- ------------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS enquiries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    category_id UUID NOT NULL REFERENCES categories(id) ON DELETE RESTRICT,
    title VARCHAR(250) NOT NULL,
    description TEXT NOT NULL,
    shoot_date DATE,
    duration_days INT NOT NULL DEFAULT 1,
    location VARCHAR(200) NOT NULL,
    city VARCHAR(100) NOT NULL,
    budget_min_minor BIGINT,
    budget_max_minor BIGINT,
    currency_code VARCHAR(3) NOT NULL DEFAULT 'INR',
    status VARCHAR(30) NOT NULL DEFAULT 'open' CHECK (status IN ('open', 'responded', 'booked', 'expired', 'cancelled')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS enquiry_recipients (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    enquiry_id UUID NOT NULL REFERENCES enquiries(id) ON DELETE CASCADE,
    professional_id UUID NOT NULL REFERENCES professional_profiles(id) ON DELETE CASCADE,
    recipient_status VARCHAR(30) NOT NULL DEFAULT 'sent' CHECK (recipient_status IN ('sent', 'viewed', 'quoted', 'declined')),
    sent_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    viewed_at TIMESTAMPTZ,
    CONSTRAINT uq_enquiry_recipient UNIQUE (enquiry_id, professional_id)
);

CREATE TABLE IF NOT EXISTS quotations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    enquiry_id UUID NOT NULL REFERENCES enquiries(id) ON DELETE CASCADE,
    professional_id UUID NOT NULL REFERENCES professional_profiles(id) ON DELETE RESTRICT,
    version_number INT NOT NULL DEFAULT 1,
    total_amount_minor BIGINT NOT NULL,
    advance_amount_minor BIGINT NOT NULL,
    currency_code VARCHAR(3) NOT NULL DEFAULT 'INR',
    scope_of_work TEXT NOT NULL,
    deliverables JSONB NOT NULL DEFAULT '[]'::jsonb,
    terms TEXT,
    valid_until TIMESTAMPTZ NOT NULL,
    status VARCHAR(30) NOT NULL DEFAULT 'sent' CHECK (status IN ('draft', 'sent', 'revised', 'accepted', 'rejected', 'expired')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_quotation_version UNIQUE (enquiry_id, professional_id, version_number)
);

CREATE TABLE IF NOT EXISTS bookings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    enquiry_id UUID REFERENCES enquiries(id) ON DELETE SET NULL,
    quotation_id UUID REFERENCES quotations(id) ON DELETE RESTRICT,
    customer_id UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    professional_id UUID NOT NULL REFERENCES professional_profiles(id) ON DELETE RESTRICT,
    shoot_date DATE NOT NULL,
    location VARCHAR(250) NOT NULL,
    agreed_amount_minor BIGINT NOT NULL,
    paid_amount_minor BIGINT NOT NULL DEFAULT 0,
    currency_code VARCHAR(3) NOT NULL DEFAULT 'INR',
    booking_status VARCHAR(30) NOT NULL DEFAULT 'confirmed' CHECK (booking_status IN ('pending_payment', 'confirmed', 'in_progress', 'completed', 'cancelled', 'disputed')),
    completion_status VARCHAR(30) NOT NULL DEFAULT 'pending' CHECK (completion_status IN ('pending', 'delivered', 'customer_accepted')),
    cancellation_reason TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ------------------------------------------------------------------------------
-- H. PAYMENTS & FINANCIAL AUDIT
-- ------------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS payments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    booking_id UUID NOT NULL REFERENCES bookings(id) ON DELETE RESTRICT,
    provider VARCHAR(50) NOT NULL DEFAULT 'mock' CHECK (provider IN ('mock', 'razorpay', 'bank_transfer')),
    provider_payment_id VARCHAR(100),
    provider_order_id VARCHAR(100),
    amount_minor BIGINT NOT NULL,
    currency_code VARCHAR(3) NOT NULL DEFAULT 'INR',
    payment_status VARCHAR(30) NOT NULL DEFAULT 'pending' CHECK (payment_status IN ('pending', 'captured', 'failed', 'refunded')),
    payment_type VARCHAR(30) NOT NULL DEFAULT 'advance' CHECK (payment_type IN ('advance', 'balance', 'full')),
    signature VARCHAR(256),
    verified_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS payment_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    payment_id UUID REFERENCES payments(id) ON DELETE SET NULL,
    provider_event_id VARCHAR(150),
    event_type VARCHAR(100) NOT NULL,
    payload_hash VARCHAR(64) NOT NULL,
    raw_payload JSONB NOT NULL,
    received_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    processed_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS refunds (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    payment_id UUID NOT NULL REFERENCES payments(id) ON DELETE RESTRICT,
    amount_minor BIGINT NOT NULL,
    currency_code VARCHAR(3) NOT NULL DEFAULT 'INR',
    reason TEXT NOT NULL,
    status VARCHAR(30) NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'processed', 'failed')),
    provider_refund_id VARCHAR(100),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ------------------------------------------------------------------------------
-- I. REVIEWS & VERIFICATION
-- ------------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS reviews (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    booking_id UUID NOT NULL UNIQUE REFERENCES bookings(id) ON DELETE RESTRICT,
    customer_id UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    professional_id UUID NOT NULL REFERENCES professional_profiles(id) ON DELETE RESTRICT,
    overall_rating NUMERIC(2, 1) NOT NULL CHECK (overall_rating >= 1.0 AND overall_rating <= 5.0),
    work_quality_rating NUMERIC(2, 1) NOT NULL CHECK (work_quality_rating >= 1.0 AND work_quality_rating <= 5.0),
    communication_rating NUMERIC(2, 1) NOT NULL CHECK (communication_rating >= 1.0 AND communication_rating <= 5.0),
    punctuality_rating NUMERIC(2, 1) NOT NULL CHECK (punctuality_rating >= 1.0 AND punctuality_rating <= 5.0),
    value_rating NUMERIC(2, 1) NOT NULL CHECK (value_rating >= 1.0 AND value_rating <= 5.0),
    review_text TEXT NOT NULL,
    moderation_status VARCHAR(30) NOT NULL DEFAULT 'approved' CHECK (moderation_status IN ('pending', 'approved', 'flagged', 'hidden')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS verification_requests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    professional_id UUID NOT NULL REFERENCES professional_profiles(id) ON DELETE CASCADE,
    document_type VARCHAR(50) NOT NULL CHECK (document_type IN ('government_id', 'business_license', 'gst_certificate', 'equipment_invoice')),
    document_storage_key VARCHAR(500) NOT NULL,
    status VARCHAR(30) NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'verified', 'rejected')),
    notes TEXT,
    reviewed_by_user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    reviewed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ------------------------------------------------------------------------------
-- J. COMMUNICATION (Conversations & Direct Messaging)
-- ------------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    enquiry_id UUID REFERENCES enquiries(id) ON DELETE SET NULL,
    booking_id UUID REFERENCES bookings(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS conversation_participants (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    participant_role VARCHAR(30) NOT NULL CHECK (participant_role IN ('customer', 'professional', 'admin')),
    CONSTRAINT uq_conv_participant UNIQUE (conversation_id, user_id)
);

CREATE TABLE IF NOT EXISTS messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    sender_id UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    message_type VARCHAR(30) NOT NULL DEFAULT 'text' CHECK (message_type IN ('text', 'image', 'quotation', 'booking_update', 'system')),
    content TEXT NOT NULL,
    attachment_id UUID REFERENCES media_assets(id) ON DELETE SET NULL,
    read_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ------------------------------------------------------------------------------
-- K. AI & VECTOR EMBEDDINGS (pgvector)
-- ------------------------------------------------------------------------------

-- Visual & textual embeddings for projects and assets
-- 384 dimensions for sentence-transformers (text) or 512 dimensions for OpenCLIP ViT-B/32 (images)
CREATE TABLE IF NOT EXISTS portfolio_embeddings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
    asset_id UUID REFERENCES media_assets(id) ON DELETE CASCADE,
    embedding_type VARCHAR(20) NOT NULL CHECK (embedding_type IN ('visual_clip', 'text_project')),
    embedding_model VARCHAR(100) NOT NULL,
    model_version VARCHAR(50) NOT NULL,
    embedding vector(512), -- OpenCLIP ViT-B/32 dimension
    generated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS recommendation_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id UUID REFERENCES users(id) ON DELETE SET NULL,
    query_text TEXT NOT NULL,
    extracted_requirements JSONB NOT NULL DEFAULT '{}'::jsonb,
    ranking_version VARCHAR(50) NOT NULL DEFAULT 'v1.0-hybrid',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS recommendation_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES recommendation_sessions(id) ON DELETE CASCADE,
    professional_id UUID NOT NULL REFERENCES professional_profiles(id) ON DELETE CASCADE,
    relevance_score NUMERIC(5, 2) NOT NULL,
    ranking_position INT NOT NULL,
    explanation_data JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ------------------------------------------------------------------------------
-- L. SAAS, AUDIT & OPERATIONS
-- ------------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS subscription_plans (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(50) NOT NULL UNIQUE,
    slug VARCHAR(60) NOT NULL UNIQUE,
    price_minor BIGINT NOT NULL DEFAULT 0,
    currency_code VARCHAR(3) NOT NULL DEFAULT 'INR',
    billing_period VARCHAR(20) NOT NULL DEFAULT 'monthly' CHECK (billing_period IN ('monthly', 'yearly')),
    features JSONB NOT NULL DEFAULT '{}'::jsonb,
    max_projects INT NOT NULL DEFAULT 5,
    max_storage_gb INT NOT NULL DEFAULT 2,
    is_active BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS subscriptions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    organization_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
    plan_id UUID NOT NULL REFERENCES subscription_plans(id) ON DELETE RESTRICT,
    status VARCHAR(30) NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'past_due', 'cancelled', 'trialing')),
    current_period_start TIMESTAMPTZ NOT NULL,
    current_period_end TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    actor_user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    action VARCHAR(100) NOT NULL,
    resource_type VARCHAR(100) NOT NULL,
    resource_id UUID,
    ip_address INET,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS idempotency_records (
    key VARCHAR(256) PRIMARY KEY,
    action VARCHAR(100) NOT NULL,
    response_code INT NOT NULL,
    response_payload JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ NOT NULL
);

-- ------------------------------------------------------------------------------
-- PERFORMANCE & SEARCH INDEXES
-- ------------------------------------------------------------------------------

-- Indexes for users and sessions
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_phone ON users(phone);
CREATE INDEX IF NOT EXISTS idx_sessions_user ON user_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_sessions_token ON user_sessions(session_token_hash);

-- Trigram and geo indexes for discovery
CREATE INDEX IF NOT EXISTS idx_prof_city ON professional_profiles(base_city);
CREATE INDEX IF NOT EXISTS idx_prof_trgm_name ON professional_profiles USING gin (display_name gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_prof_rating ON professional_profiles(avg_rating DESC, completed_bookings_count DESC);
CREATE INDEX IF NOT EXISTS idx_prof_verification ON professional_profiles(verification_status, profile_visibility);

-- Categories and skills
CREATE INDEX IF NOT EXISTS idx_categories_slug ON categories(slug);
CREATE INDEX IF NOT EXISTS idx_skills_prof ON professional_skills(professional_id);
CREATE INDEX IF NOT EXISTS idx_skills_cat ON professional_skills(category_id);

-- Projects and assets
CREATE INDEX IF NOT EXISTS idx_projects_portfolio ON projects(portfolio_id);
CREATE INDEX IF NOT EXISTS idx_projects_category ON projects(category_id);
CREATE INDEX IF NOT EXISTS idx_projects_trgm_title ON projects USING gin (title gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_media_project ON media_assets(project_id);

-- Enquiries & Bookings
CREATE INDEX IF NOT EXISTS idx_enquiries_customer ON enquiries(customer_id);
CREATE INDEX IF NOT EXISTS idx_enquiries_status ON enquiries(status, city);
CREATE INDEX IF NOT EXISTS idx_quotations_enquiry ON quotations(enquiry_id);
CREATE INDEX IF NOT EXISTS idx_bookings_prof_date ON bookings(professional_id, shoot_date);
CREATE INDEX IF NOT EXISTS idx_bookings_customer ON bookings(customer_id);

-- Reviews
CREATE INDEX IF NOT EXISTS idx_reviews_prof ON reviews(professional_id, overall_rating DESC);

-- HNSW Vector Index for AI portfolio embeddings (fast approximate nearest neighbor)
CREATE INDEX IF NOT EXISTS idx_portfolio_embeddings_hnsw 
    ON portfolio_embeddings 
    USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);
