"""Celery tasks for crawling papers."""
import asyncio
from typing import List

from app.celery_app import celery_app
from crawlers.orchestrator import CrawlerOrchestrator


@celery_app.task(bind=True, max_retries=3)
def crawl_source_task(
    self,
    source: str,
    query: str,
    limit: int = 100,
    year_from: int = None,
    year_to: int = None
) -> dict:
    """
    Celery task to crawl a specific source.
    
    Args:
        source: Source name
        query: Search query
        limit: Maximum papers
        year_from: Filter year from
        year_to: Filter year to
        
    Returns:
        Dict with results
    """
    async def run_crawl():
        orchestrator = CrawlerOrchestrator()
        papers = await orchestrator.crawl_source(
            source=source,
            query=query,
            limit=limit,
            year_from=year_from,
            year_to=year_to,
            store=True
        )
        return {
            "source": source,
            "query": query,
            "count": len(papers),
            "papers": [{"id": p.source_id, "title": p.title} for p in papers]
        }
    
    try:
        return asyncio.run(run_crawl())
    except Exception as exc:
        # Retry with exponential backoff
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))


@celery_app.task(bind=True)
def crawl_all_sources_task(
    self,
    query: str,
    limit_per_source: int = 50
) -> dict:
    """
    Celery task to crawl all sources.
    
    Args:
        query: Search query
        limit_per_source: Limit per source
        
    Returns:
        Dict with results per source
    """
    async def run_crawl():
        orchestrator = CrawlerOrchestrator()
        results = await orchestrator.crawl_all_sources(
            query=query,
            limit_per_source=limit_per_source,
            store=True
        )
        return results
    
    try:
        return asyncio.run(run_crawl())
    except Exception as exc:
        raise self.retry(exc=exc, countdown=60)
