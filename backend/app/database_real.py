"""
ZNAYKA Real Database Connection
Supports both mock mode (current) and real PostgreSQL mode
"""
import os
import sys
from pathlib import Path
from typing import Optional, AsyncGenerator
import json

# Try to import SQLAlchemy, fallback to mock if not available
try:
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
    from sqlalchemy.orm import declarative_base
    from sqlalchemy import select, insert, update, delete
    SQLALCHEMY_AVAILABLE = True
except ImportError:
    SQLALCHEMY_AVAILABLE = False
    print("Warning: SQLAlchemy not available, using mock mode")

# Check if we should use real database
USE_REAL_DB = os.getenv("USE_REAL_DATABASE", "false").lower() == "true"

if SQLALCHEMY_AVAILABLE and USE_REAL_DB:
    # Real PostgreSQL connection
    DATABASE_URL = os.getenv(
        "DATABASE_URL",
        "postgresql+asyncpg://znayka_user:znayka_pass@localhost/znayka_db"
    )
    
    engine = create_async_engine(DATABASE_URL, echo=False)
    async_session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    Base = declarative_base()
    
    async def get_db() -> AsyncGenerator[AsyncSession, None]:
        async with async_session_maker() as session:
            yield session
    
    async def init_db():
        """Initialize database tables"""
        from app.models import Base
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        print("✅ Database initialized")
    
else:
    # Mock mode - no real database
    engine = None
    async_session_maker = None
    Base = None
    
    async def get_db():
        """Yield None in mock mode"""
        yield None
    
    async def init_db():
        """No-op in mock mode"""
        print("ℹ️  Running in MOCK mode (no database)")


# In-memory storage for mock mode (faster than JSON file)
_mock_papers = []
_mock_initialized = False

def load_mock_data():
    """Load mock papers into memory"""
    global _mock_papers, _mock_initialized
    
    if _mock_initialized:
        return _mock_papers
    
    # Try to load from file
    mock_file = Path(__file__).parent / "mock_papers_large.json"
    if mock_file.exists():
        with open(mock_file) as f:
            _mock_papers = json.load(f)
        print(f"📚 Loaded {len(_mock_papers):,} mock papers")
    else:
        # Minimal fallback
        _mock_papers = [
            {
                "id": "RSH-ARX-2024-00000001",
                "title": "Deep Learning Approaches for Natural Language Processing",
                "source_type": "arxiv",
                "publication_year": 2024
            }
        ]
    
    _mock_initialized = True
    return _mock_papers


def get_mock_papers():
    """Get mock papers (lazy loading)"""
    if not _mock_initialized:
        load_mock_data()
    return _mock_papers


def add_mock_paper(paper: dict):
    """Add a paper to mock data (for testing)"""
    global _mock_papers
    if not _mock_initialized:
        load_mock_data()
    _mock_papers.insert(0, paper)
    return paper


# Export for use in main.py
__all__ = [
    "USE_REAL_DB",
    "get_db", 
    "init_db",
    "get_mock_papers",
    "add_mock_paper"
]
