"""Temporal workflows for crawler orchestration."""
from datetime import timedelta
from typing import List, Dict, Any

from temporalio import workflow
from temporalio.common import RetryPolicy

with workflow.unsafe.imports_passed_through():
    from app.temporal.activities import (
        crawl_source_activity,
        update_embeddings_activity,
        generate_stats_activity,
        clean_duplicates_activity
    )


@workflow.defn
class CrawlSourceWorkflow:
    """Workflow to crawl a single source."""
    
    @workflow.run
    async def run(
        self,
        source: str,
        query: str,
        limit: int = 100
    ) -> Dict[str, Any]:
        """
        Execute crawl workflow.
        
        Args:
            source: Source name
            query: Search query
            limit: Maximum papers
            
        Returns:
            Crawl result
        """
        return await workflow.execute_activity(
            crawl_source_activity,
            args=(source, query, limit),
            start_to_close_timeout=timedelta(minutes=30),
            retry_policy=RetryPolicy(
                maximum_attempts=3,
                initial_interval=timedelta(seconds=10)
            )
        )


@workflow.defn
class BulkCrawlWorkflow:
    """Workflow to crawl multiple sources in parallel."""
    
    @workflow.run
    async def run(
        self,
        query: str,
        sources: List[str],
        limit_per_source: int = 50
    ) -> Dict[str, Any]:
        """
        Execute bulk crawl across multiple sources.
        
        Args:
            query: Search query
            sources: List of source names
            limit_per_source: Limit per source
            
        Returns:
            Combined crawl results
        """
        results = []
        
        # Start all crawls in parallel
        tasks = []
        for source in sources:
            task = workflow.execute_activity(
                crawl_source_activity,
                args=(source, query, limit_per_source),
                start_to_close_timeout=timedelta(minutes=30),
                retry_policy=RetryPolicy(
                    maximum_attempts=2,
                    initial_interval=timedelta(seconds=10)
                )
            )
            tasks.append(task)
        
        # Wait for all to complete
        crawl_results = await workflow.gather(*tasks)
        
        total_papers = sum(r.get("count", 0) for r in crawl_results)
        successful = sum(1 for r in crawl_results if r.get("status") == "success")
        
        return {
            "total_papers": total_papers,
            "successful_sources": successful,
            "total_sources": len(sources),
            "results": crawl_results,
            "status": "success" if successful > 0 else "failed"
        }


@workflow.defn
class ScheduledMaintenanceWorkflow:
    """Workflow for scheduled maintenance tasks."""
    
    @workflow.run
    async def run(self) -> Dict[str, Any]:
        """Execute maintenance tasks."""
        results = {}
        
        # Clean duplicates
        results["cleanup"] = await workflow.execute_activity(
            clean_duplicates_activity,
            start_to_close_timeout=timedelta(minutes=10),
            retry_policy=RetryPolicy(maximum_attempts=2)
        )
        
        # Update embeddings
        results["embeddings"] = await workflow.execute_activity(
            update_embeddings_activity,
            args=(100,),
            start_to_close_timeout=timedelta(minutes=20),
            retry_policy=RetryPolicy(maximum_attempts=2)
        )
        
        # Generate stats
        results["stats"] = await workflow.execute_activity(
            generate_stats_activity,
            start_to_close_timeout=timedelta(minutes=5),
            retry_policy=RetryPolicy(maximum_attempts=2)
        )
        
        return results


@workflow.defn
class ContinuousCrawlWorkflow:
    """Workflow for continuous crawling with periodic updates."""
    
    @workflow.run
    async def run(
        self,
        queries: List[str],
        sources: List[str],
        interval_hours: int = 24
    ) -> None:
        """
        Continuously crawl with periodic updates.
        
        Args:
            queries: List of queries to crawl
            sources: List of sources
            interval_hours: Hours between crawls
        """
        while True:
            for query in queries:
                # Run bulk crawl for this query
                result = await workflow.execute_child_workflow(
                    BulkCrawlWorkflow.run,
                    query,
                    sources,
                    20,  # limit per source per run
                    id=f"bulk-crawl-{workflow.now().isoformat()}-{query[:20]}",
                )
                
                workflow.logger.info(f"Crawl result for '{query}': {result}")
            
            # Wait for next interval
            await workflow.sleep(timedelta(hours=interval_hours))
