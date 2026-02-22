"""Celery tasks for embedding generation."""
import asyncio

from app.celery_app import celery_app
from crawlers.orchestrator import CrawlerOrchestrator


@celery_app.task(bind=True)
def update_missing_embeddings(self, batch_size: int = 100) -> dict:
    """
    Update embeddings for papers that don't have them.
    
    Args:
        batch_size: Number of papers to process
        
    Returns:
        Dict with count of updated papers
    """
    async def run_update():
        orchestrator = CrawlerOrchestrator()
        count = await orchestrator.update_embeddings(batch_size)
        return {"updated": count}
    
    try:
        return asyncio.run(run_update())
    except Exception as exc:
        raise self.retry(exc=exc, countdown=300)


@celery_app.task(bind=True)
def generate_embedding_for_paper(self, paper_id: str) -> dict:
    """
    Generate embedding for a specific paper.
    
    Args:
        paper_id: Paper ID
        
    Returns:
        Dict with status
    """
    from app.db.base import AsyncSessionLocal
    from app.models import Paper
    from app.services.embedding_service import EmbeddingService
    from sqlalchemy import select
    
    async def run_generate():
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(Paper).where(Paper.id == paper_id)
            )
            paper = result.scalar_one_or_none()
            
            if not paper:
                return {"status": "not_found", "paper_id": paper_id}
            
            embedding_service = EmbeddingService()
            
            try:
                paper.title_embedding = await embedding_service.get_embedding(
                    paper.title or ""
                )
                paper.abstract_embedding = await embedding_service.get_embedding(
                    paper.abstract or ""
                )
                await db.commit()
                return {"status": "success", "paper_id": paper_id}
            except Exception as e:
                return {"status": "error", "paper_id": paper_id, "error": str(e)}
    
    try:
        return asyncio.run(run_generate())
    except Exception as exc:
        raise self.retry(exc=exc, countdown=60)
