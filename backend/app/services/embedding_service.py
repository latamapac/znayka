"""Embedding service - uses Google Vertex AI when available."""
import logging
import os
from typing import Optional, List

from app.services.vertex_ai_embeddings import get_vertex_embedding_service

logger = logging.getLogger(__name__)


class EmbeddingService:
    """
    Embedding service - Google Vertex AI (GCP) or fallback.
    """
    
    def __init__(self, dimension: int = 768):
        self.dimension = dimension
        self._vertex_service = None
        
        # Try to use Vertex AI on Google Cloud
        if os.getenv("GOOGLE_CLOUD_PROJECT"):
            try:
                self._vertex_service = get_vertex_embedding_service()
                logger.info("Using Vertex AI for embeddings (768-dim)")
            except Exception as e:
                logger.warning(f"Vertex AI not available: {e}")
        
        if not self._vertex_service:
            logger.info("Using fallback embeddings (hash-based)")
    
    async def get_embedding(self, text: str) -> Optional[List[float]]:
        """Get embedding for text."""
        if not text or not text.strip():
            return None
        
        # Use Vertex AI if available
        if self._vertex_service:
            return await self._vertex_service.get_embedding(text)
        
        # Fallback to hash-based
        return await self._fallback_embedding(text)
    
    async def _fallback_embedding(self, text: str) -> List[float]:
        """Deterministic fallback embedding."""
        import hashlib
        import random
        import math
        
        hash_obj = hashlib.md5(text.encode())
        hash_int = int(hash_obj.hexdigest(), 16)
        
        random.seed(hash_int)
        embedding = [random.uniform(-1, 1) for _ in range(self.dimension)]
        
        magnitude = math.sqrt(sum(x**2 for x in embedding))
        if magnitude > 0:
            embedding = [x / magnitude for x in embedding]
        
        return embedding
