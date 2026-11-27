"""Celery worker configuration for asynchronous media validation, EXIF stripping, and WebP publishing."""

import contextlib
import io
import logging
import uuid

from celery import Celery
from PIL import Image, ImageOps
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.integrations.storage.s3 import storage_service
from app.modules.portfolios.models import MediaAsset

logger = logging.getLogger("maancamera_workers")

# Guard against decompression bomb attacks on untrusted image uploads
Image.MAX_IMAGE_PIXELS = 40_000_000
ALLOWED_IMAGE_FORMATS = {"JPEG", "PNG", "WEBP"}

celery_app = Celery(
    "maancamera_workers",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

_is_test = settings.ENVIRONMENT == "test"
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone=settings.TIMEZONE,
    enable_utc=True,
    task_track_started=True,
    task_publish_retry=not _is_test,
    task_publish_retry_policy={
        "max_retries": 0 if _is_test else 1,
        "interval_start": 0,
        "interval_step": 0.1,
        "interval_max": 0.2,
    },
    broker_transport_options={
        "max_retries": 0 if _is_test else 1,
        "socket_connect_timeout": 0.5 if _is_test else 1.0,
        "socket_timeout": 0.5 if _is_test else 1.0,
    },
    result_backend_transport_options={
        "retry_policy": {"max_retries": 0},
    },
)


def validate_and_sanitize_image(
    image_bytes: bytes,
    max_width: int = 1600,
    thumb_width: int = 300,
    quality: int = 85,
) -> tuple[bytes, bytes, int, int]:
    """
    Validate uploaded bytes as a genuine JPEG/PNG/WEBP image via Pillow,
    auto-orient from EXIF, discard all EXIF segments, and encode WebP variants.
    Returns (display_webp_bytes, thumb_webp_bytes, final_width, final_height).
    """
    if len(image_bytes) > settings.MAX_UPLOAD_SIZE_BYTES:
        raise ValueError("Uploaded object exceeds maximum allowed image size.")

    # Verify structural integrity & declared image format
    with Image.open(io.BytesIO(image_bytes)) as probe_img:
        if probe_img.format not in ALLOWED_IMAGE_FORMATS:
            raise ValueError(f"Unsupported image format: {probe_img.format}")
        probe_img.verify()

    with Image.open(io.BytesIO(image_bytes)) as img:
        transposed = ImageOps.exif_transpose(img)
        if transposed is None:
            transposed = img.copy()

        if transposed.width > max_width:
            height = max(1, int((max_width / transposed.width) * transposed.height))
            transposed = transposed.resize((max_width, height), Image.Resampling.LANCZOS)

        if transposed.mode in ("RGBA", "LA") or (transposed.mode == "P" and "transparency" in transposed.info):
            pass
        elif transposed.mode != "RGB":
            transposed = transposed.convert("RGB")

        final_w, final_h = transposed.size

        display_buf = io.BytesIO()
        transposed.save(display_buf, format="WEBP", quality=quality, method=6)

        thumb_h = max(1, int((thumb_width / final_w) * final_h)) if final_w > thumb_width else final_h
        thumb_w = min(final_w, thumb_width)
        thumb_img = transposed.resize((thumb_w, thumb_h), Image.Resampling.LANCZOS)
        thumb_buf = io.BytesIO()
        thumb_img.save(thumb_buf, format="WEBP", quality=80, method=6)

        return display_buf.getvalue(), thumb_buf.getvalue(), final_w, final_h


def strip_exif_and_generate_webp(image_bytes: bytes, max_width: int = 1600, quality: int = 85) -> bytes:
    """Backward-compatible helper returning EXIF-stripped display WebP bytes."""
    display_webp, _, _, _ = validate_and_sanitize_image(image_bytes, max_width=max_width, quality=quality)
    return display_webp


def process_media_asset_with_storage(
    asset: MediaAsset,
    storage_key: str,
    s3_client,
) -> dict[str, object]:
    """Sanitize raw uploaded image bytes and store processed WebP variants preserving visibility."""
    is_private = (asset.visibility == "private") or storage_key.startswith("private/")
    source_bucket = (
        storage_service.private_bucket if storage_key.startswith("private/") else storage_service.public_bucket
    )
    dest_bucket = storage_service.private_bucket if is_private else storage_service.public_bucket
    prefix = "private" if is_private else "public"

    obj = s3_client.get_object(Bucket=source_bucket, Key=storage_key)
    raw_bytes = obj["Body"].read()
    display_webp, thumb_webp, width, height = validate_and_sanitize_image(raw_bytes)

    display_key = f"{prefix}/processed/{asset.id}/display.webp"
    thumb_key = f"{prefix}/processed/{asset.id}/thumb_300.webp"

    s3_client.put_object(
        Bucket=dest_bucket,
        Key=display_key,
        Body=display_webp,
        ContentType="image/webp",
    )
    s3_client.put_object(
        Bucket=dest_bucket,
        Key=thumb_key,
        Body=thumb_webp,
        ContentType="image/webp",
    )

    # Remove unsanitized raw original once sanitized variants are persisted safely
    if storage_key != display_key:
        with contextlib.suppress(Exception):
            s3_client.delete_object(Bucket=source_bucket, Key=storage_key)

    asset.visibility = "private" if is_private else "public"
    asset.storage_key = display_key
    asset.public_url = None if is_private else storage_service.get_public_url(display_key, is_public=True)
    asset.mime_type = "image/webp"
    asset.file_size_bytes = len(display_webp)
    asset.width = width
    asset.height = height
    asset.processing_status = "completed"

    return {
        "asset_id": str(asset.id),
        "bucket": dest_bucket,
        "visibility": asset.visibility,
        "storage_key": display_key,
        "status": "completed",
        "exif_stripped": True,
        "variants": [display_key, thumb_key],
    }


@celery_app.task(name="tasks.process_uploaded_media")
def process_uploaded_media(asset_id: str, storage_key: str) -> dict[str, object]:
    """Download uploaded file, validate with Pillow, strip EXIF, store preserving visibility."""
    logger.info(f"Validating and sanitizing media asset {asset_id} from {storage_key}...")
    sync_db_url = settings.SYNC_DATABASE_URL
    if sync_db_url.startswith("postgresql://"):
        sync_db_url = sync_db_url.replace("postgresql://", "postgresql+psycopg2://", 1)

    engine = create_engine(sync_db_url)
    s3 = storage_service.get_sync_client()
    source_bucket = (
        storage_service.private_bucket if storage_key.startswith("private/") else storage_service.public_bucket
    )

    with Session(engine) as session:
        session.info["rls_user_role"] = "system"
        asset = session.execute(
            select(MediaAsset).where(MediaAsset.id == uuid.UUID(asset_id))
        ).scalar_one_or_none()
        if not asset:
            return {"asset_id": asset_id, "status": "not_found"}

        try:
            result = process_media_asset_with_storage(asset, storage_key, s3)
            session.commit()
            return result
        except Exception as exc:
            logger.exception(f"Media validation failed for asset {asset_id}: {exc}")
            asset.processing_status = "failed"
            asset.public_url = None
            session.commit()
            with contextlib.suppress(Exception):
                s3.delete_object(Bucket=source_bucket, Key=storage_key)
            return {"asset_id": asset_id, "status": "failed", "error": str(exc)}
        finally:
            engine.dispose()
