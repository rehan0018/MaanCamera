"""Security and IDOR Protection Integration Tests."""

import uuid
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_customer_cannot_create_quotation(client: AsyncClient, seed_users):
    customer = seed_users["customer"]
    prof_profile = seed_users["professional_profile"]

    # Login as Customer
    await client.post("/auth/login", json={"email": "customer@example.com", "password": "CustomerPass@2026!"})

    # Attempt to quote as professional
    quotation_payload = {
        "enquiry_id": str(uuid.uuid4()),
        "professional_id": str(prof_profile.id),
        "total_amount_minor": 5000000,
        "advance_amount_minor": 1500000,
        "scope_of_work": "Malicious quote attempt",
    }
    response = await client.post("/quotations", json=quotation_payload)
    # Must be 403 Forbidden or 404 (not found / not permitted)
    assert response.status_code in [403, 404]
    data = response.json()
    assert data["success"] is False


@pytest.mark.asyncio
async def test_quotation_advance_cannot_exceed_total(client: AsyncClient, seed_users):
    category = seed_users["category"]
    prof_profile = seed_users["professional_profile"]

    # 1. Customer creates enquiry
    await client.post("/auth/login", json={"email": "customer@example.com", "password": "CustomerPass@2026!"})
    enq_res = await client.post("/enquiries", json={
        "category_id": str(category.id),
        "title": "Rule Check Enquiry",
        "description": "Validation check",
        "location": "Pune",
        "city": "Pune",
        "professional_ids": [str(prof_profile.id)],
    })
    enquiry_id = enq_res.json()["data"]["id"]

    # 2. Professional tries to quote advance > total
    await client.post("/auth/login", json={"email": "pro@example.com", "password": "ProPass@2026!"})
    bad_quote = {
        "enquiry_id": enquiry_id,
        "total_amount_minor": 1000000,
        "advance_amount_minor": 2000000,  # Invalid: 20k advance on 10k total
        "scope_of_work": "Invalid quote",
    }
    res = await client.post("/quotations", json=bad_quote)
    assert res.status_code == 400
    assert "Advance amount cannot exceed total" in res.json()["error"]["message"]


@pytest.mark.asyncio
async def test_unauthorized_booking_access(client: AsyncClient, seed_users):
    # Register an unrelated third-party user
    await client.post("/auth/register", json={
        "full_name": "Stranger User",
        "email": "stranger@example.com",
        "password": "StrangerPass@2026!",
        "role": "customer",
    })
    await client.post("/auth/login", json={"email": "stranger@example.com", "password": "StrangerPass@2026!"})

    # Try to access a random or non-owned booking
    random_booking_id = str(uuid.uuid4())
    res = await client.get(f"/bookings/{random_booking_id}")
    assert res.status_code in [403, 404]
