"""WS1 tests for email/OTP verification, password reset, TOTP 2FA, lockout, DPDP, proxy rate-limiting, headers, and AI-2."""

import logging
import re
from urllib.parse import parse_qs, urlparse

import pytest
from httpx import ASGITransport, AsyncClient
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.rate_limit import limiter
from app.core.security import PiiScrubbingFilter, generate_totp_code
from app.integrations.notifications.mailer import get_test_outbox
from app.main import app
from app.modules.ai.service import AIService
from app.modules.identity.models import ConsentRecord, User
from tests.conftest import csrf_headers


@pytest.mark.asyncio
async def test_s2_email_verify_phone_otp_and_password_reset_flow(client: AsyncClient, db_session: AsyncSession):
    # 1. Register user (explicit accept_terms=False must be rejected for DPDP consent)
    bad_reg = await client.post(
        "/auth/register",
        json={
            "full_name": "Meera Nair",
            "email": "meera@example.com",
            "password": "StrongPass@2026!",
            "accept_terms": False,
        },
    )
    assert bad_reg.status_code == 422

    reg = await client.post(
        "/auth/register",
        json={
            "full_name": "Meera Nair",
            "email": "meera@example.com",
            "phone": "+919822001122",
            "password": "StrongPass@2026!",
            "accept_terms": True,
            "accept_privacy": True,
        },
    )
    assert reg.status_code == 201
    user_data = reg.json()["data"]
    assert user_data["email_verified_at"] is None

    # Verification email captured in test outbox
    emails = [m for m in get_test_outbox() if m["event_type"] == "email_verification"]
    assert len(emails) == 1
    match = re.search(r"https?://\S+", emails[0]["body"])
    assert match
    verify_token = parse_qs(urlparse(match.group(0)).query)["token"][0]

    confirm_email = await client.post("/auth/verify-email/confirm", json={"token": verify_token})
    assert confirm_email.status_code == 200
    assert confirm_email.json()["data"]["email_verified_at"] is not None

    # Single-use token cannot be replayed
    replay_email = await client.post("/auth/verify-email/confirm", json={"token": verify_token})
    assert replay_email.status_code == 400

    # 2. Login and verify phone via OTP (with bad OTP check + valid OTP)
    login_res = await client.post(
        "/auth/login",
        json={"email": "meera@example.com", "password": "StrongPass@2026!"},
    )
    assert login_res.status_code == 200
    assert "session_token" not in login_res.json()["data"]
    old_mc_cookie = login_res.cookies.get("mc_session")
    assert old_mc_cookie

    otp_req = await client.post(
        "/auth/verify-phone/request",
        json={"phone": "+919822001122"},
        headers=csrf_headers(client),
    )
    assert otp_req.status_code == 200

    sms = [m for m in get_test_outbox() if m["event_type"] == "phone_verification"]
    assert len(sms) == 1
    otp_code = sms[0]["code"]

    wrong_otp = await client.post(
        "/auth/verify-phone/confirm",
        json={"phone": "+919822001122", "code": "000000" if otp_code != "000000" else "111111"},
        headers=csrf_headers(client),
    )
    assert wrong_otp.status_code == 400

    good_otp = await client.post(
        "/auth/verify-phone/confirm",
        json={"phone": "+919822001122", "code": otp_code},
        headers=csrf_headers(client),
    )
    assert good_otp.status_code == 200
    assert good_otp.json()["data"]["phone_verified_at"] is not None

    # 3. Password reset invalidates existing session and notifies email
    reset_req = await client.post(
        "/auth/password-reset/request",
        json={"email": "meera@example.com"},
        headers=csrf_headers(client),
    )
    assert reset_req.status_code == 200

    reset_emails = [m for m in get_test_outbox() if m["event_type"] == "password_reset"]
    assert len(reset_emails) == 1
    reset_url = re.search(r"https?://\S+", reset_emails[0]["body"]).group(0)
    reset_token = parse_qs(urlparse(reset_url).query)["token"][0]

    reset_confirm = await client.post(
        "/auth/password-reset/confirm",
        json={"token": reset_token, "new_password": "NewerStrongPass@2026!"},
        headers=csrf_headers(client),
    )
    assert reset_confirm.status_code == 200

    changed_alerts = [m for m in get_test_outbox() if m["event_type"] == "password_changed"]
    assert len(changed_alerts) == 1

    # Old HttpOnly cookie must now be invalid
    client.cookies.clear()
    client.cookies.set("mc_session", old_mc_cookie)
    stale_me = await client.get("/users/me")
    assert stale_me.status_code == 401
    client.cookies.clear()

    # New password works cleanly
    new_login = await client.post(
        "/auth/login",
        json={"email": "meera@example.com", "password": "NewerStrongPass@2026!"},
    )
    assert new_login.status_code == 200


@pytest.mark.asyncio
async def test_s6_account_lockout_totp_refresh_and_device_revocation(client: AsyncClient, seed_users):
    # 1. Login and enable TOTP 2FA on admin account
    login_res = await client.post(
        "/auth/login",
        json={"email": "admin@example.com", "password": "AdminPass@2026!"},
    )
    assert login_res.status_code == 200
    initial_cookie = login_res.cookies.get("mc_session")

    # Session refresh rotates HttpOnly cookie without exposing raw token in JSON
    refresh_res = await client.post("/auth/refresh", headers=csrf_headers(client))
    assert refresh_res.status_code == 200
    assert "session_token" not in refresh_res.json()["data"]
    rotated_cookie = refresh_res.cookies.get("mc_session")
    assert rotated_cookie and rotated_cookie != initial_cookie

    sessions_res = await client.get("/auth/sessions")
    assert sessions_res.status_code == 200
    assert len(sessions_res.json()["data"]) >= 1
    current_sid = next(s["id"] for s in sessions_res.json()["data"] if s["is_current"])

    setup_res = await client.post("/auth/totp/setup", headers=csrf_headers(client))
    assert setup_res.status_code == 200
    secret = setup_res.json()["data"]["secret"]
    assert setup_res.json()["data"]["otpauth_uri"].startswith("otpauth://totp/")

    totp_code = generate_totp_code(secret)
    enable_res = await client.post(
        "/auth/totp/enable",
        json={"code": totp_code},
        headers=csrf_headers(client),
    )
    assert enable_res.status_code == 200

    # Revoke current session by id -> subsequent /users/me fails
    revoke_res = await client.delete(f"/auth/sessions/{current_sid}", headers=csrf_headers(client))
    assert revoke_res.status_code == 200
    assert (await client.get("/users/me")).status_code == 401

    client.cookies.clear()
    # Login without TOTP fails, login with TOTP succeeds
    no_totp = await client.post(
        "/auth/login",
        json={"email": "admin@example.com", "password": "AdminPass@2026!"},
    )
    assert no_totp.status_code == 401

    with_totp = await client.post(
        "/auth/login",
        json={"email": "admin@example.com", "password": "AdminPass@2026!", "totp_code": generate_totp_code(secret)},
    )
    assert with_totp.status_code == 200

    # 2. Failed login lockout after AUTH_LOCKOUT_MAX_ATTEMPTS (5)
    client.cookies.clear()
    for _ in range(5):
        bad = await client.post(
            "/auth/login",
            json={"email": "customer@example.com", "password": "BadPassword!123"},
        )
        assert bad.status_code == 401

    locked = await client.post(
        "/auth/login",
        json={"email": "customer@example.com", "password": "CustomerPass@2026!"},
    )
    assert locked.status_code == 423


@pytest.mark.asyncio
async def test_s13_dpdp_consents_export_erasure_and_pii_log_scrubbing(
    client: AsyncClient, db_session: AsyncSession
):
    await client.post(
        "/auth/register",
        json={
            "full_name": "Karan Kulkarni",
            "email": "karan@example.com",
            "phone": "+919811122233",
            "password": "KaranPass@2026!",
        },
    )
    await client.post(
        "/auth/login",
        json={"email": "karan@example.com", "password": "KaranPass@2026!"},
    )

    consents_res = await client.get("/users/me/consents")
    assert consents_res.status_code == 200
    consent_types = {c["consent_type"] for c in consents_res.json()["data"]}
    assert {"terms_of_service", "privacy_policy"} <= consent_types

    export_res = await client.get("/users/me/export")
    assert export_res.status_code == 200
    export_json = export_res.text
    assert "Karan Kulkarni" in export_json
    assert "password_hash" not in export_json
    assert "totp_secret" not in export_json

    del_res = await client.request(
        "DELETE",
        "/users/me",
        json={"password": "KaranPass@2026!", "confirm_phrase": "DELETE"},
        headers=csrf_headers(client),
    )
    assert del_res.status_code == 200

    # Deleted user cannot access /users/me or log back in; PII is scrubbed
    assert (await client.get("/users/me")).status_code == 401
    user_row = (await db_session.execute(select(User).where(User.full_name == "Deleted User"))).scalar_one()
    assert user_row.email.endswith("@anonymized.invalid")
    assert user_row.phone is None
    assert user_row.status == "deactivated"
    assert (await db_session.execute(select(ConsentRecord).where(ConsentRecord.user_id == user_row.id))).scalars().all()

    # Log filter scrubs emails and phones
    flt = PiiScrubbingFilter()
    rec = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="Failed login for user@example.com phone +919876543210",
        args=(),
        exc_info=None,
    )
    flt.filter(rec)
    assert "user@example.com" not in rec.msg
    assert "9876543210" not in rec.msg


@pytest.mark.asyncio
async def test_s5_s8_s11_proxy_rate_limit_headers_and_prod_settings(client: AsyncClient, seed_users):
    # Security headers present on responses (S-8)
    health = await client.get("http://testserver/health")
    assert health.headers["X-Content-Type-Options"] == "nosniff"
    assert health.headers["X-Frame-Options"] == "DENY"
    assert "frame-ancestors 'none'" in health.headers["Content-Security-Policy"]

    # Production settings fail-closed validation (S-11)
    with pytest.raises(ValidationError):
        Settings(
            ENVIRONMENT="production",
            DEBUG=True,
            SECRET_KEY="x" * 40,
            CSRF_SECRET="y" * 40,
            DATABASE_URL="postgresql+asyncpg://app:real_pass_123@postgres:5432/mc",
            SYNC_DATABASE_URL="postgresql+psycopg2://owner:real_pass_456@postgres:5432/mc",
            S3_SECRET_ACCESS_KEY="real_s3_secret_key",
            PAYMENT_PROVIDER="razorpay",
            RAZORPAY_KEY_ID="rzp_live_1",
            RAZORPAY_KEY_SECRET="rzp_sec_1",
            RAZORPAY_WEBHOOK_SECRET="rzp_wh_1",
        )

    with pytest.raises(ValidationError):
        Settings(
            ENVIRONMENT="production",
            DEBUG=False,
            SECRET_KEY="x" * 40,
            CSRF_SECRET="y" * 40,
            CORS_ORIGINS=["*"],
            DATABASE_URL="postgresql+asyncpg://app:real_pass_123@postgres:5432/mc",
            SYNC_DATABASE_URL="postgresql+psycopg2://owner:real_pass_456@postgres:5432/mc",
            S3_SECRET_ACCESS_KEY="real_s3_secret_key",
            PAYMENT_PROVIDER="razorpay",
            RAZORPAY_KEY_ID="rzp_live_1",
            RAZORPAY_KEY_SECRET="rzp_sec_1",
            RAZORPAY_WEBHOOK_SECRET="rzp_wh_1",
        )

    # Proxy-header IP rate limit isolation (S-5): 2 different IPs behind trusted proxy get independent buckets
    limiter.enabled = True
    try:
        limiter.reset()
        for _ in range(5):
            r = await client.post(
                "/auth/login",
                json={"email": "nobody1@example.com", "password": "bad"},
                headers={"X-Forwarded-For": "198.51.100.10"},
            )
            assert r.status_code == 401
        r6 = await client.post(
            "/auth/login",
            json={"email": "nobody1@example.com", "password": "bad"},
            headers={"X-Forwarded-For": "198.51.100.10"},
        )
        assert r6.status_code == 429

        # Different client IP through trusted proxy is NOT rate-limited by IP1's exhaustion
        other_ip = await client.post(
            "/auth/login",
            json={"email": "nobody2@example.com", "password": "bad"},
            headers={"X-Forwarded-For": "198.51.100.20"},
        )
        assert other_ip.status_code == 401
    finally:
        limiter.reset()
        limiter.enabled = False

    # Untrusted direct client IP cannot spoof X-Forwarded-For
    untrusted_transport = ASGITransport(app=app, client=("203.0.113.55", 12345))
    async with AsyncClient(transport=untrusted_transport, base_url="http://testserver/api/v1") as uclient:
        limiter.enabled = True
        try:
            limiter.reset()
            for idx in range(5):
                res = await uclient.post(
                    "/auth/login",
                    json={"email": "nobody@example.com", "password": "bad"},
                    headers={"X-Forwarded-For": f"10.0.0.{idx + 1}"},
                )
                assert res.status_code == 401
            spoof_blocked = await uclient.post(
                "/auth/login",
                json={"email": "nobody@example.com", "password": "bad"},
                headers={"X-Forwarded-For": "10.0.0.99"},
            )
            assert spoof_blocked.status_code == 429
        finally:
            limiter.reset()
            limiter.enabled = False


@pytest.mark.asyncio
async def test_ai2_ai9_dynamic_null_reweighting_and_db_grounding(db_session: AsyncSession, seed_users):
    # Query omits budget, category, and city -> missing factors MUST be None (not 80/85/90/25)
    rec = await AIService.get_recommendations(db_session, "looking for talented artists")
    assert rec.total_matches >= 1
    first = rec.recommendations[0]

    # DB grounding (AI-9): ID, price, rating must match stored records
    prof = seed_users["professional_profile"]
    serv = seed_users["service"]
    assert first.professional_id == prof.id
    assert first.starting_price_minor == serv.starting_price_minor
    assert first.avg_rating == pytest.approx(float(prof.avg_rating))

    # Inspect persisted factor breakdown for AI-2 no-fabrication guarantee
    from app.modules.ai.models import RecommendationItem

    item = (
        await db_session.execute(
            select(RecommendationItem).where(RecommendationItem.session_id == rec.session_id)
        )
    ).scalar_one()
    factors = item.explanation_data["factors"]
    assert factors["skills_match"] is None
    assert factors["budget_fit"] is None
    assert factors["location_fit"] is None
    assert "availability" not in factors
