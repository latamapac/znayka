"""API endpoints."""
from fastapi import APIRouter

# Create main papers router
papers_router = APIRouter()

# Import and include sub-routers
try:
    from app.api.endpoints.papers import router as papers_subrouter
    papers_router.include_router(papers_subrouter)
except Exception as e:
    import logging
    logging.warning(f"Could not load papers router: {e}")

__all__ = ["papers_router"]
