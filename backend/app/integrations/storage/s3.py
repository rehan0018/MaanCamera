"""SeaweedFS S3-compatible object storage service."""

import uuid
from typing import Dict, Any, Optional
import aioboto3
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

    async def generate_presigned_upload_url(
        self,
        filename: str,
        content_type: str,
        is_public: bool = True,
        expires_in: int = 900,
    ) -> Dict[str, Any]:
        """Generate presigned PUT URL for client-side direct upload."""
        bucket = self.public_bucket if is_public else self.private_bucket
        prefix = "public" if is_public else "private"
        unique_key = f"{prefix}/{uuid.uuid4().hex}_{filename}"

        async with self._get_client() as s3:
            url = await s3.generate_presigned_url(
                ClientMethod="put_object",
                Params={
                    "Bucket": bucket,
                    "Key": unique_key,
                    "ContentType": content_type,
                },
                ExpiresIn=expires_in,
            )

        public_access_url = f"{self.public_endpoint}/{bucket}/{unique_key}" if is_public else None

        return {
            "upload_url": url,
            "storage_key": unique_key,
            "bucket": bucket,
            "public_url": public_access_url,
            "expires_in_seconds": expires_in,
        }

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
