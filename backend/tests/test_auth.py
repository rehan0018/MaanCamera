"""Authentication, CSRF, and Session Lifecycle Tests."""

import pytest
from httpx import AsyncClient

from tests.conftest import csrf_headers


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
async def test_register_cannot_self_assign_admin(client: AsyncClient):
    payload = {
        "full_name": "Malicious Admin",
        "email": "evil@example.com",
        "password": "SecurePassword@2026!",
        "role": "admin",
    }
    response = await client.post("/auth/register", json=payload)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_register_duplicate_email(client: AsyncClient):
    payload = {
        "full_name": "Duplicate User",
        "email": "dup.user@example.com",
        "password": "SecurePassword@2026!",
        "role": "customer",
    }
    first = await client.post("/auth/register", json=payload)
    assert first.status_code == 201

    second = await client.post("/auth/register", json=payload)
    assert second.status_code == 409
    data = second.json()
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
    assert "mc_csrf" in response.cookies

    me_response = await client.get("/users/me")
    assert me_response.status_code == 200
    me_data = me_response.json()
    assert me_data["success"] is True
    assert me_data["data"]["email"] == "customer@example.com"
    assert me_data["data"]["role"] == "customer"


@pytest.mark.asyncio
async def test_login_invalid_password(client: AsyncClient, seed_users):
    login_payload = {
        "email": "customer@example.com",
        "password": "WrongPassword@2026!",
    }
    response = await client.post("/auth/login", json=login_payload)
    assert response.status_code == 401
    data = response.json()
    assert data["success"] is False
    assert data["error"]["code"] == "UNAUTHORIZED"


@pytest.mark.asyncio
async def test_csrf_enforced_on_cookie_mutations(client: AsyncClient, seed_users):
    res = await client.post(
        "/auth/login",
        json={"email": "customer@example.com", "password": "CustomerPass@2026!"},
    )
    assert res.status_code == 200

    # Cross-origin rejected
    bad_origin = await client.post(
        "/auth/logout",
        headers=csrf_headers(client, {"Origin": "https://evil.example"}),
    )
    assert bad_origin.status_code == 403
    assert bad_origin.json()["error"]["code"] == "CSRF_ORIGIN_MISMATCH"

    # Missing X-CSRF-Token rejected when session cookie present
    missing_csrf = await client.post("/auth/logout")
    assert missing_csrf.status_code == 403
    assert missing_csrf.json()["error"]["code"] == "CSRF_TOKEN_INVALID"

    # Valid double-submit succeeds
    ok_logout = await client.post("/auth/logout", headers=csrf_headers(client))
    assert ok_logout.status_code == 200
