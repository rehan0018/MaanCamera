"""OpenAPI-driven authorization matrix enforcing fail-closed auth and RBAC across all routes (S-9)."""

import uuid

import pytest
from httpx import AsyncClient

from app.main import app
from tests.conftest import csrf_headers

# Intentionally unauthenticated routes (auth bootstrap, public catalog/search, or signature-authenticated webhooks)
PUBLIC_ROUTES: set[tuple[str, str]] = {
    ("GET", "/health"),
    ("GET", "/ready"),
    ("GET", "/api/v1/auth/csrf"),
    ("POST", "/api/v1/auth/register"),
    ("POST", "/api/v1/auth/login"),
    ("POST", "/api/v1/auth/logout"),
    ("POST", "/api/v1/auth/verify-email/confirm"),
    ("POST", "/api/v1/auth/password-reset/request"),
    ("POST", "/api/v1/auth/password-reset/confirm"),
    ("GET", "/api/v1/categories"),
    ("GET", "/api/v1/professionals/{id}"),
    ("GET", "/api/v1/portfolios/{portfolio_id}/projects"),
    ("GET", "/api/v1/projects/{project_id}"),
    ("GET", "/api/v1/search/professionals"),
    ("POST", "/api/v1/search/compare"),
    ("GET", "/api/v1/professionals/{id}/reviews"),
    ("POST", "/api/v1/payments/webhooks/{provider}"),
}

SAMPLE_BODIES: dict[str, dict] = {
    "/api/v1/professionals": {
        "display_name": "Unauthorized Pro",
        "base_city": "Pune",
        "state": "Maharashtra",
    },
    "/api/v1/professionals/me": {"display_name": "Updated Pro"},
    "/api/v1/professionals/{id}": {"display_name": "Updated Pro"},
    "/api/v1/professionals/me/services": {
        "category_id": str(uuid.uuid4()),
        "name": "Service",
        "starting_price_minor": 10000,
    },
    "/api/v1/projects": {
        "portfolio_id": str(uuid.uuid4()),
        "category_id": str(uuid.uuid4()),
        "title": "Sample Project",
    },
    "/api/v1/media/upload-url": {
        "filename": "photo.jpg",
        "mime_type": "image/jpeg",
        "file_size_bytes": 1024,
    },
    "/api/v1/media/complete": {
        "project_id": str(uuid.uuid4()),
        "storage_key": "public/none/file.jpg",
        "mime_type": "image/jpeg",
        "file_size_bytes": 1024,
        "checksum": "a" * 32,
    },
    "/api/v1/enquiries": {
        "category_id": str(uuid.uuid4()),
        "title": "Shoot Enquiry Title",
        "description": "Need coverage for an upcoming wedding event.",
        "location": "Pune",
        "city": "Pune",
        "professional_ids": [str(uuid.uuid4())],
    },
    "/api/v1/quotations": {
        "enquiry_id": str(uuid.uuid4()),
        "total_amount_minor": 500000,
        "advance_amount_minor": 100000,
        "scope_of_work": "Full day event photography coverage",
    },
    "/api/v1/quotations/{id}/revisions": {
        "total_amount_minor": 500000,
        "advance_amount_minor": 100000,
        "scope_of_work": "Revised scope of work for event",
    },
    "/api/v1/bookings/{id}/status": {"booking_status": "confirmed"},
    "/api/v1/bookings/{id}/cancel": {"cancellation_reason": "Plan changed"},
    "/api/v1/payments/create-order": {"booking_id": str(uuid.uuid4())},
    "/api/v1/payments/{payment_id}/refund": {"amount_minor": 10000, "reason": "Cancellation refund"},
    "/api/v1/payments/verify": {
        "payment_id": str(uuid.uuid4()),
        "provider_payment_id": "pay_123",
        "provider_signature": "sig",
    },
    "/api/v1/bookings/{id}/review": {
        "overall_rating": 5.0,
        "work_quality_rating": 5.0,
        "communication_rating": 5.0,
        "punctuality_rating": 5.0,
        "value_rating": 5.0,
        "review_text": "Great experience working together!",
    },
    "/api/v1/reviews/{id}/report": {"reason": "spam"},
    "/api/v1/admin/reviews/{id}/moderate": {"decision": "approved"},
    "/api/v1/search/ai": {"query": "Wedding photographer in Pune under 50k"},
    "/api/v1/ai/recommendations": {"query": "Wedding photographer in Pune under 50k"},
    "/api/v1/ai/portfolio/analyze": {"project_id": str(uuid.uuid4())},
    "/api/v1/ai/reviews/summarize": {"professional_id": str(uuid.uuid4())},
    "/api/v1/auth/verify-phone/request": {"phone": "+919876543210"},
    "/api/v1/auth/verify-phone/confirm": {"code": "123456"},
    "/api/v1/auth/totp/enable": {"code": "123456"},
    "/api/v1/auth/totp/disable": {"code": "123456"},
    "/api/v1/users/me": {"confirm_phrase": "DELETE"},
}


def _materialize_url(path: str) -> str:
    dummy_id = str(uuid.uuid4())
    url = (
        path.replace("{id}", dummy_id)
        .replace("{portfolio_id}", dummy_id)
        .replace("{project_id}", dummy_id)
        .replace("{session_id}", dummy_id)
        .replace("{asset_id}", dummy_id)
        .replace("{payment_id}", dummy_id)
        .replace("{booking_id}", dummy_id)
        .replace("{provider}", "razorpay")
    )
    if url.startswith("/api/v1"):
        return url[len("/api/v1") :]
    return f"http://testserver{url}"


@pytest.mark.asyncio
async def test_openapi_anonymous_access_matrix(client: AsyncClient):
    schema = app.openapi()
    http_methods = {"get", "post", "put", "patch", "delete"}

    protected_checked = 0
    for path, ops in schema["paths"].items():
        for method in ops:
            if method.lower() not in http_methods:
                continue
            route_key = (method.upper(), path)
            if route_key in PUBLIC_ROUTES:
                continue

            url = _materialize_url(path)
            body = SAMPLE_BODIES.get(path)
            if method.lower() == "delete" and body is not None:
                res = await client.request("DELETE", url, json=body)
            elif method.lower() in ("post", "patch", "put"):
                res = await client.request(method.upper(), url, json=body or {})
            else:
                res = await client.request(method.upper(), url)

            assert res.status_code in (401, 403), (
                f"Anonymous request unexpectedly allowed on protected route {route_key}: {res.status_code} {res.text}"
            )
            protected_checked += 1

    assert protected_checked >= 35


@pytest.mark.asyncio
async def test_customer_role_cannot_invoke_professional_routes(client: AsyncClient, seed_users):
    await client.post(
        "/auth/login",
        json={"email": "customer@example.com", "password": "CustomerPass@2026!"},
    )
    headers = csrf_headers(client)

    role_guarded_calls = [
        ("POST", "/professionals/me/services", SAMPLE_BODIES["/api/v1/professionals/me/services"]),
        ("PATCH", "/professionals/me", SAMPLE_BODIES["/api/v1/professionals/me"]),
        ("PATCH", f"/professionals/{seed_users['professional_profile'].id}", SAMPLE_BODIES["/api/v1/professionals/{id}"]),
        ("DELETE", f"/professionals/{seed_users['professional_profile'].id}", None),
        ("POST", "/quotations", SAMPLE_BODIES["/api/v1/quotations"]),
        ("POST", "/media/upload-url", SAMPLE_BODIES["/api/v1/media/upload-url"]),
        (
            "POST",
            "/media/complete",
            {
                **SAMPLE_BODIES["/api/v1/media/complete"],
                "project_id": str(seed_users["project"].id),
            },
        ),
        (
            "POST",
            "/projects",
            {
                **SAMPLE_BODIES["/api/v1/projects"],
                "portfolio_id": str(seed_users["portfolio"].id),
                "category_id": str(seed_users["category"].id),
            },
        ),
    ]

    for method, url, payload in role_guarded_calls:
        res = await client.request(method, url, json=payload, headers=headers)
        assert res.status_code in (403, 404), (
            f"Customer role unexpectedly passed {method} {url}: {res.status_code} {res.text}"
        )
