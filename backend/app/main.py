"""Main FastAPI application."""
import sys
import os
from pathlib import Path

# Add parent directory to path for crawlers module
parent_dir = str(Path(__file__).parent.parent.parent)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.api import api_router
from app.core.config import get_settings

settings = get_settings()

# Check if Temporal is enabled
USE_TEMPORAL = os.getenv("USE_TEMPORAL", "false").lower() == "true"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    print(f"Starting {settings.PROJECT_NAME} v{settings.PROJECT_VERSION}")
    
    # Start Temporal worker if enabled
    worker_manager = None
    if USE_TEMPORAL:
        try:
            from app.temporal.worker import worker_manager
            await worker_manager.start()
            print("Temporal worker started")
        except Exception as e:
            print(f"Failed to start Temporal worker: {e}")
    
    yield
    
    # Shutdown
    if USE_TEMPORAL and worker_manager:
        try:
            await worker_manager.stop()
            print("Temporal worker stopped")
        except Exception as e:
            print(f"Error stopping Temporal worker: {e}")
    
    print(f"Shutting down {settings.PROJECT_NAME}")


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.PROJECT_VERSION,
    description="Russian Science Hub - Academic Paper Database and Search Platform",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API router
app.include_router(api_router, prefix=settings.API_V1_PREFIX)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": settings.PROJECT_NAME,
        "version": settings.PROJECT_VERSION,
        "status": "operational",
        "docs": "/docs",
        "temporal_enabled": USE_TEMPORAL
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=settings.PORT, reload=True)
