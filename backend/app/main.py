"""Main FastAPI application - Cloud Run optimized."""
import os
import sys
import logging
from pathlib import Path

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add paths
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent.parent.parent))  # For crawlers

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="ZNAYKA",
    version="0.1.0",
    description="ZNAYKA - Academic Paper Database",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Import and register routers
logger.info("Loading API routers...")

# Sources router
try:
    from app.api.endpoints.sources import router as sources_router
    app.include_router(sources_router, prefix="/api/v1/sources")
    logger.info("✓ Sources router loaded at /api/v1/sources")
except Exception as e:
    logger.error(f"✗ Sources router failed: {e}")
    import traceback
    logger.error(traceback.format_exc())

# Papers router
try:
    from app.api.endpoints.papers import router as papers_router
    app.include_router(papers_router, prefix="/api/v1/papers")
    logger.info("✓ Papers router loaded at /api/v1/papers")
except Exception as e:
    logger.error(f"✗ Papers router failed: {e}")

# Analytics router
try:
    from app.api.endpoints.analytics import router as analytics_router
    app.include_router(analytics_router, prefix="/api/v1/analytics")
    logger.info("✓ Analytics router loaded at /api/v1/analytics")
except Exception as e:
    logger.error(f"✗ Analytics router failed: {e}")

# PDFs router (Phase 2)
try:
    from app.api.endpoints.pdfs import router as pdfs_router
    app.include_router(pdfs_router, prefix="/api/v1/pdfs")
    logger.info("✓ PDFs router loaded at /api/v1/pdfs")
except Exception as e:
    logger.error(f"✗ PDFs router failed: {e}")

@app.get("/")
async def root():
    return {
        "name": "ZNAYKA",
        "version": "0.1.0",
        "status": "operational",
        "docs": "/docs"
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8080))
    uvicorn.run("app.main:app", host="0.0.0.0", port=port)
