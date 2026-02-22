"""Vertex AI Embeddings for ZNAYKA (Google Cloud)."""
import asyncio
import logging
from typing import Optional, List
import os

logger = logging.getLogger(__name__)


class VertexAIEmbeddingService:
    """
    Google Cloud Vertex AI Embeddings.
    Uses textembedding-gecko model (768 dimensions).
    Much better than local PyTorch - managed, fast, scalable.
    """
    
    def __init__(self, project_id: Optional[str] = None, location: str = "us-central1"):
        self.project_id = project_id or os.getenv("GOOGLE_CLOUD_PROJECT")
        self.location = location
        self.dimension = 768  # Gecko model output
        self._client = None
        
        if not self.project_id:
            logger.warning("GOOGLE_CLOUD_PROJECT not set, Vertex AI disabled")
    
    def _get_client(self):
        """Lazy load Vertex AI client."""
        if self._client is None and self.project_id:
            try:
                from google.cloud import aiplatform
                aiplatform.init(project=self.project_id, location=self.location)
                from vertexai.language_models import TextEmbeddingModel
                self._client = TextEmbeddingModel.from_pretrained("textembedding-gecko@003")
                logger.info("Vertex AI client initialized")
            except ImportError:
                logger.error("google-cloud-aiplatform not installed")
                self._client = None
            except Exception as e:
                logger.error(f"Failed to init Vertex AI: {e}")
                self._client = None
        return self._client
    
    async def get_embedding(self, text: str) -> Optional[List[float]]:
        """
        Get embedding for text using Vertex AI.
        
        Args:
            text: Text to embed
            
        Returns:
            768-dimensional embedding vector
        """
        if not text or not text.strip():
            return None
        
        client = self._get_client()
        if not client:
            # Fallback to hash-based
            return await self._fallback_embedding(text)
        
        try:
            # Truncate if too long (max 3072 tokens)
            text = text[:12000]  # Rough char limit
            
            # Run in thread pool (Vertex AI client is synchronous)
            loop = asyncio.get_event_loop()
            embeddings = await loop.run_in_executor(
                None, 
                lambda: client.get_embeddings([text])
            )
            
            if embeddings and len(embeddings) > 0:
                return embeddings[0].values
            
            return None
            
        except Exception as e:
            logger.error(f"Vertex AI embedding failed: {e}")
            return await self._fallback_embedding(text)
    
    async def get_embeddings_batch(self, texts: List[str]) -> List[Optional[List[float]]]:
        """
        Get embeddings for multiple texts (batch).
        More efficient than individual calls.
        """
        if not texts:
            return []
        
        client = self._get_client()
        if not client:
            # Fallback
            return [await self._fallback_embedding(t) for t in texts]
        
        try:
            # Process in batches of 5 (Vertex AI limit)
            results = []
            for i in range(0, len(texts), 5):
                batch = texts[i:i+5]
                batch = [t[:12000] if t else "" for t in batch]
                
                loop = asyncio.get_event_loop()
                embeddings = await loop.run_in_executor(
                    None,
                    lambda: client.get_embeddings(batch)
                )
                
                results.extend([e.values for e in embeddings])
            
            return results
            
        except Exception as e:
            logger.error(f"Batch embedding failed: {e}")
            return [await self._fallback_embedding(t) for t in texts]
    
    async def _fallback_embedding(self, text: str) -> List[float]:
        """Deterministic fallback when Vertex AI unavailable."""
        import hashlib
        import random
        import math
        
        hash_obj = hashlib.md5(text.encode())
        hash_int = int(hash_obj.hexdigest(), 16)
        
        random.seed(hash_int)
        embedding = [random.uniform(-1, 1) for _ in range(self.dimension)]
        
        # Normalize
        magnitude = math.sqrt(sum(x**2 for x in embedding))
        if magnitude > 0:
            embedding = [x / magnitude for x in embedding]
        
        return embedding


# Singleton instance
_vertex_service = None

def get_vertex_embedding_service() -> VertexAIEmbeddingService:
    """Get or create Vertex AI embedding service."""
    global _vertex_service
    if _vertex_service is None:
        _vertex_service = VertexAIEmbeddingService()
    return _vertex_service
