"""Main FastAPI application - Cloud Run optimized."""
import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Get settings safely
try:
    from app.core.config import get_settings
    settings = get_settings()
    PROJECT_NAME = settings.PROJECT_NAME
    VERSION = settings.PROJECT_VERSION
except:
    PROJECT_NAME = "ZNAYKA"
    VERSION = "0.1.0"

app = FastAPI(
    title=PROJECT_NAME,
    version=VERSION,
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

# Import routers conditionally (avoid startup failures)
@app.on_event("startup")
async def startup():
    print(f"Starting {PROJECT_NAME} v{VERSION}")

try:
    from app.api.endpoints import papers_router
    from app.api.endpoints.sources import router as sources_router
    from app.api.endpoints.analytics import router as analytics_router
    
    app.include_router(papers_router, prefix="/api/v1/papers")
    app.include_router(sources_router, prefix="/api/v1/sources")
    app.include_router(analytics_router, prefix="/api/v1/analytics")
except Exception as e:
    print(f"Warning: Could not load some routers: {e}")

@app.get("/")
async def root():
    return {
        "name": PROJECT_NAME,
        "version": VERSION,
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
