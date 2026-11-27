"""Security, Fail-Closed Payments, Rate Limiting, and IDOR Protection Tests."""

import json
import uuid

import pytest
from httpx import AsyncClient

from app.core.config import settings
from app.core.rate_limit import limiter
from tests.conftest import csrf_headers


@pytest.mark.asyncio
async def test_customer_cannot_create_quotation(client: AsyncClient, seed_users):
    prof_profile = seed_users["professional_profile"]

    await client.post("/auth/login", json={"email": "customer@example.com", "password": "CustomerPass@2026!"})

    quotation_payload = {
        "enquiry_id": str(uuid.uuid4()),
        "professional_id": str(prof_profile.id),
        "total_amount_minor": 5000000,
        "advance_amount_minor": 1500000,
        "scope_of_work": "Malicious quote attempt",
    }
    response = await client.post("/quotations", json=quotation_payload, headers=csrf_headers(client))
    assert response.status_code in [403, 404]
    data = response.json()
    assert data["success"] is False


@pytest.mark.asyncio
async def test_quotation_advance_cannot_exceed_total(client: AsyncClient, seed_users):
    category = seed_users["category"]
    prof_profile = seed_users["professional_profile"]

    await client.post("/auth/login", json={"email": "customer@example.com", "password": "CustomerPass@2026!"})
    enq_res = await client.post(
        "/enquiries",
        json={
            "category_id": str(category.id),
            "title": "Rule Check Enquiry",
            "description": "Validation check",
            "location": "Pune",
            "city": "Pune",
            "professional_ids": [str(prof_profile.id)],
        },
        headers=csrf_headers(client),
    )
    enquiry_id = enq_res.json()["data"]["id"]

    await client.post(
        "/auth/login",
        json={"email": "pro@example.com", "password": "ProPass@2026!"},
        headers=csrf_headers(client),
    )
    bad_quote = {
        "enquiry_id": enquiry_id,
        "total_amount_minor": 1000000,
        "advance_amount_minor": 2000000,
        "scope_of_work": "Invalid quote",
    }
    res = await client.post("/quotations", json=bad_quote, headers=csrf_headers(client))
    assert res.status_code == 400
    assert "Advance amount cannot exceed total" in res.json()["error"]["message"]


@pytest.mark.asyncio
async def test_unauthorized_booking_access(client: AsyncClient, seed_users):
    await client.post(
        "/auth/register",
        json={
            "full_name": "Stranger User",
            "email": "stranger@example.com",
            "password": "StrangerPass@2026!",
            "role": "customer",
        },
    )
    await client.post("/auth/login", json={"email": "stranger@example.com", "password": "StrangerPass@2026!"})

    random_booking_id = str(uuid.uuid4())
    res = await client.get(f"/bookings/{random_booking_id}")
    assert res.status_code in [403, 404]


@pytest.mark.asyncio
async def test_webhook_fails_closed_when_secret_or_signature_missing(client: AsyncClient, seed_users):
    orig_secret = settings.RAZORPAY_WEBHOOK_SECRET
    try:
        settings.RAZORPAY_WEBHOOK_SECRET = ""
        res_no_secret = await client.post(
            "/payments/webhooks/razorpay",
            content=json.dumps({"event": "payment.captured"}),
            headers={"X-Razorpay-Signature": "anything", "Content-Type": "application/json"},
        )
        assert res_no_secret.status_code == 400

        settings.RAZORPAY_WEBHOOK_SECRET = "test_secret_123456"
        res_no_sig = await client.post(
            "/payments/webhooks/razorpay",
            content=json.dumps({"event": "payment.captured"}),
            headers={"Content-Type": "application/json"},
        )
        assert res_no_sig.status_code == 400
    finally:
        settings.RAZORPAY_WEBHOOK_SECRET = orig_secret


@pytest.mark.asyncio
async def test_login_rate_limiting_returns_429(client: AsyncClient, seed_users):
    limiter.enabled = True
    try:
        limiter.reset()
        last_status = None
        for _ in range(6):
            res = await client.post(
                "/auth/login",
                json={"email": "customer@example.com", "password": "WrongPassword@2026!"},
            )
            last_status = res.status_code
        assert last_status == 429
    finally:
        limiter.reset()
        limiter.enabled = False
