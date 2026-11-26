"""Authentication and Session Lifecycle Tests."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_register_customer(client: AsyncClient):
    payload = {
        "full_name": "Kavita Rao",
        "email": "kavita.rao@example.com",
        "password": "SecurePassword@2026!",
        "role": "customer",
    }
    response = await client.post("/auth/register", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["success"] is True
    assert data["data"]["email"] == "kavita.rao@example.com"
    assert data["data"]["role"] == "customer"


@pytest.mark.asyncio
async def test_register_duplicate_email(client: AsyncClient):
    payload = {
        "full_name": "Duplicate User",
        "email": "kavita.rao@example.com",
        "password": "SecurePassword@2026!",
        "role": "customer",
    }
    response = await client.post("/auth/register", json=payload)
    assert response.status_code == 409
    data = response.json()
    assert data["success"] is False
    assert data["error"]["code"] == "RESOURCE_CONFLICT"


@pytest.mark.asyncio
async def test_login_success_and_me(client: AsyncClient, seed_users):
    login_payload = {
        "email": "customer@example.com",
        "password": "CustomerPass@2026!",
    }
    response = await client.post("/auth/login", json=login_payload)
    assert response.status_code == 200
    assert "mc_session" in response.cookies

    # Test /auth/me with session cookie
    me_response = await client.get("/auth/me")
    assert me_response.status_code == 200
    me_data = me_response.json()
    assert me_data["success"] is True
    assert me_data["data"]["email"] == "customer@example.com"
    assert me_data["data"]["role"] == "customer"


@pytest.mark.asyncio
async def test_login_invalid_password(client: AsyncClient):
    login_payload = {
        "email": "customer@example.com",
        "password": "WrongPassword@2026!",
    }
    response = await client.post("/auth/login", json=login_payload)
    assert response.status_code == 401
    data = response.json()
    assert data["success"] is False
    assert data["error"]["code"] == "UNAUTHORIZED"
