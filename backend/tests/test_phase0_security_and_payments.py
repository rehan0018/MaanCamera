"""Phase 0 stabilization tests: SEC-01..SEC-08, Booking actor rules, Razorpay/webhooks/ledger/refunds."""

import hashlib
import hmac
import io
import json
import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient
from PIL import Image
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, settings
from app.modules.payments.models import Payment
from app.modules.payments.service import compute_mock_signature
from app.modules.portfolios.models import MediaAsset, Portfolio, Project
from app.workers.celery_app import process_media_asset_with_storage
from tests.conftest import csrf_headers


class _FakeS3Body:
    def __init__(self, data: bytes):
        self._data = data

    def read(self) -> bytes:
        return self._data


class _FakeS3Client:
    def __init__(self, initial: dict[tuple[str, str], bytes]):
        self.objects = dict(initial)
        self.deleted: list[tuple[str, str]] = []

    def get_object(self, Bucket: str, Key: str):
        return {"Body": _FakeS3Body(self.objects[(Bucket, Key)])}

    def put_object(self, Bucket: str, Key: str, Body: bytes, ContentType: str):
        self.objects[(Bucket, Key)] = Body

    def delete_object(self, Bucket: str, Key: str):
        self.deleted.append((Bucket, Key))
        self.objects.pop((Bucket, Key), None)


def _sample_jpeg_bytes() -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (120, 80), color=(200, 100, 50)).save(buf, format="JPEG")
    return buf.getvalue()


@pytest.mark.asyncio
async def test_sec02_private_media_isolation_in_worker_and_endpoints(
    client: AsyncClient, db_session: AsyncSession, seed_users
):
    await client.post("/auth/login", json={"email": "pro@example.com", "password": "ProPass@2026!"})
    headers = csrf_headers(client)
    project = seed_users["project"]

    # Request a private upload URL
    priv_url_res = await client.post(
        "/media/upload-url",
        json={"filename": "client-proof.jpg", "mime_type": "image/jpeg", "file_size_bytes": 4096, "is_public": False},
        headers=headers,
    )
    assert priv_url_res.status_code == 200
    priv_key = priv_url_res.json()["data"]["storage_key"]
    assert priv_key.startswith("private/")

    with patch("app.modules.portfolios.service.process_uploaded_media.delay") as delay_mock:
        comp = await client.post(
            "/media/complete",
            json={
                "project_id": str(project.id),
                "storage_key": priv_key,
                "mime_type": "image/jpeg",
                "file_size_bytes": 4096,
                "checksum": "f" * 32,
            },
            headers=headers,
        )
    assert comp.status_code == 200
    delay_mock.assert_called_once()
    asset_id = uuid.UUID(comp.json()["data"]["id"])
    assert comp.json()["data"]["visibility"] == "private"
    assert comp.json()["data"]["public_url"] is None

    # Simulate Celery worker sanitizing private upload
    asset_row = await db_session.get(MediaAsset, asset_id)
    assert asset_row is not None
    fake_s3 = _FakeS3Client({(settings.S3_BUCKET_PRIVATE_UPLOADS, priv_key): _sample_jpeg_bytes()})
    result = process_media_asset_with_storage(asset_row, priv_key, fake_s3)
    await db_session.commit()

    assert result["bucket"] == settings.S3_BUCKET_PRIVATE_UPLOADS
    assert result["visibility"] == "private"
    assert str(asset_row.storage_key).startswith("private/processed/")
    assert asset_row.public_url is None
    assert all(b == settings.S3_BUCKET_PRIVATE_UPLOADS for (b, _k) in fake_s3.objects)

    # Non-owner customer cannot fetch authorized URL for private asset OR see it on public project view
    client.cookies.clear()
    pub_proj = await client.get(f"/projects/{project.id}")
    assert pub_proj.status_code == 200
    assert all(a["visibility"] == "public" for a in pub_proj.json()["data"]["media_assets"])

    await client.post("/auth/login", json={"email": "customer@example.com", "password": "CustomerPass@2026!"})
    cust_url = await client.get(f"/media/{asset_id}/url")
    assert cust_url.status_code == 403, cust_url.text

    # Owner gets short-lived signed URL
    await client.post(
        "/auth/login",
        json={"email": "pro@example.com", "password": "ProPass@2026!"},
        headers=csrf_headers(client),
    )
    owner_url = await client.get(f"/media/{asset_id}/url")
    assert owner_url.status_code == 200
    assert owner_url.json()["data"]["visibility"] == "private"
    assert "X-Amz-Signature=" in owner_url.json()["data"]["url"]


@pytest.mark.asyncio
async def test_sec03_sec07_portfolio_visibility_and_pro_onboarding_gate(
    client: AsyncClient, db_session: AsyncSession, seed_users
):
    # SEC-07: Brand-new pro starts with private profile until adding at least 1 active service
    await client.post(
        "/auth/register",
        json={"full_name": "Riya Sen", "email": "riya@example.com", "password": "StrongPass@2026!", "role": "professional"},
    )
    await client.post("/auth/login", json={"email": "riya@example.com", "password": "StrongPass@2026!"})
    prof_res = await client.post(
        "/professionals",
        json={"display_name": "Riya Draft Studio", "base_city": "Pune", "state": "Maharashtra"},
        headers=csrf_headers(client),
    )
    assert prof_res.status_code == 201
    draft_id = prof_res.json()["data"]["id"]
    assert prof_res.json()["data"]["profile_visibility"] == "private"
    assert prof_res.json()["data"]["onboarding_completed"] is False

    # Cannot force visibility=public before adding a service
    bad_pub = await client.patch(
        "/professionals/me",
        json={"profile_visibility": "public"},
        headers=csrf_headers(client),
    )
    assert bad_pub.status_code == 400

    # Anonymous viewer cannot fetch private draft profile
    client.cookies.clear()
    assert (await client.get(f"/professionals/{draft_id}")).status_code == 403

    # SEC-03: Private portfolio & draft project blocked for anonymous/non-owner
    priv_port = Portfolio(
        professional_id=seed_users["professional_profile"].id,
        title="Private Client Gallery",
        visibility="private",
    )
    db_session.add(priv_port)
    await db_session.flush()
    draft_proj = Project(
        portfolio_id=seed_users["portfolio"].id,
        category_id=seed_users["category"].id,
        title="Unpublished Draft Shoot",
        slug=f"draft-{uuid.uuid4().hex[:6]}",
        publication_status="draft",
    )
    db_session.add(draft_proj)
    await db_session.commit()

    assert (await client.get(f"/portfolios/{priv_port.id}/projects")).status_code == 403
    assert (await client.get(f"/projects/{draft_proj.id}")).status_code == 403

    # Owner CAN still inspect private portfolio & draft project
    await client.post("/auth/login", json={"email": "pro@example.com", "password": "ProPass@2026!"})
    assert (await client.get(f"/portfolios/{priv_port.id}/projects")).status_code == 200
    assert (await client.get(f"/projects/{draft_proj.id}")).status_code == 200


@pytest.mark.asyncio
async def test_sec06_config_supports_non_razorpay_prod_without_razorpay_keys():
    prod_bank = Settings(
        ENVIRONMENT="production",
        DEBUG=False,
        SECRET_KEY="x" * 40,
        CSRF_SECRET="y" * 40,
        DATABASE_URL="postgresql+asyncpg://maancamera_app:real_prod_pw@postgres:5432/mc",
        SYNC_DATABASE_URL="postgresql+psycopg2://maancamera:real_owner_pw@postgres:5432/mc",
        S3_SECRET_ACCESS_KEY="real_s3_prod_key",
        PAYMENT_PROVIDER="bank_transfer",
    )
    assert prod_bank.PAYMENT_PROVIDER == "bank_transfer"


@pytest.mark.asyncio
async def test_payments_razorpay_order_duplicates_webhooks_refund_and_ledger(
    client: AsyncClient, db_session: AsyncSession, seed_users
):
    category = seed_users["category"]
    prof_profile = seed_users["professional_profile"]

    # Create enquiry -> quote -> accept -> pending booking (total 1000000, advance 250000)
    await client.post("/auth/login", json={"email": "customer@example.com", "password": "CustomerPass@2026!"})
    enq = await client.post(
        "/enquiries",
        json={
            "category_id": str(category.id),
            "title": "Wedding Coverage Razorpay Test",
            "description": "End-to-end payment and ledger verification shoot.",
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
            "total_amount_minor": 1000000,
            "advance_amount_minor": 250000,
            "scope_of_work": "Complete event photography & edited gallery",
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
    booking_id = uuid.UUID(acc.json()["data"]["booking"]["id"])

    # Customer cannot bypass payment by directly setting confirmed
    bypass = await client.patch(
        f"/bookings/{booking_id}/status",
        json={"booking_status": "confirmed"},
        headers=csrf_headers(client),
    )
    assert bypass.status_code == 403

    # 1. Razorpay Orders API call mocked & verified
    orig_provider = settings.PAYMENT_PROVIDER
    orig_key_id = settings.RAZORPAY_KEY_ID
    orig_key_sec = settings.RAZORPAY_KEY_SECRET
    settings.PAYMENT_PROVIDER = "razorpay"
    settings.RAZORPAY_KEY_ID = "rzp_test_key123"
    settings.RAZORPAY_KEY_SECRET = "rzp_test_secret123"
    try:
        mock_resp = MagicMock(status_code=200)
        mock_resp.json.return_value = {"id": "order_rzp_live_001", "amount": 250000, "currency": "INR"}
        post_mock = AsyncMock(return_value=mock_resp)

        class _FakeHttpxClient:
            def __init__(self, *args, **kwargs):
                pass

            async def __aenter__(self):
                return self

            async def __aexit__(self, *args):
                return False

            post = post_mock

        fake_httpx = SimpleNamespace(AsyncClient=_FakeHttpxClient)
        with patch("app.modules.payments.service.httpx", fake_httpx):
            ord_res = await client.post(
                "/payments/create-order",
                json={"booking_id": str(booking_id), "payment_type": "advance"},
                headers=csrf_headers(client, {"Idempotency-Key": "idem-key-1"}),
            )
            assert ord_res.status_code == 201
            assert ord_res.json()["data"]["provider_order_id"] == "order_rzp_live_001"
            assert ord_res.json()["data"]["provider_key_id"] == "rzp_test_key123"
            assert post_mock.call_count == 1

            # Duplicate create-order (both same stage AND same Idempotency-Key) does NOT hit Razorpay twice
            dup_stage = await client.post(
                "/payments/create-order",
                json={"booking_id": str(booking_id), "payment_type": "advance"},
                headers=csrf_headers(client),
            )
            assert dup_stage.status_code == 201
            assert dup_stage.json()["data"]["provider_order_id"] == "order_rzp_live_001"
            assert dup_stage.json()["data"]["idempotent_replay"] is True
            assert post_mock.call_count == 1
    finally:
        settings.PAYMENT_PROVIDER = orig_provider
        settings.RAZORPAY_KEY_ID = orig_key_id
        settings.RAZORPAY_KEY_SECRET = orig_key_sec

    # Switch pending payment to mock for capture + out-of-order + refund verification
    pay_row = (await db_session.execute(select(Payment).where(Payment.booking_id == booking_id))).scalar_one()
    pay_row.provider = "mock"
    await db_session.commit()

    # Capture via verify
    sig = compute_mock_signature(pay_row.provider_order_id or "", "pay_mock_001")
    ver = await client.post(
        "/payments/verify",
        json={"payment_id": str(pay_row.id), "provider_payment_id": "pay_mock_001", "provider_signature": sig},
        headers=csrf_headers(client),
    )
    assert ver.status_code == 200
    assert ver.json()["data"]["payment_status"] == "captured"

    # Webhook missing 'event' field fails closed (never defaults to payment.captured)
    missing_evt = json.dumps({"id": "evt_no_type"})
    missing_sig = hmac.new(settings.SECRET_KEY.encode("utf-8"), missing_evt.encode("utf-8"), hashlib.sha256).hexdigest()
    bad_wh = await client.post(
        "/payments/webhooks/mock",
        content=missing_evt,
        headers={"X-Mock-Signature": missing_sig, "Content-Type": "application/json"},
    )
    assert bad_wh.status_code == 400

    # Delayed out-of-order payment.failed webhook MUST NOT overwrite already captured payment
    failed_evt = json.dumps({
        "id": f"evt_late_fail_{uuid.uuid4().hex[:6]}",
        "event": "payment.failed",
        "payload": {"payment": {"entity": {"id": "pay_mock_001", "order_id": pay_row.provider_order_id}}},
    })
    fail_sig = hmac.new(settings.SECRET_KEY.encode("utf-8"), failed_evt.encode("utf-8"), hashlib.sha256).hexdigest()
    late_wh = await client.post(
        "/payments/webhooks/mock",
        content=failed_evt,
        headers={"X-Mock-Signature": fail_sig, "Content-Type": "application/json"},
    )
    assert late_wh.status_code == 200
    await db_session.refresh(pay_row)
    assert pay_row.payment_status == "captured"

    # Cancel booking -> Customer issues partial refund -> Over-refund rejected -> Summary includes ledger
    await client.post(
        f"/bookings/{booking_id}/cancel",
        json={"cancellation_reason": "Schedule postponed"},
        headers=csrf_headers(client),
    )
    ref1 = await client.post(
        f"/payments/{pay_row.id}/refund",
        json={"amount_minor": 100000, "reason": "Cancellation policy refund"},
        headers=csrf_headers(client),
    )
    assert ref1.status_code == 201

    over_ref = await client.post(
        f"/payments/{pay_row.id}/refund",
        json={"amount_minor": 200000, "reason": "Exceeds remaining refundable amount"},
        headers=csrf_headers(client),
    )
    assert over_ref.status_code == 400

    summary = await client.get(f"/payments/bookings/{booking_id}")
    assert summary.status_code == 200
    sdata = summary.json()["data"]
    assert sdata["paid_amount_minor"] == 150000
    entry_types = {e["entry_type"] for e in sdata["ledger_entries"]}
    assert {"payment_captured", "platform_commission", "payout_hold", "refund_issued"} <= entry_types

    # Admin review moderation rejects non-admins (SEC-04)
    rev_check = await client.get("/admin/reviews")
    assert rev_check.status_code == 403
