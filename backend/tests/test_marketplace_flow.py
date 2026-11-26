"""End-to-End Marketplace Flow Tests: Enquiry -> Quotation -> Booking -> Payment -> Review."""

import uuid
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_full_marketplace_lifecycle(client: AsyncClient, seed_users):
    customer = seed_users["customer"]
    prof_user = seed_users["professional_user"]
    prof_profile = seed_users["professional_profile"]
    category = seed_users["category"]

    # 1. Search professionals
    search_res = await client.get("/search/professionals?city=Pune")
    assert search_res.status_code == 200
    search_data = search_res.json()["data"]
    assert search_data["total_results"] >= 1
    assert any(p["id"] == str(prof_profile.id) for p in search_data["results"])

    # 2. Login as Customer & Post Enquiry
    await client.post("/auth/login", json={"email": "customer@example.com", "password": "CustomerPass@2026!"})

    enquiry_payload = {
        "category_id": str(category.id),
        "title": "2-Day Candid Wedding Coverage in Pune",
        "description": "Looking for candid photographer and 4K cinematic video team.",
        "duration_days": 2,
        "location": "Bavdhan, Pune",
        "city": "Pune",
        "budget_min_minor": 4000000,
        "budget_max_minor": 6000000,
        "currency_code": "INR",
        "professional_ids": [str(prof_profile.id)],
    }
    enquiry_res = await client.post("/enquiries", json=enquiry_payload)
    assert enquiry_res.status_code == 201
    enquiry_id = enquiry_res.json()["data"]["id"]

    # 3. Login as Professional & Send Quotation
    await client.post("/auth/login", json={"email": "pro@example.com", "password": "ProPass@2026!"})

    quotation_payload = {
        "enquiry_id": enquiry_id,
        "total_amount_minor": 5000000,  # 50,000 INR
        "advance_amount_minor": 1500000, # 15,000 INR deposit
        "currency_code": "INR",
        "scope_of_work": "Comprehensive 2-day candid coverage, drone coverage, and cinematic highlights reel.",
        "deliverables": ["350 edited candid photographs", "3-5 minute 4K cinematic highlight teaser"],
        "terms": "50% raw files preview in 7 days, final edits within 30 days.",
    }
    quote_res = await client.post("/quotations", json=quotation_payload)
    assert quote_res.status_code == 201
    quote_data = quote_res.json()["data"]
    quotation_id = quote_data["id"]
    assert quote_data["status"] == "sent"

    # 4. Login as Customer & Accept Quotation -> Creates Booking
    await client.post("/auth/login", json={"email": "customer@example.com", "password": "CustomerPass@2026!"})

    accept_res = await client.post(f"/quotations/{quotation_id}/accept")
    assert accept_res.status_code == 200
    booking_data = accept_res.json()["data"]["booking"]
    booking_id = booking_data["id"]
    assert booking_data["booking_status"] == "pending_payment"
    assert booking_data["completion_status"] == "pending"

    # 5. Initiate Payment Order (Server calculates advance amount)
    order_payload = {
        "booking_id": booking_id,
        "payment_type": "advance",
    }
    order_res = await client.post("/payments/create-order", json=order_payload)
    assert order_res.status_code == 201
    order_data = order_res.json()["data"]
    payment_id = order_data["payment_id"]
    assert order_data["amount_minor"] == 1500000  # Server calculated advance amount

    # 6. Verify Payment -> Transitions Booking to Confirmed
    verify_payload = {
        "payment_id": payment_id,
        "provider_payment_id": f"pay_{uuid.uuid4().hex[:12]}",
        "provider_signature": "mock_valid_signature",
    }
    verify_res = await client.post("/payments/verify", json=verify_payload)
    assert verify_res.status_code == 200
    assert verify_res.json()["data"]["payment_status"] == "captured"

    # Check booking is confirmed
    b_check = await client.get(f"/bookings/{booking_id}")
    assert b_check.status_code == 200
    assert b_check.json()["data"]["booking_status"] == "confirmed"

    # 7. Update to in_progress & Complete Booking
    patch_res = await client.patch(f"/bookings/{booking_id}/status", json={"booking_status": "in_progress"})
    assert patch_res.status_code == 200
    assert patch_res.json()["data"]["booking_status"] == "in_progress"

    # Customer marks booking complete
    comp_res = await client.post(f"/bookings/{booking_id}/complete")
    assert comp_res.status_code == 200
    assert comp_res.json()["data"]["booking_status"] == "completed"
    assert comp_res.json()["data"]["completion_status"] == "customer_accepted"

    # 8. Submit Verified Review
    review_payload = {
        "overall_rating": 5.0,
        "work_quality_rating": 5.0,
        "communication_rating": 4.8,
        "punctuality_rating": 5.0,
        "value_rating": 4.9,
        "review_text": "Remarkable visual quality and punctual arrival. The candid shots exceeded our expectations!",
    }
    rev_res = await client.post(f"/bookings/{booking_id}/review", json=review_payload)
    assert rev_res.status_code == 201
    assert rev_res.json()["data"]["overall_rating"] == 5.0

    # 9. AI Review Summary reflects actual review
    sum_res = await client.post("/ai/reviews/summarize", json={"professional_id": str(prof_profile.id)})
    assert sum_res.status_code == 200
    sum_data = sum_res.json()["data"]
    assert sum_data["total_reviews_analyzed"] >= 1
    assert len(sum_data["sentiment_highlights"]) >= 1
