"""Unified storage service."""
import os
import logging
from pathlib import Path
from typing import Optional

import aiohttp

from app.services.storage.base import StorageBackend
from app.services.storage.local import LocalStorageBackend
from app.services.storage.r2 import R2StorageBackend

logger = logging.getLogger(__name__)


class StorageService:
    """Unified storage service."""
    
    def __init__(self):
        self.backend = self._create_backend()
    
    def _create_backend(self) -> StorageBackend:
        """Create appropriate backend based on config."""
        # Try R2 first
        if os.getenv("R2_ENDPOINT"):
            logger.info("Using R2 storage backend")
            return R2StorageBackend()
        
        # Fallback to local
        logger.info("Using local storage backend")
        return LocalStorageBackend()
    
    def _generate_key(self, paper_id: str, filename: str) -> str:
        """Generate storage key from paper ID."""
        ext = Path(filename).suffix or ".pdf"
        return f"{paper_id}{ext}"
    
    async def store_pdf(self, paper_id: str, pdf_data: bytes, filename: str = "paper.pdf") -> str:
        """Store PDF, return storage URL."""
        key = self._generate_key(paper_id, filename)
        url = await self.backend.upload(key, pdf_data, "application/pdf")
        logger.info(f"Stored PDF for {paper_id}: {url}")
        return url
    
    async def get_pdf(self, paper_id: str, filename: str = "paper.pdf") -> Optional[bytes]:
        """Retrieve PDF."""
        key = self._generate_key(paper_id, filename)
        return await self.backend.download(key)
    
    async def has_pdf(self, paper_id: str, filename: str = "paper.pdf") -> bool:
        """Check if PDF exists."""
        key = self._generate_key(paper_id, filename)
        return await self.backend.exists(key)
    
    async def delete_pdf(self, paper_id: str, filename: str = "paper.pdf") -> bool:
        """Delete PDF."""
        key = self._generate_key(paper_id, filename)
        return await self.backend.delete(key)
    
    async def download_from_url(self, url: str) -> Optional[bytes]:
        """Download PDF from remote URL."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=60)) as response:
                    if response.status == 200:
                        return await response.read()
                    logger.warning(f"Download failed: HTTP {response.status} for {url}")
        except Exception as e:
            logger.error(f"Download error for {url}: {e}")
        return None


# Singleton instance
_storage_service: Optional[StorageService] = None


def get_storage_service() -> StorageService:
    """Get or create storage service."""
    global _storage_service
    if _storage_service is None:
        _storage_service = StorageService()
    return _storage_service
