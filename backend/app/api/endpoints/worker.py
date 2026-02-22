"""API endpoints for Temporal worker management."""
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from app.temporal.worker import (
    submit_crawl_workflow,
    submit_bulk_crawl_workflow,
    submit_maintenance_workflow,
    schedule_continuous_crawl
)

router = APIRouter()


class CrawlRequest(BaseModel):
    query: str
    source: Optional[str] = None
    sources: Optional[List[str]] = None
    limit: int = 50


class CrawlResponse(BaseModel):
    workflow_id: str
    message: str


class MaintenanceResponse(BaseModel):
    workflow_id: str
    message: str


@router.post("/crawl", response_model=CrawlResponse)
async def trigger_crawl(request: CrawlRequest):
    """
    Trigger a crawl workflow.
    
    If source is specified, crawls single source.
    If sources list is specified, runs bulk crawl.
    """
    try:
        if request.source:
            # Single source crawl
            workflow_id = await submit_crawl_workflow(
                source=request.source,
                query=request.query,
                limit=request.limit
            )
            return CrawlResponse(
                workflow_id=workflow_id,
                message=f"Crawl started for {request.source}: {request.query}"
            )
        elif request.sources:
            # Bulk crawl
            workflow_id = await submit_bulk_crawl_workflow(
                query=request.query,
                sources=request.sources,
                limit_per_source=request.limit
            )
            return CrawlResponse(
                workflow_id=workflow_id,
                message=f"Bulk crawl started for {len(request.sources)} sources"
            )
        else:
            raise HTTPException(
                status_code=400,
                detail="Either 'source' or 'sources' must be specified"
            )
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/maintenance", response_model=MaintenanceResponse)
async def trigger_maintenance():
    """Trigger maintenance workflow (clean duplicates, update embeddings, stats)."""
    try:
        workflow_id = await submit_maintenance_workflow()
        return MaintenanceResponse(
            workflow_id=workflow_id,
            message="Maintenance workflow started"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/schedule-continuous")
async def schedule_continuous(
    queries: List[str],
    sources: List[str],
    interval_hours: int = 24
):
    """Schedule continuous crawling workflow."""
    try:
        workflow_id = await schedule_continuous_crawl(
            queries=queries,
            sources=sources,
            interval_hours=interval_hours
        )
        return {
            "workflow_id": workflow_id,
            "message": f"Continuous crawl scheduled (interval: {interval_hours}h)"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Available sources for crawling
AVAILABLE_SOURCES = [
    "cyberleninka",
    "arxiv", 
    "elibrary",
    "rsl_dissertations",
    "rusneb",
    "inion",
    "hse_scientometrics",
    "presidential_library",
    "rosstat"
]


@router.get("/sources")
async def get_worker_sources():
    """Get list of available sources for crawling."""
    return {"sources": AVAILABLE_SOURCES}
