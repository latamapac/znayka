"""Service for generating and managing text embeddings."""
import logging
from typing import List, Optional

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Try to import optional dependencies
try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False
    np = None

try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False
    logger.info("sentence-transformers not available, using fallback embeddings")

try:
    from openai import AsyncOpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False


class EmbeddingService:
    """Service for generating text embeddings."""
    
    def __init__(self):
        self.model = None
        self.openai_client = None
        self.use_openai = bool(settings.OPENAI_API_KEY) and OPENAI_AVAILABLE
        
        if self.use_openai:
            self.openai_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
            self.embedding_model = "text-embedding-3-small"
        elif SENTENCE_TRANSFORMERS_AVAILABLE:
            # Use local sentence-transformers model
            self._load_local_model()
    
    def _load_local_model(self):
        """Load the local embedding model."""
        if self.model is None and SENTENCE_TRANSFORMERS_AVAILABLE:
            logger.info(f"Loading embedding model: {settings.EMBEDDING_MODEL}")
            try:
                self.model = SentenceTransformer(settings.EMBEDDING_MODEL)
            except Exception as e:
                logger.error(f"Failed to load embedding model: {e}")
                self.model = None
    
    async def get_embedding(self, text: str) -> List[float]:
        """
        Generate embedding for text.
        
        Args:
            text: Input text
            
        Returns:
            Embedding vector as list of floats
        """
        if not text or not text.strip():
            # Return zero vector for empty text
            return [0.0] * settings.EMBEDDING_DIMENSION
        
        if self.use_openai and OPENAI_AVAILABLE:
            return await self._get_openai_embedding(text)
        elif SENTENCE_TRANSFORMERS_AVAILABLE and self.model is not None:
            return self._get_local_embedding(text)
        else:
            # Fallback: simple hash-based embedding
            return self._get_fallback_embedding(text)
    
    async def _get_openai_embedding(self, text: str) -> List[float]:
        """Get embedding using OpenAI API."""
        try:
            response = await self.openai_client.embeddings.create(
                model=self.embedding_model,
                input=text[:8000]  # OpenAI token limit
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"OpenAI embedding error: {e}")
            # Fallback to local model or hash
            if SENTENCE_TRANSFORMERS_AVAILABLE and self.model:
                return self._get_local_embedding(text)
            return self._get_fallback_embedding(text)
    
    def _get_local_embedding(self, text: str) -> List[float]:
        """Get embedding using local model."""
        if self.model is None:
            return self._get_fallback_embedding(text)
        try:
            embedding = self.model.encode(text, convert_to_numpy=True)
            return embedding.tolist()
        except Exception as e:
            logger.error(f"Local embedding error: {e}")
            return self._get_fallback_embedding(text)
    
    def _get_fallback_embedding(self, text: str) -> List[float]:
        """
        Generate a simple deterministic embedding using hashing.
        This is not as good as real embeddings but works without ML libraries.
        """
        import hashlib
        
        # Create a deterministic embedding based on text hash
        hash_obj = hashlib.md5(text.encode())
        hash_bytes = hash_obj.digest()
        
        # Create embedding vector from hash bytes
        embedding = []
        for i in range(settings.EMBEDDING_DIMENSION):
            # Use byte values to create float between -1 and 1
            val = (hash_bytes[i % len(hash_bytes)] / 128.0) - 1.0
            embedding.append(val)
        
        return embedding
    
    async def get_embeddings_batch(
        self,
        texts: List[str],
        batch_size: int = 32
    ) -> List[List[float]]:
        """
        Generate embeddings for multiple texts.
        
        Args:
            texts: List of input texts
            batch_size: Batch size for processing
            
        Returns:
            List of embedding vectors
        """
        embeddings = []
        for text in texts:
            embedding = await self.get_embedding(text)
            embeddings.append(embedding)
        return embeddings
    
    def calculate_similarity(
        self,
        embedding1: List[float],
        embedding2: List[float]
    ) -> float:
        """
        Calculate cosine similarity between two embeddings.
        
        Args:
            embedding1: First embedding vector
            embedding2: Second embedding vector
            
        Returns:
            Cosine similarity score (0-1)
        """
        if NUMPY_AVAILABLE:
            vec1 = np.array(embedding1)
            vec2 = np.array(embedding2)
            
            dot_product = np.dot(vec1, vec2)
            norm1 = np.linalg.norm(vec1)
            norm2 = np.linalg.norm(vec2)
            
            if norm1 == 0 or norm2 == 0:
                return 0.0
            
            return float(dot_product / (norm1 * norm2))
        else:
            # Fallback cosine similarity without numpy
            dot_product = sum(a * b for a, b in zip(embedding1, embedding2))
            norm1 = sum(a * a for a in embedding1) ** 0.5
            norm2 = sum(a * a for a in embedding2) ** 0.5
            
            if norm1 == 0 or norm2 == 0:
                return 0.0
            
            return dot_product / (norm1 * norm2)
