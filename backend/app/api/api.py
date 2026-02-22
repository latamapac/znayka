"""Main API router."""
from fastapi import APIRouter

from app.api.endpoints import papers_router
from app.api.endpoints.sources import router as sources_router
from app.api.endpoints.analytics import router as analytics_router

api_router = APIRouter()

# Include paper routes
api_router.include_router(
    papers_router,
    prefix="/papers",
    tags=["papers"]
)

# Include sources routes
api_router.include_router(
    sources_router,
    prefix="/sources",
    tags=["sources"]
)

# Include analytics routes
api_router.include_router(
    analytics_router,
    prefix="/analytics",
    tags=["analytics"]
)
