"""Application boot, OpenAPI generation, and production configuration smoke tests."""

import pytest
from httpx import AsyncClient
from pydantic import ValidationError

from app.core.config import Settings
from app.main import app


def test_app_boots_and_openapi_generates():
    assert app.title == "MaanCamera API"
    schema = app.openapi()
    paths = schema.get("paths", {})
    assert "/api/v1/users/me" in paths
    assert "/api/v1/auth/login" in paths
    assert "/api/v1/professionals" in paths
    assert "/api/v1/payments/create-order" in paths


@pytest.mark.asyncio
async def test_health_endpoint(client: AsyncClient):
    res = await client.get("http://testserver/health")
    assert res.status_code == 200
    assert res.json()["status"] == "healthy"


def test_production_config_rejects_mock_payments_and_dev_secrets():
    with pytest.raises(ValidationError):
        Settings(
            ENVIRONMENT="production",
            SECRET_KEY="x" * 40,
            CSRF_SECRET="y" * 40,
            PAYMENT_PROVIDER="mock",
        )

    with pytest.raises(ValidationError):
        Settings(
            ENVIRONMENT="production",
            SECRET_KEY="x" * 40,
            CSRF_SECRET="y" * 40,
            PAYMENT_PROVIDER="razorpay",
            RAZORPAY_KEY_ID="",
            RAZORPAY_KEY_SECRET="",
            RAZORPAY_WEBHOOK_SECRET="",
        )
