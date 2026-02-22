"""API endpoints for data sources."""
from typing import List, Dict

from fastapi import APIRouter

from crawlers.sources import SOURCE_METADATA, get_available_sources

router = APIRouter()


@router.get("/list", response_model=List[Dict])
async def list_sources():
    """
    List all available data sources.
    
    Returns information about all configured crawlers and their metadata.
    """
    sources = []
    for source_id, metadata in SOURCE_METADATA.items():
        sources.append({
            "id": source_id,
            **metadata
        })
    return sources


@router.get("/types", response_model=Dict[str, List[str]])
async def get_source_types():
    """
    Get sources grouped by type.
    
    Returns academic, library, government, and other source categories.
    """
    types = {
        "academic": [],
        "library": [],
        "government": [],
        "dissertation": [],
        "other": []
    }
    
    for source_id, metadata in SOURCE_METADATA.items():
        source_type = metadata.get("type", "other")
        if source_type in types:
            types[source_type].append(source_id)
        else:
            types["other"].append(source_id)
    
    return types


@router.get("/{source_id}", response_model=Dict)
async def get_source_info(source_id: str):
    """
    Get detailed information about a specific source.
    
    Args:
        source_id: Source identifier (e.g., elibrary, cyberleninka)
    """
    from crawlers.sources import get_source_info
    
    info = get_source_info(source_id)
    if not info:
        return {"error": f"Source {source_id} not found"}
    
    return {
        "id": source_id,
        **info
    }
