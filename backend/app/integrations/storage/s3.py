"""SeaweedFS S3-compatible object storage service."""

import uuid
from typing import Any

import aioboto3
import boto3

from app.core.config import settings


class StorageService:
    """Handles object storage interactions with local SeaweedFS S3 gateway."""

    def __init__(self):
        self.session = aioboto3.Session()
        self.endpoint_url = settings.S3_ENDPOINT_URL
        self.public_endpoint = settings.S3_PUBLIC_ENDPOINT_URL
        self.access_key = settings.S3_ACCESS_KEY_ID
        self.secret_key = settings.S3_SECRET_ACCESS_KEY
        self.public_bucket = settings.S3_BUCKET_PUBLIC_PORTFOLIOS
        self.private_bucket = settings.S3_BUCKET_PRIVATE_UPLOADS

    def _get_client(self):
        return self.session.client(
            "s3",
            endpoint_url=self.endpoint_url,
            aws_access_key_id=self.access_key,
            aws_secret_access_key=self.secret_key,
            region_name=settings.S3_REGION,
        )

    def get_sync_client(self):
        """Return synchronous boto3 S3 client for Celery workers."""
        return boto3.client(
            "s3",
            endpoint_url=self.endpoint_url,
            aws_access_key_id=self.access_key,
            aws_secret_access_key=self.secret_key,
            region_name=settings.S3_REGION,
        )

    async def generate_presigned_upload_url(
        self,
        owner_user_id: uuid.UUID,
        extension: str,
        content_type: str,
        file_size_bytes: int,
        is_public: bool = True,
        expires_in: int = 900,
    ) -> dict[str, Any]:
        """Generate server-derived presigned PUT URL signing Content-Type and Content-Length."""
        bucket = self.public_bucket if is_public else self.private_bucket
        prefix = "public" if is_public else "private"
        safe_ext = extension.lower() if extension.startswith(".") else f".{extension.lower()}"
        unique_key = f"{prefix}/{owner_user_id}/{uuid.uuid4().hex}{safe_ext}"

        async with self._get_client() as s3:
            url = await s3.generate_presigned_url(
                ClientMethod="put_object",
                Params={
                    "Bucket": bucket,
                    "Key": unique_key,
                    "ContentType": content_type,
                    "ContentLength": file_size_bytes,
                },
                ExpiresIn=expires_in,
            )

        return {
            "upload_url": url,
            "storage_key": unique_key,
            "bucket": bucket,
            "public_url": None,  # Published only after Pillow worker sanitization completes
            "expires_in_seconds": expires_in,
            "max_content_length_bytes": file_size_bytes,
        }

    def get_public_url(self, storage_key: str, is_public: bool = True) -> str | None:
        if not is_public:
            return None
        return f"{self.public_endpoint}/{self.public_bucket}/{storage_key}"

    async def delete_file(self, storage_key: str, is_public: bool = True) -> bool:
        """Delete an object from SeaweedFS."""
        bucket = self.public_bucket if is_public else self.private_bucket
        try:
            async with self._get_client() as s3:
                await s3.delete_object(Bucket=bucket, Key=storage_key)
            return True
        except Exception:
            return False


storage_service = StorageService()
