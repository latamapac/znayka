"""Temporal activities for crawling papers."""
import asyncio
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any

from temporalio import activity

# Add crawlers to path
crawlers_path = str(Path(__file__).parent.parent.parent.parent)
if crawlers_path not in sys.path:
    sys.path.insert(0, crawlers_path)

try:
    from crawlers.orchestrator import CrawlerOrchestrator
    CRAWLERS_AVAILABLE = True
except ImportError:
    CRAWLERS_AVAILABLE = False
    logging.warning("Crawlers module not available")

from app.db.base import AsyncSessionLocal

try:
    from app.services.indexing_service import IndexingService
    from app.services.embedding_service import EmbeddingService
    SERVICES_AVAILABLE = True
except ImportError:
    SERVICES_AVAILABLE = False

logger = logging.getLogger(__name__)


@activity.defn
async def crawl_source_activity(
    source: str,
    query: str,
    limit: int = 100,
    year_from: int = None,
    year_to: int = None
) -> Dict[str, Any]:
    """
    Activity to crawl a specific source.
    
    Args:
        source: Source name (cyberleninka, arxiv, etc.)
        query: Search query
        limit: Maximum papers to fetch
        year_from: Filter year from
        year_to: Filter year to
        
    Returns:
        Dict with crawl results
    """
    logger.info(f"Starting crawl for {source}: {query}")
    
    if not CRAWLERS_AVAILABLE:
        return {
            "source": source,
            "query": query,
            "count": 0,
            "status": "failed",
            "error": "Crawlers module not available",
            "timestamp": datetime.utcnow().isoformat()
        }
    
    try:
        orchestrator = CrawlerOrchestrator()
        papers = await orchestrator.crawl_source(
            source=source,
            query=query,
            limit=limit,
            year_from=year_from,
            year_to=year_to,
            store=True
        )
        
        result = {
            "source": source,
            "query": query,
            "count": len(papers),
            "status": "success",
            "timestamp": datetime.utcnow().isoformat()
        }
        
        logger.info(f"Crawled {len(papers)} papers from {source}")
        return result
        
    except Exception as e:
        logger.error(f"Crawl failed for {source}: {e}")
        return {
            "source": source,
            "query": query,
            "count": 0,
            "status": "failed",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }


@activity.defn
async def update_embeddings_activity(batch_size: int = 100) -> Dict[str, Any]:
    """
    Activity to update embeddings for papers without them.
    
    Args:
        batch_size: Number of papers to process
        
    Returns:
        Dict with update results
    """
    logger.info(f"Updating embeddings for {batch_size} papers")
    
    if not CRAWLERS_AVAILABLE:
        return {
            "updated": 0,
            "status": "failed",
            "error": "Crawlers module not available",
            "timestamp": datetime.utcnow().isoformat()
        }
    
    try:
        orchestrator = CrawlerOrchestrator()
        count = await orchestrator.update_embeddings(batch_size)
        
        return {
            "updated": count,
            "status": "success",
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Embedding update failed: {e}")
        return {
            "updated": 0,
            "status": "failed",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }


@activity.defn
async def generate_stats_activity() -> Dict[str, Any]:
    """Activity to generate database statistics."""
    logger.info("Generating database statistics")
    
    if not SERVICES_AVAILABLE:
        return {
            "stats": {},
            "status": "failed",
            "error": "Services not available",
            "timestamp": datetime.utcnow().isoformat()
        }
    
    try:
        async with AsyncSessionLocal() as db:
            indexing = IndexingService(db)
            stats = await indexing.get_index_stats()
            
            return {
                "stats": stats,
                "status": "success",
                "timestamp": datetime.utcnow().isoformat()
            }
            
    except Exception as e:
        logger.error(f"Stats generation failed: {e}")
        return {
            "stats": {},
            "status": "failed",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }


@activity.defn
async def clean_duplicates_activity() -> Dict[str, Any]:
    """Activity to clean duplicate papers."""
    logger.info("Cleaning duplicate papers")
    
    try:
        async with AsyncSessionLocal() as db:
            from sqlalchemy import select, func
            from app.models.paper import Paper
            
            # Find duplicates by title
            result = await db.execute(
                select(Paper.title, func.count()).group_by(Paper.title).having(func.count() > 1)
            )
            duplicates = result.all()
            
            # Remove duplicates (keep first)
            removed = 0
            for title, count in duplicates:
                result = await db.execute(
                    select(Paper).where(Paper.title == title).offset(1)
                )
                papers_to_remove = result.scalars().all()
                for paper in papers_to_remove:
                    await db.delete(paper)
                    removed += 1
            
            await db.commit()
            
            return {
                "duplicates_found": len(duplicates),
                "removed": removed,
                "status": "success",
                "timestamp": datetime.utcnow().isoformat()
            }
            
    except Exception as e:
        logger.error(f"Duplicate cleanup failed: {e}")
        return {
            "duplicates_found": 0,
            "removed": 0,
            "status": "failed",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }
