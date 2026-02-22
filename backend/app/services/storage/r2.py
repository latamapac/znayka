"""Cloudflare R2 storage backend (S3-compatible)."""
import os
import logging
from typing import Optional

from app.services.storage.base import StorageBackend

logger = logging.getLogger(__name__)


class R2StorageBackend(StorageBackend):
    """Cloudflare R2 storage."""
    
    def __init__(self):
        self.endpoint = os.getenv("R2_ENDPOINT")
        self.access_key = os.getenv("R2_ACCESS_KEY_ID")
        self.secret_key = os.getenv("R2_SECRET_ACCESS_KEY")
        self.bucket = os.getenv("R2_BUCKET_NAME", "znayka-papers")
        self.public_url = os.getenv("R2_PUBLIC_URL")
        
        if not all([self.endpoint, self.access_key, self.secret_key]):
            raise ValueError("R2 credentials not configured")
        
        try:
            import boto3
            self.client = boto3.client(
                "s3",
                endpoint_url=self.endpoint,
                aws_access_key_id=self.access_key,
                aws_secret_access_key=self.secret_key,
            )
        except ImportError:
            logger.error("boto3 not installed for R2 support")
            raise
    
    async def upload(self, key: str, data: bytes, content_type: str = "application/pdf") -> str:
        import asyncio
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            lambda: self.client.put_object(
                Bucket=self.bucket,
                Key=key,
                Body=data,
                ContentType=content_type
            )
        )
        if self.public_url:
            return f"{self.public_url}/{key}"
        return f"{self.endpoint}/{self.bucket}/{key}"
    
    async def download(self, key: str) -> Optional[bytes]:
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self.client.get_object(Bucket=self.bucket, Key=key)
            )
            return response["Body"].read()
        except Exception as e:
            logger.error(f"R2 download failed: {e}")
            return None
    
    async def exists(self, key: str) -> bool:
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: self.client.head_object(Bucket=self.bucket, Key=key)
            )
            return True
        except:
            return False
    
    async def delete(self, key: str) -> bool:
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: self.client.delete_object(Bucket=self.bucket, Key=key)
            )
            return True
        except:
            return False
