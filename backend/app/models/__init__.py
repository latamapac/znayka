"""Database models."""
import os

# Check if using SQLite (for local development without PostgreSQL)
USE_SQLITE = os.getenv("USE_SQLITE", "false").lower() == "true"

# Also check if pgvector is available
try:
    from pgvector.sqlalchemy import Vector
    PGVECTOR_AVAILABLE = True
except ImportError:
    PGVECTOR_AVAILABLE = False
    USE_SQLITE = True  # Fallback to SQLite models

if USE_SQLITE or not PGVECTOR_AVAILABLE:
    # Use SQLite-compatible models (without pgvector)
    from app.models.paper_sqlite import Paper, Author, Citation
else:
    # Use PostgreSQL+pgvector models
    from app.models.paper import Paper, Author, Citation

__all__ = ["Paper", "Author", "Citation"]
