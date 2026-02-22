"""Application configuration."""
import os
from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""
    
    # Project
    PROJECT_NAME: str = "ZNAYKA"
    PROJECT_VERSION: str = "0.1.0"
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
    
    # API
    API_V1_PREFIX: str = "/api/v1"
    PORT: int = int(os.getenv("PORT", "8000"))
    
    # Database
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", 
        "postgresql+asyncpg://znayka:znayka@localhost:5432/znayka"
    )
    
    # CORS
    CORS_ORIGINS: List[str] = ["*"]
    
    # Embeddings (disabled for now - will use simpler method)
    EMBEDDING_DIMENSION: int = 384
    
    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings."""
    return Settings()
