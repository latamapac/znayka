"""Base storage backend interface."""
from abc import ABC, abstractmethod
from typing import Optional


class StorageBackend(ABC):
    """Abstract storage backend."""
    
    @abstractmethod
    async def upload(self, key: str, data: bytes, content_type: str = "application/pdf") -> str:
        """Upload file, return URL."""
        pass
    
    @abstractmethod
    async def download(self, key: str) -> Optional[bytes]:
        """Download file."""
        pass
    
    @abstractmethod
    async def exists(self, key: str) -> bool:
        """Check if file exists."""
        pass
    
    @abstractmethod
    async def delete(self, key: str) -> bool:
        """Delete file."""
        pass
