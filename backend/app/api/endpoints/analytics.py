"""API endpoints for Big Data Analytics (Planck integration)."""
from typing import Dict, Any, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import get_db
from app.integrations import get_planck_client
from app.services.indexing_service import IndexingService

router = APIRouter()


@router.get("/trends", response_model=Dict[str, Any])
async def get_research_trends(
    field: Optional[str] = Query(None, description="Research field"),
    year_from: int = Query(2020, description="Start year"),
    year_to: int = Query(2024, description="End year"),
    use_planck: bool = Query(True, description="Use Planck Big Data if available")
):
    """
    Get research trends analysis.
    
    Uses Planck Big Data analytics when available, falls back to local data.
    """
    if use_planck:
        planck = get_planck_client()
        result = await planck.get_research_trends(field, year_from, year_to)
        if not result.get("error"):
            return result
    
    # Fallback to local statistics
    return {
        "source": "local",
        "field": field,
        "year_from": year_from,
        "year_to": year_to,
        "message": "Planck analytics unavailable, using local data"
    }


@router.get("/statistics/comprehensive", response_model=Dict[str, Any])
async def get_comprehensive_statistics(
    use_planck: bool = Query(True),
    db: AsyncSession = Depends(get_db)
):
    """
    Get comprehensive statistics combining local and Planck data.
    """
    # Get local stats
    indexing = IndexingService(db)
    local_stats = await indexing.get_index_stats()
    
    result = {
        "local": local_stats,
        "planck": None,
        "combined": local_stats
    }
    
    if use_planck:
        planck = get_planck_client()
        planck_stats = await planck.get_paper_statistics()
        
        if planck_stats.get("planck_connected", False):
            result["planck"] = planck_stats
            # Merge data if both available
            result["combined"] = {
                **local_stats,
                "planck_enhanced": True,
                "advanced_analytics": planck_stats.get("advanced_metrics", {})
            }
    
    return result


@router.post("/query/bigdata", response_model=Dict[str, Any])
async def run_bigdata_query(
    query_type: str,
    params: Dict[str, Any],
    timeout: int = Query(60, description="Query timeout in seconds")
):
    """
    Run big data analytics query via Planck.
    
    Query types:
    - trends: Publication trends over time
    - citations: Citation network analysis
    - authors: Author collaboration networks
    - topics: Topic modeling and clustering
    """
    planck = get_planck_client()
    
    result = await planck.run_bigdata_query(
        query_type=query_type,
        params=params
    )
    
    return result


@router.get("/citations/network/{paper_id}", response_model=Dict[str, Any])
async def get_citation_network(
    paper_id: str,
    depth: int = Query(2, ge=1, le=3, description="Network depth")
):
    """
    Get citation network for a paper using Planck analytics.
    """
    planck = get_planck_client()
    
    result = await planck.get_citation_network(paper_id, depth)
    
    return result


@router.get("/export", response_model=Dict[str, Any])
async def export_analytics_data(
    format: str = Query("csv", enum=["csv", "json", "parquet"]),
    source: Optional[str] = Query(None),
    year_from: Optional[int] = None,
    year_to: Optional[int] = None
):
    """
    Export paper data for external analysis.
    
    Returns download URL or data directly.
    """
    planck = get_planck_client()
    
    filters = {}
    if source:
        filters["source"] = source
    if year_from:
        filters["year_from"] = year_from
    if year_to:
        filters["year_to"] = year_to
    
    data = await planck.export_data(format=format, filters=filters)
    
    if data:
        # In production, save to file and return URL
        # For now, return metadata
        return {
            "status": "success",
            "format": format,
            "size_bytes": len(data),
            "filters": filters,
            "download_url": "/api/v1/analytics/download/export"  # Placeholder
        }
    
    return {
        "status": "error",
        "message": "Export failed or Planck unavailable"
    }


@router.get("/dashboards/superset")
async def get_superset_dashboards():
    """
    Get list of available Superset dashboards.
    """
    # Placeholder - in production would fetch from Planck
    return {
        "dashboards": [
            {
                "id": "papers-overview",
                "title": "Papers Overview",
                "url": "/analytics/superset/dashboard/papers-overview",
                "charts": ["papers-by-year", "papers-by-source", "citation-trends"]
            },
            {
                "id": "research-trends",
                "title": "Research Trends",
                "url": "/analytics/superset/dashboard/research-trends",
                "charts": ["topic-modeling", "emerging-fields", "author-networks"]
            }
        ]
    }


@router.get("/planck/status")
async def get_planck_status():
    """
    Check Planck Big Data integration status.
    """
    planck = get_planck_client()
    
    try:
        stats = await planck.get_paper_statistics()
        return {
            "connected": stats.get("planck_connected", False),
            "base_url": planck.base_url,
            "features": [
                "bigdata_queries",
                "superset_dashboards",
                "citation_networks",
                "trends_analysis",
                "data_export"
            ]
        }
    except Exception as e:
        return {
            "connected": False,
            "error": str(e),
            "base_url": planck.base_url,
            "features": []
        }
