"""API endpoints."""
from app.api.endpoints.papers import router as papers_router
from app.api.endpoints.sources import router as sources_router

__all__ = ["papers_router", "sources_router"]
