"""Application configuration."""
from functools import lru_cache
from typing import List, Optional

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Database
    DATABASE_URL: str = "postgresql+asyncpg://user:password@localhost:5432/russia_science_hub"
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # OpenAI
    OPENAI_API_KEY: Optional[str] = None
    
    # Security
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    ALGORITHM: str = "HS256"
    
    # Storage
    PAPERS_STORAGE_PATH: str = "./storage/papers"
    MAX_FILE_SIZE_MB: int = 50
    
    # API
    API_V1_PREFIX: str = "/api/v1"
    PROJECT_NAME: str = "Russian Science Hub"
    PROJECT_VERSION: str = "0.1.0"
    PORT: int = 8000
    
    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:5173", "http://localhost:3000"]
    
    # Crawler
    CRAWLER_DELAY_SECONDS: int = 2
    CRAWLER_MAX_RETRIES: int = 3
    CRAWLER_CONCURRENT_REQUESTS: int = 5
    
    # Embeddings
    EMBEDDING_MODEL: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    EMBEDDING_DIMENSION: int = 384
    
    # Planck Big Data Integration
    PLANCK_URL: Optional[str] = None
    PLANCK_API_KEY: Optional[str] = None
    
    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
