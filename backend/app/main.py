"""Main FastAPI application with Temporal crawler tracking."""
import os
import sys
import asyncio
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from enum import Enum

# Add paths for imports
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# ==============================================================================
# CRAWL TRACKING SYSTEM (Temporal-like without full server)
# ==============================================================================

class CrawlStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"

@dataclass
class CrawlJob:
    job_id: str
    source: str
    query: str
    status: CrawlStatus
    created_at: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    papers_found: int = 0
    error_message: Optional[str] = None
    progress: Dict[str, Any] = field(default_factory=dict)


class CrawlTracker:
    """In-memory crawl job tracker (replaces Temporal for Cloud Run)"""
    
    def __init__(self):
        self.jobs: Dict[str, CrawlJob] = {}
        self.source_stats: Dict[str, Dict] = {}
        self._lock = asyncio.Lock()
    
    def create_job(self, source: str, query: str) -> CrawlJob:
        job_id = f"{source}_{query.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        job = CrawlJob(
            job_id=job_id,
            source=source,
            query=query,
            status=CrawlStatus.PENDING,
            created_at=datetime.now().isoformat()
        )
        self.jobs[job_id] = job
        return job
    
    async def start_job(self, job_id: str):
        async with self._lock:
            if job_id in self.jobs:
                self.jobs[job_id].status = CrawlStatus.RUNNING
                self.jobs[job_id].started_at = datetime.now().isoformat()
    
    async def complete_job(self, job_id: str, papers_found: int):
        async with self._lock:
            if job_id in self.jobs:
                self.jobs[job_id].status = CrawlStatus.COMPLETED
                self.jobs[job_id].completed_at = datetime.now().isoformat()
                self.jobs[job_id].papers_found = papers_found
                
                # Update source stats
                source = self.jobs[job_id].source
                if source not in self.source_stats:
                    self.source_stats[source] = {"total_papers": 0, "crawls": 0}
                self.source_stats[source]["total_papers"] += papers_found
                self.source_stats[source]["crawls"] += 1
    
    async def fail_job(self, job_id: str, error: str):
        async with self._lock:
            if job_id in self.jobs:
                self.jobs[job_id].status = CrawlStatus.FAILED
                self.jobs[job_id].completed_at = datetime.now().isoformat()
                self.jobs[job_id].error_message = error
    
    def get_summary(self) -> Dict:
        status_counts = {"pending": 0, "running": 0, "completed": 0, "failed": 0}
        total_papers = 0
        
        for job in self.jobs.values():
            status_counts[job.status.value] += 1
            total_papers += job.papers_found
        
        return {
            "total_jobs": len(self.jobs),
            "status_counts": status_counts,
            "total_papers_found": total_papers,
            "sources": self.source_stats,
            "is_complete": status_counts["running"] == 0 and status_counts["pending"] == 0
        }
    
    def get_active_jobs(self) -> List[CrawlJob]:
        return [j for j in self.jobs.values() if j.status == CrawlStatus.RUNNING]
    
    def get_completed_jobs(self) -> List[CrawlJob]:
        return [j for j in self.jobs.values() if j.status == CrawlStatus.COMPLETED]


# Global tracker instance
tracker = CrawlTracker()


# ==============================================================================
# FASTAPI APP
# ==============================================================================

app = FastAPI(
    title="ZNAYKA",
    version="0.1.0",
    description="ZNAYKA - Academic Paper Database with Temporal Crawler Tracking",
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


# ==============================================================================
# PYDANTIC MODELS
# ==============================================================================

class CrawlRequest(BaseModel):
    source: str
    query: str
    limit: int = 50

class BulkCrawlRequest(BaseModel):
    sources: List[str]
    query: str
    limit: int = 30


# ==============================================================================
# SOURCE DEFINITIONS (ALL 9 CRAWLERS)
# ==============================================================================

ALL_SOURCES = [
    {"id": "cyberleninka", "name": "CyberLeninka", "type": "academic", "region": "RU"},
    {"id": "arxiv", "name": "arXiv", "type": "academic", "region": "US"},
    {"id": "elibrary", "name": "eLibrary.ru", "type": "academic", "region": "RU"},
    {"id": "rsl_dissertations", "name": "Russian State Library", "type": "dissertation", "region": "RU"},
    {"id": "rusneb", "name": "RUSNEB", "type": "library", "region": "RU"},
    {"id": "inion", "name": "INION RAN", "type": "academic", "region": "RU"},
    {"id": "hse_scientometrics", "name": "HSE Scientometrics", "type": "academic", "region": "RU"},
    {"id": "presidential_library", "name": "Presidential Library", "type": "library", "region": "RU"},
    {"id": "rosstat_emiss", "name": "Rosstat EMISS", "type": "statistics", "region": "RU"},
]


# ==============================================================================
# CRAWLER SIMULATION (Replace with actual crawlers)
# ==============================================================================

async def simulate_crawl(source: str, query: str, limit: int) -> int:
    """Simulate a crawler run. In production, this calls actual crawlers."""
    await asyncio.sleep(2)  # Simulate crawl time
    
    # Simulate variable results per source
    source_yield = {
        "arxiv": 45,
        "cyberleninka": 30,
        "elibrary": 25,
        "rsl_dissertations": 15,
        "rusneb": 20,
        "inion": 10,
        "hse_scientometrics": 12,
        "presidential_library": 8,
        "rosstat_emiss": 5,
    }
    
    return min(source_yield.get(source, 10), limit)


async def run_crawl_job(job_id: str, source: str, query: str, limit: int):
    """Background task to run a crawler"""
    try:
        await tracker.start_job(job_id)
        papers_found = await simulate_crawl(source, query, limit)
        await tracker.complete_job(job_id, papers_found)
    except Exception as e:
        await tracker.fail_job(job_id, str(e))


# ==============================================================================
# ROUTES
# ==============================================================================

@app.get("/")
async def root():
    return {
        "name": "ZNAYKA",
        "version": "0.1.0",
        "status": "operational",
        "crawler_tracking": "enabled",
        "sources_count": len(ALL_SOURCES),
        "temporal_enabled": False  # Using in-memory tracker instead
    }


@app.get("/health")
async def health():
    return {"status": "healthy", "tracker_jobs": len(tracker.jobs)}


# === SOURCES ROUTER ===

@app.get("/api/v1/sources/list")
async def list_sources():
    """List all 9 available data sources."""
    return {"sources": ALL_SOURCES, "total": len(ALL_SOURCES)}


@app.get("/api/v1/sources/types")
async def source_types():
    """Get source types."""
    by_type = {}
    for s in ALL_SOURCES:
        by_type.setdefault(s["type"], []).append(s["id"])
    return by_type


@app.get("/api/v1/sources/{source_id}")
async def get_source(source_id: str):
    """Get source details."""
    for s in ALL_SOURCES:
        if s["id"] == source_id:
            return s
    raise HTTPException(status_code=404, detail="Source not found")


# === PAPERS ROUTER ===

@app.get("/api/v1/papers/search")
async def search_papers(q: str = "", limit: int = 10):
    """Search papers."""
    return {
        "query": q,
        "limit": limit,
        "results": [],
        "total_found": 0,
        "tracker_papers": tracker.get_summary()["total_papers_found"]
    }


@app.get("/api/v1/papers/{paper_id}")
async def get_paper(paper_id: str):
    """Get paper by ID."""
    return {"id": paper_id, "title": "Sample Paper"}


# === ANALYTICS ROUTER ===

@app.get("/api/v1/analytics/stats")
async def get_stats():
    """Get database and crawler stats."""
    summary = tracker.get_summary()
    return {
        "total_papers": summary["total_papers_found"],
        "sources": len(ALL_SOURCES),
        "active_crawls": summary["status_counts"]["running"],
        "completed_crawls": summary["status_counts"]["completed"],
        "failed_crawls": summary["status_counts"]["failed"],
        "crawl_complete": summary["is_complete"]
    }


# === CRAWLER / TEMPORAL ROUTER ===

@app.post("/api/v1/worker/crawl")
async def start_crawl(request: CrawlRequest, background_tasks: BackgroundTasks):
    """Start a single crawler job."""
    # Validate source
    valid_ids = [s["id"] for s in ALL_SOURCES]
    if request.source not in valid_ids:
        raise HTTPException(status_code=400, detail=f"Invalid source. Valid: {valid_ids}")
    
    job = tracker.create_job(request.source, request.query)
    background_tasks.add_task(run_crawl_job, job.job_id, request.source, request.query, request.limit)
    
    return {
        "status": "started",
        "job_id": job.job_id,
        "source": request.source,
        "query": request.query,
        "message": "Crawl job queued"
    }


@app.post("/api/v1/worker/bulk-crawl")
async def bulk_crawl(request: BulkCrawlRequest, background_tasks: BackgroundTasks):
    """Start multiple crawlers at once."""
    valid_ids = [s["id"] for s in ALL_SOURCES]
    invalid = [s for s in request.sources if s not in valid_ids]
    if invalid:
        raise HTTPException(status_code=400, detail=f"Invalid sources: {invalid}")
    
    jobs = []
    for source in request.sources:
        job = tracker.create_job(source, request.query)
        background_tasks.add_task(run_crawl_job, job.job_id, source, request.query, request.limit)
        jobs.append({"job_id": job.job_id, "source": source})
    
    return {
        "status": "started",
        "jobs_count": len(jobs),
        "jobs": jobs,
        "query": request.query
    }


@app.post("/api/v1/worker/crawl-all")
async def crawl_all(query: str = "machine learning", limit: int = 30, background_tasks: BackgroundTasks = None):
    """Start ALL 9 crawlers simultaneously."""
    jobs = []
    for source in ALL_SOURCES:
        job = tracker.create_job(source["id"], query)
        background_tasks.add_task(run_crawl_job, job.job_id, source["id"], query, limit)
        jobs.append({"job_id": job.job_id, "source": source["id"], "name": source["name"]})
    
    return {
        "status": "started",
        "message": f"All {len(ALL_SOURCES)} crawlers started",
        "query": query,
        "jobs": jobs
    }


@app.get("/api/v1/worker/status")
async def get_crawl_status():
    """Get status of all crawler jobs."""
    summary = tracker.get_summary()
    active = [{"job_id": j.job_id, "source": j.source, "query": j.query} for j in tracker.get_active_jobs()]
    completed = [{"job_id": j.job_id, "source": j.source, "papers": j.papers_found} for j in tracker.get_completed_jobs()]
    
    return {
        "summary": summary,
        "active_jobs": active,
        "recently_completed": completed[-10:],  # Last 10
        "is_complete": summary["is_complete"]
    }


@app.get("/api/v1/worker/status/{job_id}")
async def get_job_status(job_id: str):
    """Get status of a specific job."""
    if job_id not in tracker.jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job = tracker.jobs[job_id]
    return asdict(job)


@app.post("/api/v1/worker/maintenance")
async def maintenance(background_tasks: BackgroundTasks):
    """Run maintenance tasks."""
    return {"status": "maintenance_started"}


# === TEMPORAL-STYLE WORKFLOWS ===

@app.get("/api/v1/workflows/crawl-status")
async def workflow_crawl_status():
    """Temporal-style query for crawl completion status."""
    summary = tracker.get_summary()
    
    return {
        "workflow_type": "BulkCrawlWorkflow",
        "run_id": "in-memory",
        "status": "COMPLETED" if summary["is_complete"] else "RUNNING",
        "progress": {
            "total_sources": 9,
            "completed": summary["status_counts"]["completed"],
            "running": summary["status_counts"]["running"],
            "failed": summary["status_counts"]["failed"],
            "pending": summary["status_counts"]["pending"]
        },
        "results": {
            "total_papers": summary["total_papers_found"],
            "by_source": summary["sources"]
        }
    }


# ==============================================================================
if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
