"""Database base configuration."""
import os

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from app.core.config import get_settings

settings = get_settings()

# Check if using SQLite
USE_SQLITE = os.getenv("USE_SQLITE", "false").lower() == "true" or "sqlite" in settings.DATABASE_URL

# Create async engine with appropriate settings
if USE_SQLITE:
    # SQLite specific settings
    engine = create_async_engine(
        settings.DATABASE_URL,
        echo=False,
        future=True,
        # SQLite doesn't support pool_size
    )
else:
    # PostgreSQL settings
    engine = create_async_engine(
        settings.DATABASE_URL,
        echo=False,
        future=True,
        pool_size=20,
        max_overflow=0,
    )

# Create async session factory
AsyncSessionLocal = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

# Declarative base for models
Base = declarative_base()


async def get_db() -> AsyncSession:
    """Dependency for getting async database sessions."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db():
    """Initialize database (create tables)."""
    # Import models to register them with Base.metadata
    from app.models import Paper, Author, Citation
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
