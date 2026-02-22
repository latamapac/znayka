"""Main FastAPI application - Cloud Run optimized."""
import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

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
print("Loading API routers...")

try:
    from app.api.endpoints.sources import router as sources_router
    app.include_router(sources_router, prefix="/api/v1/sources")
    print("✓ Sources router loaded")
except Exception as e:
    print(f"✗ Sources router failed: {e}")

try:
    from app.api.endpoints.papers import router as papers_router
    app.include_router(papers_router, prefix="/api/v1/papers")
    print("✓ Papers router loaded")
except Exception as e:
    print(f"✗ Papers router failed: {e}")

try:
    from app.api.endpoints.analytics import router as analytics_router
    app.include_router(analytics_router, prefix="/api/v1/analytics")
    print("✓ Analytics router loaded")
except Exception as e:
    print(f"✗ Analytics router failed: {e}")

try:
    from app.api.endpoints.pdfs import router as pdfs_router
    app.include_router(pdfs_router, prefix="/api/v1/pdfs")
    print("✓ PDFs router loaded")
except Exception as e:
    print(f"✗ PDFs router failed: {e}")

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
