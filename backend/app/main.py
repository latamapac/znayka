"""Main FastAPI application."""
import os
import sys
from pathlib import Path

# Add paths for imports
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

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
    allow_methods=["*"],
    allow_headers=["*"],
)

# === SOURCES ROUTER ===
@app.get("/api/v1/sources/list")
async def list_sources():
    """List all available data sources."""
    return [
        {"id": "cyberleninka", "name": "CyberLeninka", "type": "academic"},
        {"id": "arxiv", "name": "arXiv", "type": "academic"},
        {"id": "elibrary", "name": "eLibrary", "type": "academic"},
        {"id": "rsl_dissertations", "name": "RSL Dissertations", "type": "dissertation"},
        {"id": "rusneb", "name": "RUSNEB", "type": "library"},
    ]

@app.get("/api/v1/sources/types")
async def source_types():
    """Get source types."""
    return {
        "academic": ["cyberleninka", "arxiv", "elibrary"],
        "library": ["rusneb"],
        "dissertation": ["rsl_dissertations"]
    }

# === PAPERS ROUTER ===
@app.get("/api/v1/papers/search")
async def search_papers(q: str = "", limit: int = 10):
    """Search papers."""
    return {"query": q, "limit": limit, "results": []}

@app.get("/api/v1/papers/{paper_id}")
async def get_paper(paper_id: str):
    """Get paper by ID."""
    return {"id": paper_id, "title": "Sample Paper"}

# === ANALYTICS ROUTER ===
@app.get("/api/v1/analytics/stats")
async def get_stats():
    """Get database stats."""
    return {"total_papers": 0, "sources": 5}

# === HEALTH ===
@app.get("/")
async def root():
    return {"name": "ZNAYKA", "version": "0.1.0", "status": "operational"}

@app.get("/health")
async def health():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
