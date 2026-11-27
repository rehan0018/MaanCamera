"""Professional profile CRUD, portfolio ownership, media upload validation, and EXIF stripping tests."""

import io
import uuid

import pytest
from httpx import AsyncClient
from PIL import Image, UnidentifiedImageError

from app.workers.celery_app import validate_and_sanitize_image
from tests.conftest import csrf_headers


@pytest.mark.asyncio
async def test_professional_lifecycle_and_endpoints(client: AsyncClient, seed_users):
    category = seed_users["category"]

    # Register & login as a brand-new professional
    reg = await client.post(
        "/auth/register",
        json={
            "full_name": "Neha Kapoor",
            "email": "neha.pro@example.com",
            "password": "ProPassword@2026!",
            "role": "professional",
        },
    )
    assert reg.status_code == 201

    login = await client.post(
        "/auth/login",
        json={"email": "neha.pro@example.com", "password": "ProPassword@2026!"},
    )
    assert login.status_code == 200

    # Create professional profile (tests owner_user_id + commit)
    create_res = await client.post(
        "/professionals",
        json={
            "display_name": "Neha Kapoor Studios",
            "headline": "Fine Art Portrait Photographer",
            "biography": "Documentary and fine art portraits in Mumbai.",
            "professional_type": "studio",
            "years_experience": 5,
            "base_city": "Mumbai",
            "state": "Maharashtra",
        },
        headers=csrf_headers(client),
    )
    assert create_res.status_code == 201
    prof = create_res.json()["data"]
    prof_id = prof["id"]

    # Duplicate creation rejected (409)
    dup_res = await client.post(
        "/professionals",
        json={
            "display_name": "Duplicate Studio",
            "base_city": "Mumbai",
            "state": "Maharashtra",
        },
        headers=csrf_headers(client),
    )
    assert dup_res.status_code == 409

    # Read /me and /{id}
    me_res = await client.get("/professionals/me")
    assert me_res.status_code == 200
    assert me_res.json()["data"]["id"] == prof_id

    by_id_res = await client.get(f"/professionals/{prof_id}")
    assert by_id_res.status_code == 200

    # Update via PATCH /professionals/me and PATCH /professionals/{id}
    patch_me = await client.patch(
        "/professionals/me",
        json={"headline": "Updated Fine Art Studio"},
        headers=csrf_headers(client),
    )
    assert patch_me.status_code == 200
    assert patch_me.json()["data"]["headline"] == "Updated Fine Art Studio"

    patch_id = await client.patch(
        f"/professionals/{prof_id}",
        json={"years_experience": 6},
        headers=csrf_headers(client),
    )
    assert patch_id.status_code == 200
    assert patch_id.json()["data"]["years_experience"] == 6

    # Create service under /professionals/me/services
    svc_res = await client.post(
        "/professionals/me/services",
        json={
            "category_id": str(category.id),
            "name": "Editorial Portrait Package",
            "starting_price_minor": 3000000,
        },
        headers=csrf_headers(client),
    )
    assert svc_res.status_code == 201
    assert svc_res.json()["data"]["starting_price_minor"] == 3000000

    # Search using style filter matching biography column
    search_res = await client.get("/search/professionals?city=Mumbai&style=documentary")
    assert search_res.status_code == 200
    assert any(p["id"] == prof_id for p in search_res.json()["data"]["results"])

    # Hit /enquiries/me and /bookings/me as professional
    assert (await client.get("/enquiries/me")).status_code == 200
    assert (await client.get("/bookings/me")).status_code == 200

    # Delete professional profile
    del_res = await client.delete(f"/professionals/{prof_id}", headers=csrf_headers(client))
    assert del_res.status_code == 200
    assert del_res.json()["data"]["deleted"] is True


@pytest.mark.asyncio
async def test_upload_url_rejects_disallowed_mime_extension_and_oversized(client: AsyncClient, seed_users):
    await client.post("/auth/login", json={"email": "pro@example.com", "password": "ProPass@2026!"})

    # Disallowed MIME type
    bad_mime = await client.post(
        "/media/upload-url",
        json={"filename": "payload.html", "mime_type": "text/html", "file_size_bytes": 1024},
        headers=csrf_headers(client),
    )
    assert bad_mime.status_code == 422

    # Mismatched extension
    bad_ext = await client.post(
        "/media/upload-url",
        json={"filename": "fake.exe", "mime_type": "image/jpeg", "file_size_bytes": 1024},
        headers=csrf_headers(client),
    )
    assert bad_ext.status_code == 422

    # Oversized file (>15 MiB)
    too_big = await client.post(
        "/media/upload-url",
        json={"filename": "huge.jpg", "mime_type": "image/jpeg", "file_size_bytes": 25 * 1024 * 1024},
        headers=csrf_headers(client),
    )
    assert too_big.status_code == 422

    # Valid upload URL returns server-generated key without client filename path
    good = await client.post(
        "/media/upload-url",
        json={"filename": "../../etc/passwd.jpg", "mime_type": "image/jpeg", "file_size_bytes": 2048},
        headers=csrf_headers(client),
    )
    assert good.status_code == 200
    key = good.json()["data"]["storage_key"]
    assert "passwd" not in key
    assert key.startswith("public/") and key.endswith(".jpg")

    # Portfolio IDOR: pro cannot complete upload into another user's prefix
    proj = seed_users["project"]
    bad_key_complete = await client.post(
        "/media/complete",
        json={
            "project_id": str(proj.id),
            "storage_key": f"public/{uuid.uuid4()}/hijack.jpg",
            "mime_type": "image/jpeg",
            "file_size_bytes": 2048,
            "checksum": "0" * 64,
        },
        headers=csrf_headers(client),
    )
    assert bad_key_complete.status_code == 400


def test_pillow_worker_strips_exif_and_rejects_non_images():
    # Reject arbitrary non-image bytes
    with pytest.raises((UnidentifiedImageError, ValueError, OSError)):
        validate_and_sanitize_image(b"not a valid image payload")

    # Create JPEG with EXIF payload and verify WebP derivative removes EXIF
    img = Image.new("RGB", (600, 400), color=(120, 45, 200))
    exif = Image.Exif()
    exif[0x010F] = "SensitiveCameraMaker"
    buf = io.BytesIO()
    img.save(buf, format="JPEG", exif=exif)

    display_webp, thumb_webp, w, h = validate_and_sanitize_image(buf.getvalue())
    assert w == 600 and h == 400
    with Image.open(io.BytesIO(display_webp)) as cleaned:
        assert cleaned.format == "WEBP"
        assert len(cleaned.getexif()) == 0
    with Image.open(io.BytesIO(thumb_webp)) as thumb:
        assert thumb.format == "WEBP"
        assert thumb.width <= 300
