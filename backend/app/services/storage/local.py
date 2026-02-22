"""Local filesystem storage backend."""
import logging
from pathlib import Path
from typing import Optional

from app.services.storage.base import StorageBackend

logger = logging.getLogger(__name__)


class LocalStorageBackend(StorageBackend):
    """Local filesystem storage."""
    
    def __init__(self, base_path: str = "/app/storage/papers"):
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
    
    def _get_path(self, key: str) -> Path:
        """Get full path for key."""
        # Organize by prefix: ab/cd/abcdef123.pdf
        prefix = key[:2] if len(key) >= 2 else "xx"
        suffix = key[2:4] if len(key) >= 4 else "xx"
        dir_path = self.base_path / prefix / suffix
        dir_path.mkdir(parents=True, exist_ok=True)
        return dir_path / key
    
    async def upload(self, key: str, data: bytes, content_type: str = "application/pdf") -> str:
        path = self._get_path(key)
        path.write_bytes(data)
        return f"file://{path}"
    
    async def download(self, key: str) -> Optional[bytes]:
        path = self._get_path(key)
        if path.exists():
            return path.read_bytes()
        return None
    
    async def exists(self, key: str) -> bool:
        return self._get_path(key).exists()
    
    async def delete(self, key: str) -> bool:
        path = self._get_path(key)
        if path.exists():
            path.unlink()
            return True
        return False
