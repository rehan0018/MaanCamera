-- ==============================================================================
-- MAANCAMERA — Master Seed Data (India Photography & Videography Ecosystem)
-- Document ID: MC-SEED-001 | Version: 2.0
-- Currency: INR (Minor units: Paise, e.g. 4500000 = Rs 45,000)
-- ==============================================================================

-- ------------------------------------------------------------------------------
-- 1. SUBSCRIPTION PLANS
-- ------------------------------------------------------------------------------
INSERT INTO subscription_plans (id, name, slug, price_minor, currency_code, billing_period, features, max_projects, max_storage_gb, is_active)
VALUES
    ('a0000000-0000-0000-0000-000000000001', 'Free Starter', 'free', 0, 'INR', 'monthly', 
     '{"enquiries": true, "portfolio_limit": 5, "ai_search_eligible": true, "verified_badge": false}'::jsonb, 5, 2, true),
    ('a0000000-0000-0000-0000-000000000002', 'Creator Pro', 'creator', 99900, 'INR', 'monthly', 
     '{"enquiries": true, "portfolio_limit": 20, "ai_search_eligible": true, "verified_badge": true, "analytics": true}'::jsonb, 20, 15, true),
    ('a0000000-0000-0000-0000-000000000003', 'Studio Master', 'studio', 249900, 'INR', 'monthly', 
     '{"enquiries": true, "portfolio_limit": 100, "ai_search_eligible": true, "verified_badge": true, "team_members": 5, "custom_domain": true}'::jsonb, 100, 100, true)
ON CONFLICT (slug) DO NOTHING;

-- ------------------------------------------------------------------------------
-- 2. CATEGORIES & TAXONOMY
-- ------------------------------------------------------------------------------
INSERT INTO categories (id, parent_id, name, slug, description, icon_name, is_active, display_order)
VALUES
    ('c0000000-0000-0000-0000-000000000001', NULL, 'Wedding Photography', 'wedding-photography', 'Candid, traditional, and destination wedding photography', 'Camera', true, 1),
    ('c0000000-0000-0000-0000-000000000002', NULL, 'Cinematic Videography', 'videography', 'Wedding cinema, music videos, documentaries, and commercials', 'Video', true, 2),
    ('c0000000-0000-0000-0000-000000000003', NULL, 'Drone & Aerial', 'aerial-drone', 'High-altitude 4K aerial photography and cinematic drone piloting', 'Plane', true, 3),
    ('c0000000-0000-0000-0000-000000000004', NULL, 'Fashion & Editorial', 'fashion-editorial', 'High fashion, model portfolios, lookbooks, and magazine editorials', 'Sparkles', true, 4),
    ('c0000000-0000-0000-0000-000000000005', NULL, 'Product & E-Commerce', 'product-ecommerce', 'High-converting product catalog, jewelry, FMCG, and white-background photography', 'Package', true, 5),
    ('c0000000-0000-0000-0000-000000000006', NULL, 'Food & Hospitality', 'food-hospitality', 'Gastronomy, restaurant menus, culinary styling, and cafe lifestyle', 'Utensils', true, 6),
    ('c0000000-0000-0000-0000-000000000007', NULL, 'Portrait & Headshots', 'portrait-headshots', 'Executive corporate headshots, studio portraits, and family memories', 'User', true, 7),
    ('c0000000-0000-0000-0000-000000000008', NULL, 'Architecture & Interiors', 'architecture-interiors', 'Architectural geometry, luxury interior design, and real estate tours', 'Home', true, 8)
ON CONFLICT (slug) DO NOTHING;

-- ------------------------------------------------------------------------------
-- 3. USERS (Password for all dev accounts: "MaanCamera@2026")
-- Argon2id hash for "MaanCamera@2026"
-- ------------------------------------------------------------------------------
INSERT INTO users (id, email, phone, password_hash, full_name, avatar_url, status, is_superuser, email_verified_at)
VALUES
    ('u0000000-0000-0000-0000-000000000001', 'admin@maancamera.com', '+919876543210', 
     '$argon2id$v=19$m=65536,t=2,p=2$K7TzG5g1JbK9L9s8Z2yQ7A$h6bE1v5u3s4V6r7z8X9y0w1a2b3c4d5e6f7g8h9i0j1', 
     'MaanCamera Administrator', 'https://images.unsplash.com/photo-1534528741775-53994a69daeb?auto=format&fit=crop&w=300&q=80', 'active', true, NOW()),

    ('u0000000-0000-0000-0000-000000000002', 'priya.sharma@example.com', '+919811122233', 
     '$argon2id$v=19$m=65536,t=2,p=2$K7TzG5g1JbK9L9s8Z2yQ7A$h6bE1v5u3s4V6r7z8X9y0w1a2b3c4d5e6f7g8h9i0j1', 
     'Priya Sharma', 'https://images.unsplash.com/photo-1494790108377-be9c29b29330?auto=format&fit=crop&w=300&q=80', 'active', false, NOW()),

    ('u0000000-0000-0000-0000-000000000003', 'rohan.kulkarni@example.com', '+919822233344', 
     '$argon2id$v=19$m=65536,t=2,p=2$K7TzG5g1JbK9L9s8Z2yQ7A$h6bE1v5u3s4V6r7z8X9y0w1a2b3c4d5e6f7g8h9i0j1', 
     'Rohan Kulkarni', 'https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?auto=format&fit=crop&w=300&q=80', 'active', false, NOW()),

    ('u0000000-0000-0000-0000-000000000004', 'ananya.sen@example.com', '+919833344455', 
     '$argon2id$v=19$m=65536,t=2,p=2$K7TzG5g1JbK9L9s8Z2yQ7A$h6bE1v5u3s4V6r7z8X9y0w1a2b3c4d5e6f7g8h9i0j1', 
     'Ananya Sen', 'https://images.unsplash.com/photo-1517841905240-472988babdf9?auto=format&fit=crop&w=300&q=80', 'active', false, NOW()),

    ('u0000000-0000-0000-0000-000000000005', 'vikram.singh@example.com', '+919844455566', 
     '$argon2id$v=19$m=65536,t=2,p=2$K7TzG5g1JbK9L9s8Z2yQ7A$h6bE1v5u3s4V6r7z8X9y0w1a2b3c4d5e6f7g8h9i0j1', 
     'Vikram Singh', 'https://images.unsplash.com/photo-1500648767791-00dcc994a43e?auto=format&fit=crop&w=300&q=80', 'active', false, NOW())
ON CONFLICT (email) DO NOTHING;

-- ------------------------------------------------------------------------------
-- 4. PROFESSIONAL PROFILES
-- ------------------------------------------------------------------------------
INSERT INTO professional_profiles (
    id, owner_user_id, display_name, slug, headline, biography, 
    profile_image, cover_image, professional_type, years_experience, 
    base_city, state, country_code, latitude, longitude, service_radius_km, 
    travel_available, verification_status, profile_visibility, avg_rating, total_reviews, completed_bookings_count
)
VALUES
    (
        'p0000000-0000-0000-0000-000000000001',
        'u0000000-0000-0000-0000-000000000003',
        'Rohan Kulkarni Films & Photography',
        'rohan-kulkarni-visuals',
        'Award-winning Candid Wedding Photographer & Cinematic Storyteller',
        'Capturing authentic emotions and timeless wedding stories across Pune, Mumbai, and destination locations across India for over 8 years. Specialized in documentary candid photography and cinematic 4K video storytelling.',
        'https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?auto=format&fit=crop&w=500&q=80',
        'https://images.unsplash.com/photo-1519741497674-611481863552?auto=format&fit=crop&w=1400&q=80',
        'individual', 8, 'Pune', 'Maharashtra', 'IN', 18.5204, 73.8567, 100, true, 'verified', 'public', 4.95, 38, 45
    ),
    (
        'p0000000-0000-0000-0000-000000000002',
        'u0000000-0000-0000-0000-000000000004',
        'Sen Studio Bombay',
        'sen-studio-bombay',
        'High Fashion, Editorial & Luxury Lookbooks',
        'Mumbai-based fashion and advertising photographer working with leading Indian apparel designers, beauty brands, and modeling talent. Studio and location productions with high-end color grading and retouching.',
        'https://images.unsplash.com/photo-1517841905240-472988babdf9?auto=format&fit=crop&w=500&q=80',
        'https://images.unsplash.com/photo-1490481651871-ab68de25d43d?auto=format&fit=crop&w=1400&q=80',
        'studio', 6, 'Mumbai', 'Maharashtra', 'IN', 19.0760, 72.8777, 60, true, 'verified', 'public', 4.88, 24, 31
    ),
    (
        'p0000000-0000-0000-0000-000000000003',
        'u0000000-0000-0000-0000-000000000005',
        'Vikram Singh AeroCinematics',
        'vikram-aerocinematics',
        'Cinematographer & DGCA-Certified Drone Pilot',
        'Cinematic drone operator, music video cinematographer, and corporate brand film director. Flying dual-operator cinema rigs and DJI Mavic 3 Cine for premium commercial productions.',
        'https://images.unsplash.com/photo-1500648767791-00dcc994a43e?auto=format&fit=crop&w=500&q=80',
        'https://images.unsplash.com/photo-1508614589041-895b88991e3e?auto=format&fit=crop&w=1400&q=80',
        'team', 7, 'Bengaluru', 'Karnataka', 'IN', 12.9716, 77.5946, 150, true, 'verified', 'public', 4.92, 19, 27
    )
ON CONFLICT (slug) DO NOTHING;

-- ------------------------------------------------------------------------------
-- 5. PROFESSIONAL SKILLS & EQUIPMENT
-- ------------------------------------------------------------------------------
INSERT INTO professional_skills (professional_id, category_id, skill_name, proficiency_level, years_experience, is_primary)
VALUES
    ('p0000000-0000-0000-0000-000000000001', 'c0000000-0000-0000-0000-000000000001', 'Candid Wedding Photography', 'master', 8, true),
    ('p0000000-0000-0000-0000-000000000001', 'c0000000-0000-0000-0000-000000000002', 'Cinematic Wedding Films', 'advanced', 6, false),
    ('p0000000-0000-0000-0000-000000000002', 'c0000000-0000-0000-0000-000000000004', 'Editorial & Lookbook Photography', 'master', 6, true),
    ('p0000000-0000-0000-0000-000000000002', 'c0000000-0000-0000-0000-000000000005', 'Jewelry & Luxury Products', 'advanced', 5, false),
    ('p0000000-0000-0000-0000-000000000003', 'c0000000-0000-0000-0000-000000000003', 'DGCA Licensed Aerial Cinematography', 'master', 5, true),
    ('p0000000-0000-0000-0000-000000000003', 'c0000000-0000-0000-0000-000000000002', 'Commercial Brand Films', 'advanced', 7, false)
ON CONFLICT DO NOTHING;

INSERT INTO equipment (professional_id, equipment_type, brand, model, description, is_primary, verified_at)
VALUES
    ('p0000000-0000-0000-0000-000000000001', 'camera', 'Sony', 'Alpha 7 IV (Dual Body)', '33MP Full-frame Hybrid sensor with dual UHS-II slots', true, NOW()),
    ('p0000000-0000-0000-0000-000000000001', 'camera', 'Sony', 'FX3 Cinema Line', 'Full-frame 4K 120p 10-bit 4:2:2 video camera', true, NOW()),
    ('p0000000-0000-0000-0000-000000000001', 'lens', 'Sony', 'GM 50mm f/1.2 & GM 24-70mm f/2.8 II', 'Ultra-fast low-light prime and professional zoom lenses', false, NOW()),
    ('p0000000-0000-0000-0000-000000000002', 'camera', 'Canon', 'EOS R5', '45MP Studio resolution with Profoto TTL sync', true, NOW()),
    ('p0000000-0000-0000-0000-000000000003', 'drone', 'DJI', 'Mavic 3 Pro Cine', 'Tri-camera Apple ProRes 422 HQ aerial system with RC Pro', true, NOW())
ON CONFLICT DO NOTHING;

-- ------------------------------------------------------------------------------
-- 6. SERVICES & PACKAGES
-- ------------------------------------------------------------------------------
INSERT INTO services (id, professional_id, category_id, name, description, pricing_type, starting_price_minor, currency_code, is_active)
VALUES
    ('s0000000-0000-0000-0000-000000000001', 'p0000000-0000-0000-0000-000000000001', 'c0000000-0000-0000-0000-000000000001', 
     '2-Day Complete Wedding Photo & Cinema', 'Full coverage of Sangeet, Wedding Ceremony, and Reception with candid photo and cinematic video.', 
     'starting_from', 7500000, 'INR', true),
    ('s0000000-0000-0000-0000-000000000002', 'p0000000-0000-0000-0000-000000000002', 'c0000000-0000-0000-0000-000000000004', 
     'Designer Fashion Lookbook & Campaign', 'Full-day studio and location fashion campaign with styling assistance and high-end retouching.', 
     'fixed', 5000000, 'INR', true),
    ('s0000000-0000-0000-0000-000000000003', 'p0000000-0000-0000-0000-000000000003', 'c0000000-0000-0000-0000-000000000003', 
     'Cinematic 4K Aerial Drone Coverage', 'Licensed aerial piloting for events, luxury properties, and commercials with color grading.', 
     'daily', 2500000, 'INR', true)
ON CONFLICT DO NOTHING;

INSERT INTO service_packages (id, service_id, package_name, description, price_minor, currency_code, estimated_duration, deliverables, is_popular)
VALUES
    ('sp000000-0000-0000-0000-000000000001', 's0000000-0000-0000-0000-000000000001', 'Signature Candid + Cinema', 
     '2 Senior Candid Photographers + 2 Cinematographers with drone teaser', 8500000, 'INR', '2 Days (Up to 18 Hours)', 
     '["500+ High-Res Color Corrected Images", "1 Cinematic Teaser (3-5 mins)", "1 Full Traditional Video (45-60 mins)", "Online Gallery for 1 Year"]'::jsonb, true),
    ('sp000000-0000-0000-0000-000000000002', 's0000000-0000-0000-0000-000000000002', 'Full Day Studio Lookbook', 
     'Up to 15 garments/looks with lighting technician and digital capture', 5000000, 'INR', '8 Hours', 
     '["40 Retouched High-Res Images", "Full Web Resolution Catalog", "Color Matching for Print"]'::jsonb, true)
ON CONFLICT DO NOTHING;

-- ------------------------------------------------------------------------------
-- 7. PORTFOLIOS & PROJECTS
-- ------------------------------------------------------------------------------
INSERT INTO portfolios (id, professional_id, title, description, visibility)
VALUES
    ('pt000000-0000-0000-0000-000000000001', 'p0000000-0000-0000-0000-000000000001', 'Weddings & Celebrations', 'Real celebrations captured with heart and candid warmth.', 'public'),
    ('pt000000-0000-0000-0000-000000000002', 'p0000000-0000-0000-0000-000000000002', 'Fashion Campaigns & High Editorial', 'Editorial series and luxury commercial fashion.', 'public'),
    ('pt000000-0000-0000-0000-000000000003', 'p0000000-0000-0000-0000-000000000003', 'Aerial & Landscape Cinema', 'Skyline perspectives and commercial landscape cinema.', 'public')
ON CONFLICT DO NOTHING;

INSERT INTO projects (id, portfolio_id, category_id, title, slug, style, location, project_date, description, publication_status, tags)
VALUES
    ('pj000000-0000-0000-0000-000000000001', 'pt000000-0000-0000-0000-000000000001', 'c0000000-0000-0000-0000-000000000001', 
     'The Royal Maharashtrian Wedding of Aniket & Sneha', 'aniket-sneha-pune-wedding', 'Candid Documentary', 'Pune, Maharashtra', '2026-02-14', 
     'A vibrant 2-day traditional wedding celebration featuring candid emotional portraits, authentic rituals, and a cinematic twilight reception.', 'published', 
     ARRAY['candid', 'wedding', 'pune', 'cultural', 'cinematic', 'night_reception']),

    ('pj000000-0000-0000-0000-000000000002', 'pt000000-0000-0000-0000-000000000002', 'c0000000-0000-0000-0000-000000000004', 
     'Ethereal Monsoon Couture 2026', 'ethereal-monsoon-couture', 'High Editorial', 'Mumbai, Maharashtra', '2026-07-20', 
     'Monochrome and deep-toned silk drapery fashion editorial for Mumbai luxury fashion house.', 'published', 
     ARRAY['fashion', 'editorial', 'mumbai', 'couture', 'studio_lighting'])
ON CONFLICT DO NOTHING;

INSERT INTO media_assets (id, project_id, storage_key, public_url, media_type, mime_type, file_size_bytes, width, height, checksum, display_order)
VALUES
    ('m0000000-0000-0000-0000-000000000001', 'pj000000-0000-0000-0000-000000000001', 
     'portfolios/p01/aniket_sneha_01.jpg', 'https://images.unsplash.com/photo-1519741497674-611481863552?auto=format&fit=crop&w=1200&q=80', 
     'image', 'image/jpeg', 2450000, 1920, 1280, 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855', 1),
    ('m0000000-0000-0000-0000-000000000002', 'pj000000-0000-0000-0000-000000000001', 
     'portfolios/p01/aniket_sneha_02.jpg', 'https://images.unsplash.com/photo-1583939003579-730e3918a45a?auto=format&fit=crop&w=1200&q=80', 
     'image', 'image/jpeg', 3120000, 1920, 1280, 'f4c8996fb92427ae41e4649b934ca495991b7852b855e3b0c44298fc1c149ab1', 2),
    ('m0000000-0000-0000-0000-000000000003', 'pj000000-0000-0000-0000-000000000002', 
     'portfolios/p02/couture_01.jpg', 'https://images.unsplash.com/photo-1490481651871-ab68de25d43d?auto=format&fit=crop&w=1200&q=80', 
     'image', 'image/jpeg', 4200000, 1920, 2400, 'a495991b7852b855e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934c', 1)
ON CONFLICT DO NOTHING;

-- Set cover assets on projects
UPDATE projects SET cover_asset_id = 'm0000000-0000-0000-0000-000000000001' WHERE id = 'pj000000-0000-0000-0000-000000000001';
UPDATE projects SET cover_asset_id = 'm0000000-0000-0000-0000-000000000003' WHERE id = 'pj000000-0000-0000-0000-000000000002';

-- ------------------------------------------------------------------------------
-- 8. COMPLETED BOOKINGS & VERIFIED REVIEWS
-- ------------------------------------------------------------------------------
INSERT INTO enquiries (id, customer_id, category_id, title, description, shoot_date, duration_days, location, city, budget_min_minor, budget_max_minor, currency_code, status)
VALUES
    ('e0000000-0000-0000-0000-000000000001', 'u0000000-0000-0000-0000-000000000002', 'c0000000-0000-0000-0000-000000000001',
     'Candid Wedding Photographer in Pune for 2 Days', 
     'We need an experienced candid photographer who can capture natural unposed moments for our 2-day wedding in Pune.',
     '2026-03-20', 2, 'Koregaon Park, Pune', 'Pune', 6000000, 9000000, 'INR', 'booked')
ON CONFLICT DO NOTHING;

INSERT INTO quotations (id, enquiry_id, professional_id, version_number, total_amount_minor, advance_amount_minor, currency_code, scope_of_work, valid_until, status)
VALUES
    ('q0000000-0000-0000-0000-000000000001', 'e0000000-0000-0000-0000-000000000001', 'p0000000-0000-0000-0000-000000000001', 
     1, 8000000, 2000000, 'INR', '2 Days Candid Photography + Cinematic Wedding Highlights', NOW() + INTERVAL '14 days', 'accepted')
ON CONFLICT DO NOTHING;

INSERT INTO bookings (id, enquiry_id, quotation_id, customer_id, professional_id, shoot_date, location, agreed_amount_minor, paid_amount_minor, currency_code, booking_status, completion_status)
VALUES
    ('b0000000-0000-0000-0000-000000000001', 'e0000000-0000-0000-0000-000000000001', 'q0000000-0000-0000-0000-000000000001',
     'u0000000-0000-0000-0000-000000000002', 'p0000000-0000-0000-0000-000000000001',
     '2026-03-20', 'Koregaon Park, Pune', 8000000, 8000000, 'INR', 'completed', 'customer_accepted')
ON CONFLICT DO NOTHING;

INSERT INTO reviews (id, booking_id, customer_id, professional_id, overall_rating, work_quality_rating, communication_rating, punctuality_rating, value_rating, review_text, moderation_status)
VALUES
    ('r0000000-0000-0000-0000-000000000001', 'b0000000-0000-0000-0000-000000000001', 
     'u0000000-0000-0000-0000-000000000002', 'p0000000-0000-0000-0000-000000000001',
     5.0, 5.0, 5.0, 5.0, 4.8, 
     'Rohan and his crew were spectacular! They were totally unobtrusive during the emotional ceremonies and the candid portraits turned out even better than we dreamed. Delivered within 3 weeks as promised.', 
     'approved')
ON CONFLICT DO NOTHING;
