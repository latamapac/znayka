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

# Include analytics routes (Planck Big Data)
api_router.include_router(
    analytics_router,
    prefix="/analytics",
    tags=["analytics"]
)

# Include worker routes (Temporal) - only if temporalio is installed
try:
    from app.api.endpoints.worker import router as worker_router
    api_router.include_router(
        worker_router,
        prefix="/worker",
        tags=["worker"]
    )
except ImportError:
    pass

# Include translation routes (626 integration) - only if available
try:
    from app.api.endpoints.translation import router as translation_router
    api_router.include_router(
        translation_router,
        prefix="/translation",
        tags=["translation"]
    )
except ImportError:
    pass
