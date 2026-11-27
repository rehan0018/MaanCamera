"""Phase 1 workflow, payment concurrency/reconciliation, admin moderation, and notification tests."""

import asyncio
import hashlib
import hmac
import json
import uuid
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.integrations.notifications.mailer import get_test_outbox
from app.modules.payments.models import Payment
from tests.conftest import csrf_headers


@pytest.mark.asyncio
async def test_draft_project_publish_workflow_and_portfolio_auto_provision(
    client: AsyncClient, seed_users
):
    cat = seed_users["category"]
    await client.post(
        "/auth/register",
        json={
            "full_name": "Kiran Rao",
            "email": "kiran.draft@example.com",
            "password": "StrongPass@2026!",
            "role": "professional",
        },
    )
    await client.post(
        "/auth/login",
        json={"email": "kiran.draft@example.com", "password": "StrongPass@2026!"},
    )
    prof_res = await client.post(
        "/professionals",
        json={"display_name": "Kiran Wedding Films", "base_city": "Pune", "state": "Maharashtra"},
        headers=csrf_headers(client),
    )
    assert prof_res.status_code == 201
    prof_id = prof_res.json()["data"]["id"]

    # Default portfolio is auto-provisioned and reachable via GET /portfolios/me
    ports_res = await client.get("/portfolios/me")
    assert ports_res.status_code == 200
    portfolios = ports_res.json()["data"]
    assert len(portfolios) == 1
    portfolio_id = portfolios[0]["id"]

    # Completing onboarding service promotes profile to public
    svc_res = await client.post(
        "/professionals/me/services",
        json={"category_id": str(cat.id), "name": "Wedding Highlight Reel", "starting_price_minor": 4000000},
        headers=csrf_headers(client),
    )
    assert svc_res.status_code == 201

    # Creating a project defaults cleanly to draft; direct publish without public media fails
    bad_pub = await client.post(
        "/projects",
        json={
            "portfolio_id": portfolio_id,
            "category_id": str(cat.id),
            "title": "Empty Published Attempt",
            "publication_status": "published",
        },
        headers=csrf_headers(client),
    )
    assert bad_pub.status_code == 400

    draft_res = await client.post(
        "/projects",
        json={
            "portfolio_id": portfolio_id,
            "category_id": str(cat.id),
            "title": "Pune Palace Wedding Shoot",
            "style": "Candid",
            "location": "Pune",
        },
        headers=csrf_headers(client),
    )
    assert draft_res.status_code == 201
    project_id = draft_res.json()["data"]["id"]
    assert draft_res.json()["data"]["publication_status"] == "draft"

    # Non-owner cannot view draft project or publish without media
    pub_err = await client.patch(
        f"/projects/{project_id}",
        json={"publication_status": "published"},
        headers=csrf_headers(client),
    )
    assert pub_err.status_code == 400

    client.cookies.clear()
    assert (await client.get(f"/projects/{project_id}")).status_code == 403
    public_ports = await client.get(f"/professionals/{prof_id}/portfolios")
    assert public_ports.status_code == 200
    assert len(public_ports.json()["data"]) == 1

    # Owner attaches a public media asset -> publishes project -> visible publicly
    await client.post(
        "/auth/login",
        json={"email": "kiran.draft@example.com", "password": "StrongPass@2026!"},
    )
    up_res = await client.post(
        "/media/upload-url",
        json={"filename": "cover.jpg", "mime_type": "image/jpeg", "file_size_bytes": 2048, "is_public": True},
        headers=csrf_headers(client),
    )
    storage_key = up_res.json()["data"]["storage_key"]
    with patch("app.modules.portfolios.service.process_uploaded_media.delay"):
        comp_res = await client.post(
            "/media/complete",
            json={
                "project_id": project_id,
                "storage_key": storage_key,
                "mime_type": "image/jpeg",
                "file_size_bytes": 2048,
                "checksum": "a" * 32,
            },
            headers=csrf_headers(client),
        )
    assert comp_res.status_code == 200
    asset_id = comp_res.json()["data"]["id"]

    pub_ok = await client.patch(
        f"/projects/{project_id}",
        json={"publication_status": "published"},
        headers=csrf_headers(client),
    )
    assert pub_ok.status_code == 200
    assert pub_ok.json()["data"]["publication_status"] == "published"

    client.cookies.clear()
    anon_proj = await client.get(f"/projects/{project_id}")
    assert anon_proj.status_code == 200
    assert len(anon_proj.json()["data"]["media_assets"]) == 1

    # Owner can delete asset and project
    await client.post(
        "/auth/login",
        json={"email": "kiran.draft@example.com", "password": "StrongPass@2026!"},
    )
    assert (await client.delete(f"/media/{asset_id}", headers=csrf_headers(client))).status_code == 200
    assert (await client.delete(f"/projects/{project_id}", headers=csrf_headers(client))).status_code == 200


@pytest.mark.asyncio
async def test_quotations_read_notifications_and_admin_verifications_reports(
    client: AsyncClient, db_session: AsyncSession, seed_users
):
    cat = seed_users["category"]
    prof_profile = seed_users["professional_profile"]

    # 1. Customer submits enquiry -> notifications outbox records enquiry_received
    await client.post("/auth/login", json={"email": "customer@example.com", "password": "CustomerPass@2026!"})
    enq_res = await client.post(
        "/enquiries",
        json={
            "category_id": str(cat.id),
            "title": "Portrait Shoot Notification Test",
            "description": "Need outdoor editorial portrait coverage.",
            "location": "Koregaon Park",
            "city": "Pune",
            "professional_ids": [str(prof_profile.id)],
        },
        headers=csrf_headers(client),
    )
    assert enq_res.status_code == 201
    enq_id = enq_res.json()["data"]["id"]
    assert any(m["event_type"] == "enquiry_received" for m in get_test_outbox())

    # 2. Pro submits quotation & private verification request
    await client.post(
        "/auth/login",
        json={"email": "pro@example.com", "password": "ProPass@2026!"},
        headers=csrf_headers(client),
    )
    quote_res = await client.post(
        "/quotations",
        json={
            "enquiry_id": enq_id,
            "total_amount_minor": 600000,
            "advance_amount_minor": 150000,
            "scope_of_work": "Editorial portrait session + color graded selects",
        },
        headers=csrf_headers(client),
    )
    assert quote_res.status_code == 201
    quot_id = quote_res.json()["data"]["id"]

    # Verify /quotations/me and /enquiries/{id}/quotations
    my_quotes = await client.get("/quotations/me")
    assert my_quotes.status_code == 200
    assert any(q["id"] == quot_id and q["enquiry_title"] == "Portrait Shoot Notification Test" for q in my_quotes.json()["data"])

    enq_quotes = await client.get(f"/enquiries/{enq_id}/quotations")
    assert enq_quotes.status_code == 200
    assert len(enq_quotes.json()["data"]) == 1

    up_ver = await client.post(
        "/media/upload-url",
        json={"filename": "pan.jpg", "mime_type": "image/jpeg", "file_size_bytes": 1024, "is_public": False},
        headers=csrf_headers(client),
    )
    ver_sub = await client.post(
        "/professionals/me/verifications",
        json={
            "document_type": "government_id",
            "document_storage_key": up_ver.json()["data"]["storage_key"],
            "notes": "Studio KYC ID",
        },
        headers=csrf_headers(client),
    )
    assert ver_sub.status_code == 201
    ver_id = ver_sub.json()["data"]["id"]

    # 3. Customer accepts -> pays -> completes -> submits review -> pro reports review
    await client.post(
        "/auth/login",
        json={"email": "customer@example.com", "password": "CustomerPass@2026!"},
        headers=csrf_headers(client),
    )
    acc = await client.post(f"/quotations/{quot_id}/accept", headers=csrf_headers(client))
    assert acc.status_code == 200
    booking_id = acc.json()["data"]["booking"]["id"]

    ord_res = await client.post(
        "/payments/create-order",
        json={"booking_id": booking_id, "payment_type": "advance"},
        headers=csrf_headers(client),
    )
    payment_id = ord_res.json()["data"]["payment_id"]
    cap_res = await client.post(f"/payments/{payment_id}/mock-capture", headers=csrf_headers(client))
    assert cap_res.status_code == 200
    assert cap_res.json()["data"]["payment_status"] == "captured"

    assert (await client.post(f"/bookings/{booking_id}/complete", headers=csrf_headers(client))).status_code == 200
    rev_res = await client.post(
        f"/bookings/{booking_id}/review",
        json={
            "overall_rating": 5.0,
            "work_quality_rating": 5.0,
            "communication_rating": 5.0,
            "punctuality_rating": 5.0,
            "value_rating": 5.0,
            "review_text": "Excellent collaboration and timely delivery.",
        },
        headers=csrf_headers(client),
    )
    assert rev_res.status_code == 201
    review_id = rev_res.json()["data"]["id"]

    rep_res = await client.post(
        f"/reviews/{review_id}/report",
        json={"reason": "inappropriate", "details": "Suspicious text review"},
        headers=csrf_headers(client),
    )
    assert rep_res.status_code == 201
    report_id = rep_res.json()["data"]["report_id"]

    # 4. Admin lists & decides verification + resolves report
    await client.post(
        "/auth/login",
        json={"email": "admin@example.com", "password": "AdminPass@2026!"},
        headers=csrf_headers(client),
    )
    ver_queue = await client.get("/admin/verifications?verification_status=pending")
    assert ver_queue.status_code == 200
    assert any(v["id"] == ver_id and "X-Amz-Signature=" in (v["document_access_url"] or "") for v in ver_queue.json()["data"])

    dec_res = await client.post(
        f"/admin/verifications/{ver_id}/decision",
        json={"decision": "verified", "notes": "KYC approved"},
        headers=csrf_headers(client),
    )
    assert dec_res.status_code == 200
    assert dec_res.json()["data"]["status"] == "verified"

    rep_queue = await client.get("/admin/reports?report_status=pending")
    assert rep_queue.status_code == 200
    assert any(r["id"] == report_id for r in rep_queue.json()["data"])

    res_rep = await client.post(
        f"/admin/reports/{report_id}/resolve",
        json={"action": "hide_content", "notes": "Hidden after review"},
        headers=csrf_headers(client),
    )
    assert res_rep.status_code == 200
    assert res_rep.json()["data"]["status"] == "action_taken"


@pytest.mark.asyncio
async def test_payments_concurrency_razorpay_webhooks_and_reconciliation(
    client: AsyncClient, db_session: AsyncSession, seed_users
):
    cat = seed_users["category"]
    prof_profile = seed_users["professional_profile"]

    await client.post("/auth/login", json={"email": "customer@example.com", "password": "CustomerPass@2026!"})
    enq = await client.post(
        "/enquiries",
        json={
            "category_id": str(cat.id),
            "title": "Razorpay Webhook & Reconcile Test",
            "description": "Concurrency, Razorpay webhook, partial multi-refunds, reconciliation.",
            "location": "Pune",
            "city": "Pune",
            "professional_ids": [str(prof_profile.id)],
        },
        headers=csrf_headers(client),
    )
    enq_id = enq.json()["data"]["id"]

    await client.post(
        "/auth/login",
        json={"email": "pro@example.com", "password": "ProPass@2026!"},
        headers=csrf_headers(client),
    )
    quot = await client.post(
        "/quotations",
        json={
            "enquiry_id": enq_id,
            "total_amount_minor": 1200000,
            "advance_amount_minor": 300000,
            "scope_of_work": "2-day wedding photo and highlight film",
        },
        headers=csrf_headers(client),
    )
    quot_id = quot.json()["data"]["id"]

    await client.post(
        "/auth/login",
        json={"email": "customer@example.com", "password": "CustomerPass@2026!"},
        headers=csrf_headers(client),
    )
    acc = await client.post(f"/quotations/{quot_id}/accept", headers=csrf_headers(client))
    booking_id = acc.json()["data"]["booking"]["id"]

    # Concurrent create-order requests produce a single pending order without double-charging
    headers = csrf_headers(client)
    res_pair = await asyncio.gather(
        client.post("/payments/create-order", json={"booking_id": booking_id, "payment_type": "advance"}, headers=headers),
        client.post("/payments/create-order", json={"booking_id": booking_id, "payment_type": "advance"}, headers=headers),
    )
    assert all(r.status_code == 201 for r in res_pair)
    order_ids = {r.json()["data"]["provider_order_id"] for r in res_pair}
    assert len(order_ids) == 1
    payment_id = uuid.UUID(res_pair[0].json()["data"]["payment_id"])

    # Simulate Razorpay stale pending order & reconcile via GET /v1/orders/{id}/payments
    pay_row = await db_session.get(Payment, payment_id)
    assert pay_row is not None
    pay_row.provider = "razorpay"
    pay_row.provider_order_id = "order_rzp_stale_101"
    pay_row.created_at = datetime.now(UTC) - timedelta(minutes=30)
    await db_session.commit()

    orig_key_id = settings.RAZORPAY_KEY_ID
    orig_key_sec = settings.RAZORPAY_KEY_SECRET
    orig_wh_sec = settings.RAZORPAY_WEBHOOK_SECRET
    settings.RAZORPAY_KEY_ID = "rzp_test_id"
    settings.RAZORPAY_KEY_SECRET = "rzp_test_sec"
    settings.RAZORPAY_WEBHOOK_SECRET = "rzp_wh_sec_123"
    try:
        # Mock capture forbidden in production
        with patch.object(settings, "ENVIRONMENT", "production"):
            prod_block = await client.post(f"/payments/{payment_id}/mock-capture", headers=csrf_headers(client))
            assert prod_block.status_code == 403

        # Admin triggers reconciliation -> captures stale order_rzp_stale_101
        await client.post(
            "/auth/login",
            json={"email": "admin@example.com", "password": "AdminPass@2026!"},
            headers=csrf_headers(client),
        )
        gw_resp = MagicMock(status_code=200)
        gw_resp.json.return_value = {
            "items": [
                {
                    "id": "pay_rzp_reconciled_01",
                    "order_id": "order_rzp_stale_101",
                    "amount": 300000,
                    "currency": "INR",
                    "status": "captured",
                }
            ]
        }

        class _FakeGetClient:
            def __init__(self, *args, **kwargs):
                pass

            async def __aenter__(self):
                return self

            async def __aexit__(self, *args):
                return False

            get = AsyncMock(return_value=gw_resp)

        with patch("app.modules.payments.service.httpx", SimpleNamespace(AsyncClient=_FakeGetClient)):
            rec_res = await client.post(
                "/payments/admin/reconcile?older_than_minutes=15",
                headers=csrf_headers(client),
            )
        assert rec_res.status_code == 200
        assert rec_res.json()["data"]["reconciled_captured"] == 1

        # Duplicate Razorpay webhook replay succeeds idempotently without adding duplicate ledger rows
        wh_payload = json.dumps({
            "id": f"evt_rzp_{uuid.uuid4().hex[:8]}",
            "event": "payment.captured",
            "payload": {
                "payment": {
                    "entity": {
                        "id": "pay_rzp_reconciled_01",
                        "order_id": "order_rzp_stale_101",
                        "amount": 300000,
                        "currency": "INR",
                    }
                }
            },
        })
        rzp_sig = hmac.new(
            settings.RAZORPAY_WEBHOOK_SECRET.encode("utf-8"),
            wh_payload.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        wh1 = await client.post(
            "/payments/webhooks/razorpay",
            content=wh_payload,
            headers={"X-Razorpay-Signature": rzp_sig, "Content-Type": "application/json"},
        )
        assert wh1.status_code == 200
        wh2 = await client.post(
            "/payments/webhooks/razorpay",
            content=wh_payload,
            headers={"X-Razorpay-Signature": rzp_sig, "Content-Type": "application/json"},
        )
        assert wh2.status_code == 200

        # refund.processed webhook marks fully refunded payment via Razorpay signed event
        ref_wh_payload = json.dumps({
            "id": f"evt_rzp_ref_{uuid.uuid4().hex[:8]}",
            "event": "refund.processed",
            "payload": {
                "refund": {
                    "entity": {
                        "id": "rfnd_rzp_001",
                        "payment_id": "pay_rzp_reconciled_01",
                        "amount": 300000,
                        "notes": {"reason": "Customer requested refund"},
                    }
                }
            },
        })
        ref_sig = hmac.new(
            settings.RAZORPAY_WEBHOOK_SECRET.encode("utf-8"),
            ref_wh_payload.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        ref_wh = await client.post(
            "/payments/webhooks/razorpay",
            content=ref_wh_payload,
            headers={"X-Razorpay-Signature": ref_sig, "Content-Type": "application/json"},
        )
        assert ref_wh.status_code == 200

        summary = await client.get(f"/payments/bookings/{booking_id}")
        assert summary.status_code == 200
        assert summary.json()["data"]["paid_amount_minor"] == 0
        assert summary.json()["data"]["payments"][0]["payment_status"] == "refunded"
    finally:
        settings.RAZORPAY_KEY_ID = orig_key_id
        settings.RAZORPAY_KEY_SECRET = orig_key_sec
        settings.RAZORPAY_WEBHOOK_SECRET = orig_wh_sec


@pytest.mark.asyncio
async def test_metrics_endpoint_exposes_prometheus_counters(client: AsyncClient):
    await client.get("/health")
    res = await client.get("http://testserver/metrics")
    assert res.status_code == 200
    assert "maancamera_up 1" in res.text
    assert "maancamera_http_requests_total" in res.text
