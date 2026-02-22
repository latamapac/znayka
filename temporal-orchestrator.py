#!/usr/bin/env python3
"""
ZNAYKA Temporal Orchestrator
Tracks all 9 crawlers and reports completion status
"""
import asyncio
import aiohttp
import json
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
from enum import Enum


class CrawlStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class CrawlJob:
    source: str
    query: str
    status: CrawlStatus
    papers_found: int = 0
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    error: Optional[str] = None


class ZnaykaOrchestrator:
    """Orchestrates and monitors all crawlers via ZNAYKA API"""
    
    BASE_URL = "https://znayka-674193695957.europe-north1.run.app"
    
    SOURCES = [
        "arxiv",
        "cyberleninka", 
        "elibrary",
        "hse_scientometrics",
        "inion",
        "presidential_library",
        "rosstat_emiss",
        "rsl_dissertations",
        "rusneb"
    ]
    
    QUERIES = [
        "machine learning",
        "artificial intelligence",
        "data science",
        "neural networks"
    ]
    
    def __init__(self):
        self.jobs: Dict[str, CrawlJob] = {}
        self.session: Optional[aiohttp.ClientSession] = None
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30))
        return self
        
    async def __aexit__(self, *args):
        if self.session:
            await self.session.close()
    
    def _job_id(self, source: str, query: str) -> str:
        return f"{source}_{query.replace(' ', '_')}"
    
    async def get_paper_count(self) -> int:
        """Get total paper count from API"""
        try:
            async with self.session.get(f"{self.BASE_URL}/api/v1/analytics/stats") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data.get("total_papers", 0)
        except Exception as e:
            print(f"⚠️ Error getting stats: {e}")
        return 0
    
    async def start_crawler(self, source: str, query: str, limit: int = 50) -> bool:
        """Start a single crawler via API"""
        job_id = self._job_id(source, query)
        
        try:
            async with self.session.post(
                f"{self.BASE_URL}/api/v1/worker/crawl",
                json={"source": source, "query": query, "limit": limit}
            ) as resp:
                if resp.status in [200, 202]:
                    self.jobs[job_id] = CrawlJob(
                        source=source,
                        query=query,
                        status=CrawlStatus.RUNNING,
                        started_at=datetime.now().isoformat()
                    )
                    print(f"  ✅ Started: {source} / '{query}'")
                    return True
                else:
                    text = await resp.text()
                    self.jobs[job_id] = CrawlJob(
                        source=source,
                        query=query,
                        status=CrawlStatus.FAILED,
                        error=f"HTTP {resp.status}: {text}"
                    )
                    print(f"  ❌ Failed: {source} / '{query}' - {text}")
                    return False
        except Exception as e:
            self.jobs[job_id] = CrawlJob(
                source=source,
                query=query,
                status=CrawlStatus.FAILED,
                error=str(e)
            )
            print(f"  ❌ Error: {source} / '{query}' - {e}")
            return False
    
    async def start_all_crawlers(self, limit: int = 30):
        """Start all 9 crawlers across all queries"""
        print(f"\n🚀 Starting {len(self.SOURCES)} crawlers × {len(self.QUERIES)} queries...")
        print(f"   Total jobs: {len(self.SOURCES) * len(self.QUERIES)}")
        print("")
        
        tasks = []
        for source in self.SOURCES:
            # Limit sources per query to avoid overwhelming
            for query in self.QUERIES[:2]:  # Use 2 queries per source
                await self.start_crawler(source, query, limit)
                await asyncio.sleep(0.5)  # Rate limit
        
        print(f"\n📊 Started {len([j for j in self.jobs.values() if j.status == CrawlStatus.RUNNING])} jobs")
    
    def print_status(self):
        """Print current status of all jobs"""
        status_counts = {"running": 0, "completed": 0, "failed": 0, "pending": 0}
        for job in self.jobs.values():
            status_counts[job.status.value] += 1
        
        print(f"\n📈 Crawler Status:")
        print(f"   Running:   {status_counts['running']} 🟡")
        print(f"   Completed: {status_counts['completed']} ✅")
        print(f"   Failed:    {status_counts['failed']} ❌")
        print(f"   Pending:   {status_counts['pending']} ⏳")
    
    async def monitor_progress(self, check_interval: int = 30, max_checks: int = 60):
        """Monitor crawling progress until complete"""
        print(f"\n🔍 Monitoring progress (checking every {check_interval}s)...")
        print("   Press Ctrl+C to stop\n")
        
        initial_count = await self.get_paper_count()
        print(f"   Initial papers: {initial_count}")
        
        for check_num in range(max_checks):
            await asyncio.sleep(check_interval)
            
            current_count = await self.get_paper_count()
            new_papers = current_count - initial_count
            
            timestamp = datetime.now().strftime("%H:%M:%S")
            print(f"   [{timestamp}] Papers: {current_count} (+{new_papers} new)")
            
            # Check if we've made significant progress
            if new_papers > 500 or check_num >= max_checks - 1:
                print(f"\n🎉 Crawling complete! Total papers: {current_count}")
                break
        
        self.print_status()
    
    async def export_results(self, filename: str = "crawl_results.json"):
        """Export crawl results to JSON"""
        data = {
            "timestamp": datetime.now().isoformat(),
            "total_jobs": len(self.jobs),
            "jobs": {k: asdict(v) for k, v in self.jobs.items()},
            "summary": await self._get_summary()
        }
        
        with open(filename, "w") as f:
            json.dump(data, f, indent=2)
        
        print(f"\n💾 Results exported to {filename}")
    
    async def _get_summary(self) -> Dict:
        """Get summary statistics"""
        status_counts = {"running": 0, "completed": 0, "failed": 0, "pending": 0}
        for job in self.jobs.values():
            status_counts[job.status.value] += 1
        
        return {
            "total_jobs": len(self.jobs),
            "running": status_counts["running"],
            "completed": status_counts["completed"],
            "failed": status_counts["failed"],
            "total_papers": await self.get_paper_count()
        }


async def main():
    """Main entry point"""
    print("╔══════════════════════════════════════════════════════╗")
    print("║     ZNAYKA TEMPORAL ORCHESTRATOR                     ║")
    print("║     Crawler Completion Tracker                       ║")
    print("╚══════════════════════════════════════════════════════╝")
    
    async with ZnaykaOrchestrator() as orchestrator:
        # Start all crawlers
        await orchestrator.start_all_crawlers(limit=50)
        
        # Monitor progress
        await orchestrator.monitor_progress(check_interval=30, max_checks=60)
        
        # Export results
        await orchestrator.export_results()
        
        # Final summary
        print("\n✅ All tasks completed!")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⏹️  Stopped by user")
