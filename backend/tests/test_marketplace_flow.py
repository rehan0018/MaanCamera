"""End-to-End Marketplace Flow Tests: Search -> Enquiry -> Quotation -> Booking -> Payment -> Review -> AI."""

import hashlib
import hmac
import json
import uuid

import pytest
from httpx import AsyncClient

from app.core.config import settings
from app.modules.payments.service import compute_mock_signature
from tests.conftest import csrf_headers


@pytest.mark.asyncio
async def test_full_marketplace_lifecycle(client: AsyncClient, seed_users):
    prof_profile = seed_users["professional_profile"]
    category = seed_users["category"]

    # 1. Search professionals with style filter (exercises biography column)
    search_res = await client.get("/search/professionals?city=Pune")
    assert search_res.status_code == 200
    search_data = search_res.json()["data"]
    assert search_data["total_results"] >= 1
    assert any(p["id"] == str(prof_profile.id) for p in search_data["results"])

    # 2. Login as Customer & Post Enquiry
    await client.post(
        "/auth/login",
        json={"email": "customer@example.com", "password": "CustomerPass@2026!"},
        headers=csrf_headers(client),
    )

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
    enquiry_res = await client.post("/enquiries", json=enquiry_payload, headers=csrf_headers(client))
    assert enquiry_res.status_code == 201
    enquiry_id = enquiry_res.json()["data"]["id"]

    # 3. Login as Professional, check enquiries & Send Quotation (exercises owner_user_id)
    await client.post(
        "/auth/login",
        json={"email": "pro@example.com", "password": "ProPass@2026!"},
        headers=csrf_headers(client),
    )
    pro_enq_res = await client.get("/enquiries/me")
    assert pro_enq_res.status_code == 200
    assert any(e["id"] == enquiry_id for e in pro_enq_res.json()["data"])

    quotation_payload = {
        "enquiry_id": enquiry_id,
        "total_amount_minor": 5000000,
        "advance_amount_minor": 1500000,
        "currency_code": "INR",
        "scope_of_work": "Comprehensive 2-day candid coverage, drone coverage, and cinematic highlights reel.",
        "deliverables": ["350 edited candid photographs", "3-5 minute 4K cinematic highlight teaser"],
        "terms": "50% raw files preview in 7 days, final edits within 30 days.",
    }
    quote_res = await client.post("/quotations", json=quotation_payload, headers=csrf_headers(client))
    assert quote_res.status_code == 201
    quote_data = quote_res.json()["data"]
    quotation_id = quote_data["id"]
    assert quote_data["status"] == "sent"

    # 4. Login as Customer & Accept Quotation -> Creates Booking
    await client.post(
        "/auth/login",
        json={"email": "customer@example.com", "password": "CustomerPass@2026!"},
        headers=csrf_headers(client),
    )

    accept_res = await client.post(f"/quotations/{quotation_id}/accept", headers=csrf_headers(client))
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
    order_res = await client.post("/payments/create-order", json=order_payload, headers=csrf_headers(client))
    assert order_res.status_code == 201
    order_data = order_res.json()["data"]
    payment_id = order_data["payment_id"]
    provider_order_id = order_data["provider_order_id"]
    assert order_data["amount_minor"] == 1500000

    # 6. Verify Payment -> Rejects forged signature, accepts valid HMAC signature
    provider_payment_id = f"pay_{uuid.uuid4().hex[:12]}"
    bad_verify = await client.post(
        "/payments/verify",
        json={
            "payment_id": payment_id,
            "provider_payment_id": provider_payment_id,
            "provider_signature": "forged_signature_must_fail_closed",
        },
        headers=csrf_headers(client),
    )
    assert bad_verify.status_code == 400

    valid_sig = compute_mock_signature(provider_order_id, provider_payment_id)
    verify_res = await client.post(
        "/payments/verify",
        json={
            "payment_id": payment_id,
            "provider_payment_id": provider_payment_id,
            "provider_signature": valid_sig,
        },
        headers=csrf_headers(client),
    )
    assert verify_res.status_code == 200
    assert verify_res.json()["data"]["payment_status"] == "captured"

    # Also test idempotent webhook delivery with valid signature & body event name
    webhook_body = json.dumps({
        "id": f"evt_{uuid.uuid4().hex[:10]}",
        "event": "payment.captured",
        "payload": {
            "payment": {
                "entity": {
                    "id": provider_payment_id,
                    "order_id": provider_order_id,
                    "amount": 1500000,
                    "currency": "INR",
                    "status": "captured",
                }
            }
        },
    })
    wh_sig = hmac.new(settings.SECRET_KEY.encode("utf-8"), webhook_body.encode("utf-8"), hashlib.sha256).hexdigest()
    wh_res = await client.post(
        "/payments/webhooks/mock",
        content=webhook_body,
        headers={"X-Mock-Signature": wh_sig, "Content-Type": "application/json"},
    )
    assert wh_res.status_code == 200

    # Check booking is confirmed
    b_check = await client.get(f"/bookings/{booking_id}")
    assert b_check.status_code == 200
    assert b_check.json()["data"]["booking_status"] == "confirmed"

    # 7. Professional starts shoot (in_progress), Customer marks complete (customer_accepted)
    await client.post(
        "/auth/login",
        json={"email": "pro@example.com", "password": "ProPass@2026!"},
        headers=csrf_headers(client),
    )
    patch_res = await client.patch(
        f"/bookings/{booking_id}/status",
        json={"booking_status": "in_progress"},
        headers=csrf_headers(client),
    )
    assert patch_res.status_code == 200
    assert patch_res.json()["data"]["booking_status"] == "in_progress"

    # Professional cannot self-complete on behalf of customer
    pro_comp = await client.post(f"/bookings/{booking_id}/complete", headers=csrf_headers(client))
    assert pro_comp.status_code == 403

    await client.post(
        "/auth/login",
        json={"email": "customer@example.com", "password": "CustomerPass@2026!"},
        headers=csrf_headers(client),
    )
    comp_res = await client.post(f"/bookings/{booking_id}/complete", headers=csrf_headers(client))
    assert comp_res.status_code == 200
    assert comp_res.json()["data"]["booking_status"] == "completed"
    assert comp_res.json()["data"]["completion_status"] == "customer_accepted"

    # 8. Submit Verified Review -> starts pending until Admin moderates
    review_payload = {
        "overall_rating": 5.0,
        "work_quality_rating": 5.0,
        "communication_rating": 4.8,
        "punctuality_rating": 5.0,
        "value_rating": 4.9,
        "review_text": "Remarkable visual quality and punctual arrival. The candid shots exceeded our expectations!",
    }
    rev_res = await client.post(f"/bookings/{booking_id}/review", json=review_payload, headers=csrf_headers(client))
    assert rev_res.status_code == 201
    rev_data = rev_res.json()["data"]
    assert rev_data["overall_rating"] == 5.0
    assert rev_data["moderation_status"] == "pending"

    # Admin approves review so it publishes into profile reviews & AI summary
    await client.post(
        "/auth/login",
        json={"email": "admin@example.com", "password": "AdminPass@2026!"},
        headers=csrf_headers(client),
    )
    mod_res = await client.post(
        f"/admin/reviews/{rev_data['id']}/moderate",
        json={"decision": "approved", "notes": "Verified booking feedback"},
        headers=csrf_headers(client),
    )
    assert mod_res.status_code == 200
    assert mod_res.json()["data"]["moderation_status"] == "approved"

    # 9. AI Review Summary & AI Search
    sum_res = await client.post(
        "/ai/reviews/summarize",
        json={"professional_id": str(prof_profile.id)},
        headers=csrf_headers(client),
    )
    assert sum_res.status_code == 200
    sum_data = sum_res.json()["data"]
    assert sum_data["total_reviews_analyzed"] >= 1
    assert len(sum_data["sentiment_highlights"]) >= 1

    ai_res = await client.post(
        "/search/ai",
        json={"query": "Need candid wedding photographer in Pune under 50k"},
        headers=csrf_headers(client),
    )
    assert ai_res.status_code == 200
    assert ai_res.json()["data"]["total_matches"] >= 1
