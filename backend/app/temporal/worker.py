"""Temporal worker for Russian Science Hub - CRAWLER ONLY."""
import asyncio
import logging
import os
from contextlib import asynccontextmanager
from typing import List

from temporalio.client import Client
from temporalio.worker import Worker

from app.temporal.workflows import (
    CrawlSourceWorkflow,
    BulkCrawlWorkflow,
    ScheduledMaintenanceWorkflow,
    ContinuousCrawlWorkflow
)
from app.temporal.activities import (
    crawl_source_activity,
    update_embeddings_activity,
    generate_stats_activity,
    clean_duplicates_activity
)

logger = logging.getLogger(__name__)

TEMPORAL_HOST = os.getenv("TEMPORAL_HOST", "localhost:7233")
TEMPORAL_NAMESPACE = os.getenv("TEMPORAL_NAMESPACE", "default")
TASK_QUEUE = "science-hub-tasks"


async def create_temporal_client() -> Client:
    """Create Temporal client."""
    client = await Client.connect(TEMPORAL_HOST, namespace=TEMPORAL_NAMESPACE)
    return client


async def run_worker():
    """Run the Temporal worker."""
    logger.info(f"Connecting to Temporal at {TEMPORAL_HOST}")
    
    client = await create_temporal_client()
    
    worker = Worker(
        client,
        task_queue=TASK_QUEUE,
        workflows=[
            CrawlSourceWorkflow,
            BulkCrawlWorkflow,
            ScheduledMaintenanceWorkflow,
            ContinuousCrawlWorkflow
        ],
        activities=[
            crawl_source_activity,
            update_embeddings_activity,
            generate_stats_activity,
            clean_duplicates_activity
        ]
    )
    
    logger.info("Starting Temporal worker with CRAWLER workflows...")
    await worker.run()


class TemporalWorkerManager:
    """Manager for Temporal worker lifecycle."""
    
    def __init__(self):
        self._worker_task = None
        self._client = None
        
    async def start(self):
        """Start the worker in background."""
        if self._worker_task is None:
            self._worker_task = asyncio.create_task(run_worker())
            logger.info("Temporal worker started")
            
    async def stop(self):
        """Stop the worker."""
        if self._worker_task:
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass
            self._worker_task = None
            logger.info("Temporal worker stopped")
            
    async def get_client(self) -> Client:
        """Get Temporal client."""
        if self._client is None:
            self._client = await create_temporal_client()
        return self._client


worker_manager = TemporalWorkerManager()


@asynccontextmanager
async def managed_worker():
    """Context manager for worker lifecycle."""
    await worker_manager.start()
    try:
        yield worker_manager
    finally:
        await worker_manager.stop()


# ============ Workflow Submission ============

async def submit_crawl_workflow(source: str, query: str, limit: int = 100) -> str:
    """Submit a crawl workflow."""
    client = await create_temporal_client()
    handle = await client.start_workflow(
        CrawlSourceWorkflow.run,
        source, query, limit,
        id=f"crawl-{source}-{asyncio.get_event_loop().time()}",
        task_queue=TASK_QUEUE
    )
    return handle.id


async def submit_bulk_crawl_workflow(query: str, sources: list, limit_per_source: int = 50) -> str:
    """Submit bulk crawl workflow."""
    client = await create_temporal_client()
    handle = await client.start_workflow(
        BulkCrawlWorkflow.run,
        query, sources, limit_per_source,
        id=f"bulk-crawl-{asyncio.get_event_loop().time()}",
        task_queue=TASK_QUEUE
    )
    return handle.id


async def submit_maintenance_workflow() -> str:
    """Submit maintenance workflow."""
    client = await create_temporal_client()
    handle = await client.start_workflow(
        ScheduledMaintenanceWorkflow.run,
        id=f"maintenance-{asyncio.get_event_loop().time()}",
        task_queue=TASK_QUEUE
    )
    return handle.id


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run_worker())
