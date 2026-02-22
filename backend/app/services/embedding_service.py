"""Embedding service - simplified version without heavy ML."""
import logging
from typing import Optional, List
import hashlib

logger = logging.getLogger(__name__)


class EmbeddingService:
    """
    Simplified embedding service.
    Uses random/projections for now - proper embeddings later.
    """
    
    def __init__(self, dimension: int = 384):
        self.dimension = dimension
        logger.info(f"EmbeddingService initialized (dimension={dimension})")
    
    async def get_embedding(self, text: str) -> Optional[List[float]]:
        """
        Get embedding for text.
        
        For now, returns deterministic pseudo-embeddings.
        Will be replaced with real model later.
        """
        if not text or not text.strip():
            return None
        
        try:
            # Create deterministic embedding from text hash
            # This is temporary - proper embeddings coming in Phase 2
            hash_obj = hashlib.md5(text.encode())
            hash_int = int(hash_obj.hexdigest(), 16)
            
            # Generate pseudo-random but deterministic vector
            import random
            random.seed(hash_int)
            embedding = [random.uniform(-1, 1) for _ in range(self.dimension)]
            
            # Normalize
            import math
            magnitude = math.sqrt(sum(x**2 for x in embedding))
            if magnitude > 0:
                embedding = [x / magnitude for x in embedding]
            
            return embedding
            
        except Exception as e:
            logger.error(f"Embedding generation failed: {e}")
            return None
